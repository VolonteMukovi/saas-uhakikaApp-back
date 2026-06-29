"""
Reçus de paiement dette — chargement données, PDF ticket (lignes monospace), URLs.
"""
from __future__ import annotations

import io
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.utils.translation import gettext as _
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import mm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from caisse.models import MouvementCaisse
from stock.models import DetteClient


def resolve_paiement_dette(paiement: MouvementCaisse) -> DetteClient | None:
    ct_dette = ContentType.objects.get_for_model(DetteClient)
    if paiement.content_type_id != ct_dette.id or not paiement.object_id:
        return None
    return (
        DetteClient.objects.filter(pk=paiement.object_id)
        .select_related('client', 'devise', 'sortie')
        .first()
    )


def fetch_grouped_mouvements(*, reference: str, tenant_id: int | None, branch_id: int | None):
    """Mouvements ENTREE liés à des dettes partageant la même reference_piece (paiement groupé)."""
    reference = (reference or '').strip()
    if not reference or tenant_id is None:
        return MouvementCaisse.objects.none()
    ct_dette = ContentType.objects.get_for_model(DetteClient)
    qs = (
        MouvementCaisse.objects.filter(
            reference_piece=reference,
            content_type=ct_dette,
            type='ENTREE',
            entreprise_id=tenant_id,
        )
        .select_related('devise', 'utilisateur')
        .prefetch_related('details__type_caisse')
        .order_by('date', 'id')
    )
    if branch_id is not None:
        qs = qs.filter(succursale_id=branch_id)
    return qs


def grouped_recu_lignes_from_mouvements(mouvements) -> list[dict]:
    """Construit les lignes dette pour le ticket groupé (ancien solde reconstitué)."""
    rows = []
    for mc in mouvements:
        dette = resolve_paiement_dette(mc)
        if not dette:
            continue
        montant = Decimal(str(mc.montant or 0))
        nouveau = Decimal(str(dette.solde_restant or 0))
        ancien = (montant + nouveau).quantize(Decimal('0.00001'))
        rows.append({
            'dette_id': dette.pk,
            'sortie_id': dette.sortie_id,
            'mouvement_caisse_id': mc.pk,
            'montant_applique': montant,
            'ancien_solde': ancien,
            'nouveau_solde': nouveau,
            'statut': dette.statut,
        })
    return rows


def ticket_lines_to_pdf_response(ticket_lines: list[str], filename: str) -> HttpResponse:
    """PDF ticket 58 mm à partir des lignes monospace (même rendu que facture-pos)."""
    POS_WIDTH = 58 * mm
    lm, rm, tm, bm = 1.2 * mm, 1.2 * mm, 2 * mm, 2 * mm
    content_width = POS_WIDTH - lm - rm
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    mono = ParagraphStyle(
        'MonoTicket',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=6.4,
        leading=7.1,
        alignment=TA_LEFT,
        wordWrap='CJK',
    )
    elements = []
    for raw in ticket_lines:
        txt = (raw or '').rstrip('\n')
        if txt.strip() == '':
            elements.append(Spacer(1, 0.6 * mm))
        else:
            safe = txt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace(' ', '&nbsp;')
            elements.append(Paragraph(safe, mono))

    main_height = sum(flow.wrap(content_width, 100000)[1] for flow in elements)
    POS_HEIGHT = main_height + tm + bm + 4.0 * mm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(POS_WIDTH, POS_HEIGHT),
        leftMargin=lm,
        rightMargin=rm,
        topMargin=tm,
        bottomMargin=bm,
        allowSplitting=0,
    )
    doc.build(elements)
    buffer.seek(0)
    return HttpResponse(
        buffer,
        content_type='application/pdf',
        headers={'Content-Disposition': f'inline; filename="{filename}"'},
    )


def recu_paiement_urls(request, paiement_id: int) -> dict:
    base = request.build_absolute_uri(f'/api/paiements-dettes/{paiement_id}/')
    return {
        'json_url': f'{base}recu-json/',
        'pdf_url': f'{base}recu-paiement/',
        'print_url': f'{base}recu-paiement-print/',
    }


def recu_groupe_urls(request, reference: str) -> dict:
    from urllib.parse import quote
    ref_q = quote(reference, safe='')
    base = request.build_absolute_uri('/api/paiements-dettes/recu-groupe/')
    return {
        'reference': reference,
        'json_url': f'{base}?reference={ref_q}',
        'pdf_url': f'{base}pdf/?reference={ref_q}',
        'print_url': request.build_absolute_uri('/api/paiements-dettes/recu-groupe-print/'),
    }


def pos_printer_check():
    """Retourne (ok, error_response_dict, status_code) si imprimante non configurée."""
    from django.conf import settings

    backend = str(getattr(settings, 'POS_PRINTER_BACKEND', 'serial') or 'serial').lower()
    if backend == 'windows':
        printer_name = (getattr(settings, 'POS_PRINTER_NAME', '') or '').strip()
        if not printer_name:
            return False, {'error': _('Imprimante Windows non configurée (POS_PRINTER_NAME).')}, 501
    else:
        port = getattr(settings, 'POS_PRINTER_PORT', None)
        if not port:
            return False, {'error': _('Port imprimante non configuré (POS_PRINTER_PORT).')}, 501
    return True, None, None


def run_pos_print(print_fn):
    """Exécute une impression ESC/POS avec gestion d'erreurs standard."""
    from rest_framework.response import Response
    from rest_framework import status

    ok, err, code = pos_printer_check()
    if not ok:
        return Response(err, status=code)
    try:
        from pos.printer_service import MP2258Printer
    except Exception as e:
        return Response({'error': _('Service ESC/POS indisponible: %(err)s') % {'err': e}}, status=501)

    printer = None
    try:
        printer = MP2258Printer()
        print_fn(printer)
        return Response({'status': _('impression lancée')})
    except ImportError as e:
        return Response(
            {'error': _('Dépendance manquante pour ESC/POS: %(err)s. Installez python-escpos.') % {'err': e}},
            status=501,
        )
    except Exception as e:
        return Response({'error': str(e)}, status=500)
    finally:
        try:
            if printer:
                printer.close()
        except Exception:
            pass
