from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from branches.models import ParentBranch, Program
from forum.models import Thread
from reports.models import Project


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return ["home", "about", "branch_details", "program_list", "public_project_list", "category_list", "contact", "donate_us"]

    def location(self, item):
        return reverse(item)


class BranchSitemap(Sitemap):
    priority = 0.9
    changefreq = "weekly"

    def items(self):
        return ParentBranch.objects.active()

    def lastmod(self, obj):
        return obj.updated_at


class ProgramSitemap(Sitemap):
    priority = 0.6
    changefreq = "monthly"

    def items(self):
        return Program.objects.order_by("-program_date")

    def lastmod(self, obj):
        return obj.program_date


class PublicProjectSitemap(Sitemap):
    priority = 0.6
    changefreq = "monthly"

    def items(self):
        return Project.objects.filter(is_published=True, status=Project.STATUS_APPROVED)

    def location(self, obj):
        return reverse("public_project_detail", args=[obj.id])

    def lastmod(self, obj):
        return obj.updated_at


class ThreadSitemap(Sitemap):
    priority = 0.4
    changefreq = "daily"

    def items(self):
        return Thread.objects.order_by("-updated_at")[:1000]

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {
    "pages": StaticViewSitemap,
    "chapters": BranchSitemap,
    "programs": ProgramSitemap,
    "impact": PublicProjectSitemap,
    "forum": ThreadSitemap,
}
