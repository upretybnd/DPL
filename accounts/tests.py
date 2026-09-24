from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .forms import DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS, validate_upload

STRONG = "Str0ng-pass-99"


class AccountTests(TestCase):
    def test_sign_up_sends_absolute_verification_link_and_saves_name(self):
        resp = self.client.post(reverse("sign_up"), {
            "fullName": "Ram Thapa", "email": "ram@example.com",
            "password": STRONG, "confirmPassword": STRONG,
        })
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(email="ram@example.com")
        self.assertFalse(user.is_active)
        self.assertEqual(user.profile.full_name, "Ram Thapa")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("http://testserver/accounts/verify-email/", mail.outbox[0].body)

    def test_sign_up_with_same_email_prefix_gets_unique_username(self):
        User.objects.create_user("ram", "ram@gmail.com", "x")
        self.client.post(reverse("sign_up"), {"email": "ram@yahoo.com", "password": STRONG, "confirmPassword": STRONG})
        self.assertEqual(User.objects.get(email="ram@yahoo.com").username, "ram2")

    def test_sign_up_rejects_weak_password(self):
        self.client.post(reverse("sign_up"), {"email": "a@example.com", "password": "123", "confirmPassword": "123"})
        self.assertFalse(User.objects.filter(email="a@example.com").exists())

    def test_unverified_user_sees_verification_message(self):
        user = User.objects.create_user("sita", "sita@example.com", STRONG)
        user.is_active = False
        user.save()
        resp = self.client.post(reverse("login"), {"email": "sita@example.com", "password": STRONG}, follow=True)
        self.assertContains(resp, "not verified")

    def test_login_is_case_insensitive_and_respects_next(self):
        User.objects.create_user("hari", "hari@example.com", STRONG)
        resp = self.client.post(reverse("login"), {"email": "HARI@example.com", "password": STRONG, "next": "/discussion/"})
        self.assertEqual(resp["Location"], "/discussion/")

    def test_login_ignores_offsite_next(self):
        User.objects.create_user("hari", "hari@example.com", STRONG)
        resp = self.client.post(reverse("login"), {"email": "hari@example.com", "password": STRONG, "next": "//evil.com"})
        self.assertEqual(resp["Location"], reverse("home"))

    def test_forgot_password_does_not_reveal_accounts(self):
        User.objects.create_user("gita", "gita@example.com", "x")
        known = self.client.post(reverse("forgot_password"), {"email": "gita@example.com"}, follow=True)
        unknown = self.client.post(reverse("forgot_password"), {"email": "nobody@example.com"}, follow=True)
        self.assertEqual([str(m) for m in known.context["messages"]], [str(m) for m in unknown.context["messages"]])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("http://testserver/accounts/reset-password/", mail.outbox[0].body)

    def test_logout_requires_post(self):
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)

    def test_election_page_is_removed(self):
        self.assertEqual(self.client.get("/accounts/register-candidacy/").status_code, 404)


class UploadValidationTests(TestCase):
    def test_rejects_non_image_upload(self):
        from django import forms
        with self.assertRaises(forms.ValidationError):
            validate_upload(SimpleUploadedFile("pay.exe", b"MZ"), IMAGE_EXTENSIONS)

    def test_accepts_pdf_document(self):
        upload = SimpleUploadedFile("id.pdf", b"%PDF-1.4")
        self.assertIs(validate_upload(upload, DOCUMENT_EXTENSIONS), upload)
