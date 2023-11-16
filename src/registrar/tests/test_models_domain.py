"""
Feature being tested: Registry Integration

This file tests the various ways in which the registrar interacts with the registry.
"""
from django.test import TestCase
from django.db.utils import IntegrityError
from unittest.mock import MagicMock, patch, call
import datetime
from registrar.models import Domain

from unittest import skip
from registrar.models.domain_application import DomainApplication
from registrar.models.domain_information import DomainInformation
from registrar.models.draft_domain import DraftDomain
from registrar.models.public_contact import PublicContact
from registrar.models.user import User
from registrar.utility.errors import ActionNotAllowed, NameserverError

from registrar.models.utility.contact_error import ContactError, ContactErrorCodes


from django_fsm import TransitionNotAllowed  # type: ignore
from epplibwrapper import (
    commands,
    common,
    extensions,
    responses,
    RegistryError,
    ErrorCode,
)
from .common import MockEppLib
import logging

logger = logging.getLogger(__name__)


class TestDomainCache(MockEppLib):
    def tearDown(self):
        PublicContact.objects.all().delete()
        Domain.objects.all().delete()
        super().tearDown()

    def test_cache_sets_resets(self):
        """Cache should be set on getter and reset on setter calls"""
        domain, _ = Domain.objects.get_or_create(name="igorville.gov")
        # trigger getter
        _ = domain.creation_date
        domain._get_property("contacts")
        # getter should set the domain cache with a InfoDomain object
        # (see InfoDomainResult)
        self.assertEquals(domain._cache["auth_info"], self.mockDataInfoDomain.auth_info)
        self.assertEquals(domain._cache["cr_date"], self.mockDataInfoDomain.cr_date)
        status_list = [status.state for status in self.mockDataInfoDomain.statuses]
        self.assertEquals(domain._cache["statuses"], status_list)
        self.assertFalse("avail" in domain._cache.keys())

        # using a setter should clear the cache
        domain.dnssecdata = []
        self.assertEquals(domain._cache, {})

        # send should have been called only once
        self.mockedSendFunction.assert_has_calls(
            [
                call(
                    commands.InfoDomain(name="igorville.gov", auth_info=None),
                    cleaned=True,
                ),
            ],
            any_order=False,  # Ensure calls are in the specified order
        )

    def test_cache_used_when_avail(self):
        """Cache is pulled from if the object has already been accessed"""
        domain, _ = Domain.objects.get_or_create(name="igorville.gov")
        cr_date = domain.creation_date

        # repeat the getter call
        cr_date = domain.creation_date

        # value should still be set correctly
        self.assertEqual(cr_date, self.mockDataInfoDomain.cr_date)
        self.assertEqual(domain._cache["cr_date"], self.mockDataInfoDomain.cr_date)

        # send was only called once & not on the second getter call
        expectedCalls = [
            call(commands.InfoDomain(name="igorville.gov", auth_info=None), cleaned=True),
        ]

        self.mockedSendFunction.assert_has_calls(expectedCalls)

    def test_cache_nested_elements(self):
        """Cache works correctly with the nested objects cache and hosts"""
        domain, _ = Domain.objects.get_or_create(name="igorville.gov")
        # The contact list will initially contain objects of type 'DomainContact'
        # this is then transformed into PublicContact, and cache should NOT
        # hold onto the DomainContact object
        expectedUnfurledContactsList = [
            common.DomainContact(contact="123", type="security"),
        ]
        expectedContactsDict = {
            PublicContact.ContactTypeChoices.ADMINISTRATIVE: None,
            PublicContact.ContactTypeChoices.SECURITY: "123",
            PublicContact.ContactTypeChoices.TECHNICAL: None,
        }
        expectedHostsDict = {
            "name": self.mockDataInfoDomain.hosts[0],
            "addrs": [item.addr for item in self.mockDataInfoHosts.addrs],
            "cr_date": self.mockDataInfoHosts.cr_date,
        }

        # this can be changed when the getter for contacts is implemented
        domain._get_property("contacts")

        # check domain info is still correct and not overridden
        self.assertEqual(domain._cache["auth_info"], self.mockDataInfoDomain.auth_info)
        self.assertEqual(domain._cache["cr_date"], self.mockDataInfoDomain.cr_date)

        # check contacts
        self.assertEqual(domain._cache["_contacts"], self.mockDataInfoDomain.contacts)
        # The contact list should not contain what is sent by the registry by default,
        # as _fetch_cache will transform the type to PublicContact
        self.assertNotEqual(domain._cache["contacts"], expectedUnfurledContactsList)
        self.assertEqual(domain._cache["contacts"], expectedContactsDict)

        # get and check hosts is set correctly
        domain._get_property("hosts")
        self.assertEqual(domain._cache["hosts"], [expectedHostsDict])
        self.assertEqual(domain._cache["contacts"], expectedContactsDict)
        # invalidate cache
        domain._cache = {}

        # get host
        domain._get_property("hosts")
        self.assertEqual(domain._cache["hosts"], [expectedHostsDict])

        # get contacts
        domain._get_property("contacts")
        self.assertEqual(domain._cache["hosts"], [expectedHostsDict])
        self.assertEqual(domain._cache["contacts"], expectedContactsDict)

    def test_map_epp_contact_to_public_contact(self):
        # Tests that the mapper is working how we expect
        domain, _ = Domain.objects.get_or_create(name="registry.gov")
        security = PublicContact.ContactTypeChoices.SECURITY
        mapped = domain.map_epp_contact_to_public_contact(
            self.mockDataInfoContact,
            self.mockDataInfoContact.id,
            security,
        )

        expected_contact = PublicContact(
            domain=domain,
            contact_type=security,
            registry_id="123",
            email="123@mail.gov",
            voice="+1.8882820870",
            fax="+1-212-9876543",
            pw="lastPw",
            name="Registry Customer Service",
            org="Cybersecurity and Infrastructure Security Agency",
            city="Arlington",
            pc="22201",
            cc="US",
            sp="VA",
            street1="4200 Wilson Blvd.",
        )

        # Test purposes only, since we're comparing
        # two duplicate objects. We would expect
        # these not to have the same state.
        expected_contact._state = mapped._state

        # Mapped object is what we expect
        self.assertEqual(mapped.__dict__, expected_contact.__dict__)

        # The mapped object should correctly translate to a DB
        # object. If not, something else went wrong.
        db_object = domain._get_or_create_public_contact(mapped)
        in_db = PublicContact.objects.filter(
            registry_id=domain.security_contact.registry_id,
            contact_type=security,
        ).get()
        # DB Object is the same as the mapped object
        self.assertEqual(db_object, in_db)

        domain.security_contact = in_db
        # Trigger the getter
        _ = domain.security_contact
        # Check to see that changes made
        # to DB objects persist in cache correctly
        in_db.email = "123test@mail.gov"
        in_db.save()

        cached_contact = domain._cache["contacts"].get(security)
        self.assertEqual(cached_contact, in_db.registry_id)
        self.assertEqual(domain.security_contact.email, "123test@mail.gov")

    def test_errors_map_epp_contact_to_public_contact(self):
        """
        Scenario: Registrant gets invalid data from EPPLib
            When the `map_epp_contact_to_public_contact` function
                gets invalid data from EPPLib
            Then the function throws the expected ContactErrors
        """
        domain, _ = Domain.objects.get_or_create(name="registry.gov")
        fakedEpp = self.fakedEppObject()
        invalid_length = fakedEpp.dummyInfoContactResultData(
            "Cymaticsisasubsetofmodalvibrationalphenomena", "lengthInvalid@mail.gov"
        )
        valid_object = fakedEpp.dummyInfoContactResultData("valid", "valid@mail.gov")

        desired_error = ContactErrorCodes.CONTACT_ID_INVALID_LENGTH
        with self.assertRaises(ContactError) as context:
            domain.map_epp_contact_to_public_contact(
                invalid_length,
                invalid_length.id,
                PublicContact.ContactTypeChoices.SECURITY,
            )
        self.assertEqual(context.exception.code, desired_error)

        desired_error = ContactErrorCodes.CONTACT_ID_NONE
        with self.assertRaises(ContactError) as context:
            domain.map_epp_contact_to_public_contact(
                valid_object,
                None,
                PublicContact.ContactTypeChoices.SECURITY,
            )
        self.assertEqual(context.exception.code, desired_error)

        desired_error = ContactErrorCodes.CONTACT_INVALID_TYPE
        with self.assertRaises(ContactError) as context:
            domain.map_epp_contact_to_public_contact(
                "bad_object",
                valid_object.id,
                PublicContact.ContactTypeChoices.SECURITY,
            )
        self.assertEqual(context.exception.code, desired_error)

        desired_error = ContactErrorCodes.CONTACT_TYPE_NONE
        with self.assertRaises(ContactError) as context:
            domain.map_epp_contact_to_public_contact(
                valid_object,
                valid_object.id,
                None,
            )
        self.assertEqual(context.exception.code, desired_error)


class TestDomainCreation(MockEppLib):
    """Rule: An approved domain application must result in a domain"""

    def test_approved_application_creates_domain_locally(self):
        """
        Scenario: Analyst approves a domain application
            When the DomainApplication transitions to approved
            Then a Domain exists in the database with the same `name`
            But a domain object does not exist in the registry
        """
        draft_domain, _ = DraftDomain.objects.get_or_create(name="igorville.gov")
        user, _ = User.objects.get_or_create()
        application = DomainApplication.objects.create(creator=user, requested_domain=draft_domain)
        # skip using the submit method
        application.status = DomainApplication.SUBMITTED
        # transition to approve state
        application.approve()
        # should have information present for this domain
        domain = Domain.objects.get(name="igorville.gov")
        self.assertTrue(domain)
        self.mockedSendFunction.assert_not_called()

    def test_accessing_domain_properties_creates_domain_in_registry(self):
        """
        Scenario: A registrant checks the status of a newly approved domain
            Given that no domain object exists in the registry
            When a property is accessed
            Then Domain sends `commands.CreateDomain` to the registry
            And `domain.state` is set to `UNKNOWN`
            And `domain.is_active()` returns False
        """
        domain = Domain.objects.create(name="beef-tongue.gov")
        # trigger getter
        _ = domain.statuses

        # contacts = PublicContact.objects.filter(domain=domain,
        # type=PublicContact.ContactTypeChoices.REGISTRANT).get()

        # Called in _fetch_cache
        self.mockedSendFunction.assert_has_calls(
            [
                # TODO: due to complexity of the test, will return to it in
                # a future ticket
                # call(
                #     commands.CreateDomain(name="beef-tongue.gov",
                #     id=contact.registry_id, auth_info=None),
                #     cleaned=True,
                # ),
                call(
                    commands.InfoDomain(name="beef-tongue.gov", auth_info=None),
                    cleaned=True,
                ),
            ],
            any_order=False,  # Ensure calls are in the specified order
        )

        self.assertEqual(domain.state, Domain.State.UNKNOWN)
        self.assertEqual(domain.is_active(), False)

    @skip("assertion broken with mock addition")
    def test_empty_domain_creation(self):
        """Can't create a completely empty domain."""
        with self.assertRaisesRegex(IntegrityError, "name"):
            Domain.objects.create()

    def test_minimal_creation(self):
        """Can create with just a name."""
        Domain.objects.create(name="igorville.gov")

    @skip("assertion broken with mock addition")
    def test_duplicate_creation(self):
        """Can't create domain if name is not unique."""
        Domain.objects.create(name="igorville.gov")
        with self.assertRaisesRegex(IntegrityError, "name"):
            Domain.objects.create(name="igorville.gov")

    def tearDown(self) -> None:
        DomainInformation.objects.all().delete()
        DomainApplication.objects.all().delete()
        PublicContact.objects.all().delete()
        Domain.objects.all().delete()
        User.objects.all().delete()
        DraftDomain.objects.all().delete()
        super().tearDown()


class TestDomainStatuses(MockEppLib):
    """Domain statuses are set by the registry"""

    def test_get_status(self):
        """Domain 'statuses' getter returns statuses by calling epp"""
        domain, _ = Domain.objects.get_or_create(name="chicken-liver.gov")
        # trigger getter
        _ = domain.statuses
        status_list = [status.state for status in self.mockDataInfoDomain.statuses]
        self.assertEquals(domain._cache["statuses"], status_list)
        # Called in _fetch_cache
        self.mockedSendFunction.assert_has_calls(
            [
                call(
                    commands.InfoDomain(name="chicken-liver.gov", auth_info=None),
                    cleaned=True,
                ),
            ],
            any_order=False,  # Ensure calls are in the specified order
        )

    def test_get_status_returns_empty_list_when_value_error(self):
        """Domain 'statuses' getter returns an empty list
        when value error"""
        domain, _ = Domain.objects.get_or_create(name="pig-knuckles.gov")

        def side_effect(self):
            raise KeyError

        patcher = patch("registrar.models.domain.Domain._get_property")
        mocked_get = patcher.start()
        mocked_get.side_effect = side_effect

        # trigger getter
        _ = domain.statuses

        with self.assertRaises(KeyError):
            _ = domain._cache["statuses"]
        self.assertEquals(_, [])

        patcher.stop()

    @skip("not implemented yet")
    def test_place_client_hold_sets_status(self):
        """Domain 'place_client_hold' method causes the registry to change statuses"""
        raise

    @skip("not implemented yet")
    def test_revert_client_hold_sets_status(self):
        """Domain 'revert_client_hold' method causes the registry to change statuses"""
        raise

    def tearDown(self) -> None:
        PublicContact.objects.all().delete()
        Domain.objects.all().delete()
        super().tearDown()


class TestDomainAvailable(MockEppLib):
    """Test Domain.available"""

    # No SetUp or tearDown necessary for these tests

    def test_domain_available(self):
        """
        Scenario: Testing whether an available domain is available
            Should return True

            Mock response to mimic EPP Response
            Validate CheckDomain command is called
            Validate response given mock
        """

        def side_effect(_request, cleaned):
            return MagicMock(
                res_data=[responses.check.CheckDomainResultData(name="available.gov", avail=True, reason=None)],
            )

        patcher = patch("registrar.models.domain.registry.send")
        mocked_send = patcher.start()
        mocked_send.side_effect = side_effect

        available = Domain.available("available.gov")
        mocked_send.assert_has_calls(
            [
                call(
                    commands.CheckDomain(
                        ["available.gov"],
                    ),
                    cleaned=True,
                )
            ]
        )
        self.assertTrue(available)
        patcher.stop()

    def test_domain_unavailable(self):
        """
        Scenario: Testing whether an unavailable domain is available
            Should return False

            Mock response to mimic EPP Response
            Validate CheckDomain command is called
            Validate response given mock
        """

        def side_effect(_request, cleaned):
            return MagicMock(
                res_data=[responses.check.CheckDomainResultData(name="unavailable.gov", avail=False, reason="In Use")],
            )

        patcher = patch("registrar.models.domain.registry.send")
        mocked_send = patcher.start()
        mocked_send.side_effect = side_effect

        available = Domain.available("unavailable.gov")
        mocked_send.assert_has_calls(
            [
                call(
                    commands.CheckDomain(
                        ["unavailable.gov"],
                    ),
                    cleaned=True,
                )
            ]
        )
        self.assertFalse(available)
        patcher.stop()

    def test_domain_available_with_value_error(self):
        """
        Scenario: Testing whether an invalid domain is available
            Should throw ValueError

            Validate ValueError is raised
        """
        with self.assertRaises(ValueError):
            Domain.available("invalid-string")

    def test_domain_available_unsuccessful(self):
        """
        Scenario: Testing behavior when registry raises a RegistryError

            Validate RegistryError is raised
        """

        def side_effect(_request, cleaned):
            raise RegistryError(code=ErrorCode.COMMAND_SYNTAX_ERROR)

        patcher = patch("registrar.models.domain.registry.send")
        mocked_send = patcher.start()
        mocked_send.side_effect = side_effect

        with self.assertRaises(RegistryError):
            Domain.available("raises-error.gov")
        patcher.stop()


class TestRegistrantContacts(MockEppLib):
    """Rule: Registrants may modify their WHOIS data"""

    def setUp(self):
        """
        Background:
            Given the registrant is logged in
            And the registrant is the admin on a domain
        """
        super().setUp()
        # Creates a domain with no contact associated to it
        self.domain, _ = Domain.objects.get_or_create(name="security.gov")
        # Creates a domain with an associated contact
        self.domain_contact, _ = Domain.objects.get_or_create(name="freeman.gov")

    def tearDown(self):
        super().tearDown()
        self.domain._invalidate_cache()
        self.domain_contact._invalidate_cache()
        PublicContact.objects.all().delete()
        Domain.objects.all().delete()

    def test_no_security_email(self):
        """
        Scenario: Registrant has not added a security contact email
            Given `domain.security_contact` has not been set to anything
            When the domain is created in the registry
            Then the domain has a valid security contact with CISA defaults
            And disclose flags are set to keep the email address hidden
        """

        # making a domain should make it domain
        expectedSecContact = PublicContact.get_default_security()
        expectedSecContact.domain = self.domain

        self.domain.dns_needed_from_unknown()

        self.assertEqual(self.mockedSendFunction.call_count, 8)
        self.assertEqual(PublicContact.objects.filter(domain=self.domain).count(), 4)
        self.assertEqual(
            PublicContact.objects.get(
                domain=self.domain,
                contact_type=PublicContact.ContactTypeChoices.SECURITY,
            ).email,
            expectedSecContact.email,
        )

        id = PublicContact.objects.get(
            domain=self.domain,
            contact_type=PublicContact.ContactTypeChoices.SECURITY,
        ).registry_id

        expectedSecContact.registry_id = id
        expectedCreateCommand = self._convertPublicContactToEpp(expectedSecContact, disclose_email=False)
        expectedUpdateDomain = commands.UpdateDomain(
            name=self.domain.name,
            add=[common.DomainContact(contact=expectedSecContact.registry_id, type="security")],
        )

        self.mockedSendFunction.assert_any_call(expectedCreateCommand, cleaned=True)
        self.mockedSendFunction.assert_any_call(expectedUpdateDomain, cleaned=True)

    def test_user_adds_security_email(self):
        """
        Scenario: Registrant adds a security contact email
            When `domain.security_contact` is set equal to a PublicContact with the
                chosen security contact email
            Then Domain sends `commands.CreateContact` to the registry
            And Domain sends `commands.UpdateDomain` to the registry with the newly
                created contact of type 'security'
        """
        # make a security contact that is a PublicContact
        # make sure a security email already exists
        self.domain.dns_needed_from_unknown()
        expectedSecContact = PublicContact.get_default_security()
        expectedSecContact.domain = self.domain
        expectedSecContact.email = "newEmail@fake.com"
        expectedSecContact.registry_id = "456"
        expectedSecContact.name = "Fakey McFakerson"

        # calls the security contact setter as if you did
        #  self.domain.security_contact=expectedSecContact
        expectedSecContact.save()

        # no longer the default email it should be disclosed
        expectedCreateCommand = self._convertPublicContactToEpp(expectedSecContact, disclose_email=True)

        expectedUpdateDomain = commands.UpdateDomain(
            name=self.domain.name,
            add=[common.DomainContact(contact=expectedSecContact.registry_id, type="security")],
        )

        # check that send has triggered the create command for the contact
        receivedSecurityContact = PublicContact.objects.get(
            domain=self.domain, contact_type=PublicContact.ContactTypeChoices.SECURITY
        )

        self.assertEqual(receivedSecurityContact, expectedSecContact)
        self.mockedSendFunction.assert_any_call(expectedCreateCommand, cleaned=True)
        self.mockedSendFunction.assert_any_call(expectedUpdateDomain, cleaned=True)

    def test_security_email_is_idempotent(self):
        """
        Scenario: Registrant adds a security contact email twice, due to a UI glitch
            When `commands.CreateContact` and `commands.UpdateDomain` are sent
                to the registry twice with identical data
            Then no errors are raised in Domain
        """

        security_contact = self.domain.get_default_security_contact()
        security_contact.registry_id = "fail"
        security_contact.save()

        self.domain.security_contact = security_contact

        expectedCreateCommand = self._convertPublicContactToEpp(security_contact, disclose_email=False)

        expectedUpdateDomain = commands.UpdateDomain(
            name=self.domain.name,
            add=[common.DomainContact(contact=security_contact.registry_id, type="security")],
        )
        expected_calls = [
            call(expectedCreateCommand, cleaned=True),
            call(expectedCreateCommand, cleaned=True),
            call(expectedUpdateDomain, cleaned=True),
        ]
        self.mockedSendFunction.assert_has_calls(expected_calls, any_order=True)
        self.assertEqual(PublicContact.objects.filter(domain=self.domain).count(), 1)

    def test_user_deletes_security_email(self):
        """
        Scenario: Registrant clears out an existing security contact email
            Given a domain exists in the registry with a user-added security email
            When `domain.security_contact` is set equal to a PublicContact with an empty
                security contact email
            Then Domain sends `commands.UpdateDomain` and `commands.DeleteContact`
                to the registry
            And the domain has a valid security contact with CISA defaults
            And disclose flags are set to keep the email address hidden
        """
        old_contact = self.domain.get_default_security_contact()

        old_contact.registry_id = "fail"
        old_contact.email = "user.entered@email.com"
        old_contact.save()
        new_contact = self.domain.get_default_security_contact()
        new_contact.registry_id = "fail"
        new_contact.email = ""
        self.domain.security_contact = new_contact

        firstCreateContactCall = self._convertPublicContactToEpp(old_contact, disclose_email=True)
        updateDomainAddCall = commands.UpdateDomain(
            name=self.domain.name,
            add=[common.DomainContact(contact=old_contact.registry_id, type="security")],
        )
        self.assertEqual(
            PublicContact.objects.filter(domain=self.domain).get().email,
            PublicContact.get_default_security().email,
        )
        # this one triggers the fail
        secondCreateContact = self._convertPublicContactToEpp(new_contact, disclose_email=True)
        updateDomainRemCall = commands.UpdateDomain(
            name=self.domain.name,
            rem=[common.DomainContact(contact=old_contact.registry_id, type="security")],
        )

        defaultSecID = PublicContact.objects.filter(domain=self.domain).get().registry_id
        default_security = PublicContact.get_default_security()
        default_security.registry_id = defaultSecID
        createDefaultContact = self._convertPublicContactToEpp(default_security, disclose_email=False)
        updateDomainWDefault = commands.UpdateDomain(
            name=self.domain.name,
            add=[common.DomainContact(contact=defaultSecID, type="security")],
        )

        expected_calls = [
            call(firstCreateContactCall, cleaned=True),
            call(updateDomainAddCall, cleaned=True),
            call(secondCreateContact, cleaned=True),
            call(updateDomainRemCall, cleaned=True),
            call(createDefaultContact, cleaned=True),
            call(updateDomainWDefault, cleaned=True),
        ]

        self.mockedSendFunction.assert_has_calls(expected_calls, any_order=True)

    def test_updates_security_email(self):
        """
        Scenario: Registrant replaces one valid security contact email with another
            Given a domain exists in the registry with a user-added security email
            When `domain.security_contact` is set equal to a PublicContact with a new
                security contact email
            Then Domain sends `commands.UpdateContact` to the registry
        """
        security_contact = self.domain.get_default_security_contact()
        security_contact.email = "originalUserEmail@gmail.com"
        security_contact.registry_id = "fail"
        security_contact.save()
        expectedCreateCommand = self._convertPublicContactToEpp(security_contact, disclose_email=True)

        expectedUpdateDomain = commands.UpdateDomain(
            name=self.domain.name,
            add=[common.DomainContact(contact=security_contact.registry_id, type="security")],
        )
        security_contact.email = "changedEmail@email.com"
        security_contact.save()
        expectedSecondCreateCommand = self._convertPublicContactToEpp(security_contact, disclose_email=True)
        updateContact = self._convertPublicContactToEpp(security_contact, disclose_email=True, createContact=False)

        expected_calls = [
            call(expectedCreateCommand, cleaned=True),
            call(expectedUpdateDomain, cleaned=True),
            call(expectedSecondCreateCommand, cleaned=True),
            call(updateContact, cleaned=True),
        ]
        self.mockedSendFunction.assert_has_calls(expected_calls, any_order=True)
        self.assertEqual(PublicContact.objects.filter(domain=self.domain).count(), 1)

    def test_not_disclosed_on_other_contacts(self):
        """
        Scenario: Registrant creates a new domain with multiple contacts
            When `domain` has registrant, admin, technical,
                and security contacts
            Then Domain sends `commands.CreateContact` to the registry
            And the field `disclose` is set to false for DF.EMAIL
                on all fields except security
        """
        # Generates a domain with four existing contacts
        domain, _ = Domain.objects.get_or_create(name="freeman.gov")

        # Contact setup
        expected_admin = domain.get_default_administrative_contact()
        expected_admin.email = self.mockAdministrativeContact.email

        expected_registrant = domain.get_default_registrant_contact()
        expected_registrant.email = self.mockRegistrantContact.email

        expected_security = domain.get_default_security_contact()
        expected_security.email = self.mockSecurityContact.email

        expected_tech = domain.get_default_technical_contact()
        expected_tech.email = self.mockTechnicalContact.email

        domain.administrative_contact = expected_admin
        domain.registrant_contact = expected_registrant
        domain.security_contact = expected_security
        domain.technical_contact = expected_tech

        contacts = [
            (expected_admin, domain.administrative_contact),
            (expected_registrant, domain.registrant_contact),
            (expected_security, domain.security_contact),
            (expected_tech, domain.technical_contact),
        ]

        # Test for each contact
        for contact in contacts:
            expected_contact = contact[0]
            actual_contact = contact[1]
            is_security = expected_contact.contact_type == "security"

            expectedCreateCommand = self._convertPublicContactToEpp(expected_contact, disclose_email=is_security)

            # Should only be disclosed if the type is security, as the email is valid
            self.mockedSendFunction.assert_any_call(expectedCreateCommand, cleaned=True)

            # The emails should match on both items
            self.assertEqual(expected_contact.email, actual_contact.email)

    def test_convert_public_contact_to_epp(self):
        self.maxDiff = None
        domain, _ = Domain.objects.get_or_create(name="freeman.gov")
        dummy_contact = domain.get_default_security_contact()
        test_disclose = self._convertPublicContactToEpp(dummy_contact, disclose_email=True).__dict__
        test_not_disclose = self._convertPublicContactToEpp(dummy_contact, disclose_email=False).__dict__

        # Separated for linter
        disclose_email_field = {common.DiscloseField.EMAIL}
        expected_disclose = {
            "auth_info": common.ContactAuthInfo(pw="2fooBAR123fooBaz"),
            "disclose": common.Disclose(flag=True, fields=disclose_email_field, types=None),
            "email": "dotgov@cisa.dhs.gov",
            "extensions": [],
            "fax": None,
            "id": "ThIq2NcRIDN7PauO",
            "ident": None,
            "notify_email": None,
            "postal_info": common.PostalInfo(
                name="Registry Customer Service",
                addr=common.ContactAddr(
                    street=["4200 Wilson Blvd.", None, None],
                    city="Arlington",
                    pc="22201",
                    cc="US",
                    sp="VA",
                ),
                org="Cybersecurity and Infrastructure Security Agency",
                type="loc",
            ),
            "vat": None,
            "voice": "+1.8882820870",
        }

        # Separated for linter
        expected_not_disclose = {
            "auth_info": common.ContactAuthInfo(pw="2fooBAR123fooBaz"),
            "disclose": common.Disclose(flag=False, fields=disclose_email_field, types=None),
            "email": "dotgov@cisa.dhs.gov",
            "extensions": [],
            "fax": None,
            "id": "ThrECENCHI76PGLh",
            "ident": None,
            "notify_email": None,
            "postal_info": common.PostalInfo(
                name="Registry Customer Service",
                addr=common.ContactAddr(
                    street=["4200 Wilson Blvd.", None, None],
                    city="Arlington",
                    pc="22201",
                    cc="US",
                    sp="VA",
                ),
                org="Cybersecurity and Infrastructure Security Agency",
                type="loc",
            ),
            "vat": None,
            "voice": "+1.8882820870",
        }

        # Set the ids equal, since this value changes
        test_disclose["id"] = expected_disclose["id"]
        test_not_disclose["id"] = expected_not_disclose["id"]

        self.assertEqual(test_disclose, expected_disclose)
        self.assertEqual(test_not_disclose, expected_not_disclose)

    def test_not_disclosed_on_default_security_contact(self):
        """
        Scenario: Registrant creates a new domain with no security email
            When `domain.security_contact.email` is equal to the default
            Then Domain sends `commands.CreateContact` to the registry
            And the field `disclose` is set to false for DF.EMAIL
        """
        domain, _ = Domain.objects.get_or_create(name="defaultsecurity.gov")
        expectedSecContact = PublicContact.get_default_security()
        expectedSecContact.domain = domain
        expectedSecContact.registry_id = "defaultSec"
        domain.security_contact = expectedSecContact

        expectedCreateCommand = self._convertPublicContactToEpp(expectedSecContact, disclose_email=False)

        self.mockedSendFunction.assert_any_call(expectedCreateCommand, cleaned=True)
        # Confirm that we are getting a default email
        self.assertEqual(domain.security_contact.email, expectedSecContact.email)

    def test_not_disclosed_on_default_technical_contact(self):
        """
        Scenario: Registrant creates a new domain with no technical contact
            When `domain.technical_contact.email` is equal to the default
            Then Domain sends `commands.CreateContact` to the registry
            And the field `disclose` is set to false for DF.EMAIL
        """
        domain, _ = Domain.objects.get_or_create(name="defaulttechnical.gov")
        expectedTechContact = PublicContact.get_default_technical()
        expectedTechContact.domain = domain
        expectedTechContact.registry_id = "defaultTech"
        domain.technical_contact = expectedTechContact

        expectedCreateCommand = self._convertPublicContactToEpp(expectedTechContact, disclose_email=False)

        self.mockedSendFunction.assert_any_call(expectedCreateCommand, cleaned=True)
        # Confirm that we are getting a default email
        self.assertEqual(domain.technical_contact.email, expectedTechContact.email)

    def test_is_disclosed_on_security_contact(self):
        """
        Scenario: Registrant creates a new domain with a security email
            When `domain.security_contact.email` is set to a valid email
                and is not the default
            Then Domain sends `commands.CreateContact` to the registry
            And the field `disclose` is set to true for DF.EMAIL
        """
        domain, _ = Domain.objects.get_or_create(name="igorville.gov")
        expectedSecContact = PublicContact.get_default_security()
        expectedSecContact.domain = domain
        expectedSecContact.email = "123@mail.gov"
        domain.security_contact = expectedSecContact

        expectedCreateCommand = self._convertPublicContactToEpp(expectedSecContact, disclose_email=True)

        self.mockedSendFunction.assert_any_call(expectedCreateCommand, cleaned=True)
        # Confirm that we are getting the desired email
        self.assertEqual(domain.security_contact.email, expectedSecContact.email)

    @skip("not implemented yet")
    def test_update_is_unsuccessful(self):
        """
        Scenario: An update to the security contact is unsuccessful
            When an error is returned from epplibwrapper
            Then a user-friendly error message is returned for displaying on the web
        """
        raise

    def test_contact_getter_security(self):
        security = PublicContact.ContactTypeChoices.SECURITY
        # Create prexisting object
        expected_contact = self.domain.map_epp_contact_to_public_contact(
            self.mockSecurityContact,
            contact_id="securityContact",
            contact_type=security,
        )

        # Checks if we grabbed the correct PublicContact
        self.assertEqual(self.domain_contact.security_contact.email, expected_contact.email)

        expected_contact_db = PublicContact.objects.filter(
            registry_id=self.domain_contact.security_contact.registry_id,
            contact_type=security,
        ).get()

        self.assertEqual(self.domain_contact.security_contact, expected_contact_db)

        self.mockedSendFunction.assert_has_calls(
            [
                call(
                    commands.InfoContact(id="securityContact", auth_info=None),
                    cleaned=True,
                ),
            ]
        )
        # Checks if we are receiving the cache we expect
        cache = self.domain_contact._cache["contacts"]
        self.assertEqual(cache.get(security), "securityContact")

    def test_contact_getter_technical(self):
        technical = PublicContact.ContactTypeChoices.TECHNICAL
        expected_contact = self.domain.map_epp_contact_to_public_contact(
            self.mockTechnicalContact,
            contact_id="technicalContact",
            contact_type=technical,
        )

        self.assertEqual(self.domain_contact.technical_contact.email, expected_contact.email)

        # Checks if we grab the correct PublicContact
        expected_contact_db = PublicContact.objects.filter(
            registry_id=self.domain_contact.technical_contact.registry_id,
            contact_type=technical,
        ).get()

        # Checks if we grab the correct PublicContact
        self.assertEqual(self.domain_contact.technical_contact, expected_contact_db)
        self.mockedSendFunction.assert_has_calls(
            [
                call(
                    commands.InfoContact(id="technicalContact", auth_info=None),
                    cleaned=True,
                ),
            ]
        )
        # Checks if we are receiving the cache we expect
        cache = self.domain_contact._cache["contacts"]
        self.assertEqual(cache.get(technical), "technicalContact")

    def test_contact_getter_administrative(self):
        administrative = PublicContact.ContactTypeChoices.ADMINISTRATIVE
        expected_contact = self.domain.map_epp_contact_to_public_contact(
            self.mockAdministrativeContact,
            contact_id="adminContact",
            contact_type=administrative,
        )

        self.assertEqual(self.domain_contact.administrative_contact.email, expected_contact.email)

        expected_contact_db = PublicContact.objects.filter(
            registry_id=self.domain_contact.administrative_contact.registry_id,
            contact_type=administrative,
        ).get()

        # Checks if we grab the correct PublicContact
        self.assertEqual(self.domain_contact.administrative_contact, expected_contact_db)
        self.mockedSendFunction.assert_has_calls(
            [
                call(
                    commands.InfoContact(id="adminContact", auth_info=None),
                    cleaned=True,
                ),
            ]
        )
        # Checks if we are receiving the cache we expect
        cache = self.domain_contact._cache["contacts"]
        self.assertEqual(cache.get(administrative), "adminContact")

    def test_contact_getter_registrant(self):
        expected_contact = self.domain.map_epp_contact_to_public_contact(
            self.mockRegistrantContact,
            contact_id="regContact",
            contact_type=PublicContact.ContactTypeChoices.REGISTRANT,
        )

        self.assertEqual(self.domain_contact.registrant_contact.email, expected_contact.email)

        expected_contact_db = PublicContact.objects.filter(
            registry_id=self.domain_contact.registrant_contact.registry_id,
            contact_type=PublicContact.ContactTypeChoices.REGISTRANT,
        ).get()

        # Checks if we grab the correct PublicContact
        self.assertEqual(self.domain_contact.registrant_contact, expected_contact_db)
        self.mockedSendFunction.assert_has_calls(
            [
                call(
                    commands.InfoContact(id="regContact", auth_info=None),
                    cleaned=True,
                ),
            ]
        )
        # Checks if we are receiving the cache we expect.
        self.assertEqual(self.domain_contact._cache["registrant"], expected_contact_db)


class TestRegistrantNameservers(MockEppLib):
    """Rule: Registrants may modify their nameservers"""

    def setUp(self):
        """
        Background:
            Given the registrant is logged in
            And the registrant is the admin on a domain
        """
        super().setUp()
        self.nameserver1 = "ns1.my-nameserver-1.com"
        self.nameserver2 = "ns1.my-nameserver-2.com"
        self.nameserver3 = "ns1.cats-are-superior3.com"

        self.domain, _ = Domain.objects.get_or_create(name="my-nameserver.gov", state=Domain.State.DNS_NEEDED)
        self.domainWithThreeNS, _ = Domain.objects.get_or_create(
            name="threenameserversDomain.gov", state=Domain.State.READY
        )

    def test_get_nameserver_changes_success_deleted_vals(self):
        """Testing only deleting and no other changes"""
        self.domain._cache["hosts"] = [
            {"name": "ns1.example.com", "addrs": None},
            {"name": "ns2.example.com", "addrs": ["1.2.3.4"]},
        ]
        newChanges = [
            ("ns1.example.com",),
        ]
        (
            deleted_values,
            updated_values,
            new_values,
            oldNameservers,
        ) = self.domain.getNameserverChanges(newChanges)

        self.assertEqual(deleted_values, ["ns2.example.com"])
        self.assertEqual(updated_values, [])
        self.assertEqual(new_values, {})
        self.assertEqual(
            oldNameservers,
            {"ns1.example.com": None, "ns2.example.com": ["1.2.3.4"]},
        )

    def test_get_nameserver_changes_success_updated_vals(self):
        """Testing only updating no other changes"""
        self.domain._cache["hosts"] = [
            {"name": "ns3.my-nameserver.gov", "addrs": ["1.2.3.4"]},
        ]
        newChanges = [
            ("ns3.my-nameserver.gov", ["1.2.4.5"]),
        ]
        (
            deleted_values,
            updated_values,
            new_values,
            oldNameservers,
        ) = self.domain.getNameserverChanges(newChanges)

        self.assertEqual(deleted_values, [])
        self.assertEqual(updated_values, [("ns3.my-nameserver.gov", ["1.2.4.5"])])
        self.assertEqual(new_values, {})
        self.assertEqual(
            oldNameservers,
            {"ns3.my-nameserver.gov": ["1.2.3.4"]},
        )

    def test_get_nameserver_changes_success_new_vals(self):
        # Testing only creating no other changes
        self.domain._cache["hosts"] = [
            {"name": "ns1.example.com", "addrs": None},
        ]
        newChanges = [
            ("ns1.example.com",),
            ("ns4.example.com",),
        ]
        (
            deleted_values,
            updated_values,
            new_values,
            oldNameservers,
        ) = self.domain.getNameserverChanges(newChanges)

        self.assertEqual(deleted_values, [])
        self.assertEqual(updated_values, [])
        self.assertEqual(new_values, {"ns4.example.com": None})
        self.assertEqual(
            oldNameservers,
            {
                "ns1.example.com": None,
            },
        )

    def test_user_adds_one_nameserver(self):
        """
        Scenario: Registrant adds a single nameserver
            Given the domain has zero nameservers
            When `domain.nameservers` is set to an array of length 1
            Then `commands.CreateHost` and `commands.UpdateDomain` is sent
                to the registry
            And `domain.is_active` returns False
        """

        # set 1 nameserver
        nameserver = "ns1.my-nameserver.com"
        self.domain.nameservers = [(nameserver,)]

        # when we create a host, we should've updated at the same time
        created_host = commands.CreateHost(nameserver)
        update_domain_with_created = commands.UpdateDomain(
            name=self.domain.name,
            add=[common.HostObjSet([created_host.name])],
            rem=[],
        )

        # checking if commands were sent (commands have to be sent in order)
        expectedCalls = [
            call(created_host, cleaned=True),
            call(update_domain_with_created, cleaned=True),
        ]

        self.mockedSendFunction.assert_has_calls(expectedCalls)

        # check that status is still NOT READY
        # as you have less than 2 nameservers
        self.assertFalse(self.domain.is_active())

    def test_user_adds_two_nameservers(self):
        """
        Scenario: Registrant adds 2 or more nameservers, thereby activating the domain
            Given the domain has zero nameservers
            When `domain.nameservers` is set to an array of length 2
            Then `commands.CreateHost` and `commands.UpdateDomain` is sent
                to the registry
            And `domain.is_active` returns True
        """

        # set 2 nameservers
        self.domain.nameservers = [(self.nameserver1,), (self.nameserver2,)]

        # when you create a host, you also have to update at same time
        created_host1 = commands.CreateHost(self.nameserver1)
        created_host2 = commands.CreateHost(self.nameserver2)

        update_domain_with_created = commands.UpdateDomain(
            name=self.domain.name,
            add=[
                common.HostObjSet([created_host1.name, created_host2.name]),
            ],
            rem=[],
        )

        infoDomain = commands.InfoDomain(name="my-nameserver.gov", auth_info=None)
        # checking if commands were sent (commands have to be sent in order)
        expectedCalls = [
            call(infoDomain, cleaned=True),
            call(created_host1, cleaned=True),
            call(created_host2, cleaned=True),
            call(update_domain_with_created, cleaned=True),
        ]

        self.mockedSendFunction.assert_has_calls(expectedCalls, any_order=True)
        self.assertEqual(4, self.mockedSendFunction.call_count)
        # check that status is READY
        self.assertTrue(self.domain.is_active())

    def test_user_adds_too_many_nameservers(self):
        """
        Scenario: Registrant adds 14 or more nameservers
            Given the domain has zero nameservers
            When `domain.nameservers` is set to an array of length 14
            Then Domain raises a user-friendly error
        """

        # set 13+ nameservers
        nameserver1 = "ns1.cats-are-superior1.com"
        nameserver2 = "ns1.cats-are-superior2.com"
        nameserver3 = "ns1.cats-are-superior3.com"
        nameserver4 = "ns1.cats-are-superior4.com"
        nameserver5 = "ns1.cats-are-superior5.com"
        nameserver6 = "ns1.cats-are-superior6.com"
        nameserver7 = "ns1.cats-are-superior7.com"
        nameserver8 = "ns1.cats-are-superior8.com"
        nameserver9 = "ns1.cats-are-superior9.com"
        nameserver10 = "ns1.cats-are-superior10.com"
        nameserver11 = "ns1.cats-are-superior11.com"
        nameserver12 = "ns1.cats-are-superior12.com"
        nameserver13 = "ns1.cats-are-superior13.com"
        nameserver14 = "ns1.cats-are-superior14.com"

        def _get_14_nameservers():
            self.domain.nameservers = [
                (nameserver1,),
                (nameserver2,),
                (nameserver3,),
                (nameserver4,),
                (nameserver5,),
                (nameserver6,),
                (nameserver7,),
                (nameserver8,),
                (nameserver9),
                (nameserver10,),
                (nameserver11,),
                (nameserver12,),
                (nameserver13,),
                (nameserver14,),
            ]

        self.assertRaises(NameserverError, _get_14_nameservers)
        self.assertEqual(self.mockedSendFunction.call_count, 0)

    def test_user_removes_some_nameservers(self):
        """
        Scenario: Registrant removes some nameservers, while keeping at least 2
            Given the domain has 3 nameservers
            When `domain.nameservers` is set to an array containing nameserver #1 and #2
            Then `commands.UpdateDomain` and `commands.DeleteHost` is sent
                to the registry
            And `domain.is_active` returns True
        """

        # Mock is set to return 3 nameservers on infodomain
        self.domainWithThreeNS.nameservers = [(self.nameserver1,), (self.nameserver2,)]
        expectedCalls = [
            # calls info domain, and info on all hosts
            # to get past values
            # then removes the single host and updates domain
            call(
                commands.InfoDomain(name=self.domainWithThreeNS.name, auth_info=None),
                cleaned=True,
            ),
            call(commands.InfoHost(name="ns1.my-nameserver-1.com"), cleaned=True),
            call(commands.InfoHost(name="ns1.my-nameserver-2.com"), cleaned=True),
            call(commands.InfoHost(name="ns1.cats-are-superior3.com"), cleaned=True),
            call(
                commands.UpdateDomain(
                    name=self.domainWithThreeNS.name,
                    add=[],
                    rem=[common.HostObjSet(hosts=["ns1.cats-are-superior3.com"])],
                    nsset=None,
                    keyset=None,
                    registrant=None,
                    auth_info=None,
                ),
                cleaned=True,
            ),
            call(commands.DeleteHost(name="ns1.cats-are-superior3.com"), cleaned=True),
        ]

        self.mockedSendFunction.assert_has_calls(expectedCalls, any_order=True)
        self.assertTrue(self.domainWithThreeNS.is_active())

    def test_user_removes_too_many_nameservers(self):
        """
        Scenario: Registrant removes some nameservers, bringing the total to less than 2
            Given the domain has 2 nameservers
            When `domain.nameservers` is set to an array containing nameserver #1
            Then `commands.UpdateDomain` and `commands.DeleteHost` is sent
                to the registry
            And `domain.is_active` returns False

        """

        self.domainWithThreeNS.nameservers = [(self.nameserver1,)]
        expectedCalls = [
            call(
                commands.InfoDomain(name=self.domainWithThreeNS.name, auth_info=None),
                cleaned=True,
            ),
            call(commands.InfoHost(name="ns1.my-nameserver-1.com"), cleaned=True),
            call(commands.InfoHost(name="ns1.my-nameserver-2.com"), cleaned=True),
            call(commands.InfoHost(name="ns1.cats-are-superior3.com"), cleaned=True),
            call(commands.DeleteHost(name="ns1.my-nameserver-2.com"), cleaned=True),
            call(
                commands.UpdateDomain(
                    name=self.domainWithThreeNS.name,
                    add=[],
                    rem=[
                        common.HostObjSet(
                            hosts=[
                                "ns1.my-nameserver-2.com",
                                "ns1.cats-are-superior3.com",
                            ]
                        ),
                    ],
                    nsset=None,
                    keyset=None,
                    registrant=None,
                    auth_info=None,
                ),
                cleaned=True,
            ),
            call(commands.DeleteHost(name="ns1.cats-are-superior3.com"), cleaned=True),
        ]

        self.mockedSendFunction.assert_has_calls(expectedCalls, any_order=True)
        self.assertFalse(self.domainWithThreeNS.is_active())

    def test_user_replaces_nameservers(self):
        """
        Scenario: Registrant simultaneously adds and removes some nameservers
            Given the domain has 3 nameservers
            When `domain.nameservers` is set to an array containing nameserver #1 plus
                two new nameservers
            Then `commands.CreateHost` is sent to create #4 and #5
            And `commands.UpdateDomain` is sent to add #4 and #5 plus remove #2 and #3
            And `commands.DeleteHost` is sent to delete #2 and #3
        """
        self.domainWithThreeNS.nameservers = [
            (self.nameserver1,),
            ("ns1.cats-are-superior1.com",),
            ("ns1.cats-are-superior2.com",),
        ]

        expectedCalls = [
            call(
                commands.InfoDomain(name=self.domainWithThreeNS.name, auth_info=None),
                cleaned=True,
            ),
            call(commands.InfoHost(name="ns1.my-nameserver-1.com"), cleaned=True),
            call(commands.InfoHost(name="ns1.my-nameserver-2.com"), cleaned=True),
            call(commands.InfoHost(name="ns1.cats-are-superior3.com"), cleaned=True),
            call(commands.DeleteHost(name="ns1.my-nameserver-2.com"), cleaned=True),
            call(
                commands.CreateHost(name="ns1.cats-are-superior1.com", addrs=[]),
                cleaned=True,
            ),
            call(
                commands.CreateHost(name="ns1.cats-are-superior2.com", addrs=[]),
                cleaned=True,
            ),
            call(
                commands.UpdateDomain(
                    name=self.domainWithThreeNS.name,
                    add=[
                        common.HostObjSet(
                            hosts=[
                                "ns1.cats-are-superior1.com",
                                "ns1.cats-are-superior2.com",
                            ]
                        ),
                    ],
                    rem=[
                        common.HostObjSet(
                            hosts=[
                                "ns1.my-nameserver-2.com",
                                "ns1.cats-are-superior3.com",
                            ]
                        ),
                    ],
                    nsset=None,
                    keyset=None,
                    registrant=None,
                    auth_info=None,
                ),
                cleaned=True,
            ),
        ]

        self.mockedSendFunction.assert_has_calls(expectedCalls, any_order=True)
        self.assertTrue(self.domainWithThreeNS.is_active())

    def test_user_cannot_add_subordinate_without_ip(self):
        """
        Scenario: Registrant adds a nameserver which is a subdomain of their .gov
            Given the domain exists in the registry
            When `domain.nameservers` is set to an array containing an entry
                with a subdomain of the domain and no IP addresses
            Then Domain raises a user-friendly error
        """

        dotgovnameserver = "my-nameserver.gov"

        with self.assertRaises(NameserverError):
            self.domain.nameservers = [(dotgovnameserver,)]

    def test_user_updates_ips(self):
        """
        Scenario: Registrant changes IP addresses for a nameserver
            Given the domain exists in the registry
            And has a subordinate nameserver
            When `domain.nameservers` is set to an array containing that nameserver
                with a different IP address(es)
            Then `commands.UpdateHost` is sent to the registry
        """
        domain, _ = Domain.objects.get_or_create(name="nameserverwithip.gov", state=Domain.State.READY)
        domain.nameservers = [
            ("ns1.nameserverwithip.gov", ["2.3.4.5", "1.2.3.4"]),
            (
                "ns2.nameserverwithip.gov",
                ["1.2.3.4", "2.3.4.5", "2001:0db8:85a3:0000:0000:8a2e:0370:7334"],
            ),
            ("ns3.nameserverwithip.gov", ["2.3.4.5"]),
        ]

        expectedCalls = [
            call(
                commands.InfoDomain(name="nameserverwithip.gov", auth_info=None),
                cleaned=True,
            ),
            call(commands.InfoHost(name="ns1.nameserverwithip.gov"), cleaned=True),
            call(commands.InfoHost(name="ns2.nameserverwithip.gov"), cleaned=True),
            call(commands.InfoHost(name="ns3.nameserverwithip.gov"), cleaned=True),
            call(
                commands.UpdateHost(
                    name="ns2.nameserverwithip.gov",
                    add=[common.Ip(addr="2001:0db8:85a3:0000:0000:8a2e:0370:7334", ip="v6")],
                    rem=[],
                    chg=None,
                ),
                cleaned=True,
            ),
            call(
                commands.UpdateHost(
                    name="ns3.nameserverwithip.gov",
                    add=[],
                    rem=[common.Ip(addr="1.2.3.4", ip=None)],
                    chg=None,
                ),
                cleaned=True,
            ),
        ]

        self.mockedSendFunction.assert_has_calls(expectedCalls, any_order=True)
        self.assertTrue(domain.is_active())

    def test_user_cannot_add_non_subordinate_with_ip(self):
        """
        Scenario: Registrant adds a nameserver which is NOT a subdomain of their .gov
            Given the domain exists in the registry
            When `domain.nameservers` is set to an array containing an entry
                which is not a subdomain of the domain and has IP addresses
            Then Domain raises a user-friendly error
        """
        dotgovnameserver = "mynameserverdotgov.gov"

        with self.assertRaises(NameserverError):
            self.domain.nameservers = [(dotgovnameserver, ["1.2.3"])]

    def test_nameservers_are_idempotent(self):
        """
        Scenario: Registrant adds a set of nameservers twice, due to a UI glitch
            When `commands.CreateHost` and `commands.UpdateDomain` are sent
                to the registry twice with identical data
            Then no errors are raised in Domain
        """

        # Checking that it doesn't create or update even if out of order
        self.domainWithThreeNS.nameservers = [
            (self.nameserver3,),
            (self.nameserver1,),
            (self.nameserver2,),
        ]

        expectedCalls = [
            call(
                commands.InfoDomain(name=self.domainWithThreeNS.name, auth_info=None),
                cleaned=True,
            ),
            call(commands.InfoHost(name="ns1.my-nameserver-1.com"), cleaned=True),
            call(commands.InfoHost(name="ns1.my-nameserver-2.com"), cleaned=True),
            call(commands.InfoHost(name="ns1.cats-are-superior3.com"), cleaned=True),
        ]

        self.mockedSendFunction.assert_has_calls(expectedCalls, any_order=True)
        self.assertEqual(self.mockedSendFunction.call_count, 4)

    def test_is_subdomain_with_no_ip(self):
        domain, _ = Domain.objects.get_or_create(name="nameserversubdomain.gov", state=Domain.State.READY)

        with self.assertRaises(NameserverError):
            domain.nameservers = [
                ("ns1.nameserversubdomain.gov",),
                ("ns2.nameserversubdomain.gov",),
            ]

    def test_not_subdomain_but_has_ip(self):
        domain, _ = Domain.objects.get_or_create(name="nameserversubdomain.gov", state=Domain.State.READY)

        with self.assertRaises(NameserverError):
            domain.nameservers = [
                ("ns1.cats-da-best.gov", ["1.2.3.4"]),
                ("ns2.cats-da-best.gov", ["2.3.4.5"]),
            ]

    def test_is_subdomain_but_ip_addr_not_valid(self):
        domain, _ = Domain.objects.get_or_create(name="nameserversubdomain.gov", state=Domain.State.READY)

        with self.assertRaises(NameserverError):
            domain.nameservers = [
                ("ns1.nameserversubdomain.gov", ["1.2.3"]),
                ("ns2.nameserversubdomain.gov", ["2.3.4"]),
            ]

    def test_setting_not_allowed(self):
        """Scenario: A domain state is not Ready or DNS Needed
        then setting nameservers is not allowed"""
        domain, _ = Domain.objects.get_or_create(name="onholdDomain.gov", state=Domain.State.ON_HOLD)
        with self.assertRaises(ActionNotAllowed):
            domain.nameservers = [self.nameserver1, self.nameserver2]

    @skip("not implemented yet")
    def test_update_is_unsuccessful(self):
        """
        Scenario: An update to the nameservers is unsuccessful
            When an error is returned from epplibwrapper
            Then a user-friendly error message is returned for displaying on the web

        Note: TODO 433 -- we will perform correct error handling and complete
        this ticket. We want to raise an error for update/create/delete, but
        don't want to lose user info (and exit out too early)
        """

        domain, _ = Domain.objects.get_or_create(name="failednameserver.gov", state=Domain.State.READY)

        with self.assertRaises(RegistryError):
            domain.nameservers = [("ns1.failednameserver.gov", ["4.5.6"])]

    def tearDown(self):
        Domain.objects.all().delete()
        return super().tearDown()


class TestNameserverValidation(TestCase):
    """Test the isValidDomain method which validates nameservers"""

    def test_255_chars_is_too_long(self):
        """Test that domain of 255 chars or longer is invalid"""
        domain_too_long = (
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            ".bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
            ".bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
            ".bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
            ".bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
            ".bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.gov"
        )
        self.assertFalse(Domain.isValidHost(domain_too_long))

    def test_64_char_label_too_long(self):
        """Test that label of 64 characters or longer is invalid"""
        label_too_long = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaabbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        domain_label_too_long = "www." + label_too_long + ".gov"
        self.assertFalse(Domain.isValidHost(domain_label_too_long))

    def test_only_tld_and_sld(self):
        """Test that host with only a tld and sld is invalid"""
        tld = "gov"
        sld = "example"
        domain_with_sld_and_tld = sld + "." + tld
        self.assertFalse(Domain.isValidHost(domain_with_sld_and_tld))

    def test_improper_chars_in_nameserver(self):
        """Test that host with improper chars is invalid"""
        invalid_chars = "*&^"
        domain_with_invalid_chars = "www.bad--" + invalid_chars + ".gov"
        self.assertFalse(Domain.isValidHost(domain_with_invalid_chars))

    def test_misplaced_dashes(self):
        """Test that misplaced dashes are invalid"""
        self.assertFalse(Domain.isValidHost("-www.example.gov"))
        self.assertFalse(Domain.isValidHost("www.example-.gov"))
        self.assertTrue(Domain.isValidHost("www.ex-ample.gov"))

    def test_valid_hostname(self):
        """Test that valid hostnames are valid"""
        self.assertTrue(Domain.isValidHost("www.tld.sld.gov"))
        self.assertTrue(Domain.isValidHost("www.valid.c"))
        self.assertTrue(Domain.isValidHost("2ww.valid.gov"))
        self.assertTrue(Domain.isValidHost("w.t.g"))


class TestRegistrantDNSSEC(MockEppLib):
    """Rule: Registrants may modify their secure DNS data"""

    # helper function to create UpdateDomainDNSSECExtention object for verification
    def createUpdateExtension(self, dnssecdata: extensions.DNSSECExtension, remove=False):
        if not remove:
            return commands.UpdateDomainDNSSECExtension(
                maxSigLife=dnssecdata.maxSigLife,
                dsData=dnssecdata.dsData,
                keyData=dnssecdata.keyData,
                remDsData=None,
                remKeyData=None,
                remAllDsKeyData=False,
            )
        else:
            return commands.UpdateDomainDNSSECExtension(
                maxSigLife=dnssecdata.maxSigLife,
                dsData=None,
                keyData=None,
                remDsData=dnssecdata.dsData,
                remKeyData=dnssecdata.keyData,
                remAllDsKeyData=False,
            )

    def setUp(self):
        """
        Background:
            Given the analyst is logged in
            And a domain exists in the registry
        """
        super().setUp()
        # for the tests, need a domain in the unknown state
        self.domain, _ = Domain.objects.get_or_create(name="fake.gov")

    def tearDown(self):
        Domain.objects.all().delete()
        super().tearDown()

    def test_user_adds_dnssec_data(self):
        """
        Scenario: Registrant adds DNSSEC ds data.
        Verify that both the setter and getter are functioning properly

        This test verifies:
        1 - setter initially calls InfoDomain command
        2 - setter then calls UpdateDomain command
        3 - setter adds the UpdateDNSSECExtension extension to the command
        4 - setter causes the getter to call info domain on next get from cache
        5 - getter properly parses dnssecdata from InfoDomain response and sets to cache

        """

        # need to use a separate patcher and side_effect for this test, as
        # response from InfoDomain must be different for different iterations
        # of the same command
        def side_effect(_request, cleaned):
            if isinstance(_request, commands.InfoDomain):
                if mocked_send.call_count == 1:
                    return MagicMock(res_data=[self.mockDataInfoDomain])
                else:
                    return MagicMock(
                        res_data=[self.mockDataInfoDomain],
                        extensions=[self.dnssecExtensionWithDsData],
                    )
            else:
                return MagicMock(res_data=[self.mockDataInfoHosts])

        patcher = patch("registrar.models.domain.registry.send")
        mocked_send = patcher.start()
        mocked_send.side_effect = side_effect

        domain, _ = Domain.objects.get_or_create(name="dnssec-dsdata.gov")
        domain.dnssecdata = self.dnssecExtensionWithDsData

        # get the DNS SEC extension added to the UpdateDomain command and
        # verify that it is properly sent
        # args[0] is the _request sent to registry
        args, _ = mocked_send.call_args
        # assert that the extension on the update matches
        self.assertEquals(
            args[0].extensions[0],
            self.createUpdateExtension(self.dnssecExtensionWithDsData),
        )
        # test that the dnssecdata getter is functioning properly
        dnssecdata_get = domain.dnssecdata
        mocked_send.assert_has_calls(
            [
                call(
                    commands.InfoDomain(
                        name="dnssec-dsdata.gov",
                    ),
                    cleaned=True,
                ),
                call(
                    commands.UpdateDomain(
                        name="dnssec-dsdata.gov",
                        nsset=None,
                        keyset=None,
                        registrant=None,
                        auth_info=None,
                    ),
                    cleaned=True,
                ),
                call(
                    commands.InfoDomain(
                        name="dnssec-dsdata.gov",
                    ),
                    cleaned=True,
                ),
            ]
        )

        self.assertEquals(dnssecdata_get.dsData, self.dnssecExtensionWithDsData.dsData)

        patcher.stop()

    def test_dnssec_is_idempotent(self):
        """
        Scenario: Registrant adds DNS data twice, due to a UI glitch

        # implementation note: this requires seeing what happens when these are actually
        # sent like this, and then implementing appropriate mocks for any errors the
        # registry normally sends in this case

        This test verifies:
        1 - InfoDomain command is called first
        2 - UpdateDomain command called on the initial setter
        3 - setter causes the getter to call info domain on next get from cache
        4 - UpdateDomain command is not called on second setter (no change)
        5 - getter properly parses dnssecdata from InfoDomain response and sets to cache

        """

        # need to use a separate patcher and side_effect for this test, as
        # response from InfoDomain must be different for different iterations
        # of the same command
        def side_effect(_request, cleaned):
            if isinstance(_request, commands.InfoDomain):
                if mocked_send.call_count == 1:
                    return MagicMock(res_data=[self.mockDataInfoDomain])
                else:
                    return MagicMock(
                        res_data=[self.mockDataInfoDomain],
                        extensions=[self.dnssecExtensionWithDsData],
                    )
            else:
                return MagicMock(res_data=[self.mockDataInfoHosts])

        patcher = patch("registrar.models.domain.registry.send")
        mocked_send = patcher.start()
        mocked_send.side_effect = side_effect

        domain, _ = Domain.objects.get_or_create(name="dnssec-dsdata.gov")

        # set the dnssecdata once
        domain.dnssecdata = self.dnssecExtensionWithDsData
        # set the dnssecdata again
        domain.dnssecdata = self.dnssecExtensionWithDsData
        # test that the dnssecdata getter is functioning properly
        dnssecdata_get = domain.dnssecdata
        mocked_send.assert_has_calls(
            [
                call(
                    commands.InfoDomain(
                        name="dnssec-dsdata.gov",
                    ),
                    cleaned=True,
                ),
                call(
                    commands.UpdateDomain(
                        name="dnssec-dsdata.gov",
                        nsset=None,
                        keyset=None,
                        registrant=None,
                        auth_info=None,
                    ),
                    cleaned=True,
                ),
                call(
                    commands.InfoDomain(
                        name="dnssec-dsdata.gov",
                    ),
                    cleaned=True,
                ),
                call(
                    commands.InfoDomain(
                        name="dnssec-dsdata.gov",
                    ),
                    cleaned=True,
                ),
            ]
        )

        self.assertEquals(dnssecdata_get.dsData, self.dnssecExtensionWithDsData.dsData)

        patcher.stop()

    def test_user_adds_dnssec_data_multiple_dsdata(self):
        """
        Scenario: Registrant adds DNSSEC data with multiple DSData.
        Verify that both the setter and getter are functioning properly

        This test verifies:
        1 - setter calls UpdateDomain command
        2 - setter adds the UpdateDNSSECExtension extension to the command
        3 - setter causes the getter to call info domain on next get from cache
        4 - getter properly parses dnssecdata from InfoDomain response and sets to cache

        """

        # need to use a separate patcher and side_effect for this test, as
        # response from InfoDomain must be different for different iterations
        # of the same command
        def side_effect(_request, cleaned):
            if isinstance(_request, commands.InfoDomain):
                if mocked_send.call_count == 1:
                    return MagicMock(res_data=[self.mockDataInfoDomain])
                else:
                    return MagicMock(
                        res_data=[self.mockDataInfoDomain],
                        extensions=[self.dnssecExtensionWithMultDsData],
                    )
            else:
                return MagicMock(res_data=[self.mockDataInfoHosts])

        patcher = patch("registrar.models.domain.registry.send")
        mocked_send = patcher.start()
        mocked_send.side_effect = side_effect

        domain, _ = Domain.objects.get_or_create(name="dnssec-multdsdata.gov")

        domain.dnssecdata = self.dnssecExtensionWithMultDsData
        # get the DNS SEC extension added to the UpdateDomain command
        # and verify that it is properly sent
        # args[0] is the _request sent to registry
        args, _ = mocked_send.call_args
        # assert that the extension matches
        self.assertEquals(
            args[0].extensions[0],
            self.createUpdateExtension(self.dnssecExtensionWithMultDsData),
        )
        # test that the dnssecdata getter is functioning properly
        dnssecdata_get = domain.dnssecdata
        mocked_send.assert_has_calls(
            [
                call(
                    commands.UpdateDomain(
                        name="dnssec-multdsdata.gov",
                        nsset=None,
                        keyset=None,
                        registrant=None,
                        auth_info=None,
                    ),
                    cleaned=True,
                ),
                call(
                    commands.InfoDomain(
                        name="dnssec-multdsdata.gov",
                    ),
                    cleaned=True,
                ),
            ]
        )

        self.assertEquals(dnssecdata_get.dsData, self.dnssecExtensionWithMultDsData.dsData)

        patcher.stop()

    def test_user_removes_dnssec_data(self):
        """
        Scenario: Registrant removes DNSSEC ds data.
        Verify that both the setter and getter are functioning properly

        This test verifies:
        1 - setter initially calls InfoDomain command
        2 - first setter calls UpdateDomain command
        3 - second setter calls InfoDomain command again
        3 - setter then calls UpdateDomain command
        4 - setter adds the UpdateDNSSECExtension extension to the command with rem

        """

        # need to use a separate patcher and side_effect for this test, as
        # response from InfoDomain must be different for different iterations
        # of the same command
        def side_effect(_request, cleaned):
            if isinstance(_request, commands.InfoDomain):
                if mocked_send.call_count == 1:
                    return MagicMock(res_data=[self.mockDataInfoDomain])
                else:
                    return MagicMock(
                        res_data=[self.mockDataInfoDomain],
                        extensions=[self.dnssecExtensionWithDsData],
                    )
            else:
                return MagicMock(res_data=[self.mockDataInfoHosts])

        patcher = patch("registrar.models.domain.registry.send")
        mocked_send = patcher.start()
        mocked_send.side_effect = side_effect

        domain, _ = Domain.objects.get_or_create(name="dnssec-dsdata.gov")
        # dnssecdata_get_initial = domain.dnssecdata  # call to force initial mock
        # domain._invalidate_cache()
        domain.dnssecdata = self.dnssecExtensionWithDsData
        domain.dnssecdata = self.dnssecExtensionRemovingDsData
        # get the DNS SEC extension added to the UpdateDomain command and
        # verify that it is properly sent
        # args[0] is the _request sent to registry
        args, _ = mocked_send.call_args
        # assert that the extension on the update matches
        self.assertEquals(
            args[0].extensions[0],
            self.createUpdateExtension(
                self.dnssecExtensionWithDsData,
                remove=True,
            ),
        )
        mocked_send.assert_has_calls(
            [
                call(
                    commands.InfoDomain(
                        name="dnssec-dsdata.gov",
                    ),
                    cleaned=True,
                ),
                call(
                    commands.UpdateDomain(
                        name="dnssec-dsdata.gov",
                        nsset=None,
                        keyset=None,
                        registrant=None,
                        auth_info=None,
                    ),
                    cleaned=True,
                ),
                call(
                    commands.InfoDomain(
                        name="dnssec-dsdata.gov",
                    ),
                    cleaned=True,
                ),
                call(
                    commands.UpdateDomain(
                        name="dnssec-dsdata.gov",
                        nsset=None,
                        keyset=None,
                        registrant=None,
                        auth_info=None,
                    ),
                    cleaned=True,
                ),
            ]
        )

        patcher.stop()

    def test_update_is_unsuccessful(self):
        """
        Scenario: An update to the dns data is unsuccessful
            When an error is returned from epplibwrapper
            Then a user-friendly error message is returned for displaying on the web
        """

        domain, _ = Domain.objects.get_or_create(name="dnssec-invalid.gov")

        with self.assertRaises(RegistryError) as err:
            domain.dnssecdata = self.dnssecExtensionWithDsData
            self.assertTrue(err.is_client_error() or err.is_session_error() or err.is_server_error())


class TestExpirationDate(MockEppLib):
    """User may renew expiration date by a number of units of time"""

    def setUp(self):
        """
        Domain exists in registry
        """
        super().setUp()
        # for the tests, need a domain in the ready state
        self.domain, _ = Domain.objects.get_or_create(name="fake.gov", state=Domain.State.READY)
        # for the test, need a domain that will raise an exception
        self.domain_w_error, _ = Domain.objects.get_or_create(name="fake-error.gov", state=Domain.State.READY)

    def tearDown(self):
        Domain.objects.all().delete()
        super().tearDown()

    def test_expiration_date_setter_not_implemented(self):
        """assert that the setter for expiration date is not implemented and will raise error"""
        with self.assertRaises(NotImplementedError) as err:
            self.domain.registry_expiration_date = datetime.date.today()

    def test_renew_domain(self):
        """assert that the renew_domain sets new expiration date in cache and saves to registrar"""
        self.domain.renew_domain()
        test_date = datetime.date(2023, 5, 25)
        self.assertEquals(self.domain._cache["ex_date"], test_date)
        self.assertEquals(self.domain.expiration_date, test_date)

    def test_renew_domain_error(self):
        """assert that the renew_domain raises an exception when registry raises error"""
        with self.assertRaises(RegistryError) as err:
            self.domain_w_error.renew_domain()

        
class TestAnalystClientHold(MockEppLib):
    """Rule: Analysts may suspend or restore a domain by using client hold"""

    def setUp(self):
        """
        Background:
            Given the analyst is logged in
            And a domain exists in the registry
        """
        super().setUp()
        # for the tests, need a domain in the ready state
        self.domain, _ = Domain.objects.get_or_create(name="fake.gov", state=Domain.State.READY)
        # for the tests, need a domain in the on_hold state
        self.domain_on_hold, _ = Domain.objects.get_or_create(name="fake-on-hold.gov", state=Domain.State.ON_HOLD)

    def tearDown(self):
        Domain.objects.all().delete()
        super().tearDown()

    def test_analyst_places_client_hold(self):
        """
        Scenario: Analyst takes a domain off the internet
            When `domain.place_client_hold()` is called
            Then `CLIENT_HOLD` is added to the domain's statuses
        """
        self.domain.place_client_hold()
        self.mockedSendFunction.assert_has_calls(
            [
                call(
                    commands.UpdateDomain(
                        name="fake.gov",
                        add=[
                            common.Status(
                                state=Domain.Status.CLIENT_HOLD,
                                description="",
                                lang="en",
                            )
                        ],
                        nsset=None,
                        keyset=None,
                        registrant=None,
                        auth_info=None,
                    ),
                    cleaned=True,
                )
            ]
        )
        self.assertEquals(self.domain.state, Domain.State.ON_HOLD)

    def test_analyst_places_client_hold_idempotent(self):
        """
        Scenario: Analyst tries to place client hold twice
            Given `CLIENT_HOLD` is already in the domain's statuses
            When `domain.place_client_hold()` is called
            Then Domain returns normally (without error)
        """
        self.domain_on_hold.place_client_hold()
        self.mockedSendFunction.assert_has_calls(
            [
                call(
                    commands.UpdateDomain(
                        name="fake-on-hold.gov",
                        add=[
                            common.Status(
                                state=Domain.Status.CLIENT_HOLD,
                                description="",
                                lang="en",
                            )
                        ],
                        nsset=None,
                        keyset=None,
                        registrant=None,
                        auth_info=None,
                    ),
                    cleaned=True,
                )
            ]
        )
        self.assertEquals(self.domain_on_hold.state, Domain.State.ON_HOLD)

    def test_analyst_removes_client_hold(self):
        """
        Scenario: Analyst restores a suspended domain
            Given `CLIENT_HOLD` is in the domain's statuses
            When `domain.remove_client_hold()` is called
            Then `CLIENT_HOLD` is no longer in the domain's statuses
        """
        self.domain_on_hold.revert_client_hold()
        self.mockedSendFunction.assert_has_calls(
            [
                call(
                    commands.UpdateDomain(
                        name="fake-on-hold.gov",
                        rem=[
                            common.Status(
                                state=Domain.Status.CLIENT_HOLD,
                                description="",
                                lang="en",
                            )
                        ],
                        nsset=None,
                        keyset=None,
                        registrant=None,
                        auth_info=None,
                    ),
                    cleaned=True,
                )
            ]
        )
        self.assertEquals(self.domain_on_hold.state, Domain.State.READY)

    def test_analyst_removes_client_hold_idempotent(self):
        """
        Scenario: Analyst tries to remove client hold twice
            Given `CLIENT_HOLD` is not in the domain's statuses
            When `domain.remove_client_hold()` is called
            Then Domain returns normally (without error)
        """
        self.domain.revert_client_hold()
        self.mockedSendFunction.assert_has_calls(
            [
                call(
                    commands.UpdateDomain(
                        name="fake.gov",
                        rem=[
                            common.Status(
                                state=Domain.Status.CLIENT_HOLD,
                                description="",
                                lang="en",
                            )
                        ],
                        nsset=None,
                        keyset=None,
                        registrant=None,
                        auth_info=None,
                    ),
                    cleaned=True,
                )
            ]
        )
        self.assertEquals(self.domain.state, Domain.State.READY)

    def test_update_is_unsuccessful(self):
        """
        Scenario: An update to place or remove client hold is unsuccessful
            When an error is returned from epplibwrapper
            Then a user-friendly error message is returned for displaying on the web
        """

        def side_effect(_request, cleaned):
            raise RegistryError(code=ErrorCode.OBJECT_STATUS_PROHIBITS_OPERATION)

        patcher = patch("registrar.models.domain.registry.send")
        mocked_send = patcher.start()
        mocked_send.side_effect = side_effect

        # if RegistryError is raised, admin formats user-friendly
        # error message if error is_client_error, is_session_error, or
        # is_server_error; so test for those conditions
        with self.assertRaises(RegistryError) as err:
            self.domain.place_client_hold()
            self.assertTrue(err.is_client_error() or err.is_session_error() or err.is_server_error())

        patcher.stop()


class TestAnalystLock(TestCase):
    """Rule: Analysts may lock or unlock a domain to prevent or allow updates"""

    def setUp(self):
        """
        Background:
            Given the analyst is logged in
            And a domain exists in the registry
        """
        pass

    @skip("not implemented yet")
    def test_analyst_locks_domain(self):
        """
        Scenario: Analyst locks a domain to prevent edits or deletion
            When `domain.lock()` is called
            Then `CLIENT_DELETE_PROHIBITED` is added to the domain's statuses
            And `CLIENT_TRANSFER_PROHIBITED` is added to the domain's statuses
            And `CLIENT_UPDATE_PROHIBITED` is added to the domain's statuses
        """
        raise

    @skip("not implemented yet")
    def test_analyst_locks_domain_idempotent(self):
        """
        Scenario: Analyst tries to lock a domain twice
            Given `CLIENT_*_PROHIBITED` is already in the domain's statuses
            When `domain.lock()` is called
            Then Domain returns normally (without error)
        """
        raise

    @skip("not implemented yet")
    def test_analyst_removes_lock(self):
        """
        Scenario: Analyst unlocks a domain to allow deletion or edits
            Given `CLIENT_*_PROHIBITED` is in the domain's statuses
            When `domain.unlock()` is called
            Then `CLIENT_DELETE_PROHIBITED` is no longer in the domain's statuses
            And `CLIENT_TRANSFER_PROHIBITED` is no longer in the domain's statuses
            And `CLIENT_UPDATE_PROHIBITED` is no longer in the domain's statuses
        """
        raise

    @skip("not implemented yet")
    def test_analyst_removes_lock_idempotent(self):
        """
        Scenario: Analyst tries to unlock a domain twice
            Given `CLIENT_*_PROHIBITED` is not in the domain's statuses
            When `domain.unlock()` is called
            Then Domain returns normally (without error)
        """
        raise

    @skip("not implemented yet")
    def test_update_is_unsuccessful(self):
        """
        Scenario: An update to lock or unlock a domain is unsuccessful
            When an error is returned from epplibwrapper
            Then a user-friendly error message is returned for displaying on the web
        """
        raise


class TestAnalystDelete(MockEppLib):
    """Rule: Analysts may delete a domain"""

    def setUp(self):
        """
        Background:
            Given the analyst is logged in
            And a domain exists in the registry
        """
        super().setUp()
        self.domain, _ = Domain.objects.get_or_create(name="fake.gov", state=Domain.State.READY)
        self.domain_on_hold, _ = Domain.objects.get_or_create(name="fake-on-hold.gov", state=Domain.State.ON_HOLD)

    def tearDown(self):
        Domain.objects.all().delete()
        super().tearDown()

    def test_analyst_deletes_domain(self):
        """
        Scenario: Analyst permanently deletes a domain
            When `domain.deletedInEpp()` is called
            Then `commands.DeleteDomain` is sent to the registry
            And `state` is set to `DELETED`
        """
        # Put the domain in client hold
        self.domain.place_client_hold()
        # Delete it...
        self.domain.deletedInEpp()
        self.mockedSendFunction.assert_has_calls(
            [
                call(
                    commands.DeleteDomain(name="fake.gov"),
                    cleaned=True,
                )
            ]
        )

        # Domain itself should not be deleted
        self.assertNotEqual(self.domain, None)

        # Domain should have the right state
        self.assertEqual(self.domain.state, Domain.State.DELETED)

        # Cache should be invalidated
        self.assertEqual(self.domain._cache, {})

    def test_deletion_is_unsuccessful(self):
        """
        Scenario: Domain deletion is unsuccessful
            When a subdomain exists
            Then a client error is returned of code 2305
            And `state` is not set to `DELETED`
        """
        # Desired domain
        domain, _ = Domain.objects.get_or_create(name="failDelete.gov", state=Domain.State.ON_HOLD)
        # Put the domain in client hold
        domain.place_client_hold()

        # Delete it
        with self.assertRaises(RegistryError) as err:
            domain.deletedInEpp()
            self.assertTrue(err.is_client_error() and err.code == ErrorCode.OBJECT_ASSOCIATION_PROHIBITS_OPERATION)
        self.mockedSendFunction.assert_has_calls(
            [
                call(
                    commands.DeleteDomain(name="failDelete.gov"),
                    cleaned=True,
                )
            ]
        )

        # Domain itself should not be deleted
        self.assertNotEqual(domain, None)
        # State should not have changed
        self.assertEqual(domain.state, Domain.State.ON_HOLD)

    def test_deletion_ready_fsm_failure(self):
        """
        Scenario: Domain deletion is unsuccessful due to FSM rules
            Given state is 'ready'
            When `domain.deletedInEpp()` is called
            and domain is of `state` is `READY`
            Then an FSM error is returned
            And `state` is not set to `DELETED`
        """
        self.assertEqual(self.domain.state, Domain.State.READY)
        with self.assertRaises(TransitionNotAllowed) as err:
            self.domain.deletedInEpp()
            self.assertTrue(err.is_client_error() and err.code == ErrorCode.OBJECT_STATUS_PROHIBITS_OPERATION)
        # Domain should not be deleted
        self.assertNotEqual(self.domain, None)
        # Domain should have the right state
        self.assertEqual(self.domain.state, Domain.State.READY)
