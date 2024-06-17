import logging
from django.core.management import BaseCommand
from registrar.management.commands.utility.terminal_helper import PopulateScriptTemplate
from registrar.models import FederalAgency, DomainRequest


logger = logging.getLogger(__name__)


# This command uses the PopulateScriptTemplate.
# This template handles logging and bulk updating for you, for repetitive scripts that update a few fields.
# It is the ultimate lazy mans shorthand. Don't use this for anything terribly complicated.
class Command(BaseCommand, PopulateScriptTemplate):
    help = "Loops through each valid User object and updates its verification_type value"
    prompt_title = "Do you wish to update all Federal Agencies?"
    display_run_summary_items_as_str = True

    def handle(self, **kwargs):
        """Loops through each valid User object and updates its verification_type value"""

        # Get all existing domain requests
        self.all_domain_requests = DomainRequest.objects.select_related("federal_agency").distinct()
        self.mass_update_records(
            FederalAgency, filter_conditions={"agency__isnull": False}, fields_to_update=["federal_type"]
        )

    def update_record(self, record: FederalAgency):
        """Defines how we update the federal_type field on each record."""
        request = self.all_domain_requests.filter(federal_agency__agency=record.agency).first()
        record.federal_type = request.federal_type
    
    def should_skip_record(self, record) -> bool:  # noqa
        """Defines the conditions in which we should skip updating a record."""
        request = self.all_domain_requests.filter(federal_agency__agency=record.agency).first()
        return not request or not request.federal_agency

