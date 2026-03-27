from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Book, Category
from .decorators import admin_required, superadmin_required, login_required_custom
from .scraper import scrape_category, save_scraped_books


# ─── Auth Views ────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('book_list')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('book_list')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'books/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')


# ─── Book Views ─────────────────────────────────────────────────────────────────

def book_list(request):
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    books = Book.objects.select_related('category').all()

    if query:
        books = books.filter(title__icontains=query)
    if category_id:
        books = books.filter(category_id=category_id)

    # Pagination — 12 books per page
    paginator = Paginator(books, 12)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    # Build query string without the page param (for filter links)
    query_params = request.GET.copy()
    query_params.pop('page', None)
    filter_querystring = query_params.urlencode()  # e.g. 'q=foo&category=2'

    categories = Category.objects.all()
    context = {
        'page_obj': page_obj,
        'books': page_obj.object_list,
        'total_count': paginator.count,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
        'filter_querystring': filter_querystring,
    }
    return render(request, 'books/book_list.html', context)


def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    return render(request, 'books/book_detail.html', {'book': book})


@admin_required
def add_book(request):
    categories = Category.objects.all()
    RATING_CHOICES = ['One', 'Two', 'Three', 'Four', 'Five']
    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        category_id = request.POST.get('category')
        price       = request.POST.get('price', '0')
        description = request.POST.get('description', '').strip()
        rating      = request.POST.get('rating', '').strip()
        image_url   = request.POST.get('image_url', '').strip()
        source_url  = request.POST.get('source_url', '').strip()

        if not title or not category_id or not price:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'books/add_book.html', {'categories': categories, 'rating_choices': RATING_CHOICES})

        category = get_object_or_404(Category, pk=category_id)
        Book.objects.create(
            title=title,
            category=category,
            price=price,
            description=description,
            rating=rating,
            image_url=image_url,
            source_url=source_url or None,  # store None instead of '' to avoid UNIQUE clash
            is_scraped=False,
        )
        messages.success(request, f'Book "{title}" added successfully.')
        return redirect('book_list')

    return render(request, 'books/add_book.html', {'categories': categories, 'rating_choices': RATING_CHOICES})


@admin_required
def update_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    categories = Category.objects.all()
    RATING_CHOICES = ['One', 'Two', 'Three', 'Four', 'Five']

    if request.method == 'POST':
        book.title       = request.POST.get('title', book.title).strip()
        book.price       = request.POST.get('price', book.price)
        book.description = request.POST.get('description', book.description).strip()
        book.rating      = request.POST.get('rating', book.rating).strip()
        book.image_url   = request.POST.get('image_url', book.image_url or '').strip()
        # Only update source_url if user submitted a non-empty value or it's unchanged
        new_source_url = request.POST.get('source_url', '').strip()
        book.source_url = new_source_url or None  # None avoids UNIQUE clash on blank
        category_id = request.POST.get('category')
        if category_id:
            book.category = get_object_or_404(Category, pk=category_id)
        book.save()
        messages.success(request, f'Book "{book.title}" updated successfully.')
        return redirect('book_detail', pk=book.pk)

    return render(request, 'books/update_book.html', {'book': book, 'categories': categories, 'rating_choices': RATING_CHOICES})


@superadmin_required
def delete_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        title = book.title
        book.delete()
        messages.success(request, f'Book "{title}" deleted successfully.')
        return redirect('book_list')
    return render(request, 'books/confirm_delete.html', {'book': book})


# ─── Scrape View ────────────────────────────────────────────────────────────────

SCRAPE_CATEGORIES = [
    ('travel_2', 'Travel'),
    ('mystery_3', 'Mystery'),
    ('historical-fiction_4', 'Historical Fiction'),
    ('sequential-art_5', 'Sequential Art'),
    ('classics_6', 'Classics'),
    ('philosophy_7', 'Philosophy'),
    ('romance_8', 'Romance'),
    ('fiction_10', 'Fiction'),
    ('childrens_11', 'Childrens'),
    ('science_13', 'Science'),
    ('science-fiction_16', 'Science Fiction'),
    ('fantasy_19', 'Fantasy'),
    ('art_25', 'Art'),
    ('psychology_26', 'Psychology'),
    ('autobiography_27', 'Autobiography'),
    ('humor_30', 'Humor'),
    ('horror_31', 'Horror'),
    ('history_32', 'History'),
    ('business_35', 'Business'),
    ('thriller_37', 'Thriller'),
]


@admin_required
def scrape_books(request):
    result = None
    if request.method == 'POST':
        category_slug = request.POST.get('category_slug', '')
        category_name = dict(SCRAPE_CATEGORIES).get(category_slug, category_slug)

        if not category_slug:
            messages.error(request, 'Please select a category to scrape.')
        else:
            # Get or create the Category object
            slug_key = category_slug.rsplit('_', 1)[0]  # e.g. 'travel' from 'travel_2'
            category_obj, _ = Category.objects.get_or_create(
                slug=slug_key,
                defaults={'name': category_name}
            )

            books_data = scrape_category(category_slug)
            created, updated, skipped = save_scraped_books(books_data, category_obj)
            result = {
                'category': category_name,
                'found': len(books_data),
                'created': created,
                'updated': updated,
                'skipped': skipped,
            }
            messages.success(
                request,
                f'Scraped "{category_name}": {created} new books added, {updated} images updated, {skipped} unchanged.'
            )

    return render(request, 'books/scrape.html', {
        'categories': SCRAPE_CATEGORIES,
        'result': result,
    })