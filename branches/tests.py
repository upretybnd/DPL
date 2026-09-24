import datetime

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from .models import BranchTeam, ParentBranch, Program


class ProgramFilterTests(TestCase):
    def setUp(self):
        self.damak = ParentBranch.objects.create(name="Damak", description="d", main_image="b.jpg")
        self.pokhara = ParentBranch.objects.create(name="Pokhara", description="p", main_image="b.jpg")
        for branch, year in [(self.damak, 2024), (self.damak, 2025), (self.pokhara, 2025)]:
            Program.objects.create(
                branch=branch, title=f"{branch.name} {year}", description="x",
                program_date=datetime.date(year, 3, 1), coordinator_name="C", image="p.jpg",
            )

    def test_filters_combine_with_and(self):
        resp = self.client.get(reverse("program_list"), {"branch": self.damak.branch_id, "year": 2025})
        self.assertEqual([p.title for p in resp.context["page_obj"]], ["Damak 2025"])

    def test_invalid_filter_values_are_ignored(self):
        resp = self.client.get(reverse("program_list"), {"year": "abc", "month": "13", "program_date": "not-a-date"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["page_obj"]), 3)


class BranchDataMigrationTests(TransactionTestCase):
    """Runs 0008 against rows shaped like the live data (no slugs, names only)."""

    migrate_from = [("branches", "0007_branch_profile_fields")]
    migrate_to = [("branches", "0012_branch_description_optional")]

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps
        OldBranch = old_apps.get_model("branches", "ParentBranch")
        OldBranch.objects.all().delete()  # start from pre-0008 data only
        for name in ["Damak", "Damak Teens", "DPL National Board", "DPL Guardain Board", "Kankai", "Kankai"]:
            OldBranch.objects.create(name=name, description="x", main_image="b.jpg")
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(self.migrate_to)

    def tearDown(self):
        MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())

    def test_slugs_types_and_parents_are_populated(self):
        rows = {b.slug: b for b in ParentBranch.objects.all()}
        self.assertEqual(set(rows), {"damak", "damak-teens", "dpl-national-board", "dpl-senate", "kankai", "kankai-2", "dpl", "dpl-nepal"})
        self.assertEqual(rows["damak-teens"].branch_type, ParentBranch.TYPE_TEENS)
        self.assertEqual(rows["damak-teens"].parent, rows["damak"])
        self.assertEqual(rows["dpl-national-board"].branch_type, ParentBranch.TYPE_NATIONAL_BOARD)
        self.assertEqual(rows["dpl-senate"].branch_type, ParentBranch.TYPE_SENATE)
        self.assertEqual(rows["dpl-senate"].name, "DPL Senate")
        self.assertEqual(rows["kankai"].branch_type, ParentBranch.TYPE_CHAPTER)
        # Boards stay in the About menu; DPL and DPL Nepal are added there as organisations.
        self.assertTrue(rows["dpl-senate"].in_about_menu)
        self.assertEqual(rows["dpl-nepal"].branch_type, ParentBranch.TYPE_ORGANISATION)


class BranchPagesTests(TestCase):
    def setUp(self):
        self.damak = ParentBranch.objects.create(name="Damak", description="Damak chapter", district="Jhapa", province="koshi")
        self.teens = ParentBranch.objects.create(
            name="Damak Teens", description="Teens wing", branch_type=ParentBranch.TYPE_TEENS, parent=self.damak
        )
        self.board = ParentBranch.objects.create(
            name="DPL National Board", description="Board", branch_type=ParentBranch.TYPE_NATIONAL_BOARD,
            in_about_menu=True,
        )
        self.hidden = ParentBranch.objects.create(name="Closed", description="x", is_active=False)
        BranchTeam.objects.create(branch=self.damak, member_name="Sita", designation="President")
        BranchTeam.objects.create(
            branch=self.damak, member_name="Hari", designation="Founder", member_type=BranchTeam.TYPE_CHARTER_PRESIDENT
        )

    def test_slug_is_generated_and_unique(self):
        self.assertEqual(self.damak.slug, "damak")
        self.assertEqual(ParentBranch.objects.create(name="Damak", description="x").slug, "damak-2")

    def test_detail_page_shows_team_groups_and_wing(self):
        resp = self.client.get(self.damak.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "branches/branch_detail.html")
        self.assertEqual([m.member_name for m in resp.context["board_members"]], ["Sita"])
        self.assertEqual([m.member_name for m in resp.context["charter_presidents"]], ["Hari"])
        self.assertContains(resp, self.teens.get_absolute_url())

    def test_inactive_branch_is_hidden(self):
        self.assertEqual(self.client.get(self.hidden.get_absolute_url()).status_code, 404)
        resp = self.client.get(reverse("branch_details"))
        self.assertNotIn(self.hidden, resp.context["chapters"])

    def test_list_shows_only_chapters_and_filters_by_province(self):
        resp = self.client.get(reverse("branch_details"))
        self.assertEqual(list(resp.context["chapters"]), [self.damak])
        self.assertEqual(list(resp.context["boards"]), [self.board])
        resp = self.client.get(reverse("branch_details"), {"province": "gandaki"})
        self.assertEqual(list(resp.context["chapters"]), [])

    def test_navbar_lists_boards_from_database(self):
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, self.board.get_absolute_url())

    def test_legacy_urls_redirect_permanently(self):
        resp = self.client.get(f"/branch/branch/{self.damak.branch_id}/")
        self.assertRedirects(resp, "/chapters/damak/", status_code=301)
        self.assertRedirects(self.client.get("/branch/branches/"), "/chapters/", status_code=301)
        self.assertRedirects(self.client.get("/branch/programs/"), "/programs/", status_code=301, fetch_redirect_response=False)


class BranchAdminScopeTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        from reports.models import BranchRole

        self.damak = ParentBranch.objects.create(name="Damak", description="x")
        self.pokhara = ParentBranch.objects.create(name="Pokhara", description="x")
        self.user = User.objects.create_user("damak_admin", "d@example.com", "pass12345!", is_staff=True)
        BranchRole.objects.create(user=self.user, branch=self.damak, role=BranchRole.ROLE_BRANCH_ADMIN)

    def test_branch_admin_sees_only_own_branch(self):
        from .admin import admin_branch_ids

        self.assertEqual(admin_branch_ids(self.user), [self.damak.branch_id])
