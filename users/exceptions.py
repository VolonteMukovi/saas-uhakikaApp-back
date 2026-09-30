"""Exceptions métier de l'authentification."""
from rest_framework import status
from rest_framework.exceptions import APIException


class ErreurConnexion(APIException):
    """
    Refus de connexion avec un `code` exploitable par le frontend
    (email_not_verified, compte_inexistant, identifiants_invalides).

    Contrairement à ValidationError, les champs complémentaires gardent leur type
    (chaîne, booléen) au lieu d'être convertis en listes de chaînes.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'erreur_connexion'

    def __init__(self, detail, *, code: str, **champs):
        super().__init__(detail=detail, code=code)
        self.code_metier = code
        self.champs = champs
