# Generated by Django 4.2.7 on 2023-12-23 01:31

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("registrar", "0060_domain_deleted_domain_first_ready"),
    ]

    operations = [
        migrations.AddField(
            model_name="domain",
            name="security_contact_registry_id",
            field=models.TextField(
                editable=False,
                help_text="Duplication of registry's security contact id for when registry unavailable",
                null=True,
            ),
        ),
    ]
