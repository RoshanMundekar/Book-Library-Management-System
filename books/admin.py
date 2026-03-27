from django.contrib import admin
from .models import Book, Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price', 'rating', 'is_scraped', 'created_at')
    list_filter = ('category', 'rating', 'is_scraped')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at', 'source_url', 'image_url')
