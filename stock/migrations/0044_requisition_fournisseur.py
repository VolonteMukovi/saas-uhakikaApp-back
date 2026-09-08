import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0012_alter_commandeitem_quantite_alter_fraislot_montant_and_more'),
        ('stock', '0043_requisition_devise'),
    ]

    operations = [
        migrations.AddField(
            model_name='requisitionligne',
            name='fournisseur',
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    'Fournisseur pressenti pour cet article (optionnel : '
                    'peut rester vide si le fournisseur n’est pas encore connu).'
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lignes_requisition',
                to='order.fournisseur',
            ),
        ),
        migrations.AddIndex(
            model_name='requisitionligne',
            index=models.Index(
                fields=['requisition_id', 'fournisseur_id'],
                name='stock_reqligne_fou_idx',
            ),
        ),
    ]
