# Generated by Django 4.2.10 on 2024-07-26 18:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrar", "0113_user_portfolio_user_portfolio_additional_permissions_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="federalagency",
            name="is_fceb",
            field=models.BooleanField(blank=True, null=True, verbose_name="Determines if this agency is FCEB"),
        ),
        migrations.AlterField(
            model_name="federalagency",
            name="agency",
            field=models.CharField(blank=True, help_text="Agency initials", max_length=10, null=True),
        ),
    ]
