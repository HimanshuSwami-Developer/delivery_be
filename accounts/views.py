import uuid
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTP, Profile, User
from .serializers import (
    AddressItemSerializer,
    GPSLocationItemSerializer,
    MasterOTPLoginSerializer,
    ProfileSerializer,
    ProfileWriteSerializer,
    ResendOTPSerializer,
    SendOTPSerializer,
    VerifyOTPSerializer,
)
from core.permissions import IsAdminRole
from core.service.sms_service import SMSService


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class OTPRateThrottle(AnonRateThrottle):
    scope = "otp"


class SendOTPView(APIView):
    """POST /api/auth/send-otp/  -> generates + SMS's a fresh OTP."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [OTPRateThrottle]

    @extend_schema(
        tags=["Auth - OTP"],
        summary="Send OTP",
        request=SendOTPSerializer,
        responses={200: OpenApiResponse(description="OTP sent successfully.")},
    )
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile_number = serializer.validated_data["mobile_number"]

        otp_code = OTP.generate_otp()
        expires_at = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

        OTP.objects.create(
            mobile_number=mobile_number,
            otp_code=otp_code,
            expires_at=expires_at,
        )

        if not SMSService.send_otp_sms(mobile_number, otp_code):
            return Response(
                {"detail": "Failed to send OTP. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "detail": "OTP sent successfully.",
                "mobile_number": mobile_number,
                "expires_in_minutes": settings.OTP_EXPIRY_MINUTES,
            },
            status=status.HTTP_200_OK,
        )


class ResendOTPView(APIView):
    """POST /api/auth/resend-otp/  -> re-sends a new OTP, rate-limited by a cooldown."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [OTPRateThrottle]

    @extend_schema(
        tags=["Auth - OTP"],
        summary="Resend OTP",
        request=ResendOTPSerializer,
        responses={200: OpenApiResponse(description="OTP resent successfully.")},
    )
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile_number = serializer.validated_data["mobile_number"]

        last_otp = (
            OTP.objects.filter(mobile_number=mobile_number).order_by("-created_at").first()
        )

        if last_otp:
            elapsed = (timezone.now() - last_otp.created_at).total_seconds()
            wait_seconds = settings.RESEND_OTP_WAIT_SECONDS
            if elapsed < wait_seconds:
                return Response(
                    {
                        "detail": f"Please wait {int(wait_seconds - elapsed)} second(s) before requesting another OTP."
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        otp_code = OTP.generate_otp()
        expires_at = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        next_resend_count = (last_otp.resend_count + 1) if last_otp else 0

        OTP.objects.create(
            mobile_number=mobile_number,
            otp_code=otp_code,
            expires_at=expires_at,
            resend_count=next_resend_count,
        )

        if not SMSService.send_otp_sms(mobile_number, otp_code):
            return Response(
                {"detail": "Failed to resend OTP. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "detail": "OTP resent successfully.",
                "mobile_number": mobile_number,
                "expires_in_minutes": settings.OTP_EXPIRY_MINUTES,
            },
            status=status.HTTP_200_OK,
        )


class VerifyOTPView(APIView):
    """POST /api/auth/verify-otp/  -> checks OTP, logs in (creates user if new), returns JWT."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [OTPRateThrottle]

    @extend_schema(
        tags=["Auth - OTP"],
        summary="Verify OTP (real login)",
        request=VerifyOTPSerializer,
        responses={200: OpenApiResponse(description="Login successful. Returns JWT tokens.")},
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile_number = serializer.validated_data["mobile_number"]
        otp_code = serializer.validated_data["otp_code"]

        otp_obj = (
            OTP.objects.filter(mobile_number=mobile_number, is_verified=False)
            .order_by("-created_at")
            .first()
        )

        if not otp_obj:
            return Response(
                {"detail": "No pending OTP found. Please request a new OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_obj.is_expired():
            return Response(
                {"detail": "OTP has expired. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_obj.attempt_count >= settings.MAX_OTP_ATTEMPTS:
            return Response(
                {"detail": "Maximum verification attempts exceeded. Please request a new OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_obj.otp_code != otp_code:
            otp_obj.attempt_count += 1
            otp_obj.save(update_fields=["attempt_count"])
            remaining = settings.MAX_OTP_ATTEMPTS - otp_obj.attempt_count
            return Response(
                {"detail": f"Invalid OTP. {remaining} attempt(s) remaining."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp_obj.is_verified = True
        otp_obj.save(update_fields=["is_verified"])

        user, created = User.objects.get_or_create(mobile_number=mobile_number)
        tokens = get_tokens_for_user(user)

        return Response(
            {
                "detail": "Login successful.",
                "is_new_user": created,
                "mobile_number": mobile_number,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class MasterOTPLoginView(APIView):
    """
    POST /api/auth/master-login/

    Logs a user in using a fixed "master OTP" configured in settings
    (settings.MASTER_OTP). No SMS is ever sent for this flow, and no OTP
    row is created. Intended for QA teams, app-store reviewers, or
    automated/staging test accounts — NOT for production end users.

    Optionally restrict which numbers may use this via
    settings.MASTER_OTP_MOBILE_NUMBERS (empty list = allowed for any number).
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [OTPRateThrottle]

    @extend_schema(
        tags=["Auth - OTP"],
        summary="Master OTP login (no SMS sent)",
        request=MasterOTPLoginSerializer,
        responses={200: OpenApiResponse(description="Login successful (master OTP). Returns JWT tokens.")},
    )
    def post(self, request):
        serializer = MasterOTPLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile_number = serializer.validated_data["mobile_number"]
        master_otp = serializer.validated_data["master_otp"]

        if master_otp != settings.MASTER_OTP:
            return Response(
                {"detail": "Invalid master OTP."}, status=status.HTTP_400_BAD_REQUEST
            )

        allowed_numbers = settings.MASTER_OTP_MOBILE_NUMBERS
        if allowed_numbers and mobile_number not in allowed_numbers:
            return Response(
                {"detail": "Master OTP login is not permitted for this number."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user, created = User.objects.get_or_create(mobile_number=mobile_number)
        tokens = get_tokens_for_user(user)

        return Response(
            {
                "detail": "Login successful (master OTP).",
                "is_new_user": created,
                "mobile_number": mobile_number,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class ProfileView(APIView):
    """
    GET    /api/profile/  -> fetch the logged-in user's profile (+ addresses + gps locations)
    POST   /api/profile/  -> complete the profile for the first time
    PUT    /api/profile/  -> full update (of `name`)
    PATCH  /api/profile/  -> partial update

    The profile is always resolved from request.user (the JWT), so there's
    no way to read/write someone else's profile through this endpoint.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Profile"], summary="Get my profile", responses=ProfileSerializer)
    def get(self, request):
        profile = getattr(request.user, "profile", None)
        if not profile:
            return Response(
                {"detail": "Profile not completed yet. Submit a POST to create it."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ProfileSerializer(profile).data)

    @extend_schema(
        tags=["Profile"],
        summary="Complete my profile (first time)",
        request=ProfileWriteSerializer,
        responses={201: ProfileSerializer},
    )
    def post(self, request):
        if Profile.objects.filter(user=request.user).exists():
            return Response(
                {"detail": "Profile already exists. Use PUT/PATCH to update it."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ProfileWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save(user=request.user)

        return Response(ProfileSerializer(profile).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Profile"],
        summary="Update my profile (full)",
        request=ProfileWriteSerializer,
        responses=ProfileSerializer,
    )
    def put(self, request):
        return self._update(request, partial=False)

    @extend_schema(
        tags=["Profile"],
        summary="Update my profile (partial)",
        request=ProfileWriteSerializer,
        responses=ProfileSerializer,
    )
    def patch(self, request):
        return self._update(request, partial=True)

    def _update(self, request, partial):
        profile = getattr(request.user, "profile", None)
        if not profile:
            return Response(
                {"detail": "Profile not found. Create it first with POST."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProfileWriteSerializer(profile, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(ProfileSerializer(profile).data)


def _get_profile_or_400(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return None, Response(
            {"detail": "Complete your profile (POST /api/profile/) first."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return profile, None


class AddressListCreateView(APIView):
    """
      GET  /api/profile/addresses/   -> list this user's addresses
      POST /api/profile/addresses/   -> add a new address
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Addresses"], summary="List my addresses", responses=AddressItemSerializer(many=True))
    def get(self, request):
        profile, error = _get_profile_or_400(request)
        if error:
            return error
        addresses = [a for a in (profile.addresses or []) if not a.get("is_delete")]
        return Response(addresses)

    @extend_schema(
        tags=["Addresses"],
        summary="Add a new address",
        request=AddressItemSerializer,
        responses={201: AddressItemSerializer},
    )
    def post(self, request):
        profile, error = _get_profile_or_400(request)
        if error:
            return error

        serializer = AddressItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        now = timezone.now().isoformat()
        new_address = dict(serializer.validated_data)
        new_address["id"] = uuid.uuid4().hex
        new_address["is_delete"] = False
        new_address["created_at"] = now
        new_address["updated_at"] = now

        addresses = profile.addresses or []
        if new_address.get("is_default"):
            for a in addresses:
                a["is_default"] = False

        addresses.append(new_address)
        profile.addresses = addresses
        profile.save(update_fields=["addresses", "updated_at"])

        return Response(new_address, status=status.HTTP_201_CREATED)


class AddressDetailView(APIView):
    """
      GET    /api/profile/addresses/{address_id}/  -> retrieve one address
      PUT    /api/profile/addresses/{address_id}/  -> full update
      PATCH  /api/profile/addresses/{address_id}/  -> partial update
      DELETE /api/profile/addresses/{address_id}/  -> soft delete
    """

    permission_classes = [IsAuthenticated]

    def _find(self, profile, address_id):
        addresses = profile.addresses or []
        for a in addresses:
            if a.get("id") == address_id and not a.get("is_delete"):
                return a, addresses
        return None, addresses

    @extend_schema(tags=["Addresses"], summary="Get a single address", responses=AddressItemSerializer)
    def get(self, request, address_id):
        profile, error = _get_profile_or_400(request)
        if error:
            return error
        address, _ = self._find(profile, address_id)
        if not address:
            return Response({"detail": "Address not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(address)

    @extend_schema(
        tags=["Addresses"], summary="Update an address (full)",
        request=AddressItemSerializer, responses=AddressItemSerializer,
    )
    def put(self, request, address_id):
        return self._update(request, address_id, partial=False)

    @extend_schema(
        tags=["Addresses"], summary="Update an address (partial)",
        request=AddressItemSerializer, responses=AddressItemSerializer,
    )
    def patch(self, request, address_id):
        return self._update(request, address_id, partial=True)

    def _update(self, request, address_id, partial):
        profile, error = _get_profile_or_400(request)
        if error:
            return error

        address, addresses = self._find(profile, address_id)
        if not address:
            return Response({"detail": "Address not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AddressItemSerializer(instance=address, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        updated = {**address, **serializer.validated_data}
        updated["updated_at"] = timezone.now().isoformat()

        if updated.get("is_default"):
            for a in addresses:
                if a.get("id") != address_id:
                    a["is_default"] = False

        for i, a in enumerate(addresses):
            if a.get("id") == address_id:
                addresses[i] = updated
                break

        profile.addresses = addresses
        profile.save(update_fields=["addresses", "updated_at"])

        return Response(updated)

    @extend_schema(tags=["Addresses"], summary="Delete an address (soft delete)", responses={204: None})
    def delete(self, request, address_id):
        profile, error = _get_profile_or_400(request)
        if error:
            return error

        address, addresses = self._find(profile, address_id)
        if not address:
            return Response({"detail": "Address not found."}, status=status.HTTP_404_NOT_FOUND)

        for a in addresses:
            if a.get("id") == address_id:
                a["is_delete"] = True
                a["updated_at"] = timezone.now().isoformat()
                break

        profile.addresses = addresses
        profile.save(update_fields=["addresses", "updated_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)


class GPSLocationListCreateView(APIView):
    """
      GET  /api/profile/gps-locations/   -> list this user's saved GPS locations
      POST /api/profile/gps-locations/   -> add a new GPS location
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["GPS Locations"], summary="List my saved GPS locations", responses=GPSLocationItemSerializer(many=True))
    def get(self, request):
        profile, error = _get_profile_or_400(request)
        if error:
            return error
        locations = [g for g in (profile.gps_locations or []) if not g.get("is_delete")]
        return Response(locations)

    @extend_schema(
        tags=["GPS Locations"],
        summary="Add a new GPS location",
        request=GPSLocationItemSerializer,
        responses={201: GPSLocationItemSerializer},
    )
    def post(self, request):
        profile, error = _get_profile_or_400(request)
        if error:
            return error

        serializer = GPSLocationItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        now = timezone.now().isoformat()
        new_location = dict(serializer.validated_data)
        new_location["id"] = uuid.uuid4().hex
        new_location["is_delete"] = False
        new_location["created_at"] = now
        new_location["updated_at"] = now

        locations = profile.gps_locations or []
        locations.append(new_location)
        profile.gps_locations = locations
        profile.save(update_fields=["gps_locations", "updated_at"])

        return Response(new_location, status=status.HTTP_201_CREATED)


class GPSLocationDetailView(APIView):
    """
      GET    /api/profile/gps-locations/{location_id}/  -> retrieve one location
      PUT    /api/profile/gps-locations/{location_id}/  -> full update
      PATCH  /api/profile/gps-locations/{location_id}/  -> partial update
      DELETE /api/profile/gps-locations/{location_id}/  -> soft delete
    """

    permission_classes = [IsAuthenticated]

    def _find(self, profile, location_id):
        locations = profile.gps_locations or []
        for g in locations:
            if g.get("id") == location_id and not g.get("is_delete"):
                return g, locations
        return None, locations

    @extend_schema(tags=["GPS Locations"], summary="Get a single GPS location", responses=GPSLocationItemSerializer)
    def get(self, request, location_id):
        profile, error = _get_profile_or_400(request)
        if error:
            return error
        location, _ = self._find(profile, location_id)
        if not location:
            return Response({"detail": "GPS location not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(location)

    @extend_schema(
        tags=["GPS Locations"], summary="Update a GPS location (full)",
        request=GPSLocationItemSerializer, responses=GPSLocationItemSerializer,
    )
    def put(self, request, location_id):
        return self._update(request, location_id, partial=False)

    @extend_schema(
        tags=["GPS Locations"], summary="Update a GPS location (partial)",
        request=GPSLocationItemSerializer, responses=GPSLocationItemSerializer,
    )
    def patch(self, request, location_id):
        return self._update(request, location_id, partial=True)

    def _update(self, request, location_id, partial):
        profile, error = _get_profile_or_400(request)
        if error:
            return error

        location, locations = self._find(profile, location_id)
        if not location:
            return Response({"detail": "GPS location not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = GPSLocationItemSerializer(instance=location, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        updated = {**location, **serializer.validated_data}
        updated["updated_at"] = timezone.now().isoformat()

        for i, g in enumerate(locations):
            if g.get("id") == location_id:
                locations[i] = updated
                break

        profile.gps_locations = locations
        profile.save(update_fields=["gps_locations", "updated_at"])

        return Response(updated)

    @extend_schema(tags=["GPS Locations"], summary="Delete a GPS location (soft delete)", responses={204: None})
    def delete(self, request, location_id):
        profile, error = _get_profile_or_400(request)
        if error:
            return error

        location, locations = self._find(profile, location_id)
        if not location:
            return Response({"detail": "GPS location not found."}, status=status.HTTP_404_NOT_FOUND)

        for g in locations:
            if g.get("id") == location_id:
                g["is_delete"] = True
                g["updated_at"] = timezone.now().isoformat()
                break

        profile.gps_locations = locations
        profile.save(update_fields=["gps_locations", "updated_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)


def _tier_for(orders_count):
    if orders_count >= 50:
        return "Platinum"
    if orders_count >= 25:
        return "Gold"
    if orders_count >= 10:
        return "Silver"
    return "New"


class AdminCustomerListView(APIView):
    """
    GET /api/auth/admin/customers/  -> the admin console's Customers screen:
    every customer with their (non-cancelled) order count, lifetime value,
    last order date, the zone their most recent order was placed from, and
    a tier derived from order count. All computed live from `orders.Order`
    — nothing here is a stored/denormalized counter.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(tags=["Customers"], summary="[Admin] List customers with order stats")
    def get(self, request):
        # Deferred import: orders.models doesn't import accounts, so this
        # isn't strictly circular, but keeping cross-app aggregation reads
        # local to the view (not accounts' own models.py) matches the
        # pattern used elsewhere in this project (see zones/delivery).
        from orders.models import Order

        customers = User.objects.filter(role=User.Role.CUSTOMER).annotate(
            orders_count=Count("orders", filter=~Q(orders__status=Order.Status.CANCELLED)),
            ltv=Sum("orders__total", filter=~Q(orders__status=Order.Status.CANCELLED)),
        )

        data = []
        for c in customers:
            last_order = (
                Order.objects.filter(customer=c)
                .exclude(status=Order.Status.CANCELLED)
                .select_related("zone")
                .order_by("-created_at")
                .first()
            )
            data.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "mobile_number": c.mobile_number,
                    "orders_count": c.orders_count,
                    "ltv": c.ltv or 0,
                    "last_order_at": last_order.created_at if last_order else None,
                    "zone": last_order.zone.name if last_order else None,
                    "tier": _tier_for(c.orders_count),
                }
            )
        return Response(data)