from django.contrib.auth.decorators import login_required
from ninja import NinjaAPI
from ninja.security import SessionAuth

from receipts.api import router as receipts_router

api = NinjaAPI(
    title="Sales Tax Tracker API",
    version="0.1.0",
    auth=SessionAuth(),
    docs_decorator=login_required,
)
api.add_router("/receipts", receipts_router)
