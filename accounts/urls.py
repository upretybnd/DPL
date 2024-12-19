from django.urls import path
from . import views

urlpatterns = [
    path('sign-up/', views.sign_up, name='sign_up'),
    path('login/', views.login_view, name='login'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('logout/', views.logout, name='logout'),
    path('reset-password/<uidb64>/<token>/', views.reset_password, name='reset_password'),
    path('register-candidacy/', views.register_candidacy, name='register_candidacy'),

]
