from django.urls import path
from .views import PaymentCreateIntentView, PaymentVerifyView

urlpatterns = [
    path('create-intent/', PaymentCreateIntentView.as_view(), name='payment-create-intent'),
    path('verify/', PaymentVerifyView.as_view(), name='payment-verify'),
]
