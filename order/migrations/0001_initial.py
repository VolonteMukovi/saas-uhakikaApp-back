# Generated manually for the initial `order` app models.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("stock", "0016_retry_ensure_mouvementcaisse_content_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="Lot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(max_length=30)),
                ("date_expedition", models.DateField(help_text="Date d'expédition du lot.")),
                ("date_arrivee_prevue", models.DateField(blank=True, help_text="Date d'arrivée prévue (optionnelle).", null=True)),
                ("statut", models.CharField(choices=[("EN_TRANSIT", "En transit"), ("ARRIVE", "Arrivé"), ("CLOTURE", "Clôturé")], default="EN_TRANSIT", max_length=20)),
                ("date_cloture", models.DateField(blank=True, help_text="Date de clôture (optionnelle).", null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "entreprise",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lots_en_transit", to="stock.entreprise"),
                ),
                (
                    "succursale",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="lots_en_transit", to="stock.succursale"),
                ),
                (
                    "fournisseur",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="lots_en_transit_as_fournisseur", to="stock.client"),
                ),
            ],
            options={
                "unique_together": {("entreprise", "reference")},
                "indexes": [
                    models.Index(fields=["entreprise", "statut"], name="order_lot_entreprise_statut_idx"),
                    models.Index(fields=["entreprise", "fournisseur"], name="order_lot_entreprise_fournisseur_idx"),
                    models.Index(fields=["entreprise", "date_expedition"], name="order_lot_entreprise_date_expedition_idx"),
                ],
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="FraisLot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type_frais", models.CharField(choices=[("TRANSPORT", "Transport"), ("DOUANE", "Douane"), ("MANUTENTION", "Manutention")], max_length=20)),
                ("montant", models.DecimalField(decimal_places=2, max_digits=14)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "entreprise",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="frais_lots", to="stock.entreprise"),
                ),
                (
                    "succursale",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="frais_lots", to="stock.succursale"),
                ),
                ("lot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="frais", to="order.lot")),
                ("devise", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="frais_lots", to="stock.devise")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["entreprise", "lot", "type_frais"], name="order_fraislots_entreprise_lot_type_frais_idx"),
                ],
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="LotItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantite", models.PositiveIntegerField()),
                ("prix_achat_unitaire", models.DecimalField(decimal_places=2, max_digits=14)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "entreprise",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lot_items", to="stock.entreprise"),
                ),
                (
                    "succursale",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="lot_items", to="stock.succursale"),
                ),
                ("lot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="order.lot")),
                ("article", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lot_items", to="stock.article")),
            ],
            options={
                "unique_together": {("lot", "article")},
                "indexes": [
                    models.Index(fields=["entreprise", "lot", "article"], name="order_lotitem_entreprise_lot_article_idx"),
                ],
                "ordering": ["-created_at", "-id"],
            },
        ),
    ]

