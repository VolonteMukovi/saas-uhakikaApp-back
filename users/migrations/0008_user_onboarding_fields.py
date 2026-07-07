"""Champs parcours onboarding + rétrocompatibilité comptes existants."""
from django.db import migrations, models


def backfill_onboarding_comptes_existants(apps, schema_editor):
    User = apps.get_model('users', 'User')
    Membership = apps.get_model('users', 'Membership')
    Entreprise = apps.get_model('stock', 'Entreprise')

    PLACEHOLDER = 'À compléter'
    CHAMPS = ('nom', 'email', 'telephone', 'adresse', 'pays', 'responsable', 'secteur')

    def entreprise_configuree(ent):
        if not ent:
            return False
        if getattr(ent, 'configuration_complete', False):
            return True
        for champ in CHAMPS:
            val = (getattr(ent, champ, None) or '').strip()
            if not val or val in (PLACEHOLDER, '-', 'N/A'):
                return False
        return True

    for user in User.objects.filter(email_verifie=True):
        prenom = (user.first_name or '').strip()
        nom = (user.last_name or '').strip()
        profil_ok = bool(prenom and nom)
        membership = (
            Membership.objects.filter(user_id=user.id, is_active=True)
            .order_by('entreprise_id', 'id')
            .first()
        )
        ent = None
        if membership:
            ent = Entreprise.objects.filter(pk=membership.entreprise_id).first()
        company_ok = entreprise_configuree(ent)

        updates = {}
        if user.message_bienvenue_envoye or (profil_ok and company_ok and membership):
            updates['onboarding_complete'] = True
            updates['workspace_activated'] = True
            updates['welcome_seen'] = True
            if user.message_bienvenue_envoye:
                updates['email_activation_envoye'] = True
        if updates:
            User.objects.filter(pk=user.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_user_email_verification'),
        ('stock', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='email_activation_envoye',
            field=models.BooleanField(
                default=False,
                help_text="True après envoi de l'e-mail d'activation finale de l'espace.",
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='onboarding_complete',
            field=models.BooleanField(
                default=False,
                help_text="True lorsque l'utilisateur a finalisé le wizard d'onboarding (étape vérification).",
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='welcome_seen',
            field=models.BooleanField(
                default=False,
                help_text="True après affichage unique de l'écran de bienvenue avant le premier accès dashboard.",
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='workspace_activated',
            field=models.BooleanField(
                default=False,
                help_text="True après clic sur le lien d'activation finale de l'espace (e-mail post-onboarding).",
            ),
        ),
        migrations.RunPython(backfill_onboarding_comptes_existants, migrations.RunPython.noop),
    ]
