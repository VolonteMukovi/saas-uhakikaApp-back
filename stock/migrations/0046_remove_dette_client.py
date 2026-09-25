from django.db import migrations


def purge_paiement_dette_mouvements(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    MouvementCaisse = apps.get_model('caisse', 'MouvementCaisse')

    MouvementCaisse.objects.filter(categorie='PAIEMENT_DETTE').delete()
    ct = ContentType.objects.filter(app_label='stock', model='detteclient').first()
    if ct:
        MouvementCaisse.objects.filter(content_type_id=ct.pk).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('caisse', '0005_mouvementcaisse_montant_applique'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('stock', '0045_move_fournisseur_to_requisition_ligne'),
    ]

    operations = [
        migrations.RunPython(purge_paiement_dette_mouvements, migrations.RunPython.noop),
        migrations.DeleteModel(
            name='DetteClient',
        ),
    ]
