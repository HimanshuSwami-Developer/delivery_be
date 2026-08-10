import cloudinary.uploader
from django.conf import settings


def upload_image(file, folder="products"):
    """Upload an image file to Cloudinary and return its secure_url.

    `file` is anything cloudinary's SDK accepts directly (a Django
    UploadedFile works fine). Only the returned URL gets persisted in our
    DB — Product.main_image_url / ProductImage.image_url are plain
    URLFields, no local media storage involved.

    Uses an unsigned upload preset (CLOUDINARY_UPLOAD_PRESET) rather than
    the API key/secret — sidesteps API keys that are scoped without
    upload ("create") permission, and only needs the account's cloud_name.
    """
    result = cloudinary.uploader.unsigned_upload(
        file, settings.CLOUDINARY_UPLOAD_PRESET, folder=folder
    )
    return result["secure_url"]
