from django.contrib import admin
from django.utils.html import format_html
from .models import AboutMilestone, AboutPage, AboutPillar, AboutStat, Carousel, ContactMessage, Donation, HomePageMedia, NewsletterSubscriber

admin.site.register(Carousel)


@admin.register(HomePageMedia)
class HomePageMediaAdmin(admin.ModelAdmin):
    list_display = ("key", "preview", "alt_text")

    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:48px;border-radius:6px" />', obj.image.url)
        return "—"


class AboutStatInline(admin.TabularInline):
    model = AboutStat
    extra = 1
    fields = ("value", "label", "display_order")


class AboutMilestoneInline(admin.TabularInline):
    model = AboutMilestone
    extra = 1
    fields = ("year", "title", "text", "display_order")


class AboutPillarInline(admin.TabularInline):
    model = AboutPillar
    extra = 1
    fields = ("icon", "title", "text", "display_order")


@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    inlines = [AboutStatInline, AboutMilestoneInline, AboutPillarInline]
    fields = ("title", "lead", "story", "image")

    def has_add_permission(self, request):
        # A single About page; edit the existing one.
        return not AboutPage.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "is_handled", "created_at")
    list_filter = ("is_handled", "created_at")
    search_fields = ("name", "email", "subject", "message")
    list_editable = ("is_handled",)
    readonly_fields = ("name", "email", "subject", "message", "created_at")


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("email",)


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "amount", "payment_method", "status", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    list_editable = ("status",)
    search_fields = ("full_name", "email", "phone")
    readonly_fields = ("full_name", "email", "phone", "amount", "payment_method", "message", "payment_proof", "created_at")
