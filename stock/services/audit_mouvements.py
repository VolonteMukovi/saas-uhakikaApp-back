"""
Audit des mouvements (page Paramètres → Audit) : tout ce qui mérite l'attention d'un
responsable, avec une explication claire pour chaque catégorie.

Sources : annulations, modifications et suppressions journalisées ; pertes et sorties non
commerciales ; manquants d'inventaire ; ventes gratuites ou sous le coût ; écarts de caisse ;
sorties d'argent manuelles. Lecture seule, filtrée par entreprise / succursale et période.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Prefetch, Q
from django.utils import timezone

from caisse.models import EcartCaisse, MouvementCaisse
from stock.models import (
    AnnulationMouvement,
    InventaireSession,
    LigneSortie,
    LigneSortieLot,
    LogSuppression,
    ModificationMouvement,
    Sortie,
)

GRAVITE_HAUTE = 'HAUTE'
GRAVITE_MOYENNE = 'MOYENNE'
GRAVITE_FAIBLE = 'FAIBLE'
LIMITE_EVENEMENTS = 1000

CATEGORIES = [
    {
        'code': 'SUPPRESSION',
        'libelle': 'Ventes supprimées',
        'gravite': GRAVITE_HAUTE,
        'explication': (
            "Une vente a été supprimée : ses articles sont revenus en stock et son encaissement a été "
            "contre-passé. Vérifiez que la vente n'avait pas réellement eu lieu (risque de vente "
            "non déclarée et d'argent conservé hors caisse)."
        ),
    },
    {
        'code': 'ANNULATION',
        'libelle': 'Mouvements annulés',
        'gravite': GRAVITE_MOYENNE,
        'explication': (
            "Une entrée ou une sortie a été annulée : stock et caisse ont été remis dans leur état "
            "antérieur. Une annulation est normale pour corriger une erreur ; des annulations "
            "répétées, tardives ou portant sur des ventes encaissées doivent être justifiées."
        ),
    },
    {
        'code': 'MODIFICATION',
        'libelle': 'Mouvements modifiés',
        'gravite': GRAVITE_MOYENNE,
        'explication': (
            "Une vente ou un approvisionnement a été modifié après son enregistrement. Les "
            "modifications sensibles (montant encaissé réduit, changement de client ou de type de "
            "vente, quantité ou prix d'achat modifié) sont signalées en priorité."
        ),
    },
    {
        'code': 'PERTE',
        'libelle': 'Pertes et sorties non commerciales',
        'gravite': GRAVITE_HAUTE,
        'explication': (
            "Marchandise sortie du stock sans vente (vol, perte, produit périmé, endommagé ou "
            "défectueux, cadeau, échantillon…). Elle ne rapporte rien : sa valeur au prix d'achat "
            "est une perte. Un volume élevé ou répété peut masquer des ventes non déclarées."
        ),
    },
    {
        'code': 'MANQUANT_INVENTAIRE',
        'libelle': "Manquants d'inventaire",
        'gravite': GRAVITE_HAUTE,
        'explication': (
            "L'inventaire physique a compté moins d'articles que le stock théorique : la "
            "différence a été retirée du stock. Un manquant sans explication peut révéler un vol "
            "ou des sorties non enregistrées."
        ),
    },
    {
        'code': 'VENTE_SOUS_COUT',
        'libelle': 'Ventes gratuites ou sous le coût',
        'gravite': GRAVITE_MOYENNE,
        'explication': (
            "Vente à un prix inférieur au prix d'achat, ou gratuite, autorisée par un "
            "administrateur avec un motif. À contrôler : remises excessives ou ventes de complaisance."
        ),
    },
    {
        'code': 'ECART_CAISSE',
        'libelle': 'Écarts de caisse',
        'gravite': GRAVITE_HAUTE,
        'explication': (
            "À la clôture, l'argent compté ne correspondait pas au solde théorique de la caisse. "
            "Un manque (perte) est le signal le plus sensible ; un surplus peut révéler une vente "
            "encaissée sans être enregistrée."
        ),
    },
    {
        'code': 'RETRAIT_CAISSE',
        'libelle': "Sorties d'argent manuelles",
        'gravite': GRAVITE_FAIBLE,
        'explication': (
            "Argent retiré de la caisse hors vente ou approvisionnement (dépense, retrait manuel). "
            "Chaque retrait doit être justifié par une pièce."
        ),
    },
]
CATEGORIES_PAR_CODE = {c['code']: c for c in CATEGORIES}
MOTS_VOL_PERTE = ('vol', 'vole', 'volee', 'perte', 'perdu', 'disparu')


def _d(value) -> Decimal:
    return Decimal(str(value or 0))


def _fmt(value) -> str:
    texte = f'{_d(value).quantize(Decimal("0.01")):f}'
    return texte


def _qte(value) -> str:
    texte = f'{_d(value).normalize():f}'
    return texte.rstrip('0').rstrip('.') if '.' in texte else texte


def _nom(user) -> str:
    if user is None:
        return ''
    return (user.get_full_name() or '').strip() or user.username


def _sans_accents(texte: str) -> str:
    import unicodedata

    texte = unicodedata.normalize('NFKD', (texte or '').lower())
    return ''.join(c for c in texte if not unicodedata.combining(c))


def periode_par_defaut(date_debut: date | None, date_fin: date | None) -> tuple[date, date]:
    fin = date_fin or timezone.localdate()
    debut = date_debut or (fin - timedelta(days=30))
    return debut, fin


def _evenement(code, *, cle, date_evenement, titre, description='', details=None, gravite=None,
               reference=None, utilisateur='', montants=None) -> dict:
    return {
        'id': f'{code}-{cle}',
        'categorie': code,
        'gravite': gravite or CATEGORIES_PAR_CODE[code]['gravite'],
        'date': date_evenement.isoformat() if date_evenement else None,
        'titre': titre,
        'description': description,
        'details': details or [],
        'reference': reference,
        'utilisateur': utilisateur,
        'montants': {k: _fmt(v) for k, v in (montants or {}).items() if _d(v) != 0},
    }


def _cout_sortie(sortie: Sortie) -> tuple[dict[str, Decimal], list[str]]:
    """Valeur au prix d'achat des articles sortis (par devise du lot) et détail par article."""
    couts: dict[str, Decimal] = defaultdict(Decimal)
    details = []
    for ligne in sortie.lignes.all():
        cout_ligne: dict[str, Decimal] = defaultdict(Decimal)
        for trace in ligne.lots_utilises.all():
            lot = trace.lot_entree
            devise = lot.devise.sigle if lot.devise_id else ''
            cout_ligne[devise] += _d(trace.quantite) * _d(lot.prix_achat_unitaire_base or lot.prix_unitaire)
        for devise, montant in cout_ligne.items():
            couts[devise] += montant
        nom = ligne.article.nom_commercial or ligne.article.nom_scientifique
        valeur = ', '.join(f'{_fmt(m)} {dv}' for dv, m in cout_ligne.items()) or '—'
        details.append(f'{nom} : {_qte(ligne.quantite)} unité(s), valeur d\'achat {valeur}')
    return couts, details


def construire_audit(
    *,
    entreprise_id: int,
    succursale_id: int | None,
    date_debut: date | None = None,
    date_fin: date | None = None,
    categorie: str | None = None,
    gravite: str | None = None,
) -> dict:
    debut, fin = periode_par_defaut(date_debut, date_fin)

    def periode(qs, champ):
        return qs.filter(**{f'{champ}__date__gte': debut, f'{champ}__date__lte': fin})

    def agence(qs, champ='succursale_id'):
        return qs.filter(**{champ: succursale_id}) if succursale_id is not None else qs

    evenements: list[dict] = []

    # --- Suppressions (journal historique des ventes supprimées) ---------------------------
    suppressions: dict[int, list[LogSuppression]] = defaultdict(list)
    for log in agence(periode(LogSuppression.objects.filter(entreprise_id=entreprise_id), 'date_suppression')):
        suppressions[log.sortie_numero].append(log)
    for numero, logs in suppressions.items():
        montants: dict[str, Decimal] = defaultdict(Decimal)
        for log in logs:
            montants[log.devise_sigle] += _d(log.quantite) * _d(log.prix_unitaire)
        premier = logs[0]
        evenements.append(_evenement(
            'SUPPRESSION', cle=numero, date_evenement=premier.date_suppression,
            titre=f'Vente #{numero} supprimée',
            description=(
                'Toute la vente a été supprimée.' if premier.motif == LogSuppression.MOTIF_SORTIE
                else 'Des articles ont été retirés de la vente.'
            ),
            details=[
                f'{log.article_nom} : {_qte(log.quantite)} × {_fmt(log.prix_unitaire)} {log.devise_sigle}'
                for log in logs
            ],
            reference={'type': 'SORTIE', 'id': numero},
            utilisateur=premier.utilisateur_nom,
            montants=montants,
        ))

    # --- Annulations ---------------------------------------------------------------------
    for ann in agence(periode(AnnulationMouvement.objects.filter(entreprise_id=entreprise_id), 'date_annulation')):
        if ann.type_mouvement == AnnulationMouvement.TYPE_SORTIE and ann.reference_id in suppressions:
            continue  # suppression de vente : déjà présentée dans « Ventes supprimées »
        montants: dict[str, Decimal] = defaultdict(Decimal)
        for impact in ann.impact_caisse or []:
            montants[impact.get('devise', '')] += _d(impact.get('montant'))
        details = [
            f"{'+' if i.get('sens') == 'RESTAURATION' else '−'}{_qte(i.get('quantite'))} en stock : {i.get('article')}"
            for i in ann.impact_stock or []
        ] + [
            f"Contre-écriture de caisse : {'sortie' if i.get('type_annulation') == 'SORTIE' else 'entrée'} "
            f"de {_fmt(i.get('montant'))} {i.get('devise', '')}"
            for i in ann.impact_caisse or []
        ]
        description = f"Motif d'origine : {ann.motif_origine or '—'}."
        if ann.motif_annulation:
            description += f" Raison de l'annulation : {ann.motif_annulation}."
        else:
            description += " Aucune raison d'annulation saisie."
        evenements.append(_evenement(
            'ANNULATION', cle=ann.pk, date_evenement=ann.date_annulation,
            titre=f'{ann.reference_libelle} annulé(e)',
            description=description,
            details=details,
            gravite=GRAVITE_HAUTE if (ann.impact_caisse and ann.nature == AnnulationMouvement.NATURE_VENTE)
            or not ann.motif_annulation else GRAVITE_MOYENNE,
            reference={'type': ann.type_mouvement, 'id': ann.reference_id},
            utilisateur=ann.annule_par_nom,
            montants=montants,
        ))

    # --- Modifications -------------------------------------------------------------------
    for modif in agence(periode(ModificationMouvement.objects.filter(entreprise_id=entreprise_id), 'date_modification')):
        details = list(modif.changements or [])
        for impact in modif.impact_caisse or []:
            nature = {'AJUSTEMENT': "Écriture d'ajustement", 'CORRECTION': 'Encaissement corrigé',
                      'ENCAISSEMENT': 'Encaissement'}.get(impact.get('nature'), 'Caisse')
            avant = f" (avant : {_fmt(impact['montant_avant'])})" if impact.get('montant_avant') else ''
            details.append(
                f"{nature} : {'entrée' if impact.get('type') == 'ENTREE' else 'sortie'} de "
                f"{_fmt(impact.get('montant'))} {impact.get('devise', '')}{avant}"
            )
        evenements.append(_evenement(
            'MODIFICATION', cle=modif.pk, date_evenement=modif.date_modification,
            titre=f'{modif.reference_libelle} modifié(e)',
            description='Modification sensible.' if modif.sensible else 'Modification courante.',
            details=details,
            gravite=GRAVITE_HAUTE if modif.sensible else GRAVITE_FAIBLE,
            reference={'type': modif.type_mouvement, 'id': modif.reference_id},
            utilisateur=modif.utilisateur_nom,
        ))

    # --- Pertes / sorties non commerciales et manquants d'inventaire --------------------
    ajustements = set(
        InventaireSession.objects.filter(entreprise_id=entreprise_id)
        .exclude(sortie_ajustement=None).values_list('sortie_ajustement_id', flat=True)
    )
    lots = LigneSortieLot.objects.select_related('lot_entree__devise')
    sorties_nc = agence(periode(
        Sortie.objects.filter(entreprise_id=entreprise_id, est_commerciale=False), 'date_creation',
    )).prefetch_related(
        Prefetch('lignes', queryset=LigneSortie.objects.select_related('article').prefetch_related(
            Prefetch('lots_utilises', queryset=lots),
        )),
    ).select_related('client', 'cree_par')
    for sortie in sorties_nc:
        couts, details = _cout_sortie(sortie)
        if sortie.pk in ajustements:
            evenements.append(_evenement(
                'MANQUANT_INVENTAIRE', cle=sortie.pk, date_evenement=sortie.date_creation,
                titre=f'Manquant constaté — sortie #{sortie.pk}',
                description=sortie.motif,
                details=details,
                reference={'type': 'SORTIE', 'id': sortie.pk},
                utilisateur=_nom(sortie.cree_par),
                montants=couts,
            ))
            continue
        motif = _sans_accents(sortie.motif)
        vol_perte = any(mot in motif.replace('/', ' ').split() for mot in MOTS_VOL_PERTE)
        evenements.append(_evenement(
            'PERTE', cle=sortie.pk, date_evenement=sortie.date_creation,
            titre=f'{sortie.motif or "Sortie non commerciale"} — sortie #{sortie.pk}',
            description=(
                'Marchandise sortie sans vente' + (f' (client : {sortie.client.nom})' if sortie.client_id else '') + '.'
            ),
            details=details,
            gravite=GRAVITE_HAUTE if vol_perte else GRAVITE_MOYENNE,
            reference={'type': 'SORTIE', 'id': sortie.pk},
            utilisateur=_nom(sortie.cree_par),
            montants=couts,
        ))

    # --- Ventes gratuites ou sous le coût -------------------------------------------------
    lignes_exception = agence(periode(
        LigneSortie.objects.filter(sortie__entreprise_id=entreprise_id, sortie__est_commerciale=True)
        .exclude(motif_prix_exception=''),
        'sortie__date_creation',
    ), 'sortie__succursale_id').select_related('article', 'devise', 'sortie__cree_par').prefetch_related(
        Prefetch('lots_utilises', queryset=lots),
    )
    for ligne in lignes_exception:
        montant = _d(ligne.get_montant_total())
        cout = sum((_d(t.quantite) * _d(t.prix_achat) for t in ligne.lots_utilises.all()), Decimal('0'))
        devise = ligne.devise.sigle if ligne.devise_id else ''
        nom = ligne.article.nom_commercial or ligne.article.nom_scientifique
        evenements.append(_evenement(
            'VENTE_SOUS_COUT', cle=ligne.pk, date_evenement=ligne.sortie.date_creation,
            titre=f"{'Vente gratuite' if montant <= 0 else 'Vente sous le coût'} — vente #{ligne.sortie_id}",
            description=f'Motif donné : {ligne.motif_prix_exception}',
            details=[
                f'{nom} : {_qte(ligne.quantite)} unité(s) vendues {_fmt(montant)} {devise} '
                f"pour un coût d'achat de {_fmt(cout)} {devise}",
            ],
            gravite=GRAVITE_HAUTE if montant <= 0 else GRAVITE_MOYENNE,
            reference={'type': 'SORTIE', 'id': ligne.sortie_id},
            utilisateur=_nom(ligne.sortie.cree_par),
            montants={devise: max(cout - montant, Decimal('0'))},
        ))

    # --- Écarts de caisse -----------------------------------------------------------------
    ecarts = periode(
        EcartCaisse.objects.filter(session__entreprise_id=entreprise_id).select_related(
            'session__devise', 'session__type_caisse', 'declare_par',
        ),
        'cree_le',
    )
    if succursale_id is not None:
        ecarts = ecarts.filter(session__succursale_id=succursale_id)
    for ecart in ecarts:
        devise = ecart.session.devise.sigle if ecart.session.devise_id else ''
        perte = ecart.type_ecart == 'PERTE'
        evenements.append(_evenement(
            'ECART_CAISSE', cle=ecart.pk, date_evenement=ecart.cree_le,
            titre=f"{'Manque' if perte else 'Surplus'} de caisse — session {ecart.session.numero}",
            description=f'Écart {ecart.get_statut_display().lower()}. {ecart.commentaire or ""}'.strip(),
            details=[
                f'Caisse : {ecart.session.type_caisse.libelle_affiche}',
                f"Solde théorique : {_fmt(ecart.session.solde_theorique)} {devise}, "
                f"compté : {_fmt(ecart.session.montant_physique)} {devise}",
            ],
            gravite=GRAVITE_HAUTE if perte else GRAVITE_MOYENNE,
            reference={'type': 'SESSION_CAISSE', 'id': ecart.session_id},
            utilisateur=(ecart.declare_par.get_full_name() or ecart.declare_par.username) if ecart.declare_par else '',
            montants={devise: ecart.montant},
        ))

    # --- Sorties d'argent manuelles ---------------------------------------------------------
    retraits = agence(periode(
        MouvementCaisse.objects.filter(
            entreprise_id=entreprise_id, type='SORTIE', sortie__isnull=True, entree__isnull=True,
            montant__gt=0,
        ).filter(Q(categorie__in=('SORTIE_MANUELLE', 'DEPENSE')) | Q(categorie='AUTRE', content_type__isnull=True)),
        'date',
    )).select_related('devise', 'type_caisse', 'utilisateur')
    for mv in retraits:
        devise = mv.devise.sigle if mv.devise_id else ''
        evenements.append(_evenement(
            'RETRAIT_CAISSE', cle=mv.pk, date_evenement=mv.date,
            titre=f"{mv.get_categorie_display()} — {_fmt(mv.montant)} {devise}",
            description=mv.motif or 'Aucun motif saisi.',
            details=[f"Caisse : {mv.type_caisse.libelle_affiche if mv.type_caisse else '—'}"]
            + ([f'Pièce : {mv.reference_piece}'] if mv.reference_piece else ['Aucune pièce justificative référencée']),
            gravite=GRAVITE_MOYENNE if not mv.motif or not mv.reference_piece else GRAVITE_FAIBLE,
            reference={'type': 'MOUVEMENT_CAISSE', 'id': mv.pk},
            utilisateur=(mv.utilisateur.get_full_name() or mv.utilisateur.username) if mv.utilisateur else '',
            montants={devise: mv.montant},
        ))

    # --- Synthèse et filtres ------------------------------------------------------------------
    synthese = []
    for cat in CATEGORIES:
        liste = [e for e in evenements if e['categorie'] == cat['code']]
        montants: dict[str, Decimal] = defaultdict(Decimal)
        for e in liste:
            for devise, montant in e['montants'].items():
                montants[devise] += _d(montant)
        synthese.append({
            **cat,
            'nombre': len(liste),
            'nombre_graves': sum(1 for e in liste if e['gravite'] == GRAVITE_HAUTE),
            'montants': {k: _fmt(v) for k, v in montants.items() if v},
        })

    if categorie:
        evenements = [e for e in evenements if e['categorie'] == categorie]
    if gravite:
        evenements = [e for e in evenements if e['gravite'] == gravite]
    evenements.sort(key=lambda e: e['date'] or '', reverse=True)
    return {
        'periode': {'date_debut': debut.isoformat(), 'date_fin': fin.isoformat()},
        'categories': synthese,
        'total': len(evenements),
        'tronque': len(evenements) > LIMITE_EVENEMENTS,
        'evenements': evenements[:LIMITE_EVENEMENTS],
    }
