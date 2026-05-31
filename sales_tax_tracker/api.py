from django.conf import settings
from django.contrib.auth.decorators import login_required
from ninja import NinjaAPI
from ninja.security import SessionAuth

from receipts.api import router as receipts_router

api = NinjaAPI(
    title="Sales Tax Tracker API",
    version=settings.APP_VERSION,
    auth=SessionAuth(),
    docs_decorator=login_required,
)
api.add_router("/receipts", receipts_router)
