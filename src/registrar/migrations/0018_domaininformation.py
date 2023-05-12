# Generated by Django 4.1.6 on 2023-05-08 15:30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("registrar", "0017_alter_domainapplication_status_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DomainInformation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization_type",
                    models.CharField(
                        blank=True,
                        choices=[
                            (
                                "federal",
                                "Federal: an agency of the U.S. government's executive, legislative, or judicial branches",
                            ),
                            (
                                "interstate",
                                "Interstate: an organization of two or more states",
                            ),
                            (
                                "state_or_territory",
                                "State or territory: one of the 50 U.S. states, the District of Columbia, American Samoa, Guam, Northern Mariana Islands, Puerto Rico, or the U.S. Virgin Islands",
                            ),
                            (
                                "tribal",
                                "Tribal: a tribal government recognized by the federal or a state government",
                            ),
                            ("county", "County: a county, parish, or borough"),
                            ("city", "City: a city, town, township, village, etc."),
                            (
                                "special_district",
                                "Special district: an independent organization within a single state",
                            ),
                            (
                                "school_district",
                                "School district: a school district that is not part of a local government",
                            ),
                        ],
                        help_text="Type of Organization",
                        max_length=255,
                        null=True,
                    ),
                ),
                (
                    "federally_recognized_tribe",
                    models.BooleanField(
                        help_text="Is the tribe federally recognized", null=True
                    ),
                ),
                (
                    "state_recognized_tribe",
                    models.BooleanField(
                        help_text="Is the tribe recognized by a state", null=True
                    ),
                ),
                (
                    "tribe_name",
                    models.TextField(blank=True, help_text="Name of tribe", null=True),
                ),
                (
                    "federal_agency",
                    models.TextField(blank=True, help_text="Federal agency", null=True),
                ),
                (
                    "federal_type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("executive", "Executive"),
                            ("judicial", "Judicial"),
                            ("legislative", "Legislative"),
                        ],
                        help_text="Federal government branch",
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "is_election_board",
                    models.BooleanField(
                        blank=True,
                        help_text="Is your organization an election office?",
                        null=True,
                    ),
                ),
                (
                    "organization_name",
                    models.TextField(
                        blank=True,
                        db_index=True,
                        help_text="Organization name",
                        null=True,
                    ),
                ),
                (
                    "address_line1",
                    models.TextField(blank=True, help_text="Street address", null=True),
                ),
                (
                    "address_line2",
                    models.CharField(
                        blank=True,
                        help_text="Street address line 2",
                        max_length=15,
                        null=True,
                    ),
                ),
                ("city", models.TextField(blank=True, help_text="City", null=True)),
                (
                    "state_territory",
                    models.CharField(
                        blank=True,
                        help_text="State, territory, or military post",
                        max_length=2,
                        null=True,
                    ),
                ),
                (
                    "zipcode",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text="Zip code",
                        max_length=10,
                        null=True,
                    ),
                ),
                (
                    "urbanization",
                    models.TextField(
                        blank=True,
                        help_text="Urbanization (Puerto Rico only)",
                        null=True,
                    ),
                ),
                (
                    "type_of_work",
                    models.TextField(
                        blank=True,
                        help_text="Type of work of the organization",
                        null=True,
                    ),
                ),
                (
                    "more_organization_information",
                    models.TextField(
                        blank=True,
                        help_text="Further information about the government organization",
                        null=True,
                    ),
                ),
                (
                    "purpose",
                    models.TextField(
                        blank=True, help_text="Purpose of your domain", null=True
                    ),
                ),
                (
                    "no_other_contacts_rationale",
                    models.TextField(
                        blank=True,
                        help_text="Reason for listing no additional contacts",
                        null=True,
                    ),
                ),
                (
                    "anything_else",
                    models.TextField(
                        blank=True, help_text="Anything else we should know?", null=True
                    ),
                ),
                (
                    "is_policy_acknowledged",
                    models.BooleanField(
                        blank=True,
                        help_text="Acknowledged .gov acceptable use policy",
                        null=True,
                    ),
                ),
                (
                    "security_email",
                    models.EmailField(
                        blank=True,
                        help_text="Security email for public use",
                        max_length=320,
                        null=True,
                    ),
                ),
                (
                    "authorizing_official",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="information_authorizing_official",
                        to="registrar.contact",
                    ),
                ),
                (
                    "creator",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="information_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "domain",
                    models.OneToOneField(
                        blank=True,
                        help_text="Domain to which this information belongs",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="domain_info",
                        to="registrar.domain",
                    ),
                ),
                (
                    "domain_application",
                    models.OneToOneField(
                        blank=True,
                        help_text="Associated domain application",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="domainapplication_info",
                        to="registrar.domainapplication",
                    ),
                ),
                (
                    "other_contacts",
                    models.ManyToManyField(
                        blank=True,
                        related_name="contact_applications_information",
                        to="registrar.contact",
                    ),
                ),
                (
                    "submitter",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="submitted_applications_information",
                        to="registrar.contact",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Domain Information",
            },
        ),
    ]