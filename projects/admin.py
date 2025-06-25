from django.contrib import admin

from .models import *

# admin.site.register(Category)
# admin.site.register(Tag)
# admin.site.register(Project)

# admin.site.register(ProjectPicture)
# admin.site.register(Donation)
# admin.site.register(Comment)
# admin.site.register(Rating)
# admin.site.register(Report)


# Inline for Project Pictures: Allows managing pictures directly from the Project admin page
class ProjectPictureInline(admin.TabularInline):
    model = ProjectPicture
    extra = 1  # Number of empty forms to display
    fields = ['image'] # Only 'image' is in your current ProjectPicture model

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    # Fields to display in the project list view
    list_display = (
        'title',
        'owner',
        'category',
        'total_target',
        'total_donations_collected', # Use the property name from models.py
        'percent_funded',           # Use the property name from models.py
        'end_time',
        'status',
        'is_featured',              # New field in Project model
        'created_at',
    )

    # Fields to enable filtering in the right sidebar
    list_filter = (
        'status',
        'is_featured',
        'category',
        'tags', # Allows filtering by tags
        'start_time',
        'end_time',
        'created_at',
    )

    # Fields to enable text search
    search_fields = (
        'title__icontains', # Case-insensitive search for title
        'details__icontains',
        'owner__username__icontains', # Search by owner's username
        'category__name__icontains',  # Search by category name
        'tags__name__icontains',      # Search by tag name
    )

    # Fields to use a raw input field (improves performance for many related objects)
    raw_id_fields = ('owner', 'category')

    # Add inlines to manage related pictures directly from the Project form
    inlines = [ProjectPictureInline]

    # Prepopulate slug field if you had one, but not needed here

    # Custom actions (optional)
    actions = ['make_featured', 'remove_featured', 'set_status_active', 'set_status_canceled']

    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, "Selected projects marked as featured.")
    make_featured.short_description = "Mark selected projects as featured"

    def remove_featured(self, request, queryset):
        queryset.update(is_featured=False)
        self.message_user(request, "Selected projects removed from featured.")
    remove_featured.short_description = "Remove selected projects from featured"

    def set_status_active(self, request, queryset):
        queryset.update(status='active')
        self.message_user(request, "Selected projects status set to active.")
    set_status_active.short_description = "Set status to Active"

    def set_status_canceled(self, request, queryset):
        queryset.update(status='canceled')
        self.message_user(request, "Selected projects status set to Canceled.")
    set_status_canceled.short_description = "Set status to Canceled"


# Register other models directly
admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(ProjectPicture) # Already linked via inline but can be standalone
admin.site.register(Donation)
admin.site.register(Comment)
admin.site.register(Rating)

# Register the concrete report models
@admin.register(ProjectReport)
class ProjectReportAdmin(admin.ModelAdmin):
    list_display = ('project', 'reporter', 'report_type', 'status', 'created_at')
    list_filter = ('status', 'report_type', 'created_at')
    search_fields = ('project__title', 'reporter__username', 'reason')
    raw_id_fields = ('project', 'reporter')
    readonly_fields = ('created_at',)

# @admin.register(CommentReport)
# class CommentReportAdmin(admin.ModelAdmin):
#     list_display = ('comment', 'reporter', 'report_type', 'status', 'created_at')
#     list_filter = ('status', 'report_type', 'created_at')
#     search_fields = ('comment__content', 'reporter__username', 'reason')
#     raw_id_fields = ('comment', 'reporter')
#     readonly_fields = ('created_at',)


