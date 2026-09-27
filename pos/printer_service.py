from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
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


def _fmt_qty(v, max_decimals: int = 5) -> str:
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


def _fmt_money(v, decimals: int = 2) -> str:
    """
    Montant ticket : exactement `decimals` chiffres après la virgule (format FR).
    Ex. 7.5 → 7,50 ; 15000 → 15.000,00
    """
    try:
        quantum = Decimal("1").scaleb(-decimals)
        d = Decimal(str(v or 0)).quantize(quantum, rounding=ROUND_DOWN)
        sign = "-" if d < 0 else ""
        d = abs(d)
        int_part = int(d)
        frac = d - Decimal(int_part)
        frac_s = f"{frac:.{decimals}f}".split(".", 1)[1]
        int_s = f"{int_part:,}".replace(",", ".")
        return f"{sign}{int_s},{frac_s}"
    except Exception:
        return str(v or 0)


def _wrap_text(text: str, width: int) -> list[str]:
    """Découpe un libellé sur plusieurs lignes sans tronquer avec '...'."""
    s = (text or "").strip()
    if not s:
        return [""]
    width = max(1, int(width))
    words = s.split()
    rows: list[str] = []
    cur = ""
    for word in words:
        pieces = [word] if len(word) <= width else [
            word[i : i + width] for i in range(0, len(word), width)
        ]
        for piece in pieces:
            if not cur:
                cur = piece
            elif len(cur) + 1 + len(piece) <= width:
                cur = f"{cur} {piece}"
            else:
                rows.append(cur)
                cur = piece
    if cur:
        rows.append(cur)
    return rows or [""]


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
    Impression ticket ESC/POS (MP-2258) via liaison Série / Windows.

    La connexion matérielle est **lazy** : construire les lignes texte
    (PDF / prévisualisation) ne nécessite ni POS_PRINTER_PORT ni imprimante.
    L'ouverture du port n'a lieu qu'au moment d'imprimer.
    """

    def __init__(self, cfg: POSPrinterConfig | None = None, *, connect: bool = False):
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
        self.printer = None
        if connect:
            self._ensure_printer()

    @staticmethod
    def list_windows_printers() -> list[str]:
        """Noms des imprimantes Windows locales / connectées."""
        try:
            import win32print  # type: ignore
        except ImportError as e:
            raise ImportError(
                "Printing with Win32Raw requires pywin32 (win32print). "
                "Installez: pip install pywin32"
            ) from e
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        return [p[2] for p in win32print.EnumPrinters(flags)]

    @classmethod
    def resolve_windows_printer_name(cls, configured_name: str) -> str:
        """
        Résout POS_PRINTER_NAME vers un nom Windows exact.
        Accepte un préfixe (ex: POS58 → POS58 Printer) pour éviter
        « Incorrect printer name » quand le libellé système est plus long.
        """
        wanted = (configured_name or "").strip()
        if not wanted:
            raise ValueError("POS_PRINTER_NAME non configuré pour backend windows")

        available = cls.list_windows_printers()
        if not available:
            raise ValueError("Aucune imprimante Windows détectée sur cette machine")

        by_lower = {name.lower(): name for name in available}
        if wanted in available:
            return wanted
        if wanted.lower() in by_lower:
            return by_lower[wanted.lower()]

        # Préfixe / containment : préférer le match le plus court (sans " (2)").
        needle = wanted.lower()
        candidates = [
            name
            for name in available
            if name.lower().startswith(needle) or needle in name.lower()
        ]
        if not candidates:
            raise ValueError(
                f"Imprimante introuvable: {wanted!r}. "
                f"Disponibles: {', '.join(available)}"
            )

        def _rank(name: str) -> tuple:
            low = name.lower()
            numbered = 1 if "(" in name else 0
            return (numbered, abs(len(name) - len(wanted)), low)

        return sorted(candidates, key=_rank)[0]

    def _ensure_printer(self):
        """Ouvre l'imprimante uniquement pour une vraie impression."""
        if self.printer is not None:
            return self.printer

        cfg = self.cfg
        if cfg.backend == "windows":
            resolved = self.resolve_windows_printer_name(cfg.printer_name)
            from escpos.printer import Win32Raw  # type: ignore

            self.printer = Win32Raw(printer_name=resolved)
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
        return self.printer

    def close(self):
        if self.printer is None:
            return
        try:
            self.printer.close()
        except Exception:
            pass
        finally:
            self.printer = None

    def _hr(self) -> str:
        n = max(16, int(self.cfg.chars_per_line))
        return "-" * n + "\n"

    def _build_vente_ticket_lines(
        self,
        sortie,
        entreprise,
        user,
        *,
        title: str,
        doc_prefix: str,
        total_label: str,
        mode_paiement: str | None = None,
    ) -> list[str]:
        """
        Source unique des lignes ticket vente (facture / reçu comptant).
        Même colonnes, largeurs, polices implicites (monospace) et totaux.
        Seuls title / préfixe numéro / libellé total / mode varient.
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
        lines.append(f"{_center_line(title, cpl)}\n")
        lines.append(f"{_center_line('-' * cpl, cpl)}\n")

        invoice_dt = getattr(sortie, "date_creation", None) or timezone.now()
        client = getattr(sortie, "client", None)
        client_name = getattr(client, "nom", None) or "Client inconnu"
        devise_sortie = getattr(sortie, "devise", None)
        currency = _currency_label(devise_sortie)
        # Numéro de document (Ndeg / FACT- / REC-) volontairement omis.
        _ = doc_prefix
        lines.append(f"Date: {invoice_dt.strftime('%d/%m/%Y %H:%M')}\n")
        lines.append(f"Client: {client_name}\n")
        if currency:
            lines.append(f"Devise: {currency}\n")
        if mode_paiement:
            lines.append(f"Mode: {mode_paiement}\n")
        lines.append("\n")

        # Devise uniquement en en-tête : pas de symbole après les montants du tableau.
        w_qty = 4
        w_pu = 8
        w_tot = 9
        nums_width = w_qty + 1 + w_pu + 1 + w_tot
        # En-tête compact (ticket 58 mm) — montants alignés à droite.
        header_nums = f"{'Qte':>{w_qty}} {'PU':>{w_pu}} {'Total':>{w_tot}}"
        lines.append(f"{'Article':<{max(0, cpl - nums_width - 1)}} {header_nums}\n")
        lines.append(self._hr())

        total_general = Decimal("0.00")
        totals_by_currency: "OrderedDict[str, Decimal]" = OrderedDict()
        lignes = getattr(sortie, "lignes", None)
        lignes_qs = lignes.all() if hasattr(lignes, "all") else (lignes or [])
        for ligne in lignes_qs:
            article = getattr(ligne, "article", None)
            nom = _article_display_name(article).strip() or "Article"

            qte_raw = getattr(ligne, "quantite", 0) or 0
            pu_raw = getattr(ligne, "prix_unitaire", 0) or 0
            qte = Decimal(str(qte_raw or 0))
            pu = Decimal(str(pu_raw or 0))
            tot = (qte * pu).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            total_general = (total_general + tot).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            line_devise = getattr(ligne, "devise", None) or devise_sortie
            line_currency = _currency_label(line_devise)

            qte_s = _fmt_qty(qte_raw, max_decimals=3)
            pu_s = _fmt_money(pu, decimals=2)
            tot_s = _fmt_money(tot, decimals=2)
            if line_currency:
                prev = totals_by_currency.get(line_currency, Decimal("0.00"))
                totals_by_currency[line_currency] = (prev + tot).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            else:
                prev = totals_by_currency.get("", Decimal("0.00"))
                totals_by_currency[""] = (prev + tot).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)

            nums = f"{qte_s:>{w_qty}} {pu_s:>{w_pu}} {tot_s:>{w_tot}}"
            name_rows = _wrap_text(nom, cpl)
            # Si le nom tient sur une ligne avec les montants, une seule ligne ; sinon nom complet puis montants.
            if len(name_rows) == 1 and len(name_rows[0]) + 1 + nums_width <= cpl:
                lines.append(f"{name_rows[0]:<{cpl - nums_width - 1}} {nums}\n")
            else:
                for row in name_rows:
                    lines.append(f"{row}\n")
                lines.append(f"{nums:>{cpl}}\n")

        lines.append(self._hr())

        if len(totals_by_currency) <= 1:
            only_total = next(iter(totals_by_currency.values()), total_general)
            total_s = _fmt_money(only_total, decimals=2)
            lines.append(f"{total_label}: {total_s}\n")
        else:
            lines.append("TOTALS PAR DEVISE:\n")
            for curr, amount in totals_by_currency.items():
                line_total = _fmt_money(amount, decimals=2) + (f" {curr}" if curr else "")
                lines.append(f"- {line_total}\n")
        lines.append("\n")

        self._append_ticket_footer(lines, user, cpl)
        return lines

    def _append_article_table(
        self,
        lines: list[str],
        lignes_qs,
        devise_sortie,
        cpl: int,
        *,
        total_label: str = "TOTAL",
    ) -> Decimal:
        """Tableau articles (nom complet, montants FR 2 décimales, sans symbole devise)."""
        w_qty = 4
        w_pu = 8
        w_tot = 9
        nums_width = w_qty + 1 + w_pu + 1 + w_tot
        header_nums = f"{'Qte':>{w_qty}} {'PU':>{w_pu}} {'Total':>{w_tot}}"
        lines.append(f"{'Article':<{max(0, cpl - nums_width - 1)}} {header_nums}\n")
        lines.append(self._hr())

        total_general = Decimal("0.00")
        for ligne in lignes_qs:
            article = getattr(ligne, "article", None)
            nom = _article_display_name(article).strip() or "Article"

            qte_raw = getattr(ligne, "quantite", 0) or 0
            pu_raw = getattr(ligne, "prix_unitaire", 0) or 0
            qte = Decimal(str(qte_raw or 0))
            pu = Decimal(str(pu_raw or 0))
            tot = (qte * pu).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
            total_general = (total_general + tot).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)

            qte_s = _fmt_qty(qte_raw, max_decimals=3)
            pu_s = _fmt_money(pu, decimals=2)
            tot_s = _fmt_money(tot, decimals=2)
            nums = f"{qte_s:>{w_qty}} {pu_s:>{w_pu}} {tot_s:>{w_tot}}"
            name_rows = _wrap_text(nom, cpl)
            if len(name_rows) == 1 and len(name_rows[0]) + 1 + nums_width <= cpl:
                lines.append(f"{name_rows[0]:<{cpl - nums_width - 1}} {nums}\n")
            else:
                for row in name_rows:
                    lines.append(f"{row}\n")
                lines.append(f"{nums:>{cpl}}\n")

        lines.append(self._hr())
        lines.append(f"{total_label}: {_fmt_money(total_general, decimals=2)}\n")
        return total_general

    def _append_ticket_footer(self, lines: list[str], user, cpl: int) -> None:
        """Pied commun : imprimé par + messages de clôture."""
        printed_by = (getattr(user, "get_full_name", lambda: "")() or getattr(user, "username", "")).strip()
        printed_by = _name_with_initial_upper(printed_by)
        if printed_by:
            lines.append(f"Imprime par: {printed_by}\n")
        lines.append(timezone.now().strftime("%d/%m/%Y %H:%M") + "\n")
        lines.append("\n")
        for row in _wrap_text("Merci pour votre confiance et votre achat.", cpl):
            lines.append(_center_line(row, cpl) + "\n")
        lines.append("\n")
        for row in _wrap_text("Article vendu, aucun retour n'est accepté.", cpl):
            lines.append(_center_line(row, cpl) + "\n")
        lines.append("\n")

    def build_facture_ticket_lines(self, sortie, entreprise, user) -> list[str]:
        """
        Ticket FACTURE — modèle de référence inchangé (vente à crédit).
        Source unique pour impression POS et PDF facture-pos.
        """
        return self._build_vente_ticket_lines(
            sortie,
            entreprise,
            user,
            title="FACTURE DE VENTE",
            doc_prefix="FACT-",
            total_label="TOTAL DU",
            mode_paiement="CRÉDIT",
        )

    def build_recu_vente_ticket_lines(self, sortie, entreprise, user) -> list[str]:
        """
        Ticket REÇU — même structure/données que la facture, libellés reçus (vente comptant).
        """
        return self._build_vente_ticket_lines(
            sortie,
            entreprise,
            user,
            title="RECU DE VENTE",
            doc_prefix="REC-",
            total_label="TOTAL RECU",
            mode_paiement="COMPTANT",
        )

    @staticmethod
    def resolve_document_vente(sortie) -> dict:
        """
        Détermine le document à imprimer selon le mode de paiement de la sortie.
        EN_CREDIT → FACTURE ; PAYEE (comptant) → RECU.
        """
        statut = (getattr(sortie, "statut", None) or "").upper()
        if statut == "EN_CREDIT":
            return {
                "type_document": "FACTURE",
                "mode_paiement": "CREDIT",
                "pdf_url": f"/api/sorties/{sortie.pk}/facture-pos/",
                "print_url": f"/api/sorties/{sortie.pk}/facture-pos-print/",
            }
        return {
            "type_document": "RECU",
            "mode_paiement": "COMPTANT",
            "pdf_url": f"/api/sorties/{sortie.pk}/bon-pos/",
            "print_url": f"/api/sorties/{sortie.pk}/bon-pos-print/",
        }

    @staticmethod
    def resolve_document_paiement_dette(paiement) -> dict:
        """URLs PDF / impression pour un reçu de paiement de dette."""
        return {
            "type_document": "RECU_PAIEMENT_DETTE",
            "mode_paiement": "PAIEMENT DETTE",
            "pdf_url": f"/api/paiements-dettes-clients/{paiement.pk}/recu-pos/",
            "print_url": f"/api/paiements-dettes-clients/{paiement.pk}/recu-pos-print/",
        }

    def _append_entreprise_header(self, lines: list[str], entreprise, title: str) -> None:
        """En-tête entreprise + titre centré (même style que facture)."""
        cpl = max(16, int(self.cfg.chars_per_line))
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
        lines.append(f"{_center_line(title, cpl)}\n")
        lines.append(f"{_center_line('-' * cpl, cpl)}\n")

    def _print_ticket_lines(self, lines: list[str]) -> bool:
        p = self._ensure_printer()
        p.set(align="left", bold=False, width=1, height=1)
        for line in lines:
            p.text(_safe_text(line))
        try:
            p.cut()
        except Exception:
            p.text("\n\n")
        return True

    def build_recu_paiement_dette_ticket_lines(
        self,
        paiement,
        entreprise,
        user,
    ) -> list[str]:
        """
        Reçu de paiement (partiel ou total) d'une dette issue d'une facture crédit.
        Même mise en page que facture/reçu vente : produits + résumé clair.
        """
        cpl = max(16, int(self.cfg.chars_per_line))
        lines: list[str] = []
        self._append_entreprise_header(lines, entreprise, "RECU PAIEMENT DETTE")

        dette = getattr(paiement, "dettes_clients", None)
        sortie = getattr(dette, "sortie", None) if dette else None
        client = getattr(sortie, "client", None) if sortie else None
        client_name = getattr(client, "nom", None) or "Client inconnu"
        devise_sortie = getattr(sortie, "devise", None) if sortie else None
        currency = _currency_label(devise_sortie)

        pay_dt = getattr(paiement, "created_at", None) or timezone.now()
        if hasattr(pay_dt, "strftime"):
            date_s = pay_dt.strftime("%d/%m/%Y %H:%M")
        else:
            date_s = str(getattr(paiement, "date", "") or "")

        vente_dt = getattr(sortie, "date_creation", None) if sortie else None
        montant_facture = Decimal(str(getattr(dette, "montant", 0) or 0))
        montant_paye_ce = Decimal(str(getattr(paiement, "montant", 0) or 0))
        total_paye = Decimal(str(getattr(dette, "paye", 0) or 0))
        reste = Decimal(str(getattr(dette, "reste", 0) or 0))
        status = (getattr(dette, "status", None) or "").upper()

        lines.append(f"Date: {date_s}\n")
        lines.append(f"Client: {client_name}\n")
        if currency:
            lines.append(f"Devise: {currency}\n")
        lines.append("Mode: PAIEMENT DETTE\n")
        if vente_dt and hasattr(vente_dt, "strftime"):
            lines.append(f"Date vente: {vente_dt.strftime('%d/%m/%Y %H:%M')}\n")
        lines.append("\n")

        # Produits de la facture à crédit liée
        for row in _wrap_text("Produits de la vente a credit:", cpl):
            lines.append(f"{row}\n")
        lignes = getattr(sortie, "lignes", None) if sortie else None
        lignes_qs = lignes.all() if hasattr(lignes, "all") else (lignes or [])
        self._append_article_table(
            lines,
            lignes_qs,
            devise_sortie,
            cpl,
            total_label="TOTAL FACTURE",
        )
        lines.append("\n")

        lines.append(f"{_center_line('-' * cpl, cpl)}\n")
        for row in _wrap_text("RESUME DU PAIEMENT", cpl):
            lines.append(f"{_center_line(row, cpl)}\n")
        lines.append(f"{_center_line('-' * cpl, cpl)}\n")
        lines.append(f"Montant facture: {_fmt_money(montant_facture)}\n")
        lines.append(f"Ce paiement:     {_fmt_money(montant_paye_ce)}\n")
        lines.append(f"Total paye:      {_fmt_money(total_paye)}\n")
        lines.append(f"Reste du:        {_fmt_money(reste)}\n")
        if status:
            lines.append(f"Statut dette:    {status}\n")
        lines.append("\n")

        self._append_ticket_footer(lines, user, cpl)
        return lines

    def build_recu_paiement_groupe_ticket_lines(
        self,
        *,
        client,
        entreprise,
        user,
        reference: str,
        lignes_dettes: list[dict],
        montant_total_paye,
        devise,
        moyen: str | None = None,
        pay_dt=None,
    ) -> list[str]:
        """Reçu groupé — même format ticket que facture / reçu paiement dette."""
        cpl = max(16, int(self.cfg.chars_per_line))
        lines: list[str] = []
        self._append_entreprise_header(lines, entreprise, "RECU PAIEMENT DETTE")

        client_name = getattr(client, "nom", None) or "Client inconnu"
        currency = _currency_label(devise)
        pay_dt = pay_dt or timezone.now()
        total_paye = Decimal(str(montant_total_paye or 0))
        solde_global = sum(
            (Decimal(str(row.get("nouveau_solde", 0) or 0)) for row in lignes_dettes),
            Decimal("0"),
        ).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)

        lines.append(f"Date: {pay_dt.strftime('%d/%m/%Y %H:%M')}\n")
        lines.append(f"Client: {client_name}\n")
        if currency:
            lines.append(f"Devise: {currency}\n")
        lines.append("Mode: PAIEMENT DETTE\n")
        if moyen:
            lines.append(f"Moyen: {moyen}\n")
        lines.append("\n")

        w_id = 6
        w_pay = 10
        w_solde = 10
        header = f"{'Dette':<{w_id}} {'Paye':>{w_pay}} {'Reste':>{w_solde}}\n"
        lines.append(header)
        lines.append(self._hr())
        for row in lignes_dettes:
            dette_id = row.get("dette_id")
            montant = Decimal(str(row.get("montant_applique", 0) or 0))
            nouveau = Decimal(str(row.get("nouveau_solde", 0) or 0))
            lines.append(
                f"#{str(dette_id):<{w_id - 1}} "
                f"{_fmt_money(montant):>{w_pay}} "
                f"{_fmt_money(nouveau):>{w_solde}}\n"
            )

        lines.append(self._hr())
        lines.append(f"Total paye: {_fmt_money(total_paye)}\n")
        lines.append(f"Solde restant: {_fmt_money(solde_global)}\n")
        if reference:
            for row in _wrap_text(f"Ref: {reference}", cpl):
                lines.append(f"{row}\n")
        lines.append("\n")

        self._append_ticket_footer(lines, user, cpl)
        return lines

    def print_recu_paiement_dette(self, paiement, entreprise, user) -> bool:
        return self._print_ticket_lines(
            self.build_recu_paiement_dette_ticket_lines(paiement, entreprise, user)
        )

    def print_recu_paiement_groupe(
        self,
        *,
        client,
        entreprise,
        user,
        reference: str,
        lignes_dettes: list[dict],
        montant_total_paye,
        devise,
        moyen: str | None = None,
        pay_dt=None,
    ) -> bool:
        lines = self.build_recu_paiement_groupe_ticket_lines(
            client=client,
            entreprise=entreprise,
            user=user,
            reference=reference,
            lignes_dettes=lignes_dettes,
            montant_total_paye=montant_total_paye,
            devise=devise,
            moyen=moyen,
            pay_dt=pay_dt,
        )
        return self._print_ticket_lines(lines)

    def print_facture(self, sortie, entreprise, user) -> bool:
        return self._print_ticket_lines(self.build_facture_ticket_lines(sortie, entreprise, user))

    def print_recu(self, sortie, entreprise, user) -> bool:
        """
        Impression reçu vente comptant — mêmes lignes ticket que le PDF bon-pos
        (source commune avec la facture, libellés reçus uniquement).
        """
        return self._print_ticket_lines(self.build_recu_vente_ticket_lines(sortie, entreprise, user))

