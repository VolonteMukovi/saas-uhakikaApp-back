"""
Service métier : réquisitions d'approvisionnement (document de travail indépendant).
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Any, Iterable

from django.db import transaction
from django.db.models import F, Max, Q, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from stock.models import (
    Article,
    LigneEntree,
    Requisition,
    RequisitionHistorique,
    RequisitionLigne,
    Stock,
)
from stock.services.stock_stats import list_articles_expiration_dans_fenetre

PRIX_PLACEHOLDER = '.....'
SOURCES_SUGGESTION = frozenset({
    'rupture',
    'alerte',
    'expiration_30',
    'expiration_90',
    'tous',
})


def is_prix_placeholder(value) -> bool:
    if value is None:
        return True
    raw = str(value).strip()
    if raw == '':
        return True
    cleaned = raw.replace('…', '.').replace('·', '.')
    if set(cleaned) <= {'.'} and len(cleaned) >= 3:
        return True
    return cleaned.lower() in ('n/a', 'na', 'null', 'none')


def _dec(value, default='0') -> Decimal:
    try:
        return Decimal(str(value if value is not None else default))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _fmt_qty(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(_dec(value).quantize(Decimal('0.00001'), rounding=ROUND_DOWN))


def _fmt_price(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(_dec(value).quantize(Decimal('0.00001'), rounding=ROUND_DOWN))


def assert_requisition_editable(requisition: Requisition) -> None:
    if requisition.archived:
        raise ValidationError({'detail': 'Cette réquisition est archivée et ne peut plus être modifiée.'})
    if requisition.statut not in Requisition.STATUTS_MODIFIABLES:
        raise ValidationError({
            'detail': (
                f'La réquisition {requisition.get_statut_display().lower()} '
                'ne peut plus être modifiée.'
            ),
        })


def log_historique(
    requisition: Requisition,
    *,
    action: str,
    utilisateur=None,
    detail: str = '',
    ancien_statut: str = '',
    nouveau_statut: str = '',
    metadata: dict | None = None,
) -> RequisitionHistorique:
    return RequisitionHistorique.objects.create(
        requisition=requisition,
        action=action,
        detail=detail or '',
        ancien_statut=ancien_statut or '',
        nouveau_statut=nouveau_statut or '',
        utilisateur=utilisateur,
        metadata=metadata or {},
    )


def generate_numero(entreprise_id: int) -> str:
    year = timezone.now().year
    prefix = f'REQ-{year}-'
    last = (
        Requisition.objects.filter(entreprise_id=entreprise_id, numero__startswith=prefix)
        .order_by('-numero')
        .values_list('numero', flat=True)
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(str(last).rsplit('-', 1)[-1]) + 1
        except (TypeError, ValueError):
            seq = Requisition.objects.filter(entreprise_id=entreprise_id).count() + 1
    return f'{prefix}{seq:05d}'


def dernier_prix_achat(article: Article | None) -> Decimal | None:
    """Dernier PU d'achat ; None si jamais approvisionné."""
    if article is None:
        return None
    last = (
        LigneEntree.objects.filter(article=article)
        .select_related('entree')
        .order_by('-entree__date_op', '-date_entree', '-id')
        .first()
    )
    if last is None or last.prix_unitaire is None:
        return None
    prix = _dec(last.prix_unitaire)
    return prix if prix > 0 else None


def stock_snapshot(article: Article) -> tuple[str, Decimal, Decimal]:
    """Retourne (statut_stock, qte, seuil)."""
    row = getattr(article, 'stock', None)
    if row is None:
        row = Stock.objects.filter(article=article).first()
    qte = _dec(getattr(row, 'Qte', 0) if row else 0)
    seuil = _dec(getattr(row, 'seuilAlert', 0) if row else 0)
    if qte <= 0:
        statut = 'RUPTURE'
    elif seuil > 0 and qte <= seuil:
        statut = 'ALERTE'
    else:
        statut = 'NORMAL'
    return statut, qte, seuil


def quantite_suggeree(qte: Decimal, seuil: Decimal) -> Decimal:
    if seuil > 0 and qte < seuil:
        return seuil - qte
    if qte <= 0 and seuil > 0:
        return seuil
    if qte <= 0:
        return Decimal('1')
    return Decimal('1')


def designation_article(article: Article) -> str:
    nom = (article.nom_commercial or '').strip() or (article.nom_scientifique or '').strip()
    return nom or article.article_id


def resume_requisition(requisition: Requisition) -> dict[str, Any]:
    lignes = requisition.lignes.all()
    total_lignes = lignes.count()
    agg = lignes.aggregate(qte=Sum('quantite'))
    montant = Decimal('0')
    prix_manquants = 0
    for ligne in lignes:
        if ligne.prix_estime is None:
            prix_manquants += 1
        else:
            montant += (ligne.quantite or Decimal('0')) * ligne.prix_estime
    return {
        'nombre_lignes': total_lignes,
        'quantite_totale': _fmt_qty(agg['qte'] or Decimal('0')),
        'montant_estime': _fmt_price(montant),
        'montant_estime_complet': prix_manquants == 0 and total_lignes > 0,
        'lignes_prix_manquants': prix_manquants,
    }


def create_requisition(
    *,
    entreprise_id: int,
    succursale_id: int | None,
    titre: str,
    cree_par=None,
    description: str = '',
    observations: str = '',
    commentaires: str = '',
    priorite: str = Requisition.PRIORITE_NORMALE,
    avec_suggestions: bool = False,
    sources: Iterable[str] | None = None,
) -> Requisition:
    with transaction.atomic():
        req = Requisition.objects.create(
            numero=generate_numero(entreprise_id),
            titre=titre.strip() or 'Nouvelle réquisition',
            description=description or '',
            observations=observations or '',
            commentaires=commentaires or '',
            priorite=priorite or Requisition.PRIORITE_NORMALE,
            statut=Requisition.STATUT_BROUILLON,
            entreprise_id=entreprise_id,
            succursale_id=succursale_id,
            cree_par=cree_par,
        )
        log_historique(
            req,
            action='CREATION',
            utilisateur=cree_par,
            detail='Réquisition créée',
            nouveau_statut=req.statut,
        )
        if avec_suggestions:
            apply_suggestions(
                req,
                sources=list(sources or ['rupture', 'alerte']),
                utilisateur=cree_par,
                replace=False,
            )
    return req


def _next_ordre(requisition: Requisition) -> int:
    current = requisition.lignes.aggregate(m=Max('ordre'))['m']
    return int(current or 0) + 1


def build_ligne_from_article(
    requisition: Requisition,
    article: Article,
    *,
    quantite: Decimal | None = None,
    ordre: int | None = None,
    remarque: str = '',
) -> RequisitionLigne:
    statut, qte, seuil = stock_snapshot(article)
    prix = dernier_prix_achat(article)
    qty = quantite if quantite is not None else quantite_suggeree(qte, seuil)
    unite = ''
    if getattr(article, 'unite', None):
        unite = article.unite.libelle or ''
    return RequisitionLigne(
        requisition=requisition,
        type_ligne=RequisitionLigne.TYPE_ARTICLE,
        article=article,
        designation=designation_article(article),
        quantite=_dec(qty),
        unite=unite,
        prix_estime=prix,
        prix_source=(
            RequisitionLigne.PRIX_SOURCE_DERNIER_ACHAT
            if prix is not None
            else RequisitionLigne.PRIX_SOURCE_MANUEL
        ),
        remarque=remarque or '',
        ordre=ordre if ordre is not None else _next_ordre(requisition),
        statut_stock=statut,
        stock_actuel=qte,
        seuil_alerte=seuil,
    )


def add_ligne_article(
    requisition: Requisition,
    article: Article,
    *,
    quantite=None,
    unite: str | None = None,
    prix_estime=None,
    remarque: str = '',
    utilisateur=None,
) -> RequisitionLigne:
    assert_requisition_editable(requisition)
    if requisition.lignes.filter(article=article, type_ligne=RequisitionLigne.TYPE_ARTICLE).exists():
        raise ValidationError({'article_id': 'Cet article est déjà présent sur la réquisition.'})

    ligne = build_ligne_from_article(
        requisition,
        article,
        quantite=_dec(quantite) if quantite is not None else None,
        remarque=remarque,
    )
    if unite is not None and str(unite).strip():
        ligne.unite = str(unite).strip()
    if prix_estime is not None and not is_prix_placeholder(prix_estime):
        ligne.prix_estime = _dec(prix_estime)
        ligne.prix_source = RequisitionLigne.PRIX_SOURCE_MANUEL
    elif is_prix_placeholder(prix_estime) and prix_estime is not None:
        # force placeholder explicit
        ligne.prix_estime = None
        ligne.prix_source = RequisitionLigne.PRIX_SOURCE_MANUEL
    ligne.save()
    log_historique(
        requisition,
        action='AJOUT_LIGNE',
        utilisateur=utilisateur,
        detail=f'Ajout article {ligne.designation}',
        metadata={'ligne_id': ligne.pk, 'article_id': article.article_id},
    )
    return ligne


def add_ligne_libre(
    requisition: Requisition,
    *,
    designation: str,
    quantite,
    unite: str = '',
    prix_estime=None,
    remarque: str = '',
    utilisateur=None,
) -> RequisitionLigne:
    assert_requisition_editable(requisition)
    nom = (designation or '').strip()
    if not nom:
        raise ValidationError({'designation': 'Le nom de la ligne libre est obligatoire.'})
    qty = _dec(quantite)
    if qty <= 0:
        raise ValidationError({'quantite': 'La quantité doit être strictement positive.'})

    prix = None
    if not is_prix_placeholder(prix_estime):
        prix = _dec(prix_estime)

    ligne = RequisitionLigne.objects.create(
        requisition=requisition,
        type_ligne=RequisitionLigne.TYPE_LIBRE,
        article=None,
        designation=nom,
        quantite=qty,
        unite=(unite or '').strip(),
        prix_estime=prix,
        prix_source=RequisitionLigne.PRIX_SOURCE_MANUEL,
        remarque=remarque or '',
        ordre=_next_ordre(requisition),
    )
    log_historique(
        requisition,
        action='AJOUT_LIGNE_LIBRE',
        utilisateur=utilisateur,
        detail=f'Ajout ligne libre « {nom} »',
        metadata={'ligne_id': ligne.pk},
    )
    return ligne


def update_ligne(
    ligne: RequisitionLigne,
    *,
    data: dict,
    utilisateur=None,
) -> RequisitionLigne:
    assert_requisition_editable(ligne.requisition)
    changed = []

    if 'designation' in data and data['designation'] is not None:
        nom = str(data['designation']).strip()
        if not nom:
            raise ValidationError({'designation': 'La désignation ne peut pas être vide.'})
        if nom != ligne.designation:
            ligne.designation = nom
            changed.append('designation')

    if 'quantite' in data and data['quantite'] is not None:
        qty = _dec(data['quantite'])
        if qty <= 0:
            raise ValidationError({'quantite': 'La quantité doit être strictement positive.'})
        if qty != ligne.quantite:
            ligne.quantite = qty
            changed.append('quantite')

    if 'unite' in data and data['unite'] is not None:
        u = str(data['unite']).strip()
        if u != ligne.unite:
            ligne.unite = u
            changed.append('unite')

    if 'remarque' in data and data['remarque'] is not None:
        r = str(data['remarque'])
        if r != ligne.remarque:
            ligne.remarque = r
            changed.append('remarque')

    if 'prix_estime' in data:
        raw = data['prix_estime']
        if is_prix_placeholder(raw):
            if ligne.prix_estime is not None:
                ligne.prix_estime = None
                ligne.prix_source = RequisitionLigne.PRIX_SOURCE_MANUEL
                changed.append('prix_estime')
        else:
            prix = _dec(raw)
            if prix < 0:
                raise ValidationError({'prix_estime': 'Le prix estimé ne peut pas être négatif.'})
            if ligne.prix_estime != prix:
                ligne.prix_estime = prix
                ligne.prix_source = RequisitionLigne.PRIX_SOURCE_MANUEL
                changed.append('prix_estime')

    if 'ordre' in data and data['ordre'] is not None:
        ordre = int(data['ordre'])
        if ordre != ligne.ordre:
            ligne.ordre = ordre
            changed.append('ordre')

    if changed:
        ligne.save()
        log_historique(
            ligne.requisition,
            action='MODIF_LIGNE',
            utilisateur=utilisateur,
            detail=f'Ligne #{ligne.pk} modifiée ({", ".join(changed)})',
            metadata={'ligne_id': ligne.pk, 'champs': changed},
        )
    return ligne


def delete_ligne(ligne: RequisitionLigne, *, utilisateur=None) -> None:
    assert_requisition_editable(ligne.requisition)
    req = ligne.requisition
    pk = ligne.pk
    designation = ligne.designation
    ligne.delete()
    log_historique(
        req,
        action='SUPPRESSION_LIGNE',
        utilisateur=utilisateur,
        detail=f'Suppression ligne « {designation} »',
        metadata={'ligne_id': pk},
    )


def dupliquer_ligne(ligne: RequisitionLigne, *, utilisateur=None) -> RequisitionLigne:
    assert_requisition_editable(ligne.requisition)
    clone = RequisitionLigne.objects.create(
        requisition=ligne.requisition,
        type_ligne=ligne.type_ligne,
        article=ligne.article,
        designation=f'{ligne.designation} (copie)',
        quantite=ligne.quantite,
        unite=ligne.unite,
        prix_estime=ligne.prix_estime,
        prix_source=ligne.prix_source,
        remarque=ligne.remarque,
        ordre=_next_ordre(ligne.requisition),
        statut_stock=ligne.statut_stock,
        stock_actuel=ligne.stock_actuel,
        seuil_alerte=ligne.seuil_alerte,
    )
    log_historique(
        ligne.requisition,
        action='DUPLICATION_LIGNE',
        utilisateur=utilisateur,
        detail=f'Duplication ligne #{ligne.pk}',
        metadata={'source_id': ligne.pk, 'ligne_id': clone.pk},
    )
    return clone


def reorder_lignes(
    requisition: Requisition,
    ordre_ids: list[int],
    *,
    utilisateur=None,
) -> list[RequisitionLigne]:
    assert_requisition_editable(requisition)
    lignes = {l.pk: l for l in requisition.lignes.all()}
    missing = [i for i in ordre_ids if i not in lignes]
    if missing:
        raise ValidationError({'ordre': f'Lignes introuvables : {missing}'})
    with transaction.atomic():
        for idx, ligne_id in enumerate(ordre_ids, start=1):
            ligne = lignes[ligne_id]
            if ligne.ordre != idx:
                ligne.ordre = idx
                ligne.save(update_fields=['ordre'])
        log_historique(
            requisition,
            action='REORDONNANCEMENT',
            utilisateur=utilisateur,
            detail='Ordre des lignes mis à jour',
            metadata={'ordre': ordre_ids},
        )
    return list(requisition.lignes.order_by('ordre', 'id'))


def _articles_by_source(
    *,
    entreprise_id: int,
    succursale_id: int | None,
    sources: list[str],
) -> dict[str, Article]:
    sources_set = {s.strip().lower() for s in sources if s}
    invalid = sources_set - SOURCES_SUGGESTION
    if invalid:
        raise ValidationError({
            'sources': f'Sources invalides : {sorted(invalid)}. '
            f'Valides : {sorted(SOURCES_SUGGESTION)}',
        })
    if not sources_set:
        sources_set = {'rupture', 'alerte'}

    qs = Article.objects.filter(entreprise_id=entreprise_id).select_related('unite', 'stock')
    if succursale_id is not None:
        qs = qs.filter(succursale_id=succursale_id)

    selected: dict[str, Article] = {}

    if 'tous' in sources_set:
        for art in qs:
            selected[art.article_id] = art
        return selected

    stocks = Stock.objects.filter(article__entreprise_id=entreprise_id)
    if succursale_id is not None:
        stocks = stocks.filter(article__succursale_id=succursale_id)

    if 'rupture' in sources_set:
        for stock in stocks.filter(Qte__lte=0).select_related('article', 'article__unite'):
            selected[stock.article_id] = stock.article
    if 'alerte' in sources_set:
        for stock in stocks.filter(Qte__gt=0, Qte__lte=F('seuilAlert')).select_related(
            'article', 'article__unite',
        ):
            selected[stock.article_id] = stock.article

    today = timezone.now().date()
    if 'expiration_30' in sources_set:
        for item in list_articles_expiration_dans_fenetre(
            entreprise_id=entreprise_id,
            succursale_id=succursale_id,
            date_fin_inclusive=today + timedelta(days=30),
            today=today,
            limit=500,
        ):
            art = Article.objects.filter(
                article_id=item['code'], entreprise_id=entreprise_id,
            ).select_related('unite', 'stock').first()
            if art:
                selected[art.article_id] = art
    if 'expiration_90' in sources_set:
        for item in list_articles_expiration_dans_fenetre(
            entreprise_id=entreprise_id,
            succursale_id=succursale_id,
            date_fin_inclusive=today + timedelta(days=90),
            today=today,
            limit=500,
        ):
            art = Article.objects.filter(
                article_id=item['code'], entreprise_id=entreprise_id,
            ).select_related('unite', 'stock').first()
            if art:
                selected[art.article_id] = art

    return selected


def preview_suggestions(
    *,
    entreprise_id: int,
    succursale_id: int | None,
    sources: list[str] | None = None,
) -> list[dict[str, Any]]:
    articles = _articles_by_source(
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        sources=list(sources or ['rupture', 'alerte']),
    )
    rows = []
    for art in articles.values():
        statut, qte, seuil = stock_snapshot(art)
        prix = dernier_prix_achat(art)
        qty = quantite_suggeree(qte, seuil)
        rows.append({
            'article_id': art.article_id,
            'designation': designation_article(art),
            'unite': art.unite.libelle if art.unite_id else '',
            'quantite_suggeree': _fmt_qty(qty),
            'stock_actuel': _fmt_qty(qte),
            'seuil_alerte': _fmt_qty(seuil),
            'statut_stock': statut,
            'prix_estime': _fmt_price(prix),
            'prix_estime_affiche': PRIX_PLACEHOLDER if prix is None else _fmt_price(prix),
            'prix_manquant': prix is None,
        })
    rows.sort(key=lambda r: (r['statut_stock'] != 'RUPTURE', r['designation'].lower()))
    return rows


def apply_suggestions(
    requisition: Requisition,
    *,
    sources: list[str],
    utilisateur=None,
    replace: bool = False,
) -> dict[str, Any]:
    assert_requisition_editable(requisition)
    articles = _articles_by_source(
        entreprise_id=requisition.entreprise_id,
        succursale_id=requisition.succursale_id,
        sources=sources,
    )
    added = 0
    skipped = 0
    with transaction.atomic():
        if replace:
            requisition.lignes.all().delete()
        existing = set(
            requisition.lignes.filter(
                type_ligne=RequisitionLigne.TYPE_ARTICLE,
                article_id__isnull=False,
            ).values_list('article_id', flat=True)
        )
        ordre = _next_ordre(requisition) if not replace else 1
        bulk = []
        for art in articles.values():
            if art.article_id in existing and not replace:
                skipped += 1
                continue
            ligne = build_ligne_from_article(requisition, art, ordre=ordre)
            bulk.append(ligne)
            ordre += 1
            added += 1
        if bulk:
            RequisitionLigne.objects.bulk_create(bulk)
        log_historique(
            requisition,
            action='SUGGESTIONS',
            utilisateur=utilisateur,
            detail=f'Suggestions appliquées ({", ".join(sources)}) : +{added}, ignorés {skipped}',
            metadata={'sources': sources, 'added': added, 'skipped': skipped, 'replace': replace},
        )
    return {'ajoutees': added, 'ignorees': skipped, 'total_lignes': requisition.lignes.count()}


def changer_statut(
    requisition: Requisition,
    *,
    nouveau_statut: str,
    utilisateur=None,
    motif: str = '',
    commentaires: str = '',
) -> Requisition:
    allowed = {c[0] for c in Requisition.STATUT_CHOICES}
    if nouveau_statut not in allowed:
        raise ValidationError({'statut': f'Statut inconnu : {nouveau_statut}'})

    transitions = {
        Requisition.STATUT_BROUILLON: {
            Requisition.STATUT_OUVERTE,
            Requisition.STATUT_EN_PREPARATION,
            Requisition.STATUT_EN_ATTENTE_VALIDATION,
            Requisition.STATUT_ANNULEE,
        },
        Requisition.STATUT_OUVERTE: {
            Requisition.STATUT_EN_PREPARATION,
            Requisition.STATUT_EN_ATTENTE_VALIDATION,
            Requisition.STATUT_ANNULEE,
            Requisition.STATUT_BROUILLON,
        },
        Requisition.STATUT_EN_PREPARATION: {
            Requisition.STATUT_EN_ATTENTE_VALIDATION,
            Requisition.STATUT_OUVERTE,
            Requisition.STATUT_ANNULEE,
        },
        Requisition.STATUT_EN_ATTENTE_VALIDATION: {
            Requisition.STATUT_VALIDEE,
            Requisition.STATUT_REJETEE,
            Requisition.STATUT_EN_PREPARATION,
            Requisition.STATUT_ANNULEE,
        },
        Requisition.STATUT_VALIDEE: {
            Requisition.STATUT_CLOTUREE,
            Requisition.STATUT_ANNULEE,
        },
        Requisition.STATUT_REJETEE: {
            Requisition.STATUT_BROUILLON,
            Requisition.STATUT_OUVERTE,
            Requisition.STATUT_EN_PREPARATION,
            Requisition.STATUT_ANNULEE,
        },
        Requisition.STATUT_ANNULEE: set(),
        Requisition.STATUT_CLOTUREE: set(),
    }
    actuel = requisition.statut
    if nouveau_statut == actuel:
        return requisition
    if nouveau_statut not in transitions.get(actuel, set()):
        raise ValidationError({
            'statut': (
                f'Transition interdite : {requisition.get_statut_display()} → '
                f'{dict(Requisition.STATUT_CHOICES).get(nouveau_statut, nouveau_statut)}.'
            ),
        })

    if nouveau_statut == Requisition.STATUT_VALIDEE and not requisition.lignes.exists():
        raise ValidationError({'detail': 'Impossible de valider une réquisition sans lignes.'})
    if nouveau_statut == Requisition.STATUT_REJETEE and not (motif or '').strip():
        raise ValidationError({'motif': 'Un motif de rejet est obligatoire.'})

    with transaction.atomic():
        ancien = requisition.statut
        requisition.statut = nouveau_statut
        if commentaires is not None and str(commentaires).strip():
            requisition.commentaires = str(commentaires).strip()
        if nouveau_statut == Requisition.STATUT_VALIDEE:
            requisition.valide_par = utilisateur
            requisition.date_validation = timezone.now()
            requisition.motif_rejet = ''
        elif nouveau_statut == Requisition.STATUT_REJETEE:
            requisition.rejete_par = utilisateur
            requisition.date_rejet = timezone.now()
            requisition.motif_rejet = motif.strip()
        elif nouveau_statut == Requisition.STATUT_CLOTUREE:
            requisition.date_cloture = timezone.now()
            requisition.archived = True
        elif nouveau_statut in (
            Requisition.STATUT_BROUILLON,
            Requisition.STATUT_OUVERTE,
            Requisition.STATUT_EN_PREPARATION,
        ):
            requisition.motif_rejet = ''
        requisition.save()
        log_historique(
            requisition,
            action='CHANGEMENT_STATUT',
            utilisateur=utilisateur,
            detail=motif or f'{ancien} → {nouveau_statut}',
            ancien_statut=ancien,
            nouveau_statut=nouveau_statut,
        )
    return requisition


def ligne_to_api_dict(ligne: RequisitionLigne) -> dict[str, Any]:
    montant = ligne.montant_ligne
    return {
        'id': ligne.pk,
        'type_ligne': ligne.type_ligne,
        'article_id': ligne.article_id,
        'designation': ligne.designation,
        'quantite': _fmt_qty(ligne.quantite),
        'unite': ligne.unite,
        'prix_estime': _fmt_price(ligne.prix_estime),
        'prix_estime_affiche': (
            PRIX_PLACEHOLDER if ligne.prix_estime is None else _fmt_price(ligne.prix_estime)
        ),
        'prix_manquant': ligne.prix_estime is None,
        'prix_source': ligne.prix_source,
        'montant_estime': _fmt_price(montant) if montant is not None else None,
        'montant_estime_affiche': (
            PRIX_PLACEHOLDER if montant is None else _fmt_price(montant)
        ),
        'remarque': ligne.remarque,
        'ordre': ligne.ordre,
        'statut_stock': ligne.statut_stock or None,
        'stock_actuel': _fmt_qty(ligne.stock_actuel),
        'seuil_alerte': _fmt_qty(ligne.seuil_alerte),
    }
