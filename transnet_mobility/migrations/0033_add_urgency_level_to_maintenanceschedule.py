from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("transnet_mobility", "0032_merge_20260107_1153"),
    ]

    operations = [
        migrations.AddField(
            model_name="maintenanceschedule",
            name="urgency_level",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("LOW", "Low"),
                    ("MEDIUM", "Medium"),
                    ("HIGH", "High"),
                    ("CRITICAL", "Critical"),
                ],
                default="MEDIUM",
            ),
        ),
    ]
