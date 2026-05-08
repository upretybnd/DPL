from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from branches.models import ParentBranch
from reports.forms import ProjectForm
from reports.models import BranchRole, Notification, Project, ProjectEvidence, ProjectReport, ReportStatusHistory


class ReportsFeatureTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="pass123", email="admin@example.com")
        self.reporter = User.objects.create_user(
            username="reporter", password="pass123", email="reporter@example.com"
        )
        self.outsider = User.objects.create_user(
            username="outsider", password="pass123", email="outsider@example.com"
        )
        image = SimpleUploadedFile("branch.jpg", b"filecontent", content_type="image/jpeg")
        self.branch = ParentBranch.objects.create(
            name="Kankai",
            main_image=image,
            description="Branch desc",
            manager=self.admin,
        )
        BranchRole.objects.create(user=self.admin, role=BranchRole.ROLE_NATIONAL_ADMIN, is_active=True)
        BranchRole.objects.create(
            user=self.reporter, branch=self.branch, role=BranchRole.ROLE_REPORTER, is_active=True
        )

    def test_public_page_shows_only_published_approved(self):
        shown = Project.objects.create(
            branch=self.branch,
            title="Published One",
            project_type="Education",
            impact_summary="ok",
            created_by=self.reporter,
            status=Project.STATUS_APPROVED,
            is_published=True,
        )
        Project.objects.create(
            branch=self.branch,
            title="Hidden One",
            project_type="Health",
            impact_summary="hidden",
            created_by=self.reporter,
            status=Project.STATUS_DRAFT,
            is_published=False,
        )
        resp = self.client.get(reverse("public_project_list"))
        self.assertContains(resp, shown.title)
        self.assertNotContains(resp, "Hidden One")

    def test_project_form_validation_for_sdg_and_budget(self):
        form = ProjectForm(
            data={
                "branch": self.branch.branch_id,
                "title": "A",
                "project_type": "Education",
                "sdg_tags": "SDG 4,SDG18",
                "event_date": "2026-05-01",
                "location": "X",
                "budget_planned": "100",
                "budget_actual": "120",
                "beneficiaries_count": "10",
                "volunteer_hours": "5",
                "impact_summary": "summary",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("sdg_tags", form.errors)
        self.assertIn("budget_actual", form.errors)

    def test_national_analytics_export_csv(self):
        Project.objects.create(
            branch=self.branch,
            title="Proj",
            project_type="Education",
            impact_summary="ok",
            created_by=self.reporter,
            status=Project.STATUS_APPROVED,
            is_published=True,
            beneficiaries_count=50,
        )
        self.client.login(username="admin", password="pass123")
        resp = self.client.get(reverse("national_analytics_export_csv"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
        self.assertIn("Kankai", resp.content.decode("utf-8"))

    def test_send_reminders_creates_notification(self):
        project = Project.objects.create(
            branch=self.branch,
            title="Needs Evidence",
            project_type="Education",
            impact_summary="pending",
            created_by=self.reporter,
            status=Project.STATUS_DRAFT,
        )
        ProjectReport.objects.create(project=project, report_period="2026-05")
        self.client.login(username="admin", password="pass123")
        self.client.get(reverse("send_submission_reminders") + "?period=2026-05")
        self.assertTrue(
            Notification.objects.filter(user=self.reporter, title__icontains="reminder").exists()
        )

    def test_evidence_delete_denied_for_non_manager(self):
        project = Project.objects.create(
            branch=self.branch,
            title="Locked Evidence",
            project_type="Education",
            impact_summary="pending",
            created_by=self.reporter,
            status=Project.STATUS_DRAFT,
        )
        evidence = ProjectEvidence.objects.create(
            project=project,
            evidence_type=ProjectEvidence.EVIDENCE_PHOTO,
            title="Photo 1",
            uploaded_by=self.reporter,
            external_url="https://example.com/photo",
        )
        self.client.login(username="outsider", password="pass123")
        resp = self.client.get(reverse("evidence_delete", args=[evidence.id]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(ProjectEvidence.objects.filter(id=evidence.id).exists())

    def test_review_note_persisted_in_status_history(self):
        project = Project.objects.create(
            branch=self.branch,
            title="Review Note Project",
            project_type="Education",
            impact_summary="ready",
            created_by=self.reporter,
            status=Project.STATUS_SUBMITTED,
        )
        ProjectReport.objects.create(project=project, report_period="2026-05")
        self.client.login(username="admin", password="pass123")
        note = "Checked metrics and compliance docs."
        resp = self.client.post(reverse("project_review_action", args=[project.id, "approve"]), {"note": note})
        self.assertEqual(resp.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.status, Project.STATUS_APPROVED)
        latest = ReportStatusHistory.objects.filter(project=project).first()
        self.assertIsNotNone(latest)
        self.assertIn(note, latest.note)
