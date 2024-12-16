from django.urls import path
from . import views

urlpatterns = [
        path('', views.category_list, name='category_list'),
        path('category/<int:category_id>/', views.category_threads, name='category_threads'),  # Modify category view
        path('thread/<int:thread_pk>/reply/', views.create_reply, name='create_reply'),
        path('user/<str:username>/', views.profile_view, name='profile_view'),
        path('thread/<int:thread_pk>/', views.thread_detail, name='thread_detail'),
        path('edit_thread/<int:thread_id>/', views.edit_thread, name='edit_thread'),
        path('edit_reply/<int:reply_id>/', views.edit_reply, name='edit_reply'),
        path('like_thread/<int:thread_id>/', views.like_thread, name='like_thread'),
        path('like_reply/<int:reply_id>/', views.like_reply, name='like_reply'),
        path('thread/edit/<int:thread_id>/', views.edit_thread, name='edit_thread'),
        path('reply/edit/<int:reply_id>/', views.edit_reply, name='edit_reply'),
        path('create/', views.create_thread, name='create_thread'),
        path('profile/<str:username>/', views.profile_view, name='profile'),  # Profile page URL


]