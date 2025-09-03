from django.contrib import admin

from .models import Location

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    search_fields = [
        'address',
    ]
    list_display = [
        'address',
        'lon',
        'lat',
    ]