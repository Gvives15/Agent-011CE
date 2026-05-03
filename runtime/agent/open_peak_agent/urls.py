from django.urls import path

from api.router import api


urlpatterns = [
    path("", api.urls),
]
