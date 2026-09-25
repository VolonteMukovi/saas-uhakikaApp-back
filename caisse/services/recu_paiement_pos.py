"""
Helpers PDF ticket POS (lignes monospace) — partagés facture / reçu vente.
"""
from __future__ import annotations

import io

from django.http import HttpResponse
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import mm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


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
