from django.contrib import admin
from django.urls import include, path

from salt_tracker.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("", include("receipts.urls")),
]
