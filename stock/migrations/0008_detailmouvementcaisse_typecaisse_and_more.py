# Multicaisse + GFK sur MouvementCaisse (remplace PaiementDette).
#
# Le DDL réel est idempotent (MySQL) : répare les bases partiellement migrées
# (tables detail/type déjà créées sans fin de migration sur stock_mouvementcaisse).

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

from stock.migration_utils.apply_0008_idempotent import (
    apply_0008_idempotent,
    backwards_noop,
)


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('stock', '0007_client_is_special'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(apply_0008_idempotent, backwards_noop),
            ],
            state_operations=[
                migrations.CreateModel(
                    name='DetailMouvementCaisse',
                    fields=[
                        (
                            'id',
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name='ID',
                            ),
                        ),
                        ('montant', models.DecimalField(decimal_places=2, max_digits=12)),
                        (
                            'motif_explicite',
                            models.TextField(
                                blank=True,
                                default='',
                                help_text='Si pas de type_caisse, motif obligatoire ou généré automatiquement.',
                            ),
                        ),
                        ('reference_piece', models.CharField(blank=True, default='', max_length=100)),
                    ],
                    options={
                        'verbose_name': 'Détail mouvement caisse',
                        'verbose_name_plural': 'Détails mouvements caisse',
                        'ordering': ['id'],
                    },
                ),
                migrations.CreateModel(
                    name='TypeCaisse',
                    fields=[
                        (
                            'id',
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name='ID',
                            ),
                        ),
                        ('libelle', models.CharField(max_length=120)),
                        ('description', models.TextField(blank=True, default='')),
                        (
                            'image',
                            models.ImageField(blank=True, null=True, upload_to='types_caisse/'),
                        ),
                        ('is_active', models.BooleanField(default=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                    ],
                    options={
                        'verbose_name': 'Type de caisse',
                        'verbose_name_plural': 'Types de caisse',
                        'ordering': ['entreprise_id', 'libelle'],
                    },
                ),
                migrations.RemoveField(
                    model_name='paiementdette',
                    name='dette',
                ),
                migrations.RemoveField(
                    model_name='paiementdette',
                    name='devise',
                ),
                migrations.RemoveField(
                    model_name='paiementdette',
                    name='entreprise',
                ),
                migrations.RemoveField(
                    model_name='paiementdette',
                    name='succursale',
                ),
                migrations.RemoveField(
                    model_name='paiementdette',
                    name='utilisateur',
                ),
                migrations.RemoveField(
                    model_name='detteclient',
                    name='montant_paye',
                ),
                migrations.RemoveField(
                    model_name='detteclient',
                    name='solde_restant',
                ),
                migrations.RemoveField(
                    model_name='mouvementcaisse',
                    name='motif',
                ),
                migrations.RemoveField(
                    model_name='mouvementcaisse',
                    name='moyen',
                ),
                migrations.RemoveField(
                    model_name='sortie',
                    name='motif',
                ),
                migrations.AddField(
                    model_name='mouvementcaisse',
                    name='categorie_operation',
                    field=models.CharField(
                        choices=[
                            ('VENTE', 'Vente'),
                            ('APPROVISIONNEMENT', 'Approvisionnement'),
                            ('PAIEMENT_DETTE', 'Paiement de dette'),
                            ('MANUEL', 'Mouvement manuel'),
                            ('AJUSTEMENT_VENTE', 'Ajustement vente'),
                            ('ANNULATION_VENTE', 'Annulation vente'),
                            ('AJUSTEMENT_ENTREE', 'Ajustement entrée'),
                            ('ANNULATION_ENTREE', 'Annulation entrée'),
                        ],
                        db_index=True,
                        default='MANUEL',
                        max_length=32,
                    ),
                ),
                migrations.AddField(
                    model_name='mouvementcaisse',
                    name='content_type',
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to='contenttypes.contenttype',
                    ),
                ),
                migrations.AddField(
                    model_name='mouvementcaisse',
                    name='object_id',
                    field=models.PositiveIntegerField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='mouvementcaisse',
                    name='utilisateur',
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='mouvements_caisse_effectues',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                migrations.AddField(
                    model_name='sortie',
                    name='libelle',
                    field=models.CharField(
                        blank=True,
                        help_text='Libellé / commentaire de la sortie (hors caisse).',
                        max_length=255,
                    ),
                ),
                migrations.AlterField(
                    model_name='mouvementcaisse',
                    name='reference_piece',
                    field=models.CharField(blank=True, default='', max_length=100),
                ),
                migrations.AddIndex(
                    model_name='mouvementcaisse',
                    index=models.Index(
                        fields=['content_type', 'object_id'],
                        name='stock_mouve_content_354bb1_idx',
                    ),
                ),
                migrations.AddIndex(
                    model_name='mouvementcaisse',
                    index=models.Index(
                        fields=['categorie_operation'],
                        name='stock_mouve_categor_3d5e8f_idx',
                    ),
                ),
                migrations.AddField(
                    model_name='detailmouvementcaisse',
                    name='mouvement',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='details',
                        to='stock.mouvementcaisse',
                    ),
                ),
                migrations.AddField(
                    model_name='typecaisse',
                    name='entreprise',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='types_caisse',
                        to='stock.entreprise',
                    ),
                ),
                migrations.AddField(
                    model_name='typecaisse',
                    name='succursale',
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='types_caisse',
                        to='stock.succursale',
                    ),
                ),
                migrations.AddField(
                    model_name='detailmouvementcaisse',
                    name='type_caisse',
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='details_mouvements',
                        to='stock.typecaisse',
                    ),
                ),
                migrations.DeleteModel(
                    name='PaiementDette',
                ),
                migrations.AddIndex(
                    model_name='typecaisse',
                    index=models.Index(
                        fields=['entreprise_id'],
                        name='stock_typec_entrepr_4f8295_idx',
                    ),
                ),
                migrations.AddIndex(
                    model_name='typecaisse',
                    index=models.Index(
                        fields=['entreprise_id', 'succursale_id'],
                        name='stock_typec_entrepr_abb535_idx',
                    ),
                ),
            ],
        ),
    ]
