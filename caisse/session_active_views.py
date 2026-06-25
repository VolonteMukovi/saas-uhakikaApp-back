"""
Endpoint canonique : état session caisse active (source de vérité UI).
"""
from django.utils.translation import gettext as _
from rest_framework.response import Response
from rest_framework.views import APIView

from caisse.models import SessionCaisse
from caisse.services.errors import validation_error_message
from caisse.services.session_active_state import build_active_state_response
from caisse.services.session_caisse import SessionCaisseError, get_session_caisse_ouverte
from stock.services.tenant_context import get_tenant_ids
from users.permissions import IsAdminOrUser


class SessionActiveAPIView(APIView):
    """
    GET /api/caisse/session-active/

    Retourne l'état réel de la caisse pour le contexte JWT (entreprise + agence).

    Query params optionnels :
    - ``devise_id`` : filtrer par devise
    - ``type_caisse_id`` ou ``caisse_id`` : filtrer par caisse
    """

    permission_classes = [IsAdminOrUser]

    def get(self, request):
        tenant_id, branch_id = get_tenant_ids(request)
        if not tenant_id:
            return Response({'detail': _('Contexte entreprise manquant.')}, status=403)

        devise_id = request.query_params.get('devise_id')
        type_caisse_id = (
            request.query_params.get('type_caisse_id')
            or request.query_params.get('caisse_id')
        )

        if devise_id:
            try:
                session = get_session_caisse_ouverte(
                    tenant_id,
                    branch_id,
                    int(devise_id),
                    int(type_caisse_id) if type_caisse_id else None,
                )
            except SessionCaisseError as exc:
                return Response(
                    {
                        'detail': validation_error_message(exc),
                        'is_open': False,
                        'ouverte': False,
                        'session': None,
                        'sessions': [],
                    },
                    status=400,
                )
            if not session:
                return Response(build_active_state_response())
            session = SessionCaisse.objects.select_related(
                'type_caisse', 'devise', 'ouvert_par',
            ).get(pk=session.pk)
            return Response(build_active_state_response(session=session))

        qs = SessionCaisse.objects.filter(
            entreprise_id=tenant_id,
            statut='OUVERTE',
        ).select_related('type_caisse', 'devise', 'ouvert_par')
        if branch_id is not None:
            qs = qs.filter(succursale_id=branch_id)
        if type_caisse_id:
            qs = qs.filter(type_caisse_id=int(type_caisse_id))

        sessions = list(qs.order_by('-ouvert_le', '-id'))
        if not sessions:
            return Response(build_active_state_response())

        return Response(build_active_state_response(session=sessions[0], sessions=sessions))
