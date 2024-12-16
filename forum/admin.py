from django.contrib import admin
from .models import Category, Thread, Reply, UserProfile, WallPost, UserPostCount


# Register Category model
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

admin.site.register(Category, CategoryAdmin)

# Register Thread model
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'created_at', 'view_count',)
    list_filter = ('category', 'created_at', )
    search_fields = ('title', 'content')

admin.site.register(Thread, ThreadAdmin)

# Register Reply model
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('author', 'thread', 'created_at')
    list_filter = ('thread', 'author')
    search_fields = ('content',)

admin.site.register(Reply, ReplyAdmin)

# Register UserProfile model
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio', 'full_name','profile_picture', 'gender', 'custom_title')
    search_fields = ('user__username', 'bio')

admin.site.register(UserProfile, UserProfileAdmin)

# Register WallPost model
class WallPostAdmin(admin.ModelAdmin):
    list_display = ('author', 'receiver', 'content', 'created_at')
    list_filter = ('created_at', 'author', 'receiver')

admin.site.register(WallPost, WallPostAdmin)
class UserPostCountAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_count')  # Columns to display
    search_fields = ('user__username',)  # Enable search by username
    list_filter = ('total_count',)  # Filter by post count

# Register the model with the custom admin class
admin.site.register(UserPostCount, UserPostCountAdmin)
