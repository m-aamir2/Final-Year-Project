from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Profile, 
    Proposal, 
    Meeting, 
    Announcement, 
    Phase1Submission, 
    Phase2Submission
)

# -----------------------------
# Profile Admin
# -----------------------------
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'semester', 'created_at', 'is_suspended')
    search_fields = ('user__username', 'user_type', 'phone')
    list_filter = ('user_type', 'is_suspended')
    ordering = ('-created_at',)


# -----------------------------
# Proposal Admin
# -----------------------------
@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ('title', 'submitted_by', 'submitted_at', 'status')
    list_filter = ('status', 'submitted_at')
    search_fields = ('title', 'description', 'submitted_by__username')
    filter_horizontal = ('group_members', 'supervisors')
    ordering = ('-submitted_at',)


# -----------------------------
# Meeting Admin
# -----------------------------
@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('title', 'supervisor', 'project', 'date_time', 'platform')
    list_filter = ('platform', 'date_time')
    search_fields = ('title', 'supervisor__username', 'project__title')
    ordering = ('-date_time',)


# -----------------------------
# Announcement Admin
# -----------------------------
@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'type',
        'post_date',
        'deadline',
        'created_by',
        'created_at',
        'file_preview',  # 👈 Add a column for file
    )
    list_filter = ('type', 'post_date')
    search_fields = ('title', 'message')
    ordering = ('-created_at',)

    def file_preview(self, obj):
        """Show file name or link in admin list."""
        if obj.file:
            # You can modify this to show file name or button style
            return format_html(
                '<a href="{}" target="_blank" style="color:#1e40af;font-weight:500;">📎 {}</a>',
                obj.file.url,
                obj.file.name.split('/')[-1]
            )
        return format_html('<span style="color:#9ca3af;">No file</span>')

    file_preview.short_description = "Attachment"


# -----------------------------
# Phase 1 Submission Admin
# -----------------------------
@admin.register(Phase1Submission)
class Phase1SubmissionAdmin(admin.ModelAdmin):
    list_display = ('title', 'submitted_by', 'submitted_at', 'status')
    list_filter = ('status', 'submitted_at')
    search_fields = ('title', 'submitted_by__username')
    ordering = ('-submitted_at',)


# -----------------------------
# Phase 2 Submission Admin
# -----------------------------
@admin.register(Phase2Submission)
class Phase2SubmissionAdmin(admin.ModelAdmin):
    list_display = ('title', 'submitted_by', 'submitted_at', 'status')
    list_filter = ('status', 'submitted_at')
    search_fields = ('title', 'submitted_by__username')
    ordering = ('-submitted_at',)
