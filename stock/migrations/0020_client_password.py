from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stock", "0019_remove_fournisseur_from_stock"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="password",
            field=models.CharField(
                blank=True,
                help_text="Hash du mot de passe pour l’espace client (connexion par e-mail). Laisser vide si le client n’a pas accès au portail.",
                max_length=128,
                null=True,
                verbose_name="Mot de passe (hash)",
            ),
        ),
        migrations.AddIndex(
            model_name="client",
            index=models.Index(fields=["entreprise_id", "email"], name="stock_client_entreprise_email_idx"),
        ),
    ]
