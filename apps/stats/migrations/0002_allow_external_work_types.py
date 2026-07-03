from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stats", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workentry",
            name="task_type",
            field=models.CharField(
                choices=[
                    ("development", "开发"),
                    ("testing", "测试"),
                    ("meeting", "会议"),
                    ("documentation", "文档"),
                    ("design", "设计"),
                    ("other", "其他"),
                ],
                default="other",
                max_length=50,
                verbose_name="任务类型",
            ),
        ),
    ]
