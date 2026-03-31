from django.utils.translation import gettext as _
from rest_framework import serializers

from stock.models import Article, Client
from stock.serializers import ArticleSerializer
from stock.services.tenant_context import get_tenant_ids

from .models import Commande, CommandeItem, CommandeResponse


def _check_commande_items_catalogue(items, tenant_id, commande_succursale_id):
    """Cohérence articles (entreprise / succursale) pour les lignes de commande."""
    for it in items:
        art = it.get("article")
        if art is None:
            continue
        if tenant_id is not None and art.entreprise_id != tenant_id:
            raise serializers.ValidationError(
                {"items": _("Chaque article catalogue doit appartenir à la même entreprise que la commande.")}
            )
        if commande_succursale_id is None:
            if art.succursale_id is not None:
                raise serializers.ValidationError(
                    {
                        "items": _(
                            "Un article rattaché à une succursale nécessite une commande avec succursale "
                            "(ou utilisez un article sans succursale : catalogue global)."
                        )
                    }
                )
        elif art.succursale_id is not None and art.succursale_id != commande_succursale_id:
            raise serializers.ValidationError(
                {
                    "items": _(
                        "Chaque article catalogue doit être de la même succursale que la commande "
                        "(ou un article sans succursale : catalogue global)."
                    )
                }
            )


class CommandeItemWriteSerializer(serializers.ModelSerializer):
    """Création / mise à jour de ligne : article catalogue OU nom libre (exclusif)."""

    article_id = serializers.PrimaryKeyRelatedField(
        queryset=Article.objects.all(),
        source="article",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = CommandeItem
        fields = ("article_id", "nom_article", "quantite")

    def validate_quantite(self, value):
        if value is None or value < 1:
            raise serializers.ValidationError(_("La quantité doit être au moins 1."))
        return value

    def validate(self, attrs):
        article = attrs.get("article")
        nom = (attrs.get("nom_article") or "").strip()
        if article is not None and nom:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        _("Renseignez soit un article du catalogue (`article_id`), soit un nom libre (`nom_article`), pas les deux."),
                    ]
                }
            )
        if article is None and not nom:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        _("Renseignez soit un article du catalogue (`article_id`), soit un nom libre (`nom_article`)."),
                    ]
                }
            )
        if nom:
            attrs["nom_article"] = nom
        return attrs


class CommandeItemReadSerializer(serializers.ModelSerializer):
    article_id = serializers.CharField(source="article.article_id", read_only=True, allow_null=True)
    article = ArticleSerializer(read_only=True)

    class Meta:
        model = CommandeItem
        fields = ("id", "article_id", "article", "nom_article", "quantite")


class CommandeResponseSerializer(serializers.ModelSerializer):
    auteur_nom = serializers.SerializerMethodField()

    class Meta:
        model = CommandeResponse
        fields = ("id", "commande", "commentaire", "auteur", "auteur_nom", "created_at")
        read_only_fields = ("id", "auteur", "created_at")

    def get_auteur_nom(self, obj):
        u = obj.auteur
        if not u:
            return ""
        return (u.get_full_name() or "").strip() or u.username


class CommandeResponseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommandeResponse
        fields = ("commentaire",)

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["commande"] = self.context["commande"]
        user = getattr(request, "user", None)
        validated_data["auteur"] = user if (user and getattr(user, "is_authenticated", False)) else None
        return super().create(validated_data)


class CommandeResponseUpdateSerializer(serializers.ModelSerializer):
    """Mise à jour du texte par le staff (auteur inchangé)."""

    class Meta:
        model = CommandeResponse
        fields = ("commentaire",)


class CommandeListSerializer(serializers.ModelSerializer):
    """Liste synthétique (sans items détaillés)."""

    client_nom = serializers.CharField(source="client.nom", read_only=True)

    class Meta:
        model = Commande
        fields = (
            "id",
            "reference",
            "nom",
            "statut",
            "client",
            "client_nom",
            "entreprise",
            "succursale",
            "note_client",
            "created_at",
            "updated_at",
        )


class CommandeDetailSerializer(serializers.ModelSerializer):
    items = CommandeItemReadSerializer(many=True, read_only=True)
    reponses = CommandeResponseSerializer(many=True, read_only=True)
    client_nom = serializers.CharField(source="client.nom", read_only=True)

    class Meta:
        model = Commande
        fields = (
            "id",
            "reference",
            "nom",
            "statut",
            "client",
            "client_nom",
            "entreprise",
            "succursale",
            "note_client",
            "items",
            "reponses",
            "created_at",
            "updated_at",
        )


class CommandeCreateSerializer(serializers.ModelSerializer):
    items = CommandeItemWriteSerializer(many=True)
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source="client",
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = Commande
        fields = ("client_id", "succursale", "nom", "note_client", "items")

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(_("Au moins une ligne de commande est requise."))
        return value

    def _resolve_succursale_pk(self, attrs):
        """Succursale de la commande : corps, lien client↔entreprise, ou contexte JWT (admin)."""
        request = self.context.get("request")
        body = attrs.get("succursale")
        if getattr(request, "client", None):
            m = request.client_membership
            if body is not None:
                if body.entreprise_id != m.entreprise_id:
                    raise serializers.ValidationError(
                        {"succursale": _("La succursale doit appartenir à l’entreprise du contexte portail.")}
                    )
                if m.succursale_id is not None and body.pk != m.succursale_id:
                    raise serializers.ValidationError(
                        {"succursale": _("La succursale doit être celle du lien client pour cette entreprise.")}
                    )
                return body.pk
            return m.succursale_id

        tenant_id, branch_id = get_tenant_ids(request)
        client = attrs.get("client")
        if not client:
            raise serializers.ValidationError(_("Le champ « client_id » est obligatoire pour un administrateur."))
        if not client.liens_entreprise.filter(entreprise_id=tenant_id).exists():
            raise serializers.ValidationError(
                {"client_id": _("Le client doit être lié à votre entreprise (ClientEntreprise).")}
            )
        if body is not None:
            if body.entreprise_id != tenant_id:
                raise serializers.ValidationError(
                    {"succursale": _("La succursale doit appartenir à votre entreprise.")}
                )
            if branch_id is not None and body.pk != branch_id:
                raise serializers.ValidationError(
                    {
                        "succursale": _(
                            "La succursale doit correspondre au contexte JWT (succursale courante)."
                        )
                    }
                )
            return body.pk
        if branch_id is not None:
            return branch_id
        lien = client.liens_entreprise.filter(entreprise_id=tenant_id).first()
        return lien.succursale_id if lien else None

    def _check_articles(self, items, tenant_id, commande_succursale_id):
        _check_commande_items_catalogue(items, tenant_id, commande_succursale_id)

    def validate(self, attrs):
        request = self.context.get("request")
        items = attrs.get("items") or []

        if getattr(request, "client", None):
            tid = request.client_membership.entreprise_id
        else:
            tid, branch_id = get_tenant_ids(request)
            if not attrs.get("client"):
                raise serializers.ValidationError(_("Le champ « client_id » est obligatoire pour un administrateur."))
            if not attrs["client"].liens_entreprise.filter(entreprise_id=tid).exists():
                raise serializers.ValidationError(
                    {"client_id": _("Le client doit être lié à votre entreprise (ClientEntreprise).")}
                )

        resolved_sid = self._resolve_succursale_pk(attrs)
        attrs["_resolved_succursale_id"] = resolved_sid
        self._check_articles(items, tid, resolved_sid)
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        resolved_sid = validated_data.pop("_resolved_succursale_id")
        items_data = validated_data.pop("items")
        validated_data.pop("succursale", None)
        nom_cmd = str(validated_data.pop("nom", "") or "").strip()
        note = validated_data.get("note_client") or ""
        if getattr(request, "client", None):
            client = request.client
            m = request.client_membership
            commande = Commande.objects.create(
                client=client,
                entreprise_id=m.entreprise_id,
                succursale_id=resolved_sid,
                nom=nom_cmd,
                note_client=note,
            )
        else:
            client = validated_data.pop("client")
            tenant_id, branch_id_unused = get_tenant_ids(request)
            commande = Commande.objects.create(
                client=client,
                entreprise_id=tenant_id,
                succursale_id=resolved_sid,
                nom=nom_cmd,
                note_client=note,
            )

        for row in items_data:
            art = row.get("article")
            nom = (row.get("nom_article") or "").strip()
            CommandeItem.objects.create(
                commande=commande,
                article=art if art else None,
                nom_article=nom if not art else "",
                quantite=row["quantite"],
            )
        return commande


class CommandeUpdateAdminSerializer(serializers.ModelSerializer):
    """
    Staff (admin ou employé) : modification du **statut uniquement**,
    vers **rejetée** ou **livrée** (équivalent API : REJETEE, LIVREE).
    """

    class Meta:
        model = Commande
        fields = ("statut",)

    def validate_statut(self, value):
        allowed = (Commande.StatutCommande.REJETEE, Commande.StatutCommande.LIVREE)
        if value not in allowed:
            raise serializers.ValidationError(
                _(
                    "Les employés et administrateurs ne peuvent fixer le statut "
                    "qu’à « rejetée » ou « livrée » (valeurs REJETEE, LIVREE)."
                )
            )
        return value


class CommandeClientUpdateSerializer(serializers.ModelSerializer):
    """Client : mise à jour uniquement si la commande est **en attente** (EN_ATTENTE)."""

    items = CommandeItemWriteSerializer(many=True, required=False)

    class Meta:
        model = Commande
        fields = ("nom", "note_client", "succursale", "items")

    def _resolve_client_succursale_update(self, attrs):
        request = self.context["request"]
        body = attrs.get("succursale")
        m = request.client_membership
        inst = self.instance
        if body is not None:
            if body.entreprise_id != m.entreprise_id:
                raise serializers.ValidationError(
                    {"succursale": _("La succursale doit appartenir à l’entreprise du contexte portail.")}
                )
            if m.succursale_id is not None and body.pk != m.succursale_id:
                raise serializers.ValidationError(
                    {"succursale": _("La succursale doit être celle du lien client pour cette entreprise.")}
                )
            return body.pk
        return inst.succursale_id

    def validate(self, attrs):
        if self.instance.statut != Commande.StatutCommande.EN_ATTENTE:
            raise serializers.ValidationError(
                {"detail": _("Seules les commandes en attente peuvent être modifiées.")}
            )
        request = self.context["request"]
        tid = request.client_membership.entreprise_id
        items = attrs.get("items")
        if items is not None or "succursale" in attrs:
            sid = self._resolve_client_succursale_update(attrs)
            attrs["_resolved_succursale_id"] = sid
        if items is not None:
            if not items:
                raise serializers.ValidationError({"items": _("Au moins une ligne de commande est requise.")})
            _check_commande_items_catalogue(items, tid, attrs["_resolved_succursale_id"])
        return attrs

    def update(self, instance, validated_data):
        validated_data.pop("succursale", None)
        sid = validated_data.pop("_resolved_succursale_id", None)
        items_data = validated_data.pop("items", None)
        if sid is not None:
            validated_data["succursale_id"] = sid
        instance = super().update(instance, validated_data)
        if items_data is not None:
            instance.items.all().delete()
            for row in items_data:
                art = row.get("article")
                nom = (row.get("nom_article") or "").strip()
                CommandeItem.objects.create(
                    commande=instance,
                    article=art if art else None,
                    nom_article=nom if not art else "",
                    quantite=row["quantite"],
                )
        return instance
