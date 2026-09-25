# Generated manually — remove PAIEMENT_DETTE from MouvementCaisse.categorie choices.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('caisse', '0005_mouvementcaisse_montant_applique'),
        ('stock', '0046_remove_dette_client'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mouvementcaisse',
            name='categorie',
            field=models.CharField(
                blank=True,
                choices=[
                    ('VENTE', 'Vente comptant'),
                    ('APPROVISIONNEMENT', 'Approvisionnement payé cash'),
                    ('DEPENSE', 'Dépense'),
                    ('ENTREE_MANUELLE', 'Entrée manuelle'),
                    ('SORTIE_MANUELLE', 'Sortie manuelle'),
                    ('AJUSTEMENT_SURPLUS_CAISSE', 'Ajustement surplus caisse'),
                    ('AJUSTEMENT_PERTE_CAISSE', 'Ajustement perte caisse'),
                    ('AUTRE', 'Autre'),
                ],
                default='AUTRE',
                max_length=40,
            ),
        ),
    ]
