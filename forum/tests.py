import json

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Category, Reply, Thread


class ForumSecurityTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", "alice@example.com", "pass12345!")
        self.bob = User.objects.create_user("bob", "bob@example.com", "pass12345!")
        self.category = Category.objects.create(name="General")
        self.thread = Thread.objects.create(title="Hello", author=self.alice, content="First", category=self.category)

    def test_user_cannot_edit_someone_elses_profile(self):
        self.client.login(username="bob", password="pass12345!")
        url = reverse("profile", kwargs={"username": "alice"}) + "?edit=true"
        self.client.post(url, {"full_name": "Hacked", "bio": "pwned"})
        self.alice.profile.refresh_from_db()
        self.assertNotEqual(self.alice.profile.full_name, "Hacked")

    def test_owner_can_edit_own_profile(self):
        self.client.login(username="alice", password="pass12345!")
        url = reverse("profile", kwargs={"username": "alice"}) + "?edit=true"
        self.client.post(url, {"full_name": "Alice A", "bio": "hi"})
        self.alice.profile.refresh_from_db()
        self.assertEqual(self.alice.profile.full_name, "Alice A")

    def test_profile_page_keeps_logged_in_user_in_header(self):
        self.client.login(username="bob", password="pass12345!")
        resp = self.client.get(reverse("profile", kwargs={"username": "alice"}))
        self.assertEqual(resp.context["user"], self.bob)
        self.assertEqual(resp.context["profile_user"], self.alice)
        self.assertNotContains(resp, "?edit=true")

    def test_edit_thread_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.login(username="alice", password="pass12345!")
        resp = client.post(
            reverse("edit_thread", args=[self.thread.id]),
            data=json.dumps({"content": "changed"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.content, "First")

    def test_edit_thread_denied_for_non_author(self):
        self.client.login(username="bob", password="pass12345!")
        resp = self.client.post(
            reverse("edit_thread", args=[self.thread.id]),
            data=json.dumps({"content": "changed"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_reply_redirects_to_login_instead_of_crashing(self):
        resp = self.client.post(reverse("thread_detail", args=[self.thread.id]), {"reply_thread": "1", "content": "hi"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])
        self.assertFalse(Reply.objects.exists())

    def test_anonymous_cannot_create_thread(self):
        resp = self.client.post(reverse("create_thread"), {"title": "x", "content": "y", "category": self.category.id})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Thread.objects.count(), 1)

    def test_logged_in_reply_is_posted(self):
        self.client.login(username="bob", password="pass12345!")
        self.client.post(reverse("thread_detail", args=[self.thread.id]), {"reply_thread": "1", "content": "hi"})
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.replies.count(), 1)
        self.assertIsNotNone(self.thread.last_reply)

    def test_like_endpoints_reject_get(self):
        self.client.login(username="bob", password="pass12345!")
        self.assertEqual(self.client.get(reverse("like_thread", args=[self.thread.id])).status_code, 405)

    def test_category_listing_does_not_inflate_views(self):
        self.client.get(reverse("category_threads", args=[self.category.id]))
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.views, 0)

    def test_rank_is_plain_text(self):
        resp = self.client.get(reverse("thread_detail", args=[self.thread.id]))
        self.assertContains(resp, "Newbie")
        self.assertNotContains(resp, "&lt;span")
