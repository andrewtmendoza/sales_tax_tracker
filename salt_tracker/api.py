from ninja import NinjaAPI

from receipts.api import router as receipts_router

api = NinjaAPI(title="Sales Tax Tracker API", version="0.1.0")
api.add_router("/receipts", receipts_router)
