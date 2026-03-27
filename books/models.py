from django.db import models

RATING_CHOICES = [
    ('One', 'One'),
    ('Two', 'Two'),
    ('Three', 'Three'),
    ('Four', 'Four'),
    ('Five', 'Five'),
]


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField(blank=True, default='')
    rating = models.CharField(max_length=10, choices=RATING_CHOICES, blank=True, default='')
    image_url = models.URLField(max_length=500, blank=True, default='')
    source_url = models.URLField(max_length=500, blank=True, null=True, default=None, unique=True)
    is_scraped = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def rating_stars(self):
        rating_map = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5}
        return '★' * rating_map.get(self.rating, 0) + '☆' * (5 - rating_map.get(self.rating, 0))