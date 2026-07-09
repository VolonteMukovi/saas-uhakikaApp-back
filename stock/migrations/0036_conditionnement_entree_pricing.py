# Generated manually for conditionnement pricing support

from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


def backfill_conditionnement_and_ligne_entree(apps, schema_editor):
    Article = apps.get_model('stock', 'Article')
    ConditionnementArticle = apps.get_model('stock', 'ConditionnementArticle')
    LigneEntree = apps.get_model('stock', 'LigneEntree')

    def get_or_create_default(article):
        cond = ConditionnementArticle.objects.filter(article_id=article.article_id, est_defaut=True).first()
        if cond:
            return cond
        unite = getattr(article, 'unite', None)
        nom = (getattr(unite, 'libelle', None) or 'Unité').strip() or 'Unité'
        cond = ConditionnementArticle.objects.filter(article_id=article.article_id, nom=nom).first()
        if cond:
            if not cond.est_defaut:
                cond.est_defaut = True
                cond.save(update_fields=['est_defaut', 'updated_at'])
            return cond
        return ConditionnementArticle.objects.create(
            article_id=article.article_id,
            nom=nom,
            multiplicateur_base=Decimal('1'),
            est_defaut=True,
        )

    for article in Article.objects.all().select_related('unite'):
        get_or_create_default(article)

    for le in LigneEntree.objects.select_related('article').all():
        cond = le.conditionnement
        if cond is None and le.article_id:
            cond = get_or_create_default(le.article)
        le.conditionnement = cond
        le.quantite_saisie = le.quantite
        le.quantite_base = le.quantite
        le.prix_achat_conditionnement = le.prix_unitaire
        le.prix_vente_conditionnement = le.prix_vente
        le.prix_achat_unitaire_base = le.prix_unitaire
        le.prix_vente_unitaire_base = le.prix_vente
        le.save(
            update_fields=[
                'conditionnement',
                'quantite_saisie',
                'quantite_base',
                'prix_achat_conditionnement',
                'prix_vente_conditionnement',
                'prix_achat_unitaire_base',
                'prix_vente_unitaire_base',
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0035_entreprise_configuration_complete'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConditionnementArticle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=100)),
                (
                    'multiplicateur_base',
                    models.DecimalField(
                        decimal_places=5,
                        default=Decimal('1'),
                        help_text="Nombre d'unités de base contenues dans ce conditionnement.",
                        max_digits=12,
                    ),
                ),
                (
                    'est_defaut',
                    models.BooleanField(
                        default=False,
                        help_text='Conditionnement appliqué par défaut (ex: pièce/unité).',
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'article',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='conditionnements',
                        to='stock.article',
                    ),
                ),
            ],
            options={
                'ordering': ['article_id', '-est_defaut', 'nom', 'id'],
            },
        ),
        migrations.AddField(
            model_name='ligneentree',
            name='conditionnement',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='lignes_entree',
                to='stock.conditionnementarticle',
            ),
        ),
        migrations.AddField(
            model_name='ligneentree',
            name='prix_achat_conditionnement',
            field=models.DecimalField(blank=True, decimal_places=5, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='ligneentree',
            name='prix_achat_unitaire_base',
            field=models.DecimalField(blank=True, decimal_places=5, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='ligneentree',
            name='prix_vente_conditionnement',
            field=models.DecimalField(blank=True, decimal_places=5, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='ligneentree',
            name='prix_vente_unitaire_base',
            field=models.DecimalField(blank=True, decimal_places=5, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='ligneentree',
            name='quantite_base',
            field=models.DecimalField(blank=True, decimal_places=5, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='ligneentree',
            name='quantite_saisie',
            field=models.DecimalField(blank=True, decimal_places=5, max_digits=12, null=True),
        ),
        migrations.CreateModel(
            name='PrixConditionnementEntree',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prix_vente', models.DecimalField(decimal_places=5, max_digits=10)),
                ('est_prix_principal', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'conditionnement',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='prix_ligne_entrees',
                        to='stock.conditionnementarticle',
                    ),
                ),
                (
                    'devise',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='prix_conditionnement_entrees',
                        to='stock.devise',
                    ),
                ),
                (
                    'ligne_entree',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='prix_conditionnements',
                        to='stock.ligneentree',
                    ),
                ),
            ],
            options={
                'ordering': ['ligne_entree_id', '-est_prix_principal', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='conditionnementarticle',
            index=models.Index(fields=['article', 'est_defaut'], name='stock_condi_article_da2a1b_idx'),
        ),
        migrations.AddConstraint(
            model_name='conditionnementarticle',
            constraint=models.UniqueConstraint(fields=('article', 'nom'), name='uniq_conditionnement_article_nom'),
        ),
        migrations.AddConstraint(
            model_name='prixconditionnemententree',
            constraint=models.UniqueConstraint(fields=('ligne_entree', 'conditionnement'), name='uniq_prix_cond_par_ligne_entree'),
        ),
        migrations.AddIndex(
            model_name='prixconditionnemententree',
            index=models.Index(fields=['ligne_entree', 'conditionnement'], name='stock_prixc_ligne_e_4fce8b_idx'),
        ),
        migrations.AddIndex(
            model_name='prixconditionnemententree',
            index=models.Index(fields=['devise'], name='stock_prixc_devise__4db93f_idx'),
        ),
        migrations.RunPython(backfill_conditionnement_and_ligne_entree, migrations.RunPython.noop),
    ]

