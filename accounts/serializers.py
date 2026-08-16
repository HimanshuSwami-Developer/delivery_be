import re

from rest_framework import serializers

from .models import DeviceToken, Profile

MOBILE_REGEX = re.compile(r"^\+?[1-9]\d{9,14}$")


def validate_mobile(value):
    if not MOBILE_REGEX.match(value):
        raise serializers.ValidationError(
            "Enter a valid mobile number in E.164-ish format, e.g. +919876543210."
        )
    return value


class SendOTPSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15)

    def validate_mobile_number(self, value):
        return validate_mobile(value)


class ResendOTPSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15)

    def validate_mobile_number(self, value):
        return validate_mobile(value)


class DeviceTokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(choices=DeviceToken.Platform.choices)


class VerifyOTPSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15)
    otp_code = serializers.CharField(max_length=6, min_length=4)

    def validate_mobile_number(self, value):
        return validate_mobile(value)


class MasterOTPLoginSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15)
    master_otp = serializers.CharField(max_length=6)

    def validate_mobile_number(self, value):
        return validate_mobile(value)


class AddressItemSerializer(serializers.Serializer):
    """One entry inside Profile.addresses (a JSON list, not its own table)."""

    id = serializers.CharField(read_only=True)
    address_type = serializers.ChoiceField(choices=["home", "work", "other"], default="home")
    address_line1 = serializers.CharField(max_length=255)
    address_line2 = serializers.CharField(
        max_length=255, required=False, allow_blank=True, allow_null=True
    )
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100)
    country = serializers.CharField(max_length=100, default="India")
    pincode = serializers.CharField(max_length=10)
    is_default = serializers.BooleanField(default=False)
    created_at = serializers.CharField(read_only=True)
    updated_at = serializers.CharField(read_only=True)


class GPSLocationItemSerializer(serializers.Serializer):
    """One entry inside Profile.gps_locations (a JSON list, not its own table)."""

    id = serializers.CharField(read_only=True)
    label = serializers.CharField(max_length=100, default="current")
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    accuracy = serializers.FloatField(required=False, allow_null=True)
    created_at = serializers.CharField(read_only=True)
    updated_at = serializers.CharField(read_only=True)


class ProfileSerializer(serializers.ModelSerializer):
    """Read serializer — includes the linked mobile number, addresses, and gps locations."""

    mobile_number = serializers.CharField(source="user.mobile_number", read_only=True)
    addresses = AddressItemSerializer(many=True, read_only=True)
    gps_locations = GPSLocationItemSerializer(many=True, read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = Profile
        fields = [
            "id", "name", "mobile_number", "role", "addresses", "gps_locations",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "mobile_number", "role", "addresses", "gps_locations",
            "created_at", "updated_at",
        ]


class ProfileWriteSerializer(serializers.ModelSerializer):
    """Write serializer for create (first-time complete profile) / update."""

    class Meta:
        model = Profile
        fields = ["name"]