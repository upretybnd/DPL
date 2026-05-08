from django.shortcuts import render
from web.models import Carousel, HomePageMedia
from branches.models import ParentBranch


def home(request):
    carousel_items = Carousel.objects.all()
    media_items = {item.key: item for item in HomePageMedia.objects.all()}
    context = {
        "carousel_items": carousel_items,
        "media_items": media_items,
        "branch_count": ParentBranch.objects.count(),
    }
    return render(request, "home.html", context)

def about(request):
    return render(request, 'about.html')  # Rendering the about page template

def contact(request):
    return render(request, 'contact.html')  # Rendering the about page template

def terms_conditions(request):
    return render(request, 'account/terms_conditions.html')  # Rendering the about page template

def privacy_policy(request):
    return render(request, 'account/privacy_policy.html')

def cookie(request):
    return render(request, 'account/cookie.html')

def donate_us(request):
    return render(request, 'account/donate_us.html')
