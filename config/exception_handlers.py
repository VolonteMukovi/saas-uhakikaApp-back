"""Point d'entrée — délègue à config.http.problem_details (RFC 9457)."""
from config.http.problem_details import exception_handler

__all__ = ['exception_handler']
