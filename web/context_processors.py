from django.templatetags.static import static

from .models import HomePageMedia


def site_images(request):
    """Default background photo, managed in the admin under Landing page images."""
    cover = HomePageMedia.objects.filter(key="default_cover").first()
    return {"default_cover_url": cover.image.url if cover and cover.image else static("img/dpl1.jpg")}
