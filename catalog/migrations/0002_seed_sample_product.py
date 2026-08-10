from django.db import migrations


def seed_sample_product(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Subcategory = apps.get_model("catalog", "Subcategory")
    Product = apps.get_model("catalog", "Product")

    category, _ = Category.objects.get_or_create(
        key="fruits-vegetables",
        defaults={
            "name": "Fruits & Vegetables",
            "icon": "🥦",
            "order": 1,
        },
    )
    subcategory, _ = Subcategory.objects.get_or_create(
        category=category,
        name="Fresh Vegetables",
        defaults={"order": 1},
    )
    Product.objects.get_or_create(
        sku="VEG-TOMATO-1KG",
        defaults={
            "name": "Fresh Tomato",
            "brand": "Local Farm",
            "category": category,
            "subcategory": subcategory,
            "pack": "1 kg",
            "hsn_code": "0702",
            "description": "Farm-fresh, hand-picked tomatoes.",
            "mrp": 60,
            "price": 45,
            "cost_price": 35,
            "gst_slab": "0",
            "main_image_url": "",
        },
    )


def remove_sample_product(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    Product.objects.filter(sku="VEG-TOMATO-1KG").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_sample_product, remove_sample_product),
    ]
