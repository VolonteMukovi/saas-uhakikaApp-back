import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("order", "0004_fournisseur_in_order_app"),
        ("stock", "0020_client_password"),
    ]

    operations = [
        migrations.CreateModel(
            name="Commande",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("statut", models.CharField(choices=[("EN_ATTENTE", "En attente"), ("ACCEPTEE", "Acceptée"), ("LIVREE", "Livrée"), ("REJETEE", "Rejetée")], db_index=True, default="EN_ATTENTE", max_length=20)),
                ("reference", models.CharField(blank=True, db_index=True, default="", help_text="Référence affichée (générée si vide).", max_length=40)),
                ("note_client", models.TextField(blank=True, default="", help_text="Message ou instructions du client.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="commandes", to="stock.client")),
                ("entreprise", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="commandes", to="stock.entreprise")),
                ("succursale", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="commandes", to="stock.succursale")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="CommandeItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom_article", models.CharField(blank=True, default="", help_text="Produit non référencé au catalogue (si pas d’article_id).", max_length=255)),
                ("quantite", models.PositiveIntegerField()),
                ("article", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="commande_items", to="stock.article")),
                ("commande", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="order.commande")),
            ],
            options={
                "ordering": ["id"],
            },
        ),
        migrations.CreateModel(
            name="CommandeResponse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("commentaire", models.TextField(help_text="Commentaire de suivi, validation ou retour.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("auteur", models.ForeignKey(blank=True, help_text="Utilisateur interne ayant saisi la réponse (admin / staff).", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="commande_reponses", to=settings.AUTH_USER_MODEL)),
                ("commande", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reponses", to="order.commande")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="commande",
            index=models.Index(fields=["entreprise_id", "client_id", "statut"], name="order_commande_entreprise_client_statut_idx"),
        ),
        migrations.AddIndex(
            model_name="commande",
            index=models.Index(fields=["entreprise_id", "created_at"], name="order_commande_entreprise_created_idx"),
        ),
        migrations.AddIndex(
            model_name="commande",
            index=models.Index(fields=["entreprise_id", "statut", "created_at"], name="order_commande_entreprise_statut_created_idx"),
        ),
        migrations.AddIndex(
            model_name="commandeitem",
            index=models.Index(fields=["commande_id", "article_id"], name="order_commandeitem_commande_article_idx"),
        ),
        migrations.AddIndex(
            model_name="commanderesponse",
            index=models.Index(fields=["commande_id", "created_at"], name="order_commande_resp_commande_created_idx"),
        ),
    ]
