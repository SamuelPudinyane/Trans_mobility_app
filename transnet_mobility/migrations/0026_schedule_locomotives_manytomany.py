from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("transnet_mobility", "0025_cargospec_additional_specs_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="schedule",
            name="locomotive",
        ),
        migrations.AddField(
            model_name="schedule",
            name="locomotives",
            field=models.ManyToManyField(
                to="transnet_mobility.LocomotiveSpec",
                related_name="schedule_locomotives",
                blank=True,
            ),
        ),
    ]
