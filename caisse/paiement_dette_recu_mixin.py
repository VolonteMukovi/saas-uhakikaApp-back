"""Actions reçus paiement dette — PDF/JSON/ESC/POS (même ticket que facture vente)."""
from decimal import Decimal, ROUND_DOWN

from django.utils.translation import gettext as _
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from caisse.services.caisse import mouvement_moyen_affiche
from caisse.services.recu_paiement_pos import (
    fetch_grouped_mouvements,
    grouped_recu_lignes_from_mouvements,
    recu_groupe_urls,
    resolve_paiement_dette,
    run_pos_print,
    ticket_lines_to_pdf_response,
)
from stock.services.tenant_context import get_tenant_ids as _get_tenant_ids


class PaiementDetteRecuMixin:
    def _resolve_paiement_dette(self, paiement):
        return resolve_paiement_dette(paiement)

    def _grouped_recu_context(self, request, reference):
        from rest_framework import status

        reference = (reference or '').strip()
        if not reference:
            return None, Response({'detail': _('Référence requise.')}, status=status.HTTP_400_BAD_REQUEST)
        tenant_id, branch_id = _get_tenant_ids(request)
        if tenant_id is None:
            return None, Response({'detail': _('Contexte entreprise manquant.')}, status=status.HTTP_403_FORBIDDEN)
        mouvements = list(fetch_grouped_mouvements(
            reference=reference, tenant_id=tenant_id, branch_id=branch_id,
        ))
        if not mouvements:
            return None, Response(
                {'detail': _('Aucun paiement trouvé pour cette référence.')},
                status=status.HTTP_404_NOT_FOUND,
            )
        lignes = grouped_recu_lignes_from_mouvements(mouvements)
        if not lignes:
            return None, Response({'detail': _('Référence invalide.')}, status=status.HTTP_400_BAD_REQUEST)
        first_dette = resolve_paiement_dette(mouvements[0])
        client = first_dette.client if first_dette else None
        if not client:
            return None, Response({'detail': _('Client introuvable.')}, status=status.HTTP_404_NOT_FOUND)
        montant_total = sum((m.montant for m in mouvements), Decimal('0'))
        devise = mouvements[0].devise or (first_dette.devise if first_dette else None)
        return {
            'reference': reference,
            'client': client,
            'mouvements': mouvements,
            'lignes_dettes': lignes,
            'montant_total_paye': montant_total,
            'devise': devise,
            'moyen': mouvement_moyen_affiche(mouvements[0]),
            'pay_dt': mouvements[-1].date,
        }, None

    @action(detail=True, methods=['get'], url_path='recu-paiement', permission_classes=[IsAuthenticated])
    def recu_paiement_pdf(self, request, pk=None):
        """PDF ticket 58 mm — lignes monospace identiques à facture-pos."""
        from pos.printer_service import MP2258Printer

        user = request.user
        paiement = self.get_object()
        dette = self._resolve_paiement_dette(paiement)
        if not dette:
            return Response({'error': _('Mouvement invalide pour un reçu de paiement de dette.')}, status=400)
        entreprise = user.get_entreprise(request)
        montant_ce_recu = Decimal(str(paiement.montant or 0))
        ancien_solde = (montant_ce_recu + Decimal(str(dette.solde_restant or 0))).quantize(
            Decimal('0.00001'), rounding=ROUND_DOWN,
        )
        lines = MP2258Printer().build_recu_paiement_dette_ticket_lines(
            paiement, dette, entreprise, user,
            moyen=mouvement_moyen_affiche(paiement),
            ancien_solde=ancien_solde,
        )
        return ticket_lines_to_pdf_response(lines, f'RECU_PAIEMENT_{paiement.pk}.pdf')

    @action(detail=True, methods=['post'], url_path='recu-paiement-print', permission_classes=[IsAuthenticated])
    def recu_paiement_print(self, request, pk=None):
        """Impression ESC/POS — reçu paiement dette."""
        user = request.user
        paiement = self.get_object()
        dette = self._resolve_paiement_dette(paiement)
        if not dette:
            return Response({'error': _('Mouvement invalide.')}, status=400)
        entreprise = user.get_entreprise(request)
        montant_ce_recu = Decimal(str(paiement.montant or 0))
        ancien_solde = (montant_ce_recu + Decimal(str(dette.solde_restant or 0))).quantize(
            Decimal('0.00001'), rounding=ROUND_DOWN,
        )
        moyen = mouvement_moyen_affiche(paiement)

        def _do_print(printer):
            printer.print_recu_paiement_dette(
                paiement, dette, entreprise, user, moyen=moyen, ancien_solde=ancien_solde,
            )

        return run_pos_print(_do_print)

    @action(detail=False, methods=['get'], url_path='recu-groupe', permission_classes=[IsAuthenticated])
    def recu_groupe_json(self, request):
        """Reçu JSON — paiement groupé (référence commune)."""
        from pos.printer_service import MP2258Printer
        from rapports.utils.report_envelope import build_metadata, serialize_agence, serialize_entreprise

        reference = request.query_params.get('reference', '')
        ctx, err = self._grouped_recu_context(request, reference)
        if err is not None:
            return err
        user = request.user
        entreprise = user.get_entreprise(request)
        tenant_id, branch_id = _get_tenant_ids(request)
        ticket_lines = MP2258Printer().build_recu_paiement_groupe_ticket_lines(
            client=ctx['client'],
            entreprise=entreprise,
            user=user,
            reference=ctx['reference'],
            lignes_dettes=ctx['lignes_dettes'],
            montant_total_paye=ctx['montant_total_paye'],
            devise=ctx['devise'],
            moyen=ctx['moyen'],
            pay_dt=ctx['pay_dt'],
        )
        solde_global = sum(
            (Decimal(str(r.get('nouveau_solde', 0) or 0)) for r in ctx['lignes_dettes']),
            Decimal('0'),
        ).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
        urls = recu_groupe_urls(request, ctx['reference'])
        return Response({
            'document': 'recu_paiement_groupe',
            'titre': _('REÇU PAIEMENT GROUPE'),
            'reference': ctx['reference'],
            'client': {'id': ctx['client'].pk, 'nom': ctx['client'].nom},
            'entreprise': serialize_entreprise(entreprise, request),
            'agence': serialize_agence(branch_id, entreprise),
            'metadata': build_metadata(user, request),
            'montant_total_paye': str(ctx['montant_total_paye']),
            'solde_global_restant': str(solde_global),
            'devise': ctx['devise'].sigle if ctx['devise'] else None,
            'moyen': ctx['moyen'],
            'dettes_payees': [
                {
                    'dette_id': r['dette_id'],
                    'mouvement_caisse_id': r['mouvement_caisse_id'],
                    'montant_applique': str(r['montant_applique']),
                    'ancien_solde': str(r['ancien_solde']),
                    'nouveau_solde': str(r['nouveau_solde']),
                    'statut': r['statut'],
                }
                for r in ctx['lignes_dettes']
            ],
            'recu': urls,
            'pdf_url': urls['pdf_url'],
            'print_url': urls['print_url'],
            'ticket_lines': [line.rstrip('\n') for line in ticket_lines],
        })

    @action(detail=False, methods=['get'], url_path='recu-groupe/pdf', permission_classes=[IsAuthenticated])
    def recu_groupe_pdf(self, request):
        from pos.printer_service import MP2258Printer

        reference = request.query_params.get('reference', '')
        ctx, err = self._grouped_recu_context(request, reference)
        if err is not None:
            return err
        user = request.user
        entreprise = user.get_entreprise(request)
        lines = MP2258Printer().build_recu_paiement_groupe_ticket_lines(
            client=ctx['client'],
            entreprise=entreprise,
            user=user,
            reference=ctx['reference'],
            lignes_dettes=ctx['lignes_dettes'],
            montant_total_paye=ctx['montant_total_paye'],
            devise=ctx['devise'],
            moyen=ctx['moyen'],
            pay_dt=ctx['pay_dt'],
        )
        safe_ref = ctx['reference'].replace('/', '-').replace('\\', '-')[:40]
        return ticket_lines_to_pdf_response(lines, f'RECU_GROUPE_{safe_ref}.pdf')

    @action(detail=False, methods=['post'], url_path='recu-groupe-print', permission_classes=[IsAuthenticated])
    def recu_groupe_print(self, request):
        reference = request.data.get('reference') or request.query_params.get('reference', '')
        ctx, err = self._grouped_recu_context(request, reference)
        if err is not None:
            return err
        user = request.user
        entreprise = user.get_entreprise(request)

        def _do_print(printer):
            printer.print_recu_paiement_groupe(
                client=ctx['client'],
                entreprise=entreprise,
                user=user,
                reference=ctx['reference'],
                lignes_dettes=ctx['lignes_dettes'],
                montant_total_paye=ctx['montant_total_paye'],
                devise=ctx['devise'],
                moyen=ctx['moyen'],
                pay_dt=ctx['pay_dt'],
            )

        return run_pos_print(_do_print)
