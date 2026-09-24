from django.db import migrations

STORY = """Dynamic Public Library (DPL) Nepal was established on November 15, 2011 and officially registered on June 28, 2012. Since then it has provided essential resources and educational support to communities across Nepal.

Operating as a non-profit organisation headquartered in Damak, DPL is one of the few public libraries in the region. The library is a hub for free access to books, ideas, information, training, scholarships and education, catering to the diverse needs of the local population.

Our library hall accommodates around 70 readers at a time, fostering an environment for learning and research. We are currently expanding to enhance our study space and broaden our impact.

DPL offers e-library facilities, giving community members and youth access to online resources not physically available in the library. We also bridge the digital divide with computer literacy programs led by dedicated volunteer professionals."""

STATS = [
    ("15", "chapters, Birtamode to Arghakhanchi"),
    ("18k+", "patrons served every year"),
    ("70", "reader seats in our Damak hall"),
]

MILESTONES = [
    ("2011", "Founded in Damak", "A community reading room opens its doors on November 15."),
    ("2012", "Officially registered", "DPL is registered as a non-profit on June 28."),
    ("15", "Chapters nationwide", "From eastern Birtamode to Arghakhanchi in the west."),
    ("Today", "Growing further", "Expanding study space and launching new teen wings."),
]

# Old homepage slot names -> the clearer landing-page names
KEY_RENAMES = {"about_left": "hero_main", "about_right": "hero_side", "feature_main": "video_cover"}


def forwards(apps, schema_editor):
    HomePageMedia = apps.get_model("web", "HomePageMedia")
    for old, new in KEY_RENAMES.items():
        HomePageMedia.objects.filter(key=old).update(key=new)

    AboutPage = apps.get_model("web", "AboutPage")
    if AboutPage.objects.exists():
        return
    page = AboutPage.objects.create(
        title="Empowering communities through education",
        lead=(
            "Since 2011 we have grown from a single reading room in Damak into a national network "
            "of public libraries — free, volunteer-run and open to everyone."
        ),
        story=STORY,
    )
    AboutStat = apps.get_model("web", "AboutStat")
    for order, (value, label) in enumerate(STATS):
        AboutStat.objects.create(page=page, value=value, label=label, display_order=order)
    AboutMilestone = apps.get_model("web", "AboutMilestone")
    for order, (year, title, text) in enumerate(MILESTONES):
        AboutMilestone.objects.create(page=page, year=year, title=title, text=text, display_order=order)


def backwards(apps, schema_editor):
    HomePageMedia = apps.get_model("web", "HomePageMedia")
    for old, new in KEY_RENAMES.items():
        HomePageMedia.objects.filter(key=new).update(key=old)


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0006_aboutpage_alter_homepagemedia_options_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
