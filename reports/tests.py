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
        self.client.post(reverse("send_submission_reminders"), {"period": "2026-05"})
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
        resp = self.client.post(reverse("evidence_delete", args=[evidence.id]))
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



class DashboardPagesTests(TestCase):
    """Every redesigned dashboard page renders for the roles that can see it."""

    def setUp(self):
        self.admin = User.objects.create_user("nat", "nat@example.com", "pass12345!")
        BranchRole.objects.create(user=self.admin, role=BranchRole.ROLE_NATIONAL_ADMIN)
        self.branch = ParentBranch.objects.create(name="Damak", description="d")
        self.project = Project.objects.create(
            branch=self.branch, title="Reading Camp", project_type="Education", impact_summary="Great",
            sdg_tags="SDG 4, SDG 10", status=Project.STATUS_SUBMITTED, beneficiaries_count=40, created_by=self.admin,
        )
        ProjectReport.objects.create(project=self.project, report_period="2026-05")
        self.client.login(username="nat", password="pass12345!")

    def test_dashboard_pages_render(self):
        for url in [
            reverse("national_dashboard"), reverse("national_analytics"), reverse("audit_log_list"),
            reverse("branch_dashboard"), reverse("project_create"), reverse("project_detail", args=[self.project.id]),
            reverse("my_notifications"),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_analytics_chart_data_is_serialised_once(self):
        resp = self.client.get(reverse("national_analytics"))
        self.assertEqual(resp.context["chart_data"]["totals"], [1])
        self.assertContains(resp, '"sdg_labels": ["SDG 10", "SDG 4"]')

    def test_review_card_lists_actions_for_submitted_project(self):
        resp = self.client.get(reverse("project_detail", args=[self.project.id]))
        self.assertEqual([a[0] for a in resp.context["review_actions"]], ["review", "approve", "reject"])
        self.assertEqual(self.project.sdg_list, ["SDG 4", "SDG 10"])


class NotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", "u@example.com", "pass12345!")
        self.client.login(username="u", password="pass12345!")

    def test_open_marks_read_and_follows_internal_link(self):
        n = Notification.objects.create(user=self.user, title="t", message="m", link="/reports/")
        resp = self.client.get(reverse("notification_open", args=[n.id]))
        self.assertEqual(resp["Location"], "/reports/")
        n.refresh_from_db()
        self.assertTrue(n.is_read)

    def test_open_ignores_offsite_links(self):
        n = Notification.objects.create(user=self.user, title="t", message="m", link="//evil.example")
        resp = self.client.get(reverse("notification_open", args=[n.id]))
        self.assertEqual(resp["Location"], reverse("my_notifications"))

    def test_cannot_open_someone_elses_notification(self):
        other = User.objects.create_user("o", "o@example.com", "x")
        n = Notification.objects.create(user=other, title="t", message="m")
        self.assertEqual(self.client.get(reverse("notification_open", args=[n.id])).status_code, 404)

    def test_mark_all_read_and_header_badge(self):
        Notification.objects.create(user=self.user, title="a", message="m")
        Notification.objects.create(user=self.user, title="b", message="m")
        self.assertEqual(self.client.get(reverse("home")).context["unread_notification_count"], 2)
        self.client.post(reverse("notifications_mark_read"))
        self.assertFalse(Notification.objects.filter(user=self.user, is_read=False).exists())



class PortalTests(TestCase):
    def test_visitors_see_portal_with_sign_in(self):
        resp = self.client.get(reverse("portal"))
        self.assertContains(resp, "DPL Management System")
        self.assertContains(resp, "DPL MIS")
        self.assertContains(self.client.get(reverse("home")), 'href="/portal/"')

    def test_staff_are_sent_to_their_dashboard(self):
        user = User.objects.create_user("staff", "staff@example.com", "pass12345!")
        BranchRole.objects.create(user=user, role=BranchRole.ROLE_NATIONAL_ADMIN)
        self.client.login(username="staff", password="pass12345!")
        self.assertRedirects(self.client.get(reverse("portal")), reverse("report_home"), fetch_redirect_response=False)

    def test_member_without_role_is_told_how_to_get_access(self):
        User.objects.create_user("member", "m@example.com", "pass12345!")
        self.client.login(username="member", password="pass12345!")
        self.assertContains(self.client.get(reverse("portal")), "don't have a portal role yet")
        self.assertRedirects(self.client.get(reverse("report_home")), reverse("portal"))

    def test_staff_login_lands_on_dashboard(self):
        user = User.objects.create_user("rep", "rep@example.com", "pass12345!")
        branch = ParentBranch.objects.create(name="Damak", description="d")
        BranchRole.objects.create(user=user, branch=branch, role=BranchRole.ROLE_REPORTER)
        resp = self.client.post(reverse("login"), {"email": "rep@example.com", "password": "pass12345!"})
        self.assertEqual(resp["Location"], reverse("report_home"))
