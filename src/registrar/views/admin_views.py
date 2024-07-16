"""Admin-related views."""

from django.http import HttpResponse
from django.views import View
from django.shortcuts import render
from django.contrib import admin
from django.db.models import Avg, F
from .. import models
import datetime
from django.utils import timezone

from registrar.utility import csv_export

import logging

logger = logging.getLogger(__name__)


class AnalyticsView(View):
    def get(self, request):
        thirty_days_ago = datetime.datetime.today() - datetime.timedelta(days=30)
        thirty_days_ago = timezone.make_aware(thirty_days_ago)

        last_30_days_applications = models.DomainRequest.objects.filter(created_at__gt=thirty_days_ago)
        last_30_days_approved_applications = models.DomainRequest.objects.filter(
            created_at__gt=thirty_days_ago, status=models.DomainRequest.DomainRequestStatus.APPROVED
        )
        avg_approval_time = last_30_days_approved_applications.annotate(
            approval_time=F("approved_domain__created_at") - F("submission_date")
        ).aggregate(Avg("approval_time"))["approval_time__avg"]
        # Format the timedelta to display only days
        if avg_approval_time is not None:
            avg_approval_time_display = f"{avg_approval_time.days} days"
        else:
            avg_approval_time_display = "No approvals to use"

        # The start and end dates are passed as url params
        start_date = request.GET.get("start_date", "")
        end_date = request.GET.get("end_date", "")

        start_date_formatted = csv_export.format_start_date(start_date)
        end_date_formatted = csv_export.format_end_date(end_date)

        filter_managed_domains_start_date = {
            "domain__permissions__isnull": False,
            "domain__first_ready__lte": start_date_formatted,
        }
        filter_managed_domains_end_date = {
            "domain__permissions__isnull": False,
            "domain__first_ready__lte": end_date_formatted,
        }
        managed_domains_sliced_at_start_date = csv_export.DomainExport.get_sliced_domains(
            filter_managed_domains_start_date
        )
        managed_domains_sliced_at_end_date = csv_export.DomainExport.get_sliced_domains(filter_managed_domains_end_date)

        filter_unmanaged_domains_start_date = {
            "domain__permissions__isnull": True,
            "domain__first_ready__lte": start_date_formatted,
        }
        filter_unmanaged_domains_end_date = {
            "domain__permissions__isnull": True,
            "domain__first_ready__lte": end_date_formatted,
        }
        unmanaged_domains_sliced_at_start_date = csv_export.DomainExport.get_sliced_domains(
            filter_unmanaged_domains_start_date
        )
        unmanaged_domains_sliced_at_end_date = csv_export.DomainExport.get_sliced_domains(
            filter_unmanaged_domains_end_date
        )

        filter_ready_domains_start_date = {
            "domain__state__in": [models.Domain.State.READY],
            "domain__first_ready__lte": start_date_formatted,
        }
        filter_ready_domains_end_date = {
            "domain__state__in": [models.Domain.State.READY],
            "domain__first_ready__lte": end_date_formatted,
        }
        ready_domains_sliced_at_start_date = csv_export.DomainExport.get_sliced_domains(filter_ready_domains_start_date)
        ready_domains_sliced_at_end_date = csv_export.DomainExport.get_sliced_domains(filter_ready_domains_end_date)

        filter_deleted_domains_start_date = {
            "domain__state__in": [models.Domain.State.DELETED],
            "domain__deleted__lte": start_date_formatted,
        }
        filter_deleted_domains_end_date = {
            "domain__state__in": [models.Domain.State.DELETED],
            "domain__deleted__lte": end_date_formatted,
        }
        deleted_domains_sliced_at_start_date = csv_export.DomainExport.get_sliced_domains(
            filter_deleted_domains_start_date
        )
        deleted_domains_sliced_at_end_date = csv_export.DomainExport.get_sliced_domains(filter_deleted_domains_end_date)

        filter_requests_start_date = {
            "created_at__lte": start_date_formatted,
        }
        filter_requests_end_date = {
            "created_at__lte": end_date_formatted,
        }
        requests_sliced_at_start_date = csv_export.DomainRequestExport.get_sliced_requests(filter_requests_start_date)
        requests_sliced_at_end_date = csv_export.DomainRequestExport.get_sliced_requests(filter_requests_end_date)

        filter_submitted_requests_start_date = {
            "status": models.DomainRequest.DomainRequestStatus.SUBMITTED,
            "submission_date__lte": start_date_formatted,
        }
        filter_submitted_requests_end_date = {
            "status": models.DomainRequest.DomainRequestStatus.SUBMITTED,
            "submission_date__lte": end_date_formatted,
        }
        submitted_requests_sliced_at_start_date = csv_export.DomainRequestExport.get_sliced_requests(
            filter_submitted_requests_start_date
        )
        submitted_requests_sliced_at_end_date = csv_export.DomainRequestExport.get_sliced_requests(
            filter_submitted_requests_end_date
        )

        context = dict(
            # Generate a dictionary of context variables that are common across all admin templates
            # (site_header, site_url, ...),
            # include it in the larger context dictionary so it's available in the template rendering context.
            # This ensures that the admin interface styling and behavior are consistent with other admin pages.
            **admin.site.each_context(request),
            data=dict(
                user_count=models.User.objects.all().count(),
                domain_count=models.Domain.objects.all().count(),
                ready_domain_count=models.Domain.objects.filter(state=models.Domain.State.READY).count(),
                last_30_days_applications=last_30_days_applications.count(),
                last_30_days_approved_applications=last_30_days_approved_applications.count(),
                average_application_approval_time_last_30_days=avg_approval_time_display,
                managed_domains_sliced_at_start_date=managed_domains_sliced_at_start_date,
                unmanaged_domains_sliced_at_start_date=unmanaged_domains_sliced_at_start_date,
                managed_domains_sliced_at_end_date=managed_domains_sliced_at_end_date,
                unmanaged_domains_sliced_at_end_date=unmanaged_domains_sliced_at_end_date,
                ready_domains_sliced_at_start_date=ready_domains_sliced_at_start_date,
                deleted_domains_sliced_at_start_date=deleted_domains_sliced_at_start_date,
                ready_domains_sliced_at_end_date=ready_domains_sliced_at_end_date,
                deleted_domains_sliced_at_end_date=deleted_domains_sliced_at_end_date,
                requests_sliced_at_start_date=requests_sliced_at_start_date,
                submitted_requests_sliced_at_start_date=submitted_requests_sliced_at_start_date,
                requests_sliced_at_end_date=requests_sliced_at_end_date,
                submitted_requests_sliced_at_end_date=submitted_requests_sliced_at_end_date,
                start_date=start_date,
                end_date=end_date,
            ),
        )
        return render(request, "admin/analytics.html", context)


class ExportDataType(View):
    def get(self, request, *args, **kwargs):
        # match the CSV example with all the fields
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="domains-by-type.csv"'
        csv_export.DomainDataType.export_data_to_csv(response)
        return response

class ExportDataTypeUser(View):
    """Returns a domain report for a given user on the request"""
    def get(self, request, *args, **kwargs):
        # match the CSV example with all the fields
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="your-domains.csv"'
        csv_export.DomainDataTypeUser.export_data_to_csv(response, request)
        return response

class ExportDataFull(View):
    def get(self, request, *args, **kwargs):
        # Smaller export based on 1
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="current-full.csv"'
        csv_export.DomainDataFull.export_data_to_csv(response)
        return response


class ExportDataFederal(View):
    def get(self, request, *args, **kwargs):
        # Federal only
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="current-federal.csv"'
        csv_export.DomainDataFederal.export_data_to_csv(response)
        return response


class ExportDomainRequestDataFull(View):
    """Generates a downloaded report containing all Domain Requests (except started)"""

    def get(self, request, *args, **kwargs):
        """Returns a content disposition response for current-full-domain-request.csv"""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="current-full-domain-request.csv"'
        csv_export.DomainRequestDataFull.export_data_to_csv(response)
        return response


class ExportDataDomainsGrowth(View):
    def get(self, request, *args, **kwargs):
        start_date = request.GET.get("start_date", "")
        end_date = request.GET.get("end_date", "")

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="domain-growth-report-{start_date}-to-{end_date}.csv"'
        csv_export.DomainGrowth.export_data_to_csv(response, start_date=start_date, end_date=end_date)

        return response


class ExportDataRequestsGrowth(View):
    def get(self, request, *args, **kwargs):
        start_date = request.GET.get("start_date", "")
        end_date = request.GET.get("end_date", "")

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="requests-{start_date}-to-{end_date}.csv"'
        csv_export.DomainRequestGrowth.export_data_to_csv(response, start_date=start_date, end_date=end_date)

        return response


class ExportDataManagedDomains(View):
    def get(self, request, *args, **kwargs):
        start_date = request.GET.get("start_date", "")
        end_date = request.GET.get("end_date", "")
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="managed-domains-{start_date}-to-{end_date}.csv"'
        csv_export.DomainManaged.export_data_to_csv(response, start_date=start_date, end_date=end_date)

        return response


class ExportDataUnmanagedDomains(View):
    def get(self, request, *args, **kwargs):
        start_date = request.GET.get("start_date", "")
        end_date = request.GET.get("end_date", "")
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="unmanaged-domains-{start_date}-to-{end_date}.csv"'
        csv_export.DomainUnmanaged.export_data_to_csv(response, start_date=start_date, end_date=end_date)

        return response
