from django.db import migrations

# Organisation pages that live under the About menu. Descriptions and teams are filled in from the admin.
ORGANISATIONS = [
    ("DPL", "dpl", "Dynamic Public Library — a volunteer-led network of community libraries."),
    ("DPL Nepal", "dpl-nepal", "Dynamic Public Library Nepal, headquartered in Damak, Jhapa."),
]


def forwards(apps, schema_editor):
    ParentBranch = apps.get_model("branches", "ParentBranch")
    for order, (name, slug, tagline) in enumerate(ORGANISATIONS):
        existing = ParentBranch.objects.filter(slug=slug).first()
        if existing:
            # A page with this address already exists (e.g. added earlier as a chapter): make it the About page.
            existing.branch_type = "organisation"
            existing.in_about_menu = True
            existing.save(update_fields=["branch_type", "in_about_menu"])
        else:
            ParentBranch.objects.create(
                name=name,
                slug=slug,
                tagline=tagline,
                description="",
                branch_type="organisation",
                in_about_menu=True,
                display_order=order,
            )
    # Boards were already listed under About; keep them there.
    ParentBranch.objects.filter(branch_type__in=["national_board", "senate"]).update(in_about_menu=True)


class Migration(migrations.Migration):
    dependencies = [
        ("branches", "0010_parentbranch_in_about_menu_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
