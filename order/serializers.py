from datetime import datetime

from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _
from django.db.models import Sum
from rest_framework import serializers

from stock.models import Article, Devise
from stock.serializers import ArticleSerializer, LocalizedDecimalField
from stock.services.tenant_context import get_tenant_ids

from .models import Fournisseur, FraisLot, Lot, LotItem
from .services.lot_closure import apply_stock_on_lot_closure


class LotClosureApprovisionnementSerializer(serializers.Serializer):
    """Payload uniquement à la clôture : alimente ``LigneEntree``, rien n'est stocké sur ``LotItem``."""

    article_id = serializers.CharField()
    prix_vente = serializers.DecimalField(max_digits=14, decimal_places=2)
    seuil_alerte = LocalizedDecimalField(max_digits=12, decimal_places=3, min_value=0)
    date_expiration = serializers.DateField(required=False, allow_null=True)

    def validate_article_id(self, value):
        s = str(value).strip()
        if not s:
            raise serializers.ValidationError(_("Identifiant article requis."))
        return s


def _filter_queryset_by_tenant(qs, request):
    """Filtre un queryset par `entreprise_id` / `succursale_id` (si champs présents)."""
    tenant_id, branch_id = get_tenant_ids(request)
    if tenant_id is None:
        return qs.none()

    if hasattr(qs.model, "entreprise_id"):
        qs = qs.filter(entreprise_id=tenant_id)
    if branch_id is not None and hasattr(qs.model, "succursale_id"):
        qs = qs.filter(succursale_id=branch_id)
    return qs


class FournisseurSerializer(serializers.ModelSerializer):
    """CRUD fournisseur (périmètre entreprise imposé par la vue / le tenant)."""

    class Meta:
        model = Fournisseur
        fields = [
            "id",
            "code",
            "nom",
            "telephone",
            "email",
            "adresse",
            "ville",
            "pays",
            "nif",
            "notes",
            "is_active",
            "entreprise",
            "succursale",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "entreprise", "created_at", "updated_at"]

    def validate_code(self, value):
        if value is not None and str(value).strip() == "":
            return ""
        return str(value).strip() if value is not None else value

    def validate(self, attrs):
        request = self.context.get("request")
        tenant_id, branch_id = get_tenant_ids(request)
        if tenant_id is None:
            raise serializers.ValidationError(_("Contexte entreprise manquant."))
        code = attrs.get("code", None)
        if self.instance is not None and code is None:
            code = self.instance.code
        code_stripped = str(code).strip() if code is not None else ""
        if code_stripped:
            qs = Fournisseur.objects.filter(entreprise_id=tenant_id, code=code_stripped)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"code": _("Ce code fournisseur existe déjà pour votre entreprise.")})
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        tenant_id, branch_id = get_tenant_ids(request)
        validated_data["entreprise_id"] = tenant_id
        validated_data["succursale_id"] = branch_id
        return super().create(validated_data)


class FraisLotSerializer(serializers.ModelSerializer):
    devise_id = serializers.PrimaryKeyRelatedField(
        source="devise",
        queryset=Devise.objects.all(),
        allow_null=False,
    )

    class Meta:
        model = FraisLot
        fields = [
            "id",
            "lot",
            "type_frais",
            "montant",
            "devise_id",
            "entreprise",
            "succursale",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "entreprise", "succursale", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is None:
            return
        self.fields["devise_id"].queryset = _filter_queryset_by_tenant(
            self.fields["devise_id"].queryset, request
        )

    def validate_lot(self, lot):
        request = self.context.get("request")
        tenant_id, branch_id = get_tenant_ids(request)
        if lot.entreprise_id != tenant_id:
            raise serializers.ValidationError(_("Le lot ne correspond pas à votre entreprise."))
        if lot.statut in (Lot.StatutLot.ARRIVE, Lot.StatutLot.CLOTURE):
            raise serializers.ValidationError(
                _("Impossible d'ajouter ou de modifier des frais : le lot est arrivé ou clôturé.")
            )
        return lot

    def validate(self, attrs):
        lot = attrs.get("lot")
        if lot is None and self.instance is not None:
            lot = self.instance.lot
        if lot and lot.statut in (Lot.StatutLot.ARRIVE, Lot.StatutLot.CLOTURE):
            raise serializers.ValidationError(
                _("Impossible d'ajouter ou de modifier des frais : le lot est arrivé ou clôturé.")
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        tenant_id, branch_id = get_tenant_ids(request)
        validated_data["entreprise_id"] = tenant_id
        validated_data["succursale_id"] = branch_id
        return super().create(validated_data)


class LotItemSerializer(serializers.ModelSerializer):
    """En écriture : `article_id` (PK métier). En lecture : objet `article` complet + `article_id` rappel."""

    article_id = serializers.PrimaryKeyRelatedField(
        source="article",
        queryset=Article.objects.all(),
        write_only=True,
        required=False,
    )
    article = ArticleSerializer(read_only=True)
    quantite = LocalizedDecimalField(max_digits=12, decimal_places=3)

    class Meta:
        model = LotItem
        fields = [
            "id",
            "lot",
            "article_id",
            "article",
            "quantite",
            "prix_achat_unitaire",
            "entreprise",
            "succursale",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "entreprise", "succursale", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is None:
            return
        self.fields["article_id"].queryset = _filter_queryset_by_tenant(
            self.fields["article_id"].queryset, request
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Réexpose le code article en clair (PK métier) pour compatibilité avec les clients existants.
        if getattr(instance, "article_id", None) and getattr(instance, "article", None):
            data["article_id"] = instance.article.article_id
        return data

    def validate_lot(self, lot):
        request = self.context.get("request")
        tenant_id, branch_id = get_tenant_ids(request)
        if lot.entreprise_id != tenant_id:
            raise serializers.ValidationError(_("Le lot ne correspond pas à votre entreprise."))
        return lot

    def validate(self, attrs):
        article = attrs.get("article") or (self.instance.article if self.instance else None)
        lot = attrs.get("lot") or (self.instance.lot if self.instance else None)
        if lot:
            if lot.statut in (Lot.StatutLot.ARRIVE, Lot.StatutLot.CLOTURE) or getattr(
                lot, "entree_stock_id", None
            ):
                raise serializers.ValidationError(
                    _(
                        "Impossible de créer, modifier ou supprimer des lignes d'article : "
                        "le lot est arrivé ou clôturé."
                    )
                )
        if article and lot and article.entreprise_id != lot.entreprise_id:
            raise serializers.ValidationError(
                {"article_id": _("L'article et le lot doivent appartenir à la même entreprise.")}
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        tenant_id, branch_id = get_tenant_ids(request)
        validated_data["entreprise_id"] = tenant_id
        validated_data["succursale_id"] = branch_id
        return super().create(validated_data)


class LotSerializer(serializers.ModelSerializer):
    fournisseur_id = serializers.PrimaryKeyRelatedField(
        source="fournisseur",
        queryset=Fournisseur.objects.all(),
        required=False,
        allow_null=True,
    )

    items = LotItemSerializer(many=True, read_only=True)
    frais = FraisLotSerializer(many=True, read_only=True)
    total_frais = serializers.SerializerMethodField(read_only=True)
    approvisionnement = LotClosureApprovisionnementSerializer(
        many=True,
        write_only=True,
        required=False,
        help_text=(
            "Obligatoire lors du passage à statut CLOTURE : une entrée par article du lot "
            "(article_id métier, prix_vente, seuil_alerte, date_expiration optionnelle). "
            "Non persisté sur le lot ; copié vers LigneEntree à la clôture."
        ),
    )

    class Meta:
        model = Lot
        fields = [
            "id",
            "reference",
            "fournisseur_id",
            "date_expedition",
            "date_arrivee_prevue",
            "statut",
            "date_cloture",
            "entree_stock",
            "entreprise",
            "succursale",
            "created_at",
            "updated_at",
            "items",
            "frais",
            "total_frais",
            "approvisionnement",
        ]
        read_only_fields = [
            "id",
            "entreprise",
            "succursale",
            "created_at",
            "updated_at",
            "items",
            "frais",
            "entree_stock",
        ]

    def get_total_frais(self, obj: Lot):
        # Somme des frais du lot (toutes lignes confondues).
        # Note : si plusieurs devises existent, il s'agit d'un total "brut" ; à normaliser côté reporting si besoin.
        total = obj.frais.all().aggregate(s=Sum("montant"))["s"]
        return str(total or 0)

    @staticmethod
    def _lot_same_calendar_date(a, b) -> bool:
        """Compare deux dates (date ou datetime) en ignorant l’heure."""
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        da = a.date() if isinstance(a, datetime) else a
        db = b.date() if isinstance(b, datetime) else b
        return da == db

    def _lot_field_value_unchanged(self, instance: Lot, field_name: str, value) -> bool:
        """True si la valeur proposée est identique à l'instance (PATCH qui renvoie tout l'objet GET)."""
        if field_name == "reference":
            return str(value or "").strip() == str(instance.reference or "").strip()
        # PrimaryKeyRelatedField(source="fournisseur") → clé interne « fournisseur », pas « fournisseur_id »
        if field_name in ("fournisseur", "fournisseur_id"):
            if value is None:
                return instance.fournisseur_id is None
            pk = getattr(value, "pk", value)
            return pk == instance.fournisseur_id
        if field_name == "date_expedition":
            return self._lot_same_calendar_date(value, instance.date_expedition)
        if field_name == "date_arrivee_prevue":
            return self._lot_same_calendar_date(value, instance.date_arrivee_prevue)
        if field_name == "date_cloture":
            return self._lot_same_calendar_date(value, instance.date_cloture)
        if field_name == "statut":
            return value == instance.statut
        return False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # PUT/PATCH : ne pas exiger tous les champs (le front n'envoie pas toujours le corps complet).
        if self.instance is not None:
            for name in (
                "reference",
                "date_expedition",
                "statut",
                "date_cloture",
                "date_arrivee_prevue",
            ):
                if name in self.fields:
                    self.fields[name].required = False
        request = self.context.get("request")
        if request is None:
            return
        self.fields["fournisseur_id"].queryset = _filter_queryset_by_tenant(
            self.fields["fournisseur_id"].queryset, request
        )

    def validate_fournisseur(self, value):
        if value is None:
            return value
        request = self.context.get("request")
        tenant_id, branch_id = get_tenant_ids(request)
        if value.entreprise_id != tenant_id:
            raise serializers.ValidationError(_("Ce fournisseur n'appartient pas à votre entreprise."))
        return value

    def create(self, validated_data):
        if validated_data.get("statut") == Lot.StatutLot.CLOTURE:
            raise serializers.ValidationError(
                {
                    "statut": _(
                        "Impossible de créer un lot directement à l'état « clôturé ». "
                        "Créez le lot et ses lignes, puis mettez à jour le statut avec le payload "
                        "`approvisionnement` pour la clôture."
                    )
                }
            )
        request = self.context.get("request")
        tenant_id, branch_id = get_tenant_ids(request)
        validated_data["entreprise_id"] = tenant_id
        validated_data["succursale_id"] = branch_id
        try:
            return super().create(validated_data)
        except IntegrityError:
            ref = str(validated_data.get("reference", "") or "").strip()
            msg = _(
                "Un lot avec la référence « %(ref)s » existe déjà pour cette entreprise."
            ) % {"ref": ref or "?"}
            raise serializers.ValidationError({"reference": msg}) from None

    @transaction.atomic
    def update(self, instance, validated_data):
        approvisionnement = validated_data.pop("approvisionnement", None)
        new_statut = validated_data.get("statut", instance.statut)
        old_statut = instance.statut
        closing = new_statut == Lot.StatutLot.CLOTURE and old_statut != Lot.StatutLot.CLOTURE
        if closing:
            appr_list = [dict(row) for row in (approvisionnement or [])]
            apply_stock_on_lot_closure(instance, appr_list)
            instance.refresh_from_db()
        return super().update(instance, validated_data)

    def validate(self, attrs):
        request = self.context.get("request")
        inst = self.instance

        # Lot ARRIVÉ : le front envoie souvent tout le corps (référence, dates, fournisseur inchangés).
        # On retire les champs strictement identiques à l'instance avant de contrôler la clôture.
        if inst is not None and inst.statut == Lot.StatutLot.ARRIVE:
            allowed_closure = {"statut", "approvisionnement", "date_cloture"}
            for key in list(attrs.keys()):
                if key in allowed_closure:
                    if key == "statut" and self._lot_field_value_unchanged(inst, key, attrs[key]):
                        del attrs[key]
                    elif key == "date_cloture" and self._lot_same_calendar_date(
                        attrs.get("date_cloture"), inst.date_cloture
                    ):
                        del attrs[key]
                    continue
                if self._lot_field_value_unchanged(inst, key, attrs[key]):
                    del attrs[key]
                else:
                    raise serializers.ValidationError(
                        {
                            "detail": _(
                                "Un lot arrivé ne peut être modifié que pour être clôturé "
                                "(statut CLOTURE, approvisionnement, date_cloture optionnelle). "
                                "Les autres champs ne peuvent pas être modifiés."
                            )
                        }
                    )

        tenant_id, branch_id = get_tenant_ids(request) if request else (None, None)
        if tenant_id is not None:
            ref = attrs.get("reference")
            if ref is not None and str(ref).strip() != "":
                ref_s = str(ref).strip()
                qs = Lot.objects.filter(entreprise_id=tenant_id, reference=ref_s)
                if self.instance is not None:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise serializers.ValidationError(
                        {
                            "reference": _(
                                "Un lot avec la référence « %(ref)s » existe déjà pour cette entreprise."
                            )
                            % {"ref": ref_s}
                        }
                    )

        if inst is not None:
            if inst.statut == Lot.StatutLot.CLOTURE and attrs:
                raise serializers.ValidationError(
                    {"detail": _("Un lot clôturé ne peut plus être modifié.")}
                )
            if inst.statut == Lot.StatutLot.ARRIVE:
                incoming = set(attrs.keys())
                if not incoming.issubset({"statut", "approvisionnement", "date_cloture"}):
                    raise serializers.ValidationError(
                        {
                            "detail": _(
                                "Un lot arrivé ne peut être modifié que pour être clôturé "
                                "(statut CLOTURE, approvisionnement, date_cloture optionnelle)."
                            )
                        }
                    )
                new_s = attrs.get("statut", Lot.StatutLot.ARRIVE)
                if new_s != Lot.StatutLot.CLOTURE and incoming:
                    raise serializers.ValidationError(
                        {
                            "detail": _(
                                "Un lot arrivé ne peut être modifié que pour être clôturé."
                            )
                        }
                    )

        if self.instance is not None:
            new_statut = attrs.get("statut", self.instance.statut)
            old_statut = self.instance.statut
            if new_statut == Lot.StatutLot.CLOTURE and old_statut != Lot.StatutLot.CLOTURE:
                appr = attrs.get("approvisionnement")
                if appr is None or (isinstance(appr, list) and len(appr) == 0):
                    raise serializers.ValidationError(
                        {
                            "approvisionnement": _(
                                "Obligatoire pour clôturer : tableau avec une entrée par article du lot "
                                "(clés : article_id, prix_vente, seuil_alerte ; date_expiration optionnelle). "
                                "Ces valeurs ne sont pas enregistrées sur les lignes de lot ; elles alimentent "
                                "uniquement les lignes d'entrée en stock."
                            )
                        }
                    )
        if attrs.get("statut") == Lot.StatutLot.CLOTURE:
            dc = attrs.get("date_cloture")
            de = attrs.get("date_expedition")
            if self.instance is not None:
                if de is None:
                    de = self.instance.date_expedition
                if dc is None:
                    dc = self.instance.date_cloture
            if dc and de and dc < de:
                raise serializers.ValidationError(
                    {"date_cloture": _("La date de clôture ne peut pas être antérieure à la date d'expédition.")}
                )
        return attrs
