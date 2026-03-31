# Déplace la table métier Fournisseur de `stock` vers `order` (copie des lignes + FK Lot).

import django.db.models.deletion
from django.db import migrations, models


def copy_fournisseurs_stock_to_order(apps, schema_editor):
    StockFournisseur = apps.get_model("stock", "Fournisseur")
    OrderFournisseur = apps.get_model("order", "Fournisseur")
    for s in StockFournisseur.objects.order_by("pk"):
        OrderFournisseur.objects.create(
            id=s.pk,
            entreprise_id=s.entreprise_id,
            succursale_id=s.succursale_id,
            code=s.code or "",
            nom=s.nom,
            telephone=s.telephone,
            email=s.email,
            adresse=s.adresse,
            ville=s.ville,
            pays=s.pays,
            nif=s.nif,
            notes=s.notes or "",
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0003_rename_order_fraislots_entreprise_lot_type_frais_idx_order_frais_entrepr_cf6b25_idx_and_more"),
        ("stock", "0018_fournisseur_code_blank"),
    ]

    operations = [
        migrations.CreateModel(
            name="Fournisseur",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(blank=True, default="", help_text="Code interne unique par entreprise (généré automatiquement si vide).", max_length=40)),
                ("nom", models.CharField(max_length=255)),
                ("telephone", models.CharField(blank=True, max_length=50, null=True)),
                ("email", models.EmailField(blank=True, max_length=254, null=True)),
                ("adresse", models.CharField(blank=True, max_length=255, null=True)),
                ("ville", models.CharField(blank=True, max_length=100, null=True)),
                ("pays", models.CharField(blank=True, max_length=100, null=True)),
                ("nif", models.CharField(blank=True, max_length=100, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "entreprise",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fournisseurs", to="stock.entreprise"),
                ),
                (
                    "succursale",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="fournisseurs", to="stock.succursale"),
                ),
            ],
            options={
                "verbose_name": "Fournisseur",
                "verbose_name_plural": "Fournisseurs",
                "ordering": ["nom", "id"],
                "unique_together": {("entreprise", "code")},
            },
        ),
        migrations.AddIndex(
            model_name="fournisseur",
            index=models.Index(fields=["entreprise_id", "nom"], name="order_fournisseur_entreprise_nom_idx"),
        ),
        migrations.AddIndex(
            model_name="fournisseur",
            index=models.Index(fields=["entreprise_id", "is_active"], name="order_fournisseur_entreprise_active_idx"),
        ),
        migrations.AddIndex(
            model_name="fournisseur",
            index=models.Index(fields=["entreprise_id", "code"], name="order_fournisseur_entreprise_code_idx"),
        ),
        migrations.AddIndex(
            model_name="fournisseur",
            index=models.Index(fields=["entreprise_id", "created_at"], name="order_fournisseur_entreprise_created_idx"),
        ),
        migrations.RunPython(copy_fournisseurs_stock_to_order, noop_reverse),
        migrations.AlterField(
            model_name="lot",
            name="fournisseur",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="lots_en_transit",
                to="order.fournisseur",
            ),
        ),
    ]
