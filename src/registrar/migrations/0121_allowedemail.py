# Generated by Django 4.2.10 on 2024-08-29 18:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrar", "0120_add_domainrequest_submission_dates"),
    ]

    operations = [
        migrations.CreateModel(
            name="AllowedEmail",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("email", models.EmailField(max_length=320, unique=True)),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
