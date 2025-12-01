from django.contrib import admin
from .models import User, Profile, TemporaryUser, Tag, Post, Reply, Reaction, ReplyReaction
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'display_name', 'is_anonymous_by_default', 'created_at')
    search_fields = ('user__username', 'display_name')
    list_filter = ('is_anonymous_by_default',)

@admin.register(TemporaryUser)
class TemporaryUserAdmin(admin.ModelAdmin):
    list_display = ('token', 'display_name', 'created_at')
    search_fields = ('token', 'display_name')

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class ReplyInline(admin.TabularInline):
    model = Reply
    extra = 0
    readonly_fields = ('content', 'created_at')

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'post_type', 'author_display_name', 'created_at', 'hide_identity')
    list_filter = ('post_type', 'hide_identity', 'created_at')
    search_fields = ('title', 'description')
    autocomplete_fields = ('author', 'temp_author', 'tags', 'saved_by')
    inlines = [ReplyInline]

@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('post', 'author_display_name', 'created_at', 'hide_identity')
    search_fields = ('content',)
    list_filter = ('hide_identity', 'created_at')
    autocomplete_fields = ('post', 'author', 'temp_author')

@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'temp_user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('post__title', 'user__username', 'temp_user__display_name')

@admin.register(ReplyReaction)
class ReplyReactionAdmin(admin.ModelAdmin):
    list_display = ('reply', 'reaction', 'user', 'temp_user', 'created_at')
    list_filter = ('reaction', 'created_at')
    search_fields = ('reply__content', 'user__username', 'temp_user__display_name')


class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('email', 'full_name', 'is_staff')
    search_fields = ('email', 'full_name')
    ordering = ('email',)
    fieldsets = (
        (None, {"fields": ("email", "full_name", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "password1", "password2", "is_staff", "is_superuser"),
        }),
    )

admin.site.register(User, UserAdmin)
