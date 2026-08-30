from django.db import migrations

# Mirrors lib/features/basket/presentation/festival_theme.dart's `Festivals`
# catalog 1:1 — same colours/greetings, so a fresh install matches the app's
# own built-in defaults until an admin changes something.
_SEED = [
    dict(
        key="diwali", accent_color="#F3B14A", gradient_start="#6B2A17", gradient_end="#3B120A",
        motif="diyaLights", greeting_text="Happy Diwali! Festive picks inside ✨",
        popup_title="Happy Diwali! \U0001FA94", popup_message="Celebrate with festive prices on your favourite picks.",
    ),
    dict(
        key="holi", accent_color="#FFC94D", gradient_start="#7B2D8E", gradient_end="#1F6FB2",
        motif="colorSplash", greeting_text="Happy Holi! Colours of savings \U0001F389",
        popup_title="Happy Holi! \U0001F389", popup_message="Splash into Holi deals across the store.",
    ),
    dict(
        key="christmas", accent_color="#E6B450", gradient_start="#1E4B3A", gradient_end="#0B2A20",
        motif="snowfall", greeting_text="Merry Christmas! Holiday deals are here \U0001F384",
        popup_title="Merry Christmas! \U0001F384", popup_message="Unwrap holiday offers on groceries & gifts.",
    ),
    dict(
        key="new_year", accent_color="#F3B14A", gradient_start="#241B4E", gradient_end="#0A1F3C",
        motif="confetti", greeting_text="Happy New Year! Fresh deals to start the year \U0001F386",
        popup_title="Happy New Year! \U0001F386", popup_message="Start the year with fresh savings.",
    ),
    dict(
        key="independence_day", accent_color="#F3B14A", gradient_start="#0A1F3C", gradient_end="#1F6F4A",
        motif="confetti", greeting_text="Happy Independence Day! Freedom sale is live \U0001F1EE\U0001F1F3",
        popup_title="Happy Independence Day! \U0001F1EE\U0001F1F3", popup_message="Celebrate with our Freedom Sale.",
    ),
    dict(
        key="raksha_bandhan", accent_color="#F3B14A", gradient_start="#8A1E3B", gradient_end="#43101E",
        motif="diyaLights", greeting_text="Happy Raksha Bandhan! Rakhi specials inside \U0001F397️",
        popup_title="Happy Raksha Bandhan! \U0001F397️", popup_message="Rakhi specials & gifting deals inside.",
    ),
]


def seed_festival_settings(apps, schema_editor):
    FestivalSetting = apps.get_model("promotions", "FestivalSetting")
    for row in _SEED:
        FestivalSetting.objects.get_or_create(key=row["key"], defaults=row)


def remove_festival_settings(apps, schema_editor):
    FestivalSetting = apps.get_model("promotions", "FestivalSetting")
    FestivalSetting.objects.filter(key__in=[row["key"] for row in _SEED]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('promotions', '0004_festivalsetting'),
    ]

    operations = [
        migrations.RunPython(seed_festival_settings, remove_festival_settings),
    ]
