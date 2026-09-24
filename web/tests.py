from django.test import TestCase
from django.urls import reverse

from .models import ContactMessage, NewsletterSubscriber


class PublicPagesTests(TestCase):
    def test_key_pages_render(self):
        for name in ["home", "about", "contact", "donate_us", "branch_details", "program_list", "category_list", "public_project_list", "sign_up", "login", "forgot_password", "terms_conditions", "privacy_policy", "cookie"]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_contact_form_saves_message(self):
        self.client.post(reverse("contact"), {"name": "Ram", "email": "ram@example.com", "subject": "Hi", "message": "Hello"})
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_contact_honeypot_blocks_bots(self):
        self.client.post(reverse("contact"), {"name": "Bot", "email": "b@example.com", "message": "spam", "website": "x"})
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_newsletter_subscribe_is_idempotent(self):
        for _ in range(2):
            self.client.post(reverse("newsletter_subscribe"), {"email": "Reader@Example.com"})
        self.assertEqual(NewsletterSubscriber.objects.filter(email="reader@example.com").count(), 1)



class DonationTests(TestCase):
    def test_donation_pledge_is_saved(self):
        from .models import Donation
        resp = self.client.post(reverse("donate_us"), {
            "full_name": "Sita", "email": "s@example.com", "phone": "9800000000",
            "amount": "1000", "payment_method": "esewa", "message": "For Damak",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Donation.objects.get().amount, 1000)

    def test_donation_rejects_non_positive_amount(self):
        from .models import Donation
        self.client.post(reverse("donate_us"), {
            "full_name": "Sita", "email": "s@example.com", "phone": "98", "amount": "0", "payment_method": "bank",
        })
        self.assertFalse(Donation.objects.exists())

    def test_placeholder_bank_details_are_hidden(self):
        resp = self.client.get(reverse("donate_us"))
        self.assertNotContains(resp, "XYZ Bank")
        self.assertNotContains(resp, "1234567890")


class SeoTests(TestCase):
    def test_sitemap_lists_chapters(self):
        from branches.models import ParentBranch
        ParentBranch.objects.create(name="Damak", description="d")
        resp = self.client.get("/sitemap.xml")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/chapters/damak/")

    def test_robots_points_to_sitemap(self):
        resp = self.client.get("/robots.txt")
        self.assertContains(resp, "Sitemap: http://testserver/sitemap.xml")
        self.assertContains(resp, "Disallow: /admin/")

    def test_pages_have_title_description_and_canonical(self):
        resp = self.client.get(reverse("about"))
        self.assertContains(resp, "<title>About us · Dynamic Public Library</title>", html=False)
        self.assertContains(resp, '<meta name="description"')
        self.assertContains(resp, '<link rel="canonical" href="http://testserver/about/">')

    def test_404_page_is_branded(self):
        with self.settings(DEBUG=False):
            resp = self.client.get("/definitely-missing/")
        self.assertEqual(resp.status_code, 404)
        self.assertContains(resp, "missing from the shelf", status_code=404)



class AdminManagedContentTests(TestCase):
    def test_about_page_content_comes_from_admin(self):
        from .models import AboutPage
        page = AboutPage.objects.get()
        self.assertEqual([s.value for s in page.stats.all()], ["15", "18k+", "70"])
        page.stats.filter(value="15").update(value="16")
        page.pillars.create(icon="star", title="Book clubs", text="Monthly reading circles", display_order=99)
        resp = self.client.get(reverse("about"))
        self.assertContains(resp, ">16<")
        self.assertContains(resp, "Book clubs")
        self.assertEqual(len(page.paragraphs()), 4)

    def test_about_menu_lists_dpl_and_dpl_nepal(self):
        resp = self.client.get(reverse("home"))
        names = [p.name for p in resp.context["nav_about"]]
        self.assertIn("DPL", names)
        self.assertIn("DPL Nepal", names)
        self.assertContains(resp, 'href="/about/dpl-nepal/"')
        self.assertNotContains(resp, "Elections")

    def test_organisation_page_shows_team_and_uses_about_url(self):
        from branches.models import BranchTeam, ParentBranch
        org = ParentBranch.objects.get(slug="dpl-nepal")
        BranchTeam.objects.create(branch=org, member_name="Sita Sharma", designation="Chairperson")
        resp = self.client.get("/about/dpl-nepal/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Our team")
        self.assertContains(resp, "Sita Sharma")
        self.assertRedirects(self.client.get("/chapters/dpl-nepal/"), "/about/dpl-nepal/", status_code=301)

    def test_new_about_menu_page_can_be_added_like_a_branch(self):
        from branches.models import ParentBranch
        ParentBranch.objects.create(name="DPL Youth Council", branch_type=ParentBranch.TYPE_ORGANISATION, in_about_menu=True)
        self.assertContains(self.client.get(reverse("home")), 'href="/about/dpl-youth-council/"')

    def test_landing_images_come_from_admin(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import HomePageMedia
        HomePageMedia.objects.create(key="hero_main", image=SimpleUploadedFile("hero.jpg", b"x", content_type="image/jpeg"), alt_text="Readers in Damak")
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "/media/homepage/hero")
        self.assertContains(resp, 'alt="Readers in Damak"')

    def test_default_background_photo_is_dpl_and_admin_replaceable(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import HomePageMedia
        resp = self.client.get(reverse("login"))
        self.assertContains(resp, "/static/img/dpl1.jpg")
        self.assertNotContains(resp, "books.jpg")
        HomePageMedia.objects.create(key="default_cover", image=SimpleUploadedFile("cover.jpg", b"x", content_type="image/jpeg"))
        self.assertContains(self.client.get(reverse("login")), "/media/homepage/cover")
