from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from decimal import Decimal
from unittest.mock import patch, MagicMock
from .models import Book, Category
from .scraper import scrape_category


def create_group(name):
    group, _ = Group.objects.get_or_create(name=name)
    return group


def create_user(username, group_name=None, password='testpass123'):
    user = User.objects.create_user(username=username, password=password)
    if group_name:
        grp = create_group(group_name)
        user.groups.add(grp)
    return user


class BookListViewTest(TestCase):
    """Any visitor (authenticated or not) can view the book list."""

    def setUp(self):
        self.client = Client()
        cat = Category.objects.create(name='Fiction', slug='fiction')
        Book.objects.create(title='Test Book', category=cat, price=Decimal('9.99'), description='A test book.')

    def test_book_list_anonymous(self):
        response = self.client.get(reverse('book_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'books/book_list.html')
        self.assertContains(response, 'Test Book')

    def test_book_list_filtered_by_category(self):
        cat = Category.objects.first()
        response = self.client.get(reverse('book_list'), {'category': cat.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Book')

    def test_book_list_search_by_title(self):
        response = self.client.get(reverse('book_list'), {'q': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Book')

    def test_book_list_search_no_match(self):
        response = self.client.get(reverse('book_list'), {'q': 'ZZZZZ'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Test Book')


class BookDetailViewTest(TestCase):
    def setUp(self):
        cat = Category.objects.create(name='Mystery', slug='mystery')
        self.book = Book.objects.create(
            title='The Hidden Secret', category=cat,
            price=Decimal('12.99'), description='Thrilling mystery.'
        )

    def test_book_detail_accessible(self):
        response = self.client.get(reverse('book_detail', args=[self.book.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The Hidden Secret')

    def test_book_detail_404_for_invalid_pk(self):
        response = self.client.get(reverse('book_detail', args=[9999]))
        self.assertEqual(response.status_code, 404)


class AddBookPermissionTest(TestCase):
    """Only Admins and SuperAdmins can add books."""

    def setUp(self):
        self.client = Client()
        self.cat = Category.objects.create(name='Art', slug='art')
        self.admin_user = create_user('admin_user', 'Admin')
        self.plain_user = create_user('plain_user')

    def test_admin_can_access_add_book_page(self):
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(reverse('add_book'))
        self.assertEqual(response.status_code, 200)

    def test_plain_user_cannot_access_add_book(self):
        self.client.login(username='plain_user', password='testpass123')
        response = self.client.get(reverse('add_book'))
        self.assertRedirects(response, reverse('book_list'))

    def test_anonymous_cannot_access_add_book(self):
        response = self.client.get(reverse('add_book'))
        self.assertRedirects(response, reverse('login'))

    def test_admin_can_post_new_book(self):
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.post(reverse('add_book'), {
            'title': 'New Admin Book',
            'category': self.cat.id,
            'price': '14.99',
            'description': 'Added by admin.',
        })
        self.assertRedirects(response, reverse('book_list'))
        self.assertTrue(Book.objects.filter(title='New Admin Book').exists())


class DeleteBookPermissionTest(TestCase):
    """Only SuperAdmins can delete books."""

    def setUp(self):
        self.client = Client()
        cat = Category.objects.create(name='Thriller', slug='thriller')
        self.book = Book.objects.create(
            title='Delete Me', category=cat, price=Decimal('5.00'), description='Test'
        )
        self.superadmin = create_user('superadmin_user', 'SuperAdmin')
        self.admin_user = create_user('admin_user', 'Admin')
        self.plain_user = create_user('plain_user')

    def test_superadmin_can_delete(self):
        self.client.login(username='superadmin_user', password='testpass123')
        response = self.client.post(reverse('delete_book', args=[self.book.pk]))
        self.assertRedirects(response, reverse('book_list'))
        self.assertFalse(Book.objects.filter(pk=self.book.pk).exists())

    def test_admin_cannot_delete(self):
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.post(reverse('delete_book', args=[self.book.pk]))
        self.assertRedirects(response, reverse('book_list'))
        self.assertTrue(Book.objects.filter(pk=self.book.pk).exists())

    def test_plain_user_cannot_delete(self):
        self.client.login(username='plain_user', password='testpass123')
        response = self.client.post(reverse('delete_book', args=[self.book.pk]))
        self.assertRedirects(response, reverse('book_list'))
        self.assertTrue(Book.objects.filter(pk=self.book.pk).exists())


class ScraperUnitTest(TestCase):
    """Unit tests for the scraper using mocked HTTP responses."""

    def _make_mock_html(self, books_html, has_next=False):
        next_btn = '<li class="next"><a href="page-2.html">next</a></li>' if has_next else ''
        return f"""
        <html><body>
            <ul><li class="next">{next_btn}</li></ul>
            <div class="col-sm-8 col-md-9">
                {books_html}
            </div>
        </body></html>
        """

    def _single_book_html(self, title='Test Title', price='12.99', rating='Three'):
        return f"""
        <article class="product_pod">
            <div class="image_container">
                <img src="../../media/cache/img.jpg" alt="{title}">
            </div>
            <p class="star-rating {rating}"></p>
            <h3><a href="../../catalogue/test-book/index.html" title="{title}">{title}</a></h3>
            <div class="product_price">
                <p class="price_color">£{price}</p>
            </div>
        </article>
        """

    @patch('books.scraper.requests.get')
    def test_scrape_returns_book_list(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = self._make_mock_html(self._single_book_html())
        mock_get.return_value = mock_resp

        books = scrape_category('fiction_10')
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]['title'], 'Test Title')
        self.assertEqual(books[0]['price'], Decimal('12.99'))
        self.assertEqual(books[0]['rating'], 'Three')

    @patch('books.scraper.requests.get')
    def test_scrape_returns_empty_on_404(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        books = scrape_category('nonexistent_99')
        self.assertEqual(books, [])

    @patch('books.scraper.requests.get')
    def test_scrape_handles_network_error(self, mock_get):
        import requests as req
        mock_get.side_effect = req.RequestException("Connection error")

        books = scrape_category('fiction_10')
        self.assertEqual(books, [])

    @patch('books.scraper.requests.get')
    @patch('books.scraper.get_book_description')
    def test_save_scraped_books_skips_duplicates(self, mock_desc, mock_get):
        from .scraper import save_scraped_books
        mock_desc.return_value = 'A great book.'
        cat = Category.objects.create(name='Fiction', slug='fiction')

        book_data = [{
            'title': 'Existing Book',
            'price': Decimal('9.99'),
            'rating': 'Four',
            'image_url': 'http://example.com/img.jpg',
            'source_url': 'http://example.com/book1',
        }]

        # First save: should create
        created, skipped = save_scraped_books(book_data, cat)
        self.assertEqual(created, 1)
        self.assertEqual(skipped, 0)

        # Second save: should skip (duplicate)
        created, skipped = save_scraped_books(book_data, cat)
        self.assertEqual(created, 0)
        self.assertEqual(skipped, 1)
