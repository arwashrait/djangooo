from django.contrib import admin

from .models import *

admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(Project)

admin.site.register(ProjectPicture)
admin.site.register(Donation)
admin.site.register(Comment)
admin.site.register(Rating)
# admin.site.register(Report)


