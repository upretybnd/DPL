from django.db import migrations

PILLARS = [
    {"icon": "library", "title": "Free public library", "text": "Books, ideas, information, training and scholarships — free to everyone, from children to adults."},
    {"icon": "monitor-smartphone", "title": "E-library & digital literacy", "text": "Online resources in our study hall, plus computer and internet skills taught by volunteer professionals."},
    {"icon": "mic", "title": "Youth capacity building", "text": "Workshops on literature, poem recitation, public speaking, training of trainers, and proposal and report writing."},
    {"icon": "clipboard-list", "title": "Community surveys", "text": "Research on sanitation, tobacco, alcohol and public smoking, shared through street programs and newspapers."},
    {"icon": "smile", "title": "Teens & children", "text": "A dedicated Teens/Child team runs programs designed for young readers in every chapter."},
    {"icon": "users-round", "title": "National volunteer team", "text": "The DPL National Team works across the country to run public programs within communities."},
]


def forwards(apps, schema_editor):
    AboutPage = apps.get_model("web", "AboutPage")
    AboutPillar = apps.get_model("web", "AboutPillar")
    for page in AboutPage.objects.all():
        if page.pillars.exists():
            continue
        for order, item in enumerate(PILLARS):
            AboutPillar.objects.create(page=page, display_order=order, **item)


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0008_about_pillars"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
