# 📚 Book Library Management System

A full-featured **Book Library Management System** built with Django 5.2, featuring role-based access control, web scraping, pagination, and a professional dark-themed UI powered by Tailwind CSS v3.

---

## 🖥️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11 · Django 5.2 |
| **Database** | SQLite (via Django ORM) |
| **Frontend** | Tailwind CSS v3 (CDN) · Vanilla JS |
| **Scraping** | `requests` · `BeautifulSoup4` |
| **Fonts** | Inter (Google Fonts) |
| **Auth** | Django built-in auth + Group-based RBAC |

---

## 🚀 Features

### 📖 Book Management (CRUD)
- Add books with title, category, price, and description
- View books in a responsive card grid (2–6 columns)
- Edit book details (Admin / Super Admin only)
- Delete books with confirmation (Super Admin only)
- Search books by title
- Filter books by category
- Paginated list — 12 books per page

### 🔐 Role-Based Access Control
| Feature | User | Admin | Super Admin |
|---|:---:|:---:|:---:|
| View books | ✅ | ✅ | ✅ |
| Add books | ❌ | ✅ | ✅ |
| Edit books | ❌ | ✅ | ✅ |
| Delete books | ❌ | ❌ | ✅ |
| Scrape books | ❌ | ✅ | ✅ |

### 🕷️ Web Scraping
- Scrapes live data from [books.toscrape.com](http://books.toscrape.com)
- 20 selectable categories (Travel, Mystery, Classics, etc.)
- Fetches up to 5 pages (~100 books) per scrape
- Auto-extracts: title, price, rating, cover image, description, source URL
- Duplicate detection via `source_url` uniqueness
- Updates existing records with missing images (upsert logic)
- Result dashboard: Found / Added / Updated / Skipped

### 🎨 UI/UX
- Professional dark theme with glassmorphism cards
- Gradient hero sections on Book List and Scrape pages
- Responsive hamburger navigation on mobile
- Role badge in navbar (User / Admin / Super Admin / Super Admin)
- Flash message system with auto-dismiss
- Hover action overlay on book cards (View / Edit / Delete)
- Split-screen login page with stats panel
- Multi-column footer with system status indicator

---

## 📁 Project Structure

```
Book_Library_Management_System/
└── library_system/
    ├── manage.py
    ├── db.sqlite3
    ├── library_system/
    │   ├── settings.py
    │   └── urls.py
    └── books/
        ├── models.py           # Book + Category models
        ├── views.py            # All CRUD, auth, and scrape views
        ├── urls.py             # App URL configuration
        ├── admin.py            # Django admin registration
        ├── decorators.py       # login_required, admin_required, superadmin_required
        ├── scraper.py          # scrape_category() + save_scraped_books()
        ├── tests.py            # 17 unit tests
        ├── migrations/
        ├── templates/books/
        │   ├── base.html           # Shared layout + navbar + footer
        │   ├── login.html          # Split-screen login
        │   ├── book_list.html      # Hero + grid + filter + pagination
        │   ├── book_detail.html    # Detail view with meta grid
        │   ├── add_book.html       # Add form
        │   ├── update_book.html    # Edit form
        │   ├── confirm_delete.html # Delete confirmation
        │   └── scrape.html         # Scraper UI + result stats
        ├── static/books/
        │   └── style.css           # Legacy CSS (now overridden by Tailwind)
        └── management/commands/
            └── setup_groups.py     # Creates SuperAdmin, Admin, User groups
```

---

## ⚙️ Setup & Installation

### 1. Prerequisites

- Anaconda with `djangopro` environment (Django 5.2 + requests + beautifulsoup4)

```bash
conda activate djangopro
```

### 2. Navigate to project

```bash
cd d:\jack_sparrow\Book_Library_Management_System\library_system
```

### 3. Apply migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create permission groups

```bash
python manage.py setup_groups
```

> Creates: `SuperAdmin`, `Admin`, `User` groups

### 5. Create a superuser

```bash
python manage.py createsuperuser
```

### 6. Run the development server

```bash
python manage.py runserver
```

Open → **http://127.0.0.1:8000/**

---

## 🔑 User Management

1. Log in at `/admin/` with your superuser credentials
2. Go to **Authentication → Users** → create new users
3. Assign each user to a group: `SuperAdmin`, `Admin`, or `User`

---

## 🌐 URL Routes

| URL | View | Access |
|---|---|---|
| `/` | Book list | Public |
| `/book/<id>/` | Book detail | Public |
| `/add/` | Add book | Admin+ |
| `/update/<id>/` | Edit book | Admin+ |
| `/delete/<id>/` | Delete book | Super Admin |
| `/scrape/` | Scrape page | Admin+ |
| `/login/` | Login page | Public |
| `/logout/` | Logout | Authenticated |

---

## 🧪 Running Tests

```bash
python manage.py test books -v 2
```

**17 tests — all passing:**

| Test Suite | Count | Coverage |
|---|---|---|
| `BookListViewTest` | 4 | Search, filter, anonymous access |
| `BookDetailViewTest` | 2 | Valid pk, 404 on invalid |
| `AddBookPermissionTest` | 4 | Admin can add, User/Anonymous blocked |
| `DeleteBookPermissionTest` | 3 | SuperAdmin can delete, Admin/User blocked |
| `ScraperUnitTest` | 4 | Mocked HTTP, duplicate skip, network error |

---

## 🕷️ Scraping Details

### How It Works

1. User selects a category from the dropdown on `/scrape/`
2. `scrape_category(slug)` fetches up to 5 pages from `books.toscrape.com`
3. For each book article, extracts:
   - Title, price, star rating, cover image URL (via `urljoin` for correct absolute URLs), source URL
4. `save_scraped_books()` upserts to DB:
   - **New book** → full create with description fetched from detail page
   - **Existing book with blank image** → updates `image_url` only
   - **Complete duplicate** → skipped
5. Result card shows: Found / Added / Updated / Skipped counts

### Available Categories (20)
Travel, Mystery, Historical Fiction, Sequential Art, Classics, Philosophy, Romance, Womens Fiction, Fiction, Childrens, Religion, Nonfiction, Music, Science Fiction, Sports And Games, Add A Comment, Fantasy, New Adult, Young Adult, Science

---

## 📊 Data Models

### `Category`
| Field | Type | Notes |
|---|---|---|
| `name` | CharField | e.g. "Mystery" |
| `slug` | SlugField | URL-safe identifier |

### `Book`
| Field | Type | Notes |
|---|---|---|
| `title` | CharField | Book title |
| `category` | ForeignKey | → Category |
| `price` | DecimalField | In GBP (£) |
| `rating` | CharField | One / Two / Three / Four / Five |
| `description` | TextField | Optional |
| `image_url` | URLField | Cover image (scraped) |
| `source_url` | URLField | Unique — source page link |
| `is_scraped` | BooleanField | True if auto-imported |
| `created_at` | DateTimeField | Auto timestamp |
| `updated_at` | DateTimeField | Auto timestamp |

---

## 🔧 Key Settings

```python
# library_system/settings.py
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:8000', 'http://localhost:8000']
```

---

## 📝 License

This project is built for educational purposes. Book data is scraped from [books.toscrape.com](http://books.toscrape.com), a safe sandbox scraping website.
