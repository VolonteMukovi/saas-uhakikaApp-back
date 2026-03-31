from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stock", "0017_fournisseur"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fournisseur",
            name="code",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Code interne unique par entreprise (généré automatiquement si vide).",
                max_length=40,
            ),
        ),
    ]
