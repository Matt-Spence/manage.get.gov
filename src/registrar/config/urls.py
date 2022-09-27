"""URL Configuration

For more information see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
"""

from django.contrib import admin
from django.urls import include, path

from registrar.views import health, index, profile, whoami

urlpatterns = [
    path("", index.index, name="home"),
    path("whoami", whoami.whoami, name="whoami"),
    path("admin/", admin.site.urls),
    path("health/", health.health),
    path("edit_profile/", profile.edit_profile, name="edit-profile"),
    path("openid/", include("djangooidc.urls")),
    # these views respect the DEBUG setting
    path("__debug__/", include("debug_toolbar.urls")),
]
