import jwt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django.utils.translation import gettext as _

from stock.models import Client, ClientEntreprise, DetteClient, Sortie, Succursale
from stock.serializers import EntrepriseSerializer, SuccursaleSerializer

from .authentication import ClientJWTAuthentication
from .branch_scope import branch_q_for_membership
from .models import Commande
from .commande_serializers import CommandeListSerializer
from .jwt_client import issue_client_tokens, refresh_client_access
from .openapi_params import TAG_PORTAIL_CLIENT
from .permissions import IsClientAuthenticated


def _client_public_dict(c: Client):
    return {
        "id": c.id,
        "nom": c.nom,
        "email": c.email,
        "telephone": c.telephone,
        "adresse": c.adresse,
    }


def _contexte_dict(m: ClientEntreprise):
    return {
        "membership_id": m.id,
        "entreprise_id": m.entreprise_id,
        "succursale_id": m.succursale_id,
    }


def _entreprises_portal_payload(request, liens):
    """Pour chaque lien client↔entreprise : entreprise complète + liste des succursales."""
    out = []
    for lien in liens:
        ent = lien.entreprise
        ent_data = EntrepriseSerializer(ent, context={"request": request}).data
        succs = SuccursaleSerializer(
            Succursale.objects.filter(entreprise=ent).order_by("nom"),
            many=True,
            context={"request": request},
        ).data
        out.append(
            {
                "lien": {
                    "id": lien.id,
                    "entreprise_id": lien.entreprise_id,
                    "succursale_id": lien.succursale_id,
                    "is_special": lien.is_special,
                },
                "entreprise": ent_data,
                "succursales": succs,
            }
        )
    return out


@swagger_auto_schema(
    method="post",
    operation_summary="Connexion portail client (e-mail + mot de passe)",
    operation_description=(
        "Authentifie un **Client** global (une fiche par personne) par e-mail et mot de passe. "
        "Réponse : **toutes** les entreprises liées (`ClientEntreprise`) avec données complètes "
        "et succursales. Les JWT portail portent un **membership_id** (contexte entreprise/succursale). "
        "Si le client a **plusieurs** entreprises, le body doit inclure **`entreprise_id`** pour choisir "
        "le contexte des tokens ; sinon **400** avec la liste `entreprises` pour sélection."
    ),
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["email", "password"],
        properties={
            "email": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL),
            "password": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD),
            "entreprise_id": openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description="Obligatoire si plusieurs liens entreprise ; sinon optionnel (contexte unique).",
                nullable=True,
            ),
        },
    ),
    responses={
        200: openapi.Response(
            "Tokens + client + entreprises + contexte",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "access": openapi.Schema(type=openapi.TYPE_STRING),
                    "refresh": openapi.Schema(type=openapi.TYPE_STRING),
                    "client": openapi.Schema(type=openapi.TYPE_OBJECT),
                    "entreprises": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    "contexte": openapi.Schema(type=openapi.TYPE_OBJECT),
                },
            ),
        ),
        400: "Identifiants invalides ou sélection d'entreprise requise",
    },
    tags=[TAG_PORTAIL_CLIENT],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def client_portal_login(request):
    email = (request.data.get("email") or "").strip()
    password = request.data.get("password") or ""
    if not email:
        return Response({"detail": _("L’e-mail est obligatoire.")}, status=status.HTTP_400_BAD_REQUEST)

    client = Client.objects.filter(email__iexact=email).first()
    if not client or not client.has_portal_password():
        return Response(
            {"detail": _("Identifiants invalides ou compte non activé pour le portail.")},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not client.check_password(password):
        return Response({"detail": _("Identifiants invalides.")}, status=status.HTTP_400_BAD_REQUEST)

    liens = list(
        ClientEntreprise.objects.filter(client=client)
        .select_related("entreprise", "succursale")
        .order_by("entreprise_id")
    )
    if not liens:
        return Response(
            {"detail": _("Aucune entreprise n’est associée à ce compte client.")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    entreprises_payload = _entreprises_portal_payload(request, liens)

    raw_eid = request.data.get("entreprise_id")
    if len(liens) > 1:
        if raw_eid is None or str(raw_eid).strip() == "":
            return Response(
                {
                    "detail": _("Indiquez « entreprise_id » pour choisir le contexte de travail."),
                    "client": _client_public_dict(client),
                    "entreprises": entreprises_payload,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            eid = int(raw_eid)
        except (TypeError, ValueError):
            return Response(
                {"detail": _("Le champ « entreprise_id » doit être un entier.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        membership = next((x for x in liens if x.entreprise_id == eid), None)
        if not membership:
            return Response(
                {"detail": _("L’entreprise indiquée n’est pas liée à ce compte.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
    else:
        membership = liens[0]
        if raw_eid is not None and str(raw_eid).strip() != "":
            try:
                eid = int(raw_eid)
            except (TypeError, ValueError):
                return Response(
                    {"detail": _("Le champ « entreprise_id » doit être un entier.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if eid != membership.entreprise_id:
                return Response(
                    {"detail": _("L’entreprise indiquée ne correspond pas au seul lien disponible.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

    access, refresh = issue_client_tokens(client, membership)
    return Response(
        {
            "access": access,
            "refresh": refresh,
            "client": _client_public_dict(client),
            "entreprises": entreprises_payload,
            "contexte": _contexte_dict(membership),
        }
    )


@swagger_auto_schema(
    method="post",
    operation_summary="Rafraîchir les tokens portail client",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["refresh"],
        properties={"refresh": openapi.Schema(type=openapi.TYPE_STRING)},
    ),
    responses={200: "Nouveaux access + refresh"},
    tags=[TAG_PORTAIL_CLIENT],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def client_portal_refresh(request):
    raw = (request.data.get("refresh") or "").strip()
    if not raw:
        return Response({"detail": _("Le champ « refresh » est obligatoire.")}, status=status.HTTP_400_BAD_REQUEST)
    try:
        access, refresh = refresh_client_access(raw)
    except jwt.PyJWTError:
        return Response({"detail": _("Refresh token invalide ou expiré.")}, status=status.HTTP_401_UNAUTHORIZED)
    return Response({"access": access, "refresh": refresh})


@swagger_auto_schema(
    method="post",
    operation_summary="Changer de contexte (entreprise / succursale) — portail client",
    operation_description=(
        "Permet au client connecté de sélectionner l’entreprise active (lien `ClientEntreprise`). "
        "Retourne de nouveaux JWT (`access`, `refresh`) et le nouveau contexte."
    ),
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["entreprise_id"],
        properties={
            "entreprise_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            "succursale_id": openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
        },
    ),
    responses={200: "Nouveaux access + refresh + contexte"},
    tags=[TAG_PORTAIL_CLIENT],
)
@api_view(["POST"])
@authentication_classes([ClientJWTAuthentication])
@permission_classes([IsClientAuthenticated])
def client_portal_select_context(request):
    client = request.client
    try:
        entreprise_id = int(request.data.get("entreprise_id"))
    except (TypeError, ValueError):
        return Response(
            {"detail": _("Le champ « entreprise_id » est obligatoire et doit être un entier.")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    membership = (
        ClientEntreprise.objects.filter(client=client, entreprise_id=entreprise_id)
        .select_related("entreprise", "succursale")
        .first()
    )
    if not membership:
        return Response({"detail": _("Vous n’êtes pas lié à cette entreprise.")}, status=status.HTTP_400_BAD_REQUEST)

    raw_sid = request.data.get("succursale_id")
    if raw_sid is not None:
        if str(raw_sid).strip() == "":
            membership.succursale_id = None
            membership.save(update_fields=["succursale"])
        else:
            try:
                sid = int(raw_sid)
            except (TypeError, ValueError):
                return Response(
                    {"detail": _("Le champ « succursale_id » doit être un entier.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not Succursale.objects.filter(pk=sid, entreprise_id=entreprise_id).exists():
                return Response({"detail": _("Succursale invalide pour cette entreprise.")}, status=status.HTTP_400_BAD_REQUEST)
            membership.succursale_id = sid
            membership.save(update_fields=["succursale"])

    access, refresh = issue_client_tokens(client, membership)
    return Response({"access": access, "refresh": refresh, "contexte": _contexte_dict(membership)})


@swagger_auto_schema(
    method="get",
    operation_summary="Tableau de bord client (dettes, ventes, commandes — périmètre membership)",
    manual_parameters=[
        openapi.Parameter(
            "Authorization",
            openapi.IN_HEADER,
            description="Bearer &lt;access_token_portail&gt;",
            type=openapi.TYPE_STRING,
            required=True,
        ),
    ],
    tags=[TAG_PORTAIL_CLIENT],
)
@api_view(["GET"])
@authentication_classes([ClientJWTAuthentication])
@permission_classes([IsClientAuthenticated])
def client_portal_dashboard(request):
    client = request.client
    m = request.client_membership
    bq = branch_q_for_membership(m)
    dettes = (
        DetteClient.objects.filter(client=client, entreprise_id=m.entreprise_id)
        .filter(bq)
        .select_related("devise", "sortie")
        .order_by("-date_creation")[:100]
    )
    dettes_data = [
        {
            "id": d.id,
            "montant_total": str(d.montant_total),
            "montant_paye": str(d.montant_paye),
            "solde_restant": str(d.solde_restant),
            "statut": d.statut,
            "date_creation": d.date_creation,
            "devise_sigle": d.devise.sigle if d.devise else None,
            "sortie_id": d.sortie_id,
        }
        for d in dettes
    ]
    sorties = (
        Sortie.objects.filter(client=client, entreprise_id=m.entreprise_id)
        .filter(bq)
        .prefetch_related("lignes__article", "lignes__devise")
        .order_by("-date_creation")[:50]
    )
    sorties_data = []
    for s in sorties:
        sorties_data.append(
            {
                "id": s.id,
                "date_creation": s.date_creation,
                "statut": s.statut,
                "motif": s.motif,
                "lignes": [
                    {
                        "article_id": l.article_id,
                        "nom_scientifique": l.article.nom_scientifique if l.article else None,
                        "quantite": l.quantite,
                        "prix_unitaire": str(l.prix_unitaire),
                    }
                    for l in s.lignes.all()
                ],
            }
        )
    commandes = (
        Commande.objects.filter(client=client, entreprise_id=m.entreprise_id)
        .filter(bq)
        .order_by("-created_at")[:50]
    )
    commandes_data = CommandeListSerializer(commandes, many=True, context={"request": request}).data

    return Response(
        {
            "client": _client_public_dict(client),
            "contexte": _contexte_dict(m),
            "dettes": dettes_data,
            "ventes": sorties_data,
            "commandes": commandes_data,
        }
    )
