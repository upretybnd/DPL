# apps/website/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact-us/', views.contact, name='contact'),
    path('donate-us/', views.donate_us, name ='donate_us'),
    path('terms-&-conditions/', views.terms_conditions, name ='terms_conditions'),
    path('privacy-policy/', views.privacy_policy, name ='privacy_policy'),
    path('cookie/', views.cookie, name='cookie')

] # Define your URL pattern here