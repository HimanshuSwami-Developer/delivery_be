from django.db import migrations

# (category_key, category_name, icon, [(subcategory_name, [(sku, name, brand, pack, mrp, price, gst_slab, hsn), ...])])
CATALOG = [
    (
        "fruits-vegetables", "Fruits & Vegetables", "🥦",
        [
            ("Fresh Vegetables", [
                ("FV-ONION-1KG", "Fresh Onion", "Local Farm", "1 kg", 40, 35, "0", "0703"),
                ("FV-POTATO-1KG", "Fresh Potato", "Local Farm", "1 kg", 35, 28, "0", "0701"),
                ("FV-SPINACH-250G", "Fresh Spinach", "Local Farm", "250 g", 28, 22, "0", "0709"),
                ("FV-CAPSICUM-500G", "Green Capsicum", "Local Farm", "500 g", 45, 38, "0", "0709"),
            ]),
            ("Fresh Fruits", [
                ("FV-BANANA-1DZ", "Banana Robusta", "Local Farm", "1 dozen", 60, 49, "0", "0803"),
                ("FV-APPLE-1KG", "Apple Shimla", "Local Farm", "1 kg", 180, 149, "0", "0808"),
                ("FV-ORANGE-1KG", "Orange", "Local Farm", "1 kg", 110, 89, "0", "0805"),
            ]),
        ],
    ),
    (
        "dairy-breakfast", "Dairy & Breakfast", "🥛",
        [
            ("Milk & Dairy", [
                ("DB-MILK-500ML", "Toned Milk", "Amul", "500 ml", 28, 28, "0", "0401"),
                ("DB-BUTTER-100G", "Butter", "Amul", "100 g", 58, 56, "12", "0405"),
                ("DB-EGGS-6PC", "Brown Eggs", "Farm Fresh", "6 pcs", 78, 72, "0", "0407"),
                ("DB-PANEER-200G", "Paneer", "Amul", "200 g", 90, 84, "5", "0406"),
            ]),
            ("Breakfast", [
                ("DB-COFFEE-50G", "Classic Instant Coffee", "Nescafe", "50 g", 180, 165, "18", "2101"),
                ("DB-CORNFLAKES-475G", "Corn Flakes", "Kellogg's", "475 g", 230, 210, "18", "1904"),
                ("DB-BREAD-400G", "White Bread", "Britannia", "400 g", 48, 45, "5", "1905"),
            ]),
        ],
    ),
    (
        "snacks-munchies", "Snacks & Munchies", "🍿",
        [
            ("Chips & Namkeen", [
                ("SN-LAYS-52G", "Classic Salted Chips", "Lay's", "52 g", 20, 20, "12", "2005"),
                ("SN-BHUJIA-200G", "Aloo Bhujia", "Haldiram's", "200 g", 60, 55, "12", "2106"),
                ("SN-KURKURE-90G", "Masala Munch", "Kurkure", "90 g", 20, 20, "12", "2005"),
                ("SN-SEV-200G", "Bhujia Sev", "Bikaji", "200 g", 55, 50, "12", "2106"),
            ]),
            ("Biscuits & Cookies", [
                ("SN-OREO-120G", "Chocolate Cream Biscuits", "Oreo", "120 g", 45, 40, "18", "1905"),
                ("SN-MARIE-250G", "Marie Gold Biscuits", "Britannia", "250 g", 40, 36, "18", "1905"),
            ]),
        ],
    ),
    (
        "beverages", "Beverages", "🥤",
        [
            ("Soft Drinks & Juices", [
                ("BV-COKE-750ML", "Coca-Cola", "Coca-Cola", "750 ml", 40, 40, "18", "2202"),
                ("BV-JUICE-1L", "Mixed Fruit Juice", "Real", "1 L", 120, 110, "12", "2009"),
                ("BV-TROPICANA-1L", "Orange Juice", "Tropicana", "1 L", 130, 120, "12", "2009"),
                ("BV-WATER-1L", "Mineral Water", "Bisleri", "1 L", 20, 20, "18", "2201"),
            ]),
            ("Tea & Energy", [
                ("BV-REDBULL-250ML", "Energy Drink", "Red Bull", "250 ml", 125, 115, "18", "2202"),
                ("BV-TEA-250G", "Premium Tea", "Tata Tea", "250 g", 140, 128, "5", "0902"),
            ]),
        ],
    ),
    (
        "bakery", "Bakery", "🍞",
        [
            ("Cakes & Pastries", [
                ("BK-CAKESLICE-4PC", "Cake Slice", "Britannia", "4 pcs", 40, 35, "5", "1905"),
                ("BK-MUFFIN-4PC", "Chocolate Muffin", "Local Bakery", "4 pcs", 99, 90, "5", "1905"),
                ("BK-CROISSANT-2PC", "Butter Croissant", "Local Bakery", "2 pcs", 65, 60, "5", "1905"),
            ]),
            ("Bread", [
                ("BK-WHEATBREAD-400G", "Whole Wheat Bread", "Local Bakery", "400 g", 45, 42, "5", "1905"),
            ]),
        ],
    ),
    (
        "personal-care", "Personal Care", "🧴",
        [
            ("Bath & Body", [
                ("PC-DOVESOAP-100G", "Moisturising Soap", "Dove", "100 g", 60, 55, "18", "3401"),
                ("PC-SHAMPOO-180ML", "Shampoo", "Head & Shoulders", "180 ml", 180, 165, "18", "3305"),
                ("PC-LOTION-200ML", "Body Lotion", "Nivea", "200 ml", 210, 190, "18", "3304"),
            ]),
            ("Oral & Shaving", [
                ("PC-TOOTHPASTE-200G", "Strong Teeth Toothpaste", "Colgate", "200 g", 105, 95, "18", "3306"),
                ("PC-RAZOR-1PC", "Disposable Razor", "Gillette Guard", "1 pc", 50, 45, "18", "8212"),
            ]),
        ],
    ),
    (
        "household", "Household Essentials", "🧹",
        [
            ("Cleaning", [
                ("HH-DETERGENT-1KG", "Detergent Powder", "Surf Excel", "1 kg", 155, 140, "18", "3402"),
                ("HH-DISHGEL-500ML", "Dishwash Gel", "Vim", "500 ml", 105, 95, "18", "3402"),
                ("HH-TOILETCLN-500ML", "Toilet Cleaner", "Harpic", "500 ml", 95, 85, "18", "3402"),
                ("HH-SCRUBPAD-2PC", "Scrub Pad", "Scotch-Brite", "2 pcs", 40, 35, "18", "6805"),
            ]),
            ("Home Care", [
                ("HH-MOSQUITO-1PC", "Mosquito Repellent Refill", "Good Knight", "1 pc", 70, 65, "18", "3808"),
            ]),
        ],
    ),
    (
        "meat-seafood", "Meat & Seafood", "🍗",
        [
            ("Poultry & Meat", [
                ("MS-CHICKENBREAST-500G", "Chicken Breast Boneless", "Fresh Catch", "500 g", 240, 220, "0", "0207"),
                ("MS-MUTTON-500G", "Mutton Curry Cut", "Fresh Catch", "500 g", 480, 450, "0", "0204"),
            ]),
            ("Seafood", [
                ("MS-PRAWNS-250G", "Fresh Prawns", "Fresh Catch", "250 g", 300, 280, "0", "0306"),
                ("MS-ROHU-500G", "Rohu Fish Cleaned", "Fresh Catch", "500 g", 200, 180, "0", "0302"),
            ]),
        ],
    ),
]


def seed_more_catalog(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Subcategory = apps.get_model("catalog", "Subcategory")
    Product = apps.get_model("catalog", "Product")

    for order, (key, name, icon, subcats) in enumerate(CATALOG, start=1):
        category, _ = Category.objects.get_or_create(
            key=key,
            defaults={"name": name, "icon": icon, "order": order},
        )
        for sub_order, (sub_name, products) in enumerate(subcats, start=1):
            subcategory, _ = Subcategory.objects.get_or_create(
                category=category,
                name=sub_name,
                defaults={"order": sub_order},
            )
            for sku, pname, brand, pack, mrp, price, gst_slab, hsn in products:
                Product.objects.get_or_create(
                    sku=sku,
                    defaults={
                        "name": pname,
                        "brand": brand,
                        "category": category,
                        "subcategory": subcategory,
                        "pack": pack,
                        "hsn_code": hsn,
                        "description": f"{pname} ({pack}) from {brand}.",
                        "mrp": mrp,
                        "price": price,
                        "cost_price": max(1, int(price * 0.8)),
                        "gst_slab": gst_slab,
                        "main_image_url": "",
                    },
                )


def remove_more_catalog(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    skus = [sku for _, _, _, subcats in CATALOG for _, products in subcats for sku, *_ in products]
    Product.objects.filter(sku__in=skus).delete()
    Category = apps.get_model("catalog", "Category")
    Category.objects.filter(key__in=[key for key, *_ in CATALOG if key != "fruits-vegetables"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_seed_sample_product"),
    ]

    operations = [
        migrations.RunPython(seed_more_catalog, remove_more_catalog),
    ]
