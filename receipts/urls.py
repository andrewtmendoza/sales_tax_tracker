from django.urls import path

from receipts import views

app_name = "receipts"

urlpatterns = [
    path("manifest.json", views.web_manifest, name="manifest"),
    path("service-worker.js", views.service_worker, name="service_worker"),
    path("", views.dashboard, name="dashboard"),
    path("capture/", views.capture, name="capture"),
    path("receipts/<int:receipt_id>/", views.receipt_detail, name="receipt_detail"),
    path("receipts/<int:receipt_id>/image/", views.receipt_image, name="receipt_image"),
    path(
        "receipts/<int:receipt_id>/image/thumbnail/",
        views.receipt_thumbnail,
        name="receipt_thumbnail",
    ),
    path("receipts/<int:receipt_id>/update/", views.receipt_update, name="receipt_update"),
    path("receipts/<int:receipt_id>/delete/", views.receipt_delete, name="receipt_delete"),
]
