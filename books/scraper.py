import requests
from bs4 import BeautifulSoup
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

BASE_URL = "http://books.toscrape.com"

RATING_MAP = {
    'One': 'One', 'Two': 'Two', 'Three': 'Three', 'Four': 'Four', 'Five': 'Five'
}


def scrape_category(category_slug, max_pages=5):
    """
    Scrape books from a specific category on books.toscrape.com.
    Returns a list of dicts with: title, price, rating, image_url, source_url, genre.
    max_pages limits pagination to avoid huge imports.
    """
    books = []
    page = 1
    category_url = f"{BASE_URL}/catalogue/category/books/{category_slug}/index.html"

    while page <= max_pages:
        if page == 1:
            url = category_url
        else:
            url = f"{BASE_URL}/catalogue/category/books/{category_slug}/page-{page}.html"

        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                break
        except requests.RequestException:
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.select('article.product_pod')

        if not articles:
            break

        for article in articles:
            try:
                title_tag = article.select_one('h3 a')
                title = title_tag['title'] if title_tag else 'Unknown'

                price_text = article.select_one('.price_color').text.strip()
                price_text = price_text.replace('£', '').replace('Â', '').strip()
                try:
                    price = Decimal(price_text)
                except InvalidOperation:
                    price = Decimal('0.00')

                rating_class = article.select_one('.star-rating')
                rating_word = rating_class['class'][1] if rating_class else 'One'
                rating = RATING_MAP.get(rating_word, 'One')

                img_tag = article.select_one('img')
                img_src = img_tag['src'] if img_tag else ''
                img_src = urljoin(url, img_src) if img_src else ''

                href = title_tag['href'] if title_tag else ''
                source_url = urljoin(url, href) if href else ''

                books.append({
                    'title': title,
                    'price': price,
                    'rating': rating,
                    'image_url': img_src,
                    'source_url': source_url,
                })
            except Exception:
                continue

        # Check for next page
        next_btn = soup.select_one('li.next a')
        if next_btn:
            page += 1
        else:
            break

    return books


def get_book_description(book_url):
    """Fetch the description from an individual book page."""
    try:
        response = requests.get(book_url, timeout=10)
        if response.status_code != 200:
            return ''
        soup = BeautifulSoup(response.text, 'html.parser')
        desc_tag = soup.select_one('#product_description ~ p')
        return desc_tag.text.strip() if desc_tag else ''
    except requests.RequestException:
        return ''


def save_scraped_books(books_data, category_obj):
    """
    Upsert scraped books into the database.
    - Creates new books for unknown source_urls.
    - Updates image_url / rating on existing records if they are blank/broken.
    Returns (created_count, updated_count, skipped_count).
    """
    from .models import Book

    created = 0
    updated = 0
    skipped = 0

    for data in books_data:
        source_url = data.get('source_url', '')
        if not source_url:
            skipped += 1
            continue

        new_image = data.get('image_url', '')
        new_rating = data.get('rating', '')

        existing = Book.objects.filter(source_url=source_url).first()
        if existing:
            # Patch missing/broken image_url or rating without a full re-scrape
            needs_save = False
            if new_image and (not existing.image_url or not existing.image_url.startswith('http')):
                existing.image_url = new_image
                needs_save = True
            if new_rating and not existing.rating:
                existing.rating = new_rating
                needs_save = True
            if needs_save:
                existing.save(update_fields=['image_url', 'rating', 'updated_at'])
                updated += 1
            else:
                skipped += 1
            continue

        description = get_book_description(source_url)

        Book.objects.create(
            title=data['title'],
            category=category_obj,
            price=data['price'],
            rating=new_rating,
            image_url=new_image,
            source_url=source_url,
            description=description,
            is_scraped=True,
        )
        created += 1

    return created, updated, skipped
