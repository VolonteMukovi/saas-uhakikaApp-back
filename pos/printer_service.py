from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import unicodedata
from collections import OrderedDict

from django.conf import settings
from django.utils import timezone


def _article_display_name(article) -> str:
    """Nom lisible: commercial (scientifique) sinon scientifique."""
    if not article:
        return ""
    nom_comm = getattr(article, "nom_commercial", None)
    nom_sci = getattr(article, "nom_scientifique", None)
    if nom_comm:
        return f"{nom_comm} ({nom_sci})" if nom_sci else str(nom_comm)
    if nom_sci:
        return str(nom_sci)
    return str(getattr(article, "article_id", str(article)))


def _fmt_qty(v, max_decimals: int = 3) -> str:
    if v is None or v == "":
        return "0"
    try:
        d = Decimal(str(v))
        quantum = Decimal("1").scaleb(-max_decimals)
        d = d.quantize(quantum)
        s = f"{d:f}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s or "0"
    except Exception:
        return str(v)


def _fmt_money(v) -> str:
    try:
        return f"{Decimal(str(v or 0)).quantize(Decimal('0.01')):.2f}"
    except Exception:
        return str(v or 0)


def _currency_label(devise) -> str:
    """
    Libellé devise compact pour ticket POS.
    Priorité: symbole, puis sigle, sinon vide.
    """
    if not devise:
        return ""
    sym = (getattr(devise, "symbole", "") or "").strip()
    if sym:
        return sym
    sigle = (getattr(devise, "sigle", "") or "").strip()
    return sigle


def _safe_text(value: str) -> str:
    """
    Rend le texte plus robuste pour les imprimantes ESC/POS
    (évite les caractères Unicode non supportés).
    """
    s = str(value or "")
    s = s.replace("…", "...")
    s = (
        s.replace("°", "deg")
        .replace("–", "-")
        .replace("—", "-")
        .replace("’", "'")
    )
    # Supprime les accents pour limiter les erreurs d'encodage CP437/CP850.
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s


def _name_with_initial_upper(value: str) -> str:
    """Met une majuscule initiale tout en conservant le reste du texte."""
    s = (value or "").strip()
    if not s:
        return ""
    return s[:1].upper() + s[1:]


def _center_line(text: str, width: int) -> str:
    """Centre une ligne dans une largeur fixe (mode ticket monospace)."""
    s = str(text or "")
    if len(s) >= width:
        return s
    left = (width - len(s)) // 2
    right = width - len(s) - left
    return (" " * left) + s + (" " * right)


@dataclass(frozen=True)
class POSPrinterConfig:
    backend: str = "serial"  # serial | windows
    port: str = ""
    printer_name: str = ""
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = "N"
    stopbits: int = 1
    timeout: int = 1
    chars_per_line: int = 32  # 58mm: souvent 32/42 selon la police


class MP2258Printer:
    """
    Impression ticket ESC/POS (MP-2258) via liaison Série.
    Ne génère pas de PDF: envoi direct de commandes ESC/POS.
    """

    def __init__(self, cfg: POSPrinterConfig | None = None):
        if cfg is None:
            cfg = POSPrinterConfig(
                backend=str(getattr(settings, "POS_PRINTER_BACKEND", "serial") or "serial").lower(),
                port=getattr(settings, "POS_PRINTER_PORT", "") or "",
                printer_name=str(getattr(settings, "POS_PRINTER_NAME", "") or ""),
                baudrate=int(getattr(settings, "POS_PRINTER_BAUDRATE", 9600)),
                bytesize=int(getattr(settings, "POS_PRINTER_BYTESIZE", 8)),
                parity=str(getattr(settings, "POS_PRINTER_PARITY", "N")),
                stopbits=int(getattr(settings, "POS_PRINTER_STOPBITS", 1)),
                timeout=int(getattr(settings, "POS_PRINTER_TIMEOUT", 1)),
                chars_per_line=int(getattr(settings, "POS_PRINTER_CHARS_PER_LINE", 32)),
            )
        self.cfg = cfg

        if cfg.backend == "windows":
            if not cfg.printer_name:
                raise ValueError("POS_PRINTER_NAME non configuré pour backend windows")
            from escpos.printer import Win32Raw  # type: ignore

            self.printer = Win32Raw(printer_name=cfg.printer_name)
        else:
            if not cfg.port:
                raise ValueError("POS_PRINTER_PORT non configuré pour backend serial")
            from escpos.printer import Serial  # type: ignore

            self.printer = Serial(
                devfile=cfg.port,
                baudrate=cfg.baudrate,
                bytesize=cfg.bytesize,
                parity=cfg.parity,
                stopbits=cfg.stopbits,
                timeout=cfg.timeout,
            )

    def close(self):
        try:
            self.printer.close()
        except Exception:
            pass

    def _hr(self) -> str:
        n = max(16, int(self.cfg.chars_per_line))
        return "-" * n + "\n"

    def build_facture_ticket_lines(self, sortie, entreprise, user) -> list[str]:
        """
        Construit les lignes texte du ticket facture.
        Cette méthode sert de source unique pour:
        - l'impression POS directe (print_facture)
        - la visualisation PDF (facture-pos)
        """
        cpl = max(16, int(self.cfg.chars_per_line))
        lines: list[str] = []

        nom_entreprise = (getattr(entreprise, "nom", "") or "").strip()
        if nom_entreprise:
            lines.append(f"{_center_line(nom_entreprise, cpl)}\n")
        tel = (getattr(entreprise, "telephone", None) or "").strip()
        if tel:
            lines.append(f"{_center_line(f'Tel: {tel}', cpl)}\n")
        adr = (getattr(entreprise, "adresse", None) or "").strip()
        if adr:
            lines.append(f"{_center_line(adr, cpl)}\n")
        email = (getattr(entreprise, "email", None) or "").strip()
        if email:
            lines.append(f"{_center_line(email, cpl)}\n")

        lines.append(f"{_center_line('-' * cpl, cpl)}\n")
        lines.append(f"{_center_line('FACTURE DE VENTE', cpl)}\n")
        lines.append(f"{_center_line('-' * cpl, cpl)}\n")

        invoice_dt = getattr(sortie, "date_creation", None) or timezone.now()
        client = getattr(sortie, "client", None)
        client_name = getattr(client, "nom", None) or "Client inconnu"
        devise_sortie = getattr(sortie, "devise", None)
        currency = _currency_label(devise_sortie)
        lines.append(f"Ndeg: FACT-{int(sortie.pk):06d}\n")
        lines.append(f"Date: {invoice_dt.strftime('%d/%m/%Y %H:%M')}\n")
        lines.append(f"Client: {client_name}\n")
        if currency:
            lines.append(f"Devise: {currency}\n")
        lines.append("\n")

        money_extra = len(currency) if currency else 0
        w_art = max(8, cpl - (1 + 6 + 1 + (6 + money_extra) + 1 + (7 + money_extra)))
        w_qty = 6
        w_pu = 6 + money_extra
        w_tot = 7 + money_extra

        header = f"{'Article':<{w_art}} {'Qte':>{w_qty}} {'PU':>{w_pu}} {'Total':>{w_tot}}\n"
        lines.append(header)
        lines.append(self._hr())

        total_general = Decimal("0.00")
        totals_by_currency: "OrderedDict[str, Decimal]" = OrderedDict()
        lignes = getattr(sortie, "lignes", None)
        lignes_qs = lignes.all() if hasattr(lignes, "all") else (lignes or [])
        for ligne in lignes_qs:
            article = getattr(ligne, "article", None)
            nom = _article_display_name(article).strip()
            if len(nom) > w_art:
                nom = nom[: max(0, w_art - 3)] + "..."

            qte_raw = getattr(ligne, "quantite", 0) or 0
            pu_raw = getattr(ligne, "prix_unitaire", 0) or 0
            qte = Decimal(str(qte_raw or 0))
            pu = Decimal(str(pu_raw or 0))
            tot = (qte * pu).quantize(Decimal("0.01"))
            total_general = (total_general + tot).quantize(Decimal("0.01"))
            line_devise = getattr(ligne, "devise", None) or devise_sortie
            line_currency = _currency_label(line_devise)

            qte_s = _fmt_qty(qte_raw)
            pu_s = _fmt_money(pu)
            tot_s = _fmt_money(tot)
            if line_currency:
                pu_s = f"{pu_s}{line_currency}"
                tot_s = f"{tot_s}{line_currency}"
                prev = totals_by_currency.get(line_currency, Decimal("0.00"))
                totals_by_currency[line_currency] = (prev + tot).quantize(Decimal("0.01"))
            else:
                prev = totals_by_currency.get("", Decimal("0.00"))
                totals_by_currency[""] = (prev + tot).quantize(Decimal("0.01"))

            lines.append(f"{nom:<{w_art}} {qte_s:>{w_qty}} {pu_s:>{w_pu}} {tot_s:>{w_tot}}\n")

        lines.append(self._hr())

        if len(totals_by_currency) <= 1:
            only_currency = next(iter(totals_by_currency.keys()), currency)
            only_total = next(iter(totals_by_currency.values()), total_general)
            total_s = _fmt_money(only_total) + (f" {only_currency}" if only_currency else "")
            lines.append(f"TOTAL DU: {total_s}\n")
        else:
            lines.append("TOTALS PAR DEVISE:\n")
            for curr, amount in totals_by_currency.items():
                line_total = _fmt_money(amount) + (f" {curr}" if curr else "")
                lines.append(f"- {line_total}\n")
        lines.append("\n")

        printed_by = (getattr(user, "get_full_name", lambda: "")() or getattr(user, "username", "")).strip()
        printed_by = _name_with_initial_upper(printed_by)
        if printed_by:
            lines.append(f"Imprime par: {printed_by}\n")
        lines.append(timezone.now().strftime("%d/%m/%Y %H:%M") + "\n")
        lines.append("\n")
        return lines

    def print_facture(self, sortie, entreprise, user) -> bool:
        p = self.printer
        p.set(align="left", bold=False, width=1, height=1)
        for line in self.build_facture_ticket_lines(sortie, entreprise, user):
            p.text(_safe_text(line))

        try:
            p.cut()
        except Exception:
            # Certaines imprimantes/configs ne supportent pas le cut.
            p.text("\n\n")

        return True

    def print_recu(self, sortie, entreprise, user) -> bool:
        """
        Impression d'un reçu (ticket simplifié) pour une sortie.
        """
        p = self.printer
        cpl = max(16, int(self.cfg.chars_per_line))

        p.set(align="center", bold=True, width=1, height=1)
        p.text(_safe_text((getattr(entreprise, "nom", "") or "").strip()) + "\n")
        p.set(align="center", bold=False)
        tel = (getattr(entreprise, "telephone", None) or "").strip()
        if tel:
            p.text(_safe_text(f"Tel: {tel}\n"))
        p.text(self._hr())
        p.set(align="center", bold=True)
        p.text(_safe_text("RECU DE VENTE\n"))
        p.set(align="center", bold=False)
        p.text(self._hr())

        invoice_dt = getattr(sortie, "date_creation", None) or timezone.now()
        client = getattr(sortie, "client", None)
        client_name = getattr(client, "nom", None) or "Client anonyme"
        devise_sortie = getattr(sortie, "devise", None)
        currency = _currency_label(devise_sortie)

        p.set(align="left")
        p.text(_safe_text(f"Ndeg: REC-{int(sortie.pk):06d}\n"))
        p.text(_safe_text(f"Date: {invoice_dt.strftime('%d/%m/%Y %H:%M')}\n"))
        p.text(_safe_text(f"Client: {client_name}\n"))
        if currency:
            p.text(_safe_text(f"Devise: {currency}\n"))
        p.text("\n")

        money_extra = len(currency) if currency else 0
        w_art = max(8, cpl - (1 + 6 + 1 + (6 + money_extra) + 1 + (7 + money_extra)))
        w_qty = 6
        w_pu = 6 + money_extra
        w_tot = 7 + money_extra

        header = f"{'Article':<{w_art}} {'Qte':>{w_qty}} {'PU':>{w_pu}} {'Total':>{w_tot}}\n"
        p.text(_safe_text(header))
        p.text(self._hr())

        total_general = Decimal("0.00")
        totals_by_currency: "OrderedDict[str, Decimal]" = OrderedDict()
        lignes = getattr(sortie, "lignes", None)
        lignes_qs = lignes.all() if hasattr(lignes, "all") else (lignes or [])
        for ligne in lignes_qs:
            article = getattr(ligne, "article", None)
            nom = _article_display_name(article).strip()
            if len(nom) > w_art:
                nom = nom[: max(0, w_art - 3)] + "..."

            qte_raw = getattr(ligne, "quantite", 0) or 0
            pu_raw = getattr(ligne, "prix_unitaire", 0) or 0
            qte = Decimal(str(qte_raw or 0))
            pu = Decimal(str(pu_raw or 0))
            tot = (qte * pu).quantize(Decimal("0.01"))
            total_general = (total_general + tot).quantize(Decimal("0.01"))
            line_devise = getattr(ligne, "devise", None) or devise_sortie
            line_currency = _currency_label(line_devise)

            qte_s = _fmt_qty(qte_raw)
            pu_s = _fmt_money(pu)
            tot_s = _fmt_money(tot)
            if line_currency:
                pu_s = f"{pu_s}{line_currency}"
                tot_s = f"{tot_s}{line_currency}"
                prev = totals_by_currency.get(line_currency, Decimal("0.00"))
                totals_by_currency[line_currency] = (prev + tot).quantize(Decimal("0.01"))
            else:
                prev = totals_by_currency.get("", Decimal("0.00"))
                totals_by_currency[""] = (prev + tot).quantize(Decimal("0.01"))

            line = f"{nom:<{w_art}} {qte_s:>{w_qty}} {pu_s:>{w_pu}} {tot_s:>{w_tot}}\n"
            p.text(_safe_text(line))

        p.text(self._hr())

        p.set(align="right", bold=True)
        if len(totals_by_currency) <= 1:
            only_currency = next(iter(totals_by_currency.keys()), currency)
            only_total = next(iter(totals_by_currency.values()), total_general)
            total_s = _fmt_money(only_total) + (f" {only_currency}" if only_currency else "")
            p.text(_safe_text(f"TOTAL RECU: {total_s}\n"))
        else:
            p.text(_safe_text("TOTALS PAR DEVISE:\n"))
            for curr, amount in totals_by_currency.items():
                line_total = _fmt_money(amount) + (f" {curr}" if curr else "")
                p.text(_safe_text(f"- {line_total}\n"))
        p.set(align="left", bold=False)
        p.text("\n")

        printed_by = (getattr(user, "get_full_name", lambda: "")() or getattr(user, "username", "")).strip()
        printed_by = _name_with_initial_upper(printed_by)
        p.set(align="center")
        if printed_by:
            p.text(_safe_text(f"Imprime par: {printed_by}\n"))
        p.text(_safe_text(timezone.now().strftime("%d/%m/%Y %H:%M") + "\n"))
        p.text(_safe_text("-- Fin --\n"))

        try:
            p.cut()
        except Exception:
            p.text("\n\n")

        return True

