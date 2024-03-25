# Generated by Django 4.2.10 on 2024-03-13 21:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrar", "0075_create_groups_v08"),
    ]

    operations = [
        migrations.AlterField(
            model_name="domainrequest",
            name="current_websites",
            field=models.ManyToManyField(
                blank=True, related_name="current+", to="registrar.website", verbose_name="Current websites"
            ),
        ),
        migrations.AlterField(
            model_name="domainrequest",
            name="other_contacts",
            field=models.ManyToManyField(
                blank=True,
                related_name="contact_domain_requests",
                to="registrar.contact",
                verbose_name="Other employees",
            ),
        ),
        migrations.AlterField(
            model_name="domaininformation",
            name="other_contacts",
            field=models.ManyToManyField(
                blank=True,
                related_name="contact_domain_requests_information",
                to="registrar.contact",
                verbose_name="Other employees",
            ),
        ),
    ]