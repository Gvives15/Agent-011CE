from ninja import NinjaAPI

from browser_api.urls import router as v1_router

api = NinjaAPI(title="open-peak-browser", version="v1")
api.add_router("/v1", v1_router)
