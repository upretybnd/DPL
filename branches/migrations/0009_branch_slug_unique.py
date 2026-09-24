from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("branches", "0008_populate_branch_slugs_and_types"),
    ]

    operations = [
        migrations.AlterField(
            model_name="parentbranch",
            name="slug",
            field=models.SlugField(
                help_text="Used in the web address, e.g. /chapters/damak/", max_length=120, unique=True
            ),
        ),
    ]
