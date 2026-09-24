from django.db import migrations
from django.utils.text import slugify


def _guess_type(name):
    lowered = name.lower()
    if "national board" in lowered:
        return "national_board"
    if "guardian" in lowered or "guardain" in lowered or "senate" in lowered:
        return "senate"
    if "teen" in lowered:
        return "teens"
    return "chapter"


def populate(apps, schema_editor):
    ParentBranch = apps.get_model("branches", "ParentBranch")
    used = set()
    branches = list(ParentBranch.objects.order_by("branch_id"))
    for branch in branches:
        branch.branch_type = _guess_type(branch.name)
        if branch.branch_type == "senate":
            # The Guardian Board was renamed to the DPL Senate.
            branch.name = "DPL Senate"
        base = slugify(branch.name)[:110] or "branch"
        slug, n = base, 1
        while slug in used:
            n += 1
            slug = f"{base}-{n}"
        used.add(slug)
        branch.slug = slug
        branch.save(update_fields=["name", "slug", "branch_type"])

    # Link "X Teens" wings to the "X" chapter when one exists.
    chapters = {b.name.lower().strip(): b for b in branches if b.branch_type == "chapter"}
    for branch in branches:
        if branch.branch_type != "teens":
            continue
        parent_name = branch.name.lower().replace("teens", "").replace("teen", "").strip(" -")
        parent = chapters.get(parent_name)
        if parent:
            branch.parent_id = parent.branch_id
            branch.save(update_fields=["parent"])


class Migration(migrations.Migration):
    dependencies = [
        ("branches", "0007_branch_profile_fields"),
    ]

    operations = [
        migrations.RunPython(populate, migrations.RunPython.noop),
    ]
