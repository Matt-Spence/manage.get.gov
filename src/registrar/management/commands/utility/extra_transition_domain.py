""""""
import csv
from dataclasses import dataclass
from enum import Enum
import glob
import re
import logging

import os
from typing import List

from registrar.models.transition_domain import TransitionDomain
from transition_domain_arguments import TransitionDomainArguments
from epp_data_containers import (
    AgencyAdhoc,
    DomainAdditionalData,
    DomainTypeAdhoc,
    OrganizationAdhoc,
    AuthorityAdhoc,
    EnumFilenames,
)

logger = logging.getLogger(__name__)

class LogCode(Enum):
    """Stores the desired log severity"""
    ERROR = 1
    WARNING = 2
    INFO = 3
    DEBUG = 4


class FileTransitionLog:
    """Container for storing event logs. Used to lessen
    the complexity of storing multiple logs across multiple 
    variables. 
    
    self.logs: dict -> {
        EnumFilenames.DOMAIN_ADHOC: List[LogItem],
        EnumFilenames.AGENCY_ADHOC: List[LogItem],
        EnumFilenames.ORGANIZATION_ADHOC: List[LogItem],
        EnumFilenames.DOMAIN_ADDITIONAL: List[LogItem],
    }
    """
    def __init__(self):
        self.logs = {
            EnumFilenames.DOMAIN_ADHOC: [],
            EnumFilenames.AGENCY_ADHOC: [],
            EnumFilenames.ORGANIZATION_ADHOC: [],
            EnumFilenames.DOMAIN_ADDITIONAL: [],
        }

    class LogItem:
        """Used for storing data about logger information."""
        def __init__(self, file_type, code, message, domain_name):
            self.file_type = file_type
            self.code = code
            self.message = message
            self.domain_name = domain_name

    def add_log(self, file_type, code, message, domain_name):
        """Adds a log item to self.logs

        file_type -> Which array to add to, 
        ex. EnumFilenames.DOMAIN_ADHOC

        code -> Log severity or other metadata, ex. LogCode.ERROR

        message -> Message to display
        """
        self.logs[file_type].append(self.LogItem(file_type, code, message, domain_name))

    def create_log_item(self, file_type, code, message, domain_name=None, add_to_list=True):
        """Creates and returns an LogItem object.

        add_to_list: bool -> If enabled, add it to the logs array.
        """
        log = self.LogItem(file_type, code, message, domain_name)
        if not add_to_list:
            return log
        else:
            self.logs[file_type].append(log)
        return log

    def display_logs(self, file_type):
        """Displays all logs in the given file_type in EnumFilenames.
        Will log with the correct severity depending on code.
        """
        for log in self.logs.get(file_type):
            match log.code:
                case LogCode.ERROR:
                    logger.error(log.message)
                case LogCode.WARNING:
                    logger.warning(log.message)
                case LogCode.INFO:
                    logger.info(log.message)
                case LogCode.DEBUG:
                    logger.debug(log.message)


class LoadExtraTransitionDomain:
    """Grabs additional data for TransitionDomains."""

    def __init__(self, options: TransitionDomainArguments):
        # Stores event logs and organizes them
        self.parse_logs = FileTransitionLog()

        # Reads and parses migration files
        self.domain_object = ExtraTransitionDomain(
            agency_adhoc_filename=options.agency_adhoc_filename,
            domain_additional_filename=options.domain_additional_filename,
            domain_adhoc_filename=options.domain_adhoc_filename,
            organization_adhoc_filename=options.organization_adhoc_filename,
            directory=options.directory,
            seperator=options.seperator,
        )
        self.domain_object.parse_all_files()

        # Given the data we just parsed, update each
        # transition domain object with that data.
        self.update_transition_domain_models()

        
    def update_transition_domain_models(self):
        """Updates TransitionDomain objects based off the file content
        given in self.domain_object"""
        all_transition_domains = TransitionDomain.objects.all()
        if not all_transition_domains.exists():
            raise Exception("No TransitionDomain objects exist.")

        for transition_domain in all_transition_domains:
            domain_name = transition_domain.domain_name.upper()
            updated_transition_domain = transition_domain
            # STEP 1: Parse organization data
            updated_transition_domain = self.parse_org_data(
                domain_name, transition_domain
            )
            self.parse_logs.display_logs(EnumFilenames.ORGANIZATION_ADHOC)

            # STEP 2: Parse domain type data
            updated_transition_domain = self.parse_domain_type_data(
                domain_name, transition_domain
            )
            self.parse_logs.display_logs(EnumFilenames.DOMAIN_ADHOC)

            # STEP 3: Parse agency data
            updated_transition_domain = self.parse_agency_data(
                domain_name, transition_domain
            )
            self.parse_logs.display_logs(EnumFilenames.AGENCY_ADHOC)

            # STEP 4: Parse expiration data - TODO
            updated_transition_domain = self.parse_expiration_data(
                domain_name, transition_domain
            )
            # self.parse_logs(EnumFilenames.EXPIRATION_DATA)

            updated_transition_domain.save()

    # TODO - Implement once Niki gets her ticket in
    def parse_expiration_data(self, domain_name, transition_domain):
        """Grabs expiration_date from the parsed files and associates it 
        with a transition_domain object, then returns that object."""
        return transition_domain

    def parse_agency_data(self, domain_name, transition_domain) -> TransitionDomain:
        """Grabs federal_agency from the parsed files and associates it 
        with a transition_domain object, then returns that object."""
        if not isinstance(transition_domain, TransitionDomain):
            raise ValueError("Not a valid object, must be TransitionDomain")

        info = self.get_agency_info(domain_name)
        if info is None:
            self.parse_logs.create_log_item(
                EnumFilenames.AGENCY_ADHOC,
                LogCode.ERROR,
                f"Could not add federal_agency on {domain_name}, no data exists.",
                domain_name
            )
            return transition_domain

        agency_exists = (
            transition_domain.federal_agency is not None
            and transition_domain.federal_agency.strip() != ""
        )

        if not info.active.lower() == "y":
            self.parse_logs.create_log_item(
                EnumFilenames.DOMAIN_ADHOC,
                LogCode.ERROR,
                f"Could not add inactive agency {info.agencyname} on {domain_name}",
                domain_name
            )
            return transition_domain
        
        if not info.isfederal.lower() == "y":
            self.parse_logs.create_log_item(
                EnumFilenames.DOMAIN_ADHOC,
                LogCode.ERROR,
                f"Could not add non-federal agency {info.agencyname} on {domain_name}",
                domain_name
            )
            return transition_domain
        
        transition_domain.federal_agency = info.agencyname

        # Logs if we either added to this property,
        # or modified it.
        self._add_or_change_message(
            EnumFilenames.AGENCY_ADHOC,
            "federal_agency",
            transition_domain.federal_agency,
            domain_name,
            agency_exists
        )

        return transition_domain

    def parse_domain_type_data(self, domain_name, transition_domain: TransitionDomain) -> TransitionDomain:
        """Grabs organization_type and federal_type from the parsed files 
        and associates it with a transition_domain object, then returns that object."""
        if not isinstance(transition_domain, TransitionDomain):
            raise ValueError("Not a valid object, must be TransitionDomain")

        info = self.get_domain_type_info(domain_name)
        if info is None:
            self.parse_logs.create_log_item(
                EnumFilenames.DOMAIN_ADHOC,
                LogCode.ERROR,
                f"Could not add domain_type on {domain_name}, no data exists.",
                domain_name
            )
            return transition_domain

        # This data is stored as follows: FEDERAL - Judicial
        # For all other records, it is stored as so: Interstate
        # We can infer if it is federal or not based on this fact.
        domain_type = info.domaintype.split("-")
        domain_type_length = len(domain_type)
        if domain_type_length < 1 or domain_type_length > 2:
            raise ValueError("Found invalid data on DOMAIN_ADHOC")

        # Then, just grab the organization type.
        new_organization_type = domain_type[0].strip()

        # Check if this domain_type is active or not.
        # If not, we don't want to add this.
        if not info.active.lower() == "y":
            self.parse_logs.create_log_item(
                EnumFilenames.DOMAIN_ADHOC,
                LogCode.ERROR,
                f"Could not add inactive domain_type {domain_type[0]} on {domain_name}",
                domain_name
            )
            return transition_domain

        # Are we updating data that already exists,
        # or are we adding new data in its place?
        organization_type_exists = (
            transition_domain.organization_type is not None
            and transition_domain.organization_type.strip() != ""
        )
        federal_type_exists = (
            transition_domain.federal_type is not None
            and transition_domain.federal_type.strip() != ""
        )

        # If we get two records, then we know it is federal.
        # needs to be lowercase for federal type
        is_federal = domain_type_length == 2
        if is_federal:
            new_federal_type = domain_type[1].strip()
            transition_domain.organization_type = new_organization_type
            transition_domain.federal_type = new_federal_type
        else:
            transition_domain.organization_type = new_organization_type
            transition_domain.federal_type = None

        # Logs if we either added to this property,
        # or modified it.
        self._add_or_change_message(
            EnumFilenames.DOMAIN_ADHOC,
            "organization_type",
            transition_domain.organization_type,
            domain_name,
            organization_type_exists,
        )

        self._add_or_change_message(
            EnumFilenames.DOMAIN_ADHOC,
            "federal_type",
            transition_domain.federal_type,
            domain_name,
            federal_type_exists,
        )

        return transition_domain

    def parse_org_data(self, domain_name, transition_domain: TransitionDomain) -> TransitionDomain:
        """Grabs organization_name from the parsed files and associates it 
        with a transition_domain object, then returns that object."""
        if not isinstance(transition_domain, TransitionDomain):
            raise ValueError("Not a valid object, must be TransitionDomain")

        org_info = self.get_org_info(domain_name)
        if org_info is None:
            self.parse_logs.create_log_item(
                EnumFilenames.ORGANIZATION_ADHOC,
                LogCode.ERROR,
                f"Could not add organization_name on {domain_name}, no data exists.",
                domain_name
            )
            return transition_domain

        desired_property_exists = (
            transition_domain.organization_name is not None
            and transition_domain.organization_name.strip() != ""
        )

        transition_domain.organization_name = org_info.orgname

        # Logs if we either added to this property,
        # or modified it.
        self._add_or_change_message(
            EnumFilenames.ORGANIZATION_ADHOC,
            "organization_name",
            transition_domain.organization_name,
            domain_name,
            desired_property_exists,
        )

        return transition_domain

    def _add_or_change_message(
        self, file_type, var_name, changed_value, domain_name, is_update=False
    ):
        """Creates a log instance when a property
        is successfully changed on a given TransitionDomain."""
        if not is_update:
            self.parse_logs.create_log_item(
                file_type,
                LogCode.DEBUG,
                f"Added {var_name} as '{changed_value}' on {domain_name}",
                domain_name
            )
        else:
            self.parse_logs.create_log_item(
                file_type,
                LogCode.INFO,
                f"Updated existing {var_name} to '{changed_value}' on {domain_name}",
                domain_name
            )

    # Property getters, i.e. orgid or domaintypeid
    def get_org_info(self, domain_name) -> OrganizationAdhoc:
        """Maps an id given in get_domain_data to a organization_adhoc 
        record which has its corresponding definition"""
        domain_info = self.get_domain_data(domain_name)
        if domain_info is None:
            return None
        org_id = domain_info.orgid
        return self.get_organization_adhoc(org_id)

    def get_domain_type_info(self, domain_name) -> DomainTypeAdhoc:
        """Maps an id given in get_domain_data to a domain_type_adhoc 
        record which has its corresponding definition"""
        domain_info = self.get_domain_data(domain_name)
        if domain_info is None:
            return None
        type_id = domain_info.domaintypeid
        return self.get_domain_adhoc(type_id)

    def get_agency_info(self, domain_name) -> AgencyAdhoc:
        """Maps an id given in get_domain_data to a agency_adhoc 
        record which has its corresponding definition"""
        domain_info = self.get_domain_data(domain_name)
        if domain_info is None:
            return None
        type_id = domain_info.orgid
        return self.get_domain_adhoc(type_id)
    
    def get_authority_info(self, domain_name):
        """Maps an id given in get_domain_data to a authority_adhoc 
        record which has its corresponding definition"""
        domain_info = self.get_domain_data(domain_name)
        if domain_info is None:
            return None
        type_id = domain_info.authorityid
        return self.get_authority_adhoc(type_id)

    # Object getters, i.e. DomainAdditionalData or OrganizationAdhoc
    def get_domain_data(self, desired_id) -> DomainAdditionalData:
        """Grabs a corresponding row within the DOMAIN_ADDITIONAL file,
        based off a desired_id"""
        return self.get_object_by_id(EnumFilenames.DOMAIN_ADDITIONAL, desired_id)

    def get_organization_adhoc(self, desired_id) -> OrganizationAdhoc:
        """Grabs a corresponding row within the ORGANIZATION_ADHOC file,
        based off a desired_id"""
        return self.get_object_by_id(EnumFilenames.ORGANIZATION_ADHOC, desired_id)

    def get_domain_adhoc(self, desired_id) -> DomainTypeAdhoc:
        """Grabs a corresponding row within the DOMAIN_ADHOC file,
        based off a desired_id"""
        return self.get_object_by_id(EnumFilenames.DOMAIN_ADHOC, desired_id)

    def get_agency_adhoc(self, desired_id) -> AgencyAdhoc:
        """Grabs a corresponding row within the AGENCY_ADHOC file,
        based off a desired_id"""
        return self.get_object_by_id(EnumFilenames.AGENCY_ADHOC, desired_id)
    
    def get_authority_adhoc(self, desired_id) -> AuthorityAdhoc:
        """Grabs a corresponding row within the AUTHORITY_ADHOC file,
        based off a desired_id"""
        return self.get_object_by_id(EnumFilenames.AUTHORITY_ADHOC, desired_id)

    def get_object_by_id(self, file_type: EnumFilenames, desired_id):
        """Returns a field in a dictionary based off the type and id.

        vars:
            file_type: (constant) EnumFilenames -> Which data file to target.
            An example would be `EnumFilenames.DOMAIN_ADHOC`.

            desired_id: str -> Which id you want to search on. 
            An example would be `"12"` or `"igorville.gov"`
        
        Explanation:
            Each data file has an associated type (file_type) for tracking purposes.

            Each file_type is a dictionary which 
            contains a dictionary of row[id_field]: object.

            In practice, this would look like:

            EnumFilenames.AUTHORITY_ADHOC: { 
                "1": AuthorityAdhoc(...),
                "2": AuthorityAdhoc(...),
                ...
            }
            
            desired_id will then specify which id to grab. If we wanted "1",
            then this function will return the value of id "1".
            So, `AuthorityAdhoc(...)`
        """
        # Grabs a dict associated with the file_type.
        # For example, EnumFilenames.DOMAIN_ADDITIONAL.
        desired_type = self.domain_object.file_data.get(file_type)
        if desired_type is None:
            self.parse_logs.create_log_item(
                file_type, LogCode.ERROR, f"Type {file_type} does not exist"
            )
            return None

        # Grab the value given an Id within that file_type dict. 
        # For example, "igorville.gov".
        obj = desired_type.data.get(desired_id)
        if obj is None:
            self.parse_logs.create_log_item(
                file_type, LogCode.ERROR, f"Id {desired_id} does not exist"
            )
        return obj


@dataclass
class PatternMap:
    """Helper class that holds data and metadata about a requested file.

    filename: str -> The desired filename to target. If no filename is given,
    it is assumed that you are passing in a filename pattern and it will look
    for a filename that matches the given postfix you pass in.

    regex: re.Pattern -> Defines what regex you want to use when inferring
    filenames. If none, no matching occurs.

    data_type: type -> Metadata about the desired type for data.

    id_field: str -> Defines which field should act as the id in data.

    data: dict -> The returned data. Intended to be used with data_type
    to cross-reference.

    """

    def __init__(
        self,
        filename: str,
        regex: re.Pattern,
        data_type: type,
        id_field: str,
    ):
        self.regex = regex
        self.data_type = data_type
        self.id_field = id_field
        self.data = {}
        self.filename = filename
        self.could_infer = False

    def try_infer_filename(self, current_file_name, default_file_name):
        """Tries to match a given filename to a regex, 
        then uses that match to generate the filename."""
        # returns (filename, inferred_successfully)
        return self._infer_filename(self.regex, current_file_name, default_file_name)

    def _infer_filename(self, regex: re.Pattern, matched_file_name, default_file_name):
        if not isinstance(regex, re.Pattern):
            return (self.filename, False)
        
        match = regex.match(matched_file_name)
        
        if not match:
            return (self.filename, False)

        date = match.group(1)
        filename_without_date = match.group(2)

        # Can the supplied self.regex do a match on the filename?
        can_infer = filename_without_date == default_file_name
        if not can_infer:
            return (self.filename, False)

        # If so, note that and return the inferred name
        full_filename = date + "." + filename_without_date
        return (full_filename, can_infer)


class ExtraTransitionDomain:
    """Helper class to aid in storing TransitionDomain data spread across
    multiple files."""
    filenames = EnumFilenames
    #strip_date_regex = re.compile(r"\d+\.(.+)")
    strip_date_regex = re.compile(r"(?:.*\/)?(\d+)\.(.+)")

    def __init__(
        self,
        agency_adhoc_filename=filenames.AGENCY_ADHOC.value[1],
        domain_additional_filename=filenames.DOMAIN_ADDITIONAL.value[1],
        domain_adhoc_filename=filenames.DOMAIN_ADHOC.value[1],
        organization_adhoc_filename=filenames.ORGANIZATION_ADHOC.value[1],
        authority_adhoc_filename=filenames.AUTHORITY_ADHOC.value[1],
        directory="migrationdata",
        seperator="|",
    ):
        # Add a slash if the last character isn't one
        if directory and directory[-1] != "/":
            directory += "/"
        self.directory = directory
        self.seperator = seperator

        self.all_files = glob.glob(f"{directory}*")
        # Create a set with filenames as keys for quick lookup
        self.all_files_set = {os.path.basename(file) for file in self.all_files}
        self.file_data = {
            # (filename, default_url): metadata about the desired file
            self.filenames.AGENCY_ADHOC: PatternMap(
                agency_adhoc_filename, self.strip_date_regex, AgencyAdhoc, "agencyid"
            ),
            self.filenames.DOMAIN_ADDITIONAL: PatternMap(
                domain_additional_filename,
                self.strip_date_regex,
                DomainAdditionalData,
                "domainname",
            ),
            self.filenames.DOMAIN_ADHOC: PatternMap(
                domain_adhoc_filename,
                self.strip_date_regex,
                DomainTypeAdhoc,
                "domaintypeid",
            ),
            self.filenames.ORGANIZATION_ADHOC: PatternMap(
                organization_adhoc_filename,
                self.strip_date_regex,
                OrganizationAdhoc,
                "orgid",
            ),
            self.filenames.AUTHORITY_ADHOC: PatternMap(
                authority_adhoc_filename,
                self.strip_date_regex,
                AuthorityAdhoc,
                "authorityid",
            ),
        }

    def parse_all_files(self, infer_filenames=True):
        """Clears all preexisting data then parses each related CSV file.

        overwrite_existing_data: bool -> Determines if we should clear
        file_data.data if it already exists
        """
        self.clear_file_data()
        for name, value in self.file_data.items():

            filename = f"{value.filename}"
            if filename in self.all_files_set:
                _file = f"{self.directory}{value.filename}"
                value.data = self._read_csv_file(
                    _file,
                    self.seperator,
                    value.data_type,
                    value.id_field,
                )
            else:
                if not infer_filenames:
                    logger.error(f"Could not find file: {filename}")
                    continue
                
                logger.warning(
                    "Attempting to infer filename" 
                    f" for file: {filename}."
                )
                for filename in self.all_files:
                    default_name = name.value[1]
                    match = value.try_infer_filename(filename, default_name)
                    filename = match[0]
                    can_infer = match[1]
                    if can_infer:
                        break

                if filename in self.all_files_set:
                    logger.info(f"Infer success. Found file {filename}")
                    _file = f"{self.directory}{filename}"
                    value.data = self._read_csv_file(
                        _file,
                        self.seperator,
                        value.data_type,
                        value.id_field,
                    )
                    continue
                # Log if we can't find the desired file
                logger.error(f"Could not find file: {filename}")

    def clear_file_data(self):
        for item in self.file_data.values():
            file_type: PatternMap = item
            file_type.data = {}

    def _read_csv_file(self, file, seperator, dataclass_type, id_field):
        with open(file, "r", encoding="utf-8-sig") as requested_file:
            reader = csv.DictReader(requested_file, delimiter=seperator)
            """
            for row in reader:
                print({key: type(key) for key in row.keys()})  # print out the keys and their types
                test = {row[id_field]: dataclass_type(**row)}
            """
            dict_data = {}
            for row in reader:
                if None in row:
                    print("Skipping row with None key")
                    #for key, value in row.items():
                        #print(f"key: {key} value: {value}")
                    continue
                row_id = row[id_field]
                dict_data[row_id] = dataclass_type(**row)
            #dict_data = {row[id_field]: dataclass_type(**row) for row in reader}
            return dict_data