from django.contrib import admin
from django.urls import include, path

from sales_tax_tracker import views
from sales_tax_tracker.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("health/", views.health, name="health"),
    path("api/", api.urls),
    path("", include("receipts.urls")),
]
