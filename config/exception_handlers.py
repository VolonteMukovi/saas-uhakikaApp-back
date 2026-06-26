"""Gestionnaire d'exceptions DRF — erreurs métier caisse en 400."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from caisse.services.caisse_defaut import CaisseError
from caisse.services.errors import validation_error_message
from caisse.services.session_caisse import SessionCaisseError


def exception_handler(exc, context):
    if isinstance(exc, (SessionCaisseError, CaisseError)):
        return Response(
            {'detail': validation_error_message(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return drf_exception_handler(exc, context)
