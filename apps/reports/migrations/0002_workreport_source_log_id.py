from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="workreport",
            name="source_log_id",
            field=models.BigIntegerField(
                blank=True, db_index=True, null=True, unique=True, verbose_name="外部日志ID"
            ),
        ),
    ]
