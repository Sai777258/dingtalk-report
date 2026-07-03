from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stats", "0002_allow_external_work_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="workentry",
            name="source_item_id",
            field=models.BigIntegerField(
                blank=True, db_index=True, null=True, unique=True, verbose_name="外部条目ID"
            ),
        ),
    ]
