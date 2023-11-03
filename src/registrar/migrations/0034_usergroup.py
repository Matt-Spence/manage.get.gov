# Generated by Django 4.2.1 on 2023-09-20 19:04

import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("registrar", "0033_alter_userdomainrole_role"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserGroup",
            fields=[
                (
                    "group_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="auth.group",
                    ),
                ),
            ],
            options={
                "verbose_name": "User group",
                "verbose_name_plural": "User groups",
            },
            bases=("auth.group",),
            managers=[
                ("objects", django.contrib.auth.models.GroupManager()),
            ],
        ),
    ]