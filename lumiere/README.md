# Lumiere Clothing – E-Commerce Platform

COSC 612 / AIT 624 · Group 4

Lumiere is a full-stack clothing e-commerce web application built with **Python, Django, MySQL, HTML, CSS and JavaScript**. Customers can browse and search the catalog, choose a size and color, manage a cart, check out through an external payment service, and track their orders. Administrators manage products, stock and order status.

---

## Features by use case

| Use case | Where it lives |
|---|---|
| UC1 Register / Log In | `accounts/` – hashed passwords, generic login error, lock after 5 failed attempts, role-based admin access |
| UC2 Browse and Search Products | `catalog/views.py` – home page, keyword, category, size, color, price range, sort, pagination (no login needed) |
| UC3 View Product Details | `catalog/views.py` – photo, sizes, colors, stock per variant, "Add to cart" disabled when out of stock, related products |
| UC4 Manage Shopping Cart | `cart/services.py` – stock check, merge repeated adds, update/remove, subtotal, price-change notice |
| UC5 Place Order / Checkout | `orders/services.py` – atomic checkout with row locks; payment via `payments/gateway.py` |
| UC6 View Order History | `orders/views.py` – own orders only; other customers' orders return "Access denied" |
| UC8 Manage Product Catalog | Django admin – create/edit/deactivate products, upload product photos; products in past orders cannot be deleted |
| UC9 Manage Inventory | Django admin – edit stock per size/color variant |
| UC10 Manage Orders | Django admin – only valid status transitions; cancelling restores stock |

UC7 (Recommendations) has its database table in place; the recommendation engine is planned future work.

---

## Tools and technologies

| Component | Technology |
|---|---|
| Language | Python 3.9+ |
| Web framework | Django 4.2 – 5.2 |
| Database | MySQL 8.0 (via `mysqlclient`) |
| Frontend | Django templates, HTML, CSS, JavaScript, Bootstrap 5.3 (included locally in `static/vendor/`) |
| Images | Pillow (product photo uploads) |
| Payments | Built-in mock service, or Stripe API in test mode |
| Security | PBKDF2 password hashing, CSRF protection, role checks, parameterized ORM queries |

---

## Project structure

```
lumiere/
├── manage.py
├── requirements.txt
├── .env.example
├── lumiere/            settings.py, urls.py
├── accounts/           User (customer/admin role), Address, register/login/logout
├── catalog/            Category, Product, Variant, Recommendation, browse/search/detail
│   └── fixtures/seed_catalog.json   sample catalog (6 categories, 25 products, 278 variants)
├── cart/               Cart, CartItem, services.py (add_item, update_quantity, remove_item, calculate_subtotal)
├── orders/             Order, OrderItem, Payment, services.py (place_order, update_status), admin
├── payments/           gateway.py (submit_payment)
├── templates/          HTML pages (Bootstrap)
├── static/             css/style.css, img/ (banner, category tiles), vendor/ (Bootstrap)
└── media/products/     product photos (sample photos included)
```

Database tables created by the migrations: `users`, `addresses`, `categories`, `products`, `variants`, `carts`, `cart_items`, `orders`, `order_items`, `payments`, `recommendations` (plus Django's own auth/session tables).

---

## Setup

### 1. Prerequisites
- Python 3.9 or newer (the Mac built-in python3 works)
- MySQL Server 8.0 running locally
- **macOS only:** `brew install mysql-client pkg-config` before installing requirements
- **Linux only:** `sudo apt install python3-dev default-libmysqlclient-dev build-essential pkg-config`

### 2. Create and activate a virtual environment
```bash
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create the MySQL database
```bash
mysql -u root -p -e "CREATE DATABASE lumiere_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 5. Configure environment
Copy `.env.example` to `.env` and set `DB_PASSWORD` (and `DB_USER` if not root).

### 6. Create tables and an admin account
```bash
python manage.py migrate
python manage.py createsuperuser        # asks for email, name and password
```

### 7. Load the sample catalog
```bash
python manage.py loaddata seed_catalog.json
```

### 8. Run the app
```bash
python manage.py runserver
```
- Store home page: http://127.0.0.1:8000/
- Shop (search and filters): http://127.0.0.1:8000/shop/
- Admin: http://127.0.0.1:8000/admin/ (log in with the superuser email and password)

> No MySQL yet? For a quick look only, set `DB_ENGINE=sqlite` in `.env` and repeat steps 6–8. Use MySQL for the real project.

---

## Payments

Lumiere never receives or stores card numbers. At checkout the customer picks a **test payment method**, and only the provider reference and status are saved in the `payments` table.

| Test method | Result |
|---|---|
| Visa test card | Payment succeeds → order created, stock reduced, cart cleared |
| Declined test card | Payment declined → no order, stock unchanged, cart kept |
| Insufficient funds test card | Payment declined → no order, stock unchanged, cart kept |

- `PAYMENT_MODE=mock` (default) simulates the provider with no keys or internet.
- `PAYMENT_MODE=stripe` sends real API calls to Stripe **test mode**. Put your `sk_test_...` key in `STRIPE_SECRET_KEY`. Live keys are refused on purpose.

---

## Running the tests

87 automated tests cover the equivalence classes in the Testing section (Register/Log In, Browse/Search) plus cart, checkout and order status rules.

```bash
python manage.py test
```

Django creates a temporary `test_lumiere_db`, so the MySQL user needs permission to create databases. If yours does not, run them on SQLite instead:

```bash
# Windows (PowerShell)
$env:DB_ENGINE="sqlite"; python manage.py test
# macOS / Linux
DB_ENGINE=sqlite python manage.py test
```

---

## Screenshots for the report (Fig. 9–16)

| Figure | What to capture |
|---|---|
| Fig. 9 Successful database migration | Terminal output of `python manage.py migrate` |
| Fig. 10 MySQL tables in lumiere_db | `mysql -u root -p lumiere_db -e "SHOW TABLES;"` |
| Fig. 11 Product catalog with search and filters | Shop page with a category, price range and sort applied |
| Fig. 12 Product details with size and color | A product page after choosing a size and color |
| Fig. 13 Shopping cart page | Cart with two different items |
| Fig. 14 Checkout and order confirmation | The confirmation page after a successful test payment |
| Fig. 15 Customer order history | "My orders" page |
| Fig. 16 Administrator order management | Admin → Orders list (or an order's change page) |

---

## Product photos

The sample product photos come from the **Clothing Dataset** by Alexey Grigorev
(https://github.com/alexeygrigorev/clothing-dataset-small), released under **CC0 1.0** (public domain).
The backgrounds were removed and each garment was placed on a plain studio background.

To add or change a photo, open **Admin → Products**, pick a product and upload an image (portrait, about 4:5).
Products without a photo show a neutral placeholder.

---

## Troubleshooting

- **`mysqlclient` fails to install** – install the MySQL client libraries listed under Prerequisites, then retry. On Windows, use Python 3.11–3.13 so a prebuilt wheel is available.
- **`Access denied for user`** – check `DB_USER` / `DB_PASSWORD` in `.env`.
- **`Unknown database 'lumiere_db'`** – run step 4.
- **Admin page redirects to login** – customer accounts cannot open the admin site. Use the superuser account.
- **Pictures not showing** – keep `DJANGO_DEBUG=True` in `.env` while running locally; Django only serves the `media/` photos in debug mode.
- **`Cannot use ImageField because Pillow is not installed`** – run `pip install pillow`.
- **Account locked** – after 5 wrong passwords the login is locked for 15 minutes. An admin can unlock it under Admin → Users → "Unlock selected accounts".
