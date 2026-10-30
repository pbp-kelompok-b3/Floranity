from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('akun', '0002_remove_profile_theme'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='DeletedGoogleAccount',
            new_name='DeletedAccount',
        ),
        migrations.RenameField(
            model_name='profile',
            old_name='google_photo_url',
            new_name='photo_url',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='google_id',
        ),
    ]
