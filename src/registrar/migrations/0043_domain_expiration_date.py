# Generated by Django 4.2.6 on 2023-10-30 15:37

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("registrar", "0042_create_groups_v03"),
    ]

    operations = [
        migrations.AddField(
            model_name="domain",
            name="expiration_date",
            field=models.DateField(
                help_text="Duplication of registry's expiration date saved for ease of reporting",
                null=True,
            ),
        ),
    ]
