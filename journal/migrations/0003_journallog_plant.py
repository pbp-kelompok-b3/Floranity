import django.db.models.deletion
from django.db import migrations, models


def link_unambiguous_existing_logs(apps, schema_editor):
    JournalLog = apps.get_model("journal", "JournalLog")
    Tanaman = apps.get_model("koleksi", "Tanaman")
    database = schema_editor.connection.alias

    for log in JournalLog.objects.using(database).filter(plant__isnull=True).iterator():
        matches = Tanaman.objects.using(database).filter(
            pemilik_id=log.owner_id,
            nama_panggilan__iexact=log.plant_name,
            nama_ilmiah__iexact=log.plant_species,
        )[:2]
        if len(matches) == 1:
            log.plant_id = matches[0].pk
            log.save(using=database, update_fields=["plant"])


class Migration(migrations.Migration):

    dependencies = [
        ("journal", "0002_journallog_fertilizer_type_journallog_health_status_and_more"),
        ("koleksi", "0002_jurnalpertumbuhan"),
    ]

    operations = [
        migrations.AddField(
            model_name="journallog",
            name="plant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="journal_logs",
                to="koleksi.tanaman",
            ),
        ),
        migrations.RunPython(link_unambiguous_existing_logs, migrations.RunPython.noop),
    ]
