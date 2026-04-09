from django.db import migrations


def migrate_existing_users(apps, schema_editor):
    """Copy User.first_name/last_name → UserProfile and set username = email."""
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('accounts', 'UserProfile')

    for user in User.objects.all():
        # Set username to email (Django requires username, we auto-set it)
        if user.username != user.email and user.email:
            user.username = user.email
            user.save(update_fields=['username'])

        # Copy first/last name to profile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if user.first_name and not profile.first_name:
            profile.first_name = user.first_name
        if user.last_name and not profile.last_name:
            profile.last_name = user.last_name
        if not profile.preferred_name and profile.first_name:
            profile.preferred_name = profile.first_name
        profile.save()


def reverse_migrate(apps, schema_editor):
    """Reverse: copy UserProfile names back to User."""
    UserProfile = apps.get_model('accounts', 'UserProfile')
    for profile in UserProfile.objects.select_related('user').all():
        user = profile.user
        user.first_name = profile.first_name
        user.last_name = profile.last_name
        user.save(update_fields=['first_name', 'last_name'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_restructure_userprofile_and_pending'),
    ]

    operations = [
        migrations.RunPython(migrate_existing_users, reverse_migrate),
    ]
