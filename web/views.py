import datetime
import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import mail_managers
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from branches.models import ParentBranch, Program
from forum.models import Thread
from reports.models import Project
from web.forms import ContactForm, DonationForm, NewsletterForm
from web.models import AboutPage, Carousel, HomePageMedia, NewsletterSubscriber

logger = logging.getLogger(__name__)


FOUNDED = datetime.date(2011, 11, 15)


def years_active():
    today = datetime.date.today()
    return today.year - FOUNDED.year - ((today.month, today.day) < (FOUNDED.month, FOUNDED.day))




def home(request):
    years = years_active()
    published_projects = Project.objects.filter(is_published=True, status=Project.STATUS_APPROVED)
    impact = published_projects.aggregate(people=Sum("beneficiaries_count"), hours=Sum("volunteer_hours"))
    context = {
        "carousel_items": Carousel.objects.all(),
        "media_items": {item.key: item for item in HomePageMedia.objects.all()},
        "years_active": years,
        "branch_count": ParentBranch.objects.chapters().count(),
        "program_count": Program.objects.count(),
        "people_reached": impact["people"] or 0,
        "volunteer_hours": impact["hours"] or 0,
        "featured_chapters": ParentBranch.objects.chapters().annotate(program_total=Count("programs"))[:6],
        "latest_programs": Program.objects.select_related("branch").order_by("-program_date", "-id")[:3],
        "latest_projects": published_projects.select_related("branch").order_by("-event_date", "-id")[:3],
        "latest_threads": Thread.objects.select_related("author", "category").annotate(reply_count=Count("replies")).order_by("-created_at")[:4],
    }
    return render(request, "home.html", context)


def about(request):
    return render(request, "about.html", {
        "years_active": years_active(),
        "page": AboutPage.load(),
    })

def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_message = form.save()
            try:
                mail_managers(
                    subject=f"Website contact: {contact_message.subject or contact_message.name}",
                    message=f"From: {contact_message.name} <{contact_message.email}>\n\n{contact_message.message}",
                    fail_silently=False,
                )
            except Exception:
                logger.exception("Failed to email contact message %s", contact_message.pk)
            messages.success(request, "Thank you! Your message has been sent. We will get back to you soon.")
            return redirect("contact")
        messages.error(request, "Please correct the errors in the form.")
    else:
        form = ContactForm()
    return render(request, "contact.html", {"form": form})


@require_POST
def newsletter_subscribe(request):
    form = NewsletterForm(request.POST)
    if form.is_valid():
        subscriber, created = NewsletterSubscriber.objects.get_or_create(email=form.cleaned_data["email"].lower())
        if not created and not subscriber.is_active:
            subscriber.is_active = True
            subscriber.save(update_fields=["is_active"])
        messages.success(request, "Thanks for subscribing to our newsletter!")
    else:
        messages.error(request, "Please enter a valid email address.")

    next_url = request.META.get("HTTP_REFERER", "")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = "/"
    return redirect(next_url)

def terms_conditions(request):
    return render(request, 'account/terms_conditions.html')  # Rendering the about page template

def privacy_policy(request):
    return render(request, 'account/privacy_policy.html')

def cookie(request):
    return render(request, 'account/cookie.html')

def donate_us(request):
    if request.method == "POST":
        form = DonationForm(request.POST, request.FILES)
        if form.is_valid():
            donation = form.save()
            try:
                mail_managers(
                    subject=f"New donation pledge: NPR {donation.amount} from {donation.full_name}",
                    message=(
                        f"{donation.full_name} <{donation.email}>, {donation.phone}\n"
                        f"Amount: NPR {donation.amount} via {donation.get_payment_method_display()}\n\n{donation.message}"
                    ),
                    fail_silently=False,
                )
            except Exception:
                logger.exception("Failed to email donation %s", donation.pk)
            messages.success(request, "Thank you for your generosity! We will confirm your donation once it is verified.")
            return redirect("donate_us")
        messages.error(request, "Please correct the errors in the form.")
    else:
        form = DonationForm(initial={"amount": request.GET.get("amount")})
    return render(request, "account/donate_us.html", {
        "form": form,
        "donation": settings.DONATION_DETAILS,
        "suggested_amounts": [500, 1000, 2500, 5000],
    })
