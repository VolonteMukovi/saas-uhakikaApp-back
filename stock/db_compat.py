"""
Compatibilité schéma : bases sans colonnes GFK sur ``stock_mouvementcaisse``
(migrations non appliquées). Évite OperationalError 1054 sur les SELECT ORM.
"""
from __future__ import annotations

from typing import FrozenSet

from django.db import connection

from stock.models import MouvementCaisse


def mouvementcaisse_column_names() -> FrozenSet[str]:
    """Colonnes réelles de ``stock_mouvementcaisse`` pour la connexion courante."""
    vendor = connection.vendor
    with connection.cursor() as cursor:
        if vendor == 'mysql':
            cursor.execute('SHOW COLUMNS FROM stock_mouvementcaisse')
            return frozenset(row[0] for row in cursor.fetchall())
        if vendor == 'postgresql':
            cursor.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = current_schema() AND table_name = %s
                """,
                ['stock_mouvementcaisse'],
            )
            return frozenset(row[0] for row in cursor.fetchall())
        if vendor == 'sqlite':
            cursor.execute('PRAGMA table_info(stock_mouvementcaisse)')
            return frozenset(row[1] for row in cursor.fetchall())
    return frozenset()


def mouvementcaisse_has_content_type_id(cols: FrozenSet[str] | None = None) -> bool:
    if cols is None:
        cols = mouvementcaisse_column_names()
    return 'content_type_id' in cols


def build_mouvementcaisse_queryset(cols: FrozenSet[str] | None = None):
    """
    Queryset MouvementCaisse qui n'inclut pas en SELECT les colonnes absentes
    (via defer), pour éviter 1054 sur MySQL.
    """
    if cols is None:
        cols = mouvementcaisse_column_names()
    defer: list[str] = []
    if 'content_type_id' not in cols:
        defer.append('content_type')
    if 'object_id' not in cols:
        defer.append('object_id')
    if 'utilisateur_id' not in cols:
        defer.append('utilisateur')
    qs = MouvementCaisse.objects.all()
    if defer:
        qs = qs.defer(*defer)
    return qs


def mouvementcaisse_queryset():
    """Raccourci : un seul ``SHOW COLUMNS`` si vous n'avez pas déjà les noms de colonnes."""
    return build_mouvementcaisse_queryset()
