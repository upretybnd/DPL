import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from reports.models import AuditLog, BranchRole, Project
from .models import BranchGalleryImage, BranchTeam, ParentBranch, Program


def image_file(name="photo.jpg"):
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "orange").save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


class BranchWorkspaceTests(TestCase):
    def setUp(self):
        self.damak = ParentBranch.objects.create(name="Damak", description="d")
        self.pokhara = ParentBranch.objects.create(name="Pokhara", description="p")
        self.admin = User.objects.create_user("damak_admin", "da@example.com", "pass12345!")
        self.reporter = User.objects.create_user("rep", "rep@example.com", "pass12345!")
        self.national = User.objects.create_user("nat", "nat@example.com", "pass12345!")
        BranchRole.objects.create(user=self.admin, branch=self.damak, role=BranchRole.ROLE_BRANCH_ADMIN)
        BranchRole.objects.create(user=self.reporter, branch=self.damak, role=BranchRole.ROLE_REPORTER)
        BranchRole.objects.create(user=self.national, role=BranchRole.ROLE_NATIONAL_ADMIN)

    def login(self, user):
        self.client.login(username=user.username, password="pass12345!")

    # --- access -----------------------------------------------------------

    def test_branch_admin_lands_on_own_branch(self):
        self.login(self.admin)
        self.assertRedirects(self.client.get(reverse("mis_branches")), reverse("mis_branch_profile", args=[self.damak.branch_id]))

    def test_branch_admin_cannot_manage_other_branch(self):
        self.login(self.admin)
        for name in ["mis_branch_profile", "mis_branch_team", "mis_branch_gallery", "mis_branch_programs", "mis_branch_members"]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name, args=[self.pokhara.branch_id])).status_code, 403)

    def test_reporter_cannot_manage_branch(self):
        self.login(self.reporter)
        self.assertEqual(self.client.get(reverse("mis_branch_profile", args=[self.damak.branch_id])).status_code, 403)

    def test_all_workspace_pages_render(self):
        self.login(self.admin)
        for name in ["mis_branch_profile", "mis_branch_team", "mis_branch_gallery", "mis_branch_programs", "mis_branch_members", "mis_program_create"]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name, args=[self.damak.branch_id])).status_code, 200)

    # --- profile ------------------------------------------------------------

    def test_branch_admin_edits_profile_but_not_national_settings(self):
        self.login(self.admin)
        url = reverse("mis_branch_profile", args=[self.damak.branch_id])
        self.assertNotIn("branch_type", self.client.get(url).context["form"].fields)
        self.client.post(url, {"name": "Damak Library", "tagline": "Reading for all", "description": "Updated", "branch_type": "senate"})
        self.damak.refresh_from_db()
        self.assertEqual(self.damak.name, "Damak Library")
        self.assertEqual(self.damak.branch_type, ParentBranch.TYPE_CHAPTER)
        self.assertTrue(AuditLog.objects.filter(action="branch_profile_updated").exists())

    # --- team ---------------------------------------------------------------

    def test_team_create_edit_delete(self):
        self.login(self.admin)
        team_url = reverse("mis_branch_team", args=[self.damak.branch_id])
        self.client.post(team_url, {"member_name": "Sita", "designation": "President", "member_type": "board", "display_order": 0, "member_image": image_file()})
        member = BranchTeam.objects.get(branch=self.damak)
        self.client.post(reverse("mis_team_edit", args=[self.damak.branch_id, member.id]),
                         {"member_name": "Sita Sharma", "designation": "President", "member_type": "board", "display_order": 1})
        member.refresh_from_db()
        self.assertEqual(member.member_name, "Sita Sharma")
        self.client.post(reverse("mis_team_delete", args=[self.damak.branch_id, member.id]))
        self.assertFalse(BranchTeam.objects.exists())

    def test_team_rejects_non_image_upload(self):
        self.login(self.admin)
        resp = self.client.post(reverse("mis_branch_team", args=[self.damak.branch_id]), {
            "member_name": "X", "designation": "Y", "member_type": "board", "display_order": 0,
            "member_image": SimpleUploadedFile("bad.exe", b"MZ"),
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(BranchTeam.objects.exists())

    def test_cannot_delete_other_branch_member(self):
        other = BranchTeam.objects.create(branch=self.pokhara, member_name="Ram", designation="Sec")
        self.login(self.admin)
        self.assertEqual(self.client.post(reverse("mis_team_delete", args=[self.damak.branch_id, other.id])).status_code, 404)
        self.assertTrue(BranchTeam.objects.filter(id=other.id).exists())

    # --- gallery ------------------------------------------------------------

    def test_gallery_upload_and_delete(self):
        self.login(self.admin)
        self.client.post(reverse("mis_branch_gallery", args=[self.damak.branch_id]), {"image": image_file(), "caption": "Reading day"})
        photo = BranchGalleryImage.objects.get(branch=self.damak)
        self.client.post(reverse("mis_gallery_delete", args=[self.damak.branch_id, photo.id]))
        self.assertFalse(BranchGalleryImage.objects.exists())

    # --- programs -------------------------------------------------------------

    def test_program_create_with_photos_edit_and_delete(self):
        self.login(self.admin)
        resp = self.client.post(reverse("mis_program_create", args=[self.damak.branch_id]), {
            "title": "Reading Camp", "program_date": "2026-05-01", "coordinator_name": "Hari",
            "description": "Fun", "image": image_file(), "photos": [image_file("a.jpg"), image_file("b.jpg")],
        })
        program = Program.objects.get(branch=self.damak)
        self.assertRedirects(resp, reverse("mis_program_edit", args=[self.damak.branch_id, program.id]))
        self.assertEqual(program.sub_images.count(), 2)
        photo = program.sub_images.first()
        self.client.post(reverse("mis_program_photo_delete", args=[self.damak.branch_id, program.id, photo.id]))
        self.assertEqual(program.sub_images.count(), 1)
        self.client.post(reverse("mis_program_delete", args=[self.damak.branch_id, program.id]))
        self.assertFalse(Program.objects.exists())

    # --- members --------------------------------------------------------------

    def test_branch_admin_adds_and_removes_reporter(self):
        newbie = User.objects.create_user("newbie", "new@example.com", "pass12345!")
        self.login(self.admin)
        url = reverse("mis_branch_members", args=[self.damak.branch_id])
        self.client.post(url, {"email": "NEW@example.com", "role": BranchRole.ROLE_REPORTER})
        role = BranchRole.objects.get(user=newbie, branch=self.damak)
        self.assertEqual(role.role, BranchRole.ROLE_REPORTER)
        self.client.post(reverse("mis_member_remove", args=[self.damak.branch_id, role.id]))
        role.refresh_from_db()
        self.assertFalse(role.is_active)

    def test_branch_admin_cannot_appoint_branch_admins(self):
        User.objects.create_user("newbie", "new@example.com", "pass12345!")
        self.login(self.admin)
        resp = self.client.post(reverse("mis_branch_members", args=[self.damak.branch_id]), {"email": "new@example.com", "role": BranchRole.ROLE_BRANCH_ADMIN})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(BranchRole.objects.filter(user__username="newbie").exists())

    def test_member_email_must_have_account(self):
        self.login(self.admin)
        resp = self.client.post(reverse("mis_branch_members", args=[self.damak.branch_id]), {"email": "ghost@example.com", "role": BranchRole.ROLE_VIEWER})
        self.assertContains(resp, "No active account uses this email")

    def test_national_admin_appoints_branch_admin_for_new_branch(self):
        self.login(self.national)
        resp = self.client.post(reverse("mis_branch_create"), {"name": "Butwal", "branch_type": "chapter", "is_active": "on", "display_order": 0})
        butwal = ParentBranch.objects.get(name="Butwal")
        self.assertRedirects(resp, reverse("mis_branch_members", args=[butwal.branch_id]))
        self.client.post(reverse("mis_branch_members", args=[butwal.branch_id]), {"email": "rep@example.com", "role": BranchRole.ROLE_BRANCH_ADMIN})
        self.assertTrue(BranchRole.objects.filter(user=self.reporter, branch=butwal, role=BranchRole.ROLE_BRANCH_ADMIN).exists())

    def test_only_national_admins_create_branches(self):
        self.login(self.admin)
        self.assertEqual(self.client.get(reverse("mis_branch_create")).status_code, 403)

    def test_national_admins_page(self):
        self.login(self.national)
        self.client.post(reverse("mis_national_admins"), {"email": "da@example.com"})
        self.assertTrue(BranchRole.objects.filter(user=self.admin, role=BranchRole.ROLE_NATIONAL_ADMIN, is_active=True).exists())
        self.login(self.admin)
        self.assertEqual(self.client.get(reverse("mis_branches")).status_code, 200)

    # --- project reports ------------------------------------------------------

    def test_reporter_edits_and_deletes_draft_but_not_submitted(self):
        project = Project.objects.create(branch=self.damak, title="Draft", project_type="Education", impact_summary="x", created_by=self.reporter)
        self.login(self.reporter)
        resp = self.client.post(reverse("project_edit", args=[project.id]), {
            "branch": self.damak.branch_id, "title": "Draft v2", "project_type": "Education", "event_date": "2026-05-01",
            "budget_planned": 0, "budget_actual": 0, "beneficiaries_count": 10, "volunteer_hours": 2,
            "impact_summary": "Better", "report_period": "2026-05",
        })
        self.assertRedirects(resp, reverse("project_detail", args=[project.id]))
        project.refresh_from_db()
        self.assertEqual(project.title, "Draft v2")

        project.status = Project.STATUS_SUBMITTED
        project.save()
        self.assertRedirects(self.client.get(reverse("project_edit", args=[project.id])), reverse("project_detail", args=[project.id]))
        self.client.post(reverse("project_delete", args=[project.id]))
        self.assertTrue(Project.objects.filter(id=project.id).exists())

        project.status = Project.STATUS_DRAFT
        project.save()
        self.client.post(reverse("project_delete", args=[project.id]))
        self.assertFalse(Project.objects.filter(id=project.id).exists())

    def test_forbidden_page_is_friendly(self):
        self.login(self.reporter)
        resp = self.client.get(reverse("mis_branch_team", args=[self.damak.branch_id]))
        self.assertContains(resp, "You don't have access to this page", status_code=403)
