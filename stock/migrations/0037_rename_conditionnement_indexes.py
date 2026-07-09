from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0036_conditionnement_entree_pricing'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='conditionnementarticle',
            new_name='stock_condi_article_8b96be_idx',
            old_name='stock_condi_article_da2a1b_idx',
        ),
        migrations.RenameIndex(
            model_name='prixconditionnemententree',
            new_name='stock_prixc_ligne_e_0ba817_idx',
            old_name='stock_prixc_ligne_e_4fce8b_idx',
        ),
        migrations.RenameIndex(
            model_name='prixconditionnemententree',
            new_name='stock_prixc_devise__57d1e1_idx',
            old_name='stock_prixc_devise__4db93f_idx',
        ),
    ]

