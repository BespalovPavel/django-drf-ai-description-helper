from django.urls import path

from apps.ai_helper.views import GenerateProductCardAPIView

app_name = "ai_helper"

urlpatterns = [
    path("generate-card/", GenerateProductCardAPIView.as_view(), name="generate-card"),
]
