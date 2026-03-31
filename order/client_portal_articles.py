from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from stock.models import Article
from stock.services.article_search import DEFAULT_LIMIT, MAX_LIMIT, search_articles

from .authentication import ClientJWTAuthentication
from .permissions import IsClientAuthenticated


@swagger_auto_schema(
    method="get",
    operation_summary="Recherche articles (portail client) — retourne le PK Django",
    operation_description=(
        "Recherche d'articles pour la création de commandes client.\n\n"
        "- Auth: JWT portail client (Bearer)\n"
        "- Scope: entreprise/succursale du membership\n"
        "- Retourne **id** (PK Django) + champs d'affichage.\n"
        "Utilisez `id` comme `article_id` dans POST /api/commandes/."
    ),
    manual_parameters=[
        openapi.Parameter("q", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True),
        openapi.Parameter("limit", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False),
        openapi.Parameter("offset", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False),
    ],
    responses={200: "results + meta", 400: "q requis"},
    tags=["Portail client & commandes"],
)
@api_view(["GET"])
@authentication_classes([ClientJWTAuthentication])
@permission_classes([IsClientAuthenticated])
def client_portal_articles_search(request):
    q = (request.query_params.get("q") or "").strip()
    if not q:
        return Response({"detail": "Indiquez « q »."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        limit = int(request.query_params.get("limit", DEFAULT_LIMIT))
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT
    try:
        offset = int(request.query_params.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0
    limit = min(max(1, limit), MAX_LIMIT)
    offset = max(0, offset)

    m = request.client_membership
    articles, meta = search_articles(
        entreprise_id=m.entreprise_id,
        succursale_id=m.succursale_id,
        q=q,
        limit=limit,
        offset=offset,
    )

    # Serializer léger, incluant le PK Django requis par CommandeItemWriteSerializer
    results = []
    for a in articles:
        # `a` peut être un objet Article annoté ; on s'assure d'avoir les champs utiles.
        results.append(
            {
                "id": a.pk,
                "article_id": getattr(a, "article_id", None),
                "nom_scientifique": getattr(a, "nom_scientifique", None),
                "nom_commercial": getattr(a, "nom_commercial", None),
            }
        )
    return Response({"results": results, "meta": meta})

