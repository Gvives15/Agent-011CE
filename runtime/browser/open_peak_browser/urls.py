from django.urls import path

from browser_api.router import api


urlpatterns = [
    path("", api.urls),
]
