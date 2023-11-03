# Generated by Django 4.2.1 on 2023-09-27 00:18

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("registrar", "0031_transitiondomain_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transitiondomain",
            name="status",
            field=models.CharField(
                blank=True,
                choices=[("ready", "Ready"), ("hold", "Hold")],
                default="ready",
                help_text="domain status during the transfer",
                max_length=255,
                verbose_name="Status",
            ),
        ),
    ]