from ninja import NinjaAPI

from api.urls import router as v1_router

api = NinjaAPI(title="open-peak-agent", version="v1")
api.add_router("/v1", v1_router)
