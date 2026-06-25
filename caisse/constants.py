"""Constantes métier caisse."""

CAISSE_DEFAUT_NOM = 'Caisse principale'
CAISSE_DEFAUT_LIBELLE = 'Caisse cash physique'
CAISSE_DEFAUT_CODE = 'CASH'

CODE_TYPE_CAISSE_CHOICES = [
    ('CASH', 'Caisse cash physique'),
    ('BANQUE', 'Banque'),
    ('AIRTEL_MONEY', 'Airtel Money'),
    ('MPESA', 'M-Pesa'),
    ('ORANGE_MONEY', 'Orange Money'),
    ('MOBILE_MONEY', 'Mobile Money'),
    ('AUTRE', 'Autre'),
]
