from django.urls import path

from .views import (
    AddressDetailView,
    AddressListCreateView,
    AdminCustomerListView,
    GPSLocationDetailView,
    GPSLocationListCreateView,
    MasterOTPLoginView,
    ProfileView,
    RegisterDeviceView,
    ResendOTPView,
    SendOTPView,
    VerifyOTPView,
)

app_name = "accounts"

urlpatterns = [
    path("send-otp/", SendOTPView.as_view(), name="send-otp"),
    path("resend-otp/", ResendOTPView.as_view(), name="resend-otp"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("master-login/", MasterOTPLoginView.as_view(), name="master-login"),
    path("device-token/", RegisterDeviceView.as_view(), name="device-token"),

    path("profile/", ProfileView.as_view(), name="profile"),

    path("profile/addresses/", AddressListCreateView.as_view(), name="address-list-create"),
    path("profile/addresses/<str:address_id>/", AddressDetailView.as_view(), name="address-detail"),

    path("profile/gps-locations/", GPSLocationListCreateView.as_view(), name="gps-list-create"),
    path("profile/gps-locations/<str:location_id>/", GPSLocationDetailView.as_view(), name="gps-detail"),

    path("admin/customers/", AdminCustomerListView.as_view(), name="admin-customers"),
]