"""
En-tête simplifié pour les documents POS (tickets PDF).
Les rapports métier utilisent serialize_entreprise() dans report_envelope.py.
"""


def get_entete_entreprise(entreprise):
    """
    Retourne le dictionnaire d'en-tête pour les rapports PDF.
    Contient uniquement : nom, logo_path, slogan, telephone.
    À ne pas inclure : adresse, email, NIF, responsable, etc.
    """
    if not entreprise:
        return {'entreprise': {'nom': '', 'logo_path': None, 'slogan': '', 'telephone': ''}}
    logo_path = None
    if getattr(entreprise, 'logo', None):
        try:
            logo_path = entreprise.logo.path
        except Exception:
            pass
    return {
        'entreprise': {
            'nom': entreprise.nom or '',
            'logo_path': logo_path,
            'slogan': getattr(entreprise, 'slogan', None) or '',
            'telephone': getattr(entreprise, 'telephone', None) or '',
        },
    }
