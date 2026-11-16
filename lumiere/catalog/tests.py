"""Use Cases 2 and 3 – Browse, search and product details. Mirrors Table 4."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Category, Product, Variant


class BrowseSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.jackets = Category.objects.create(name="Jackets", slug="jackets")
        cls.tees = Category.objects.create(name="T-Shirts", slug="t-shirts")
        cls.jacket = Product.objects.create(
            category=cls.jackets, name="Denim Trucker Jacket", description="Classic denim jacket",
            brand="Atelier North", price=Decimal("98.00"),
        )
        Variant.objects.create(product=cls.jacket, size="M", color="Indigo", stock_qty=5)
        cls.tee = Product.objects.create(
            category=cls.tees, name="Essential Crew Tee", description="Cotton crew tee",
            brand="Lumiere Basics", price=Decimal("22.00"),
        )
        Variant.objects.create(product=cls.tee, size="S", color="Black", stock_qty=10)
        cls.hidden = Product.objects.create(
            category=cls.jackets, name="Archive Denim Jacket", description="Old denim jacket",
            brand="Atelier North", price=Decimal("40.00"), active=False,
        )

    def browse(self, **params):
        return self.client.get(reverse("catalog:list"), params)

    def names(self, response):
        return [p.name for p in response.context["page_obj"]]

    # keyword
    def test_keyword_empty_shows_all_active(self):
        response = self.browse()
        self.assertCountEqual(self.names(response), ["Denim Trucker Jacket", "Essential Crew Tee"])

    def test_keyword_matching_valid(self):
        response = self.browse(q="denim jacket")
        self.assertEqual(self.names(response), ["Denim Trucker Jacket"])

    def test_keyword_no_match_shows_empty_message(self):
        response = self.browse(q="xyzabc")
        self.assertEqual(self.names(response), [])
        self.assertContains(response, "No products found")

    def test_keyword_too_long_invalid(self):
        response = self.browse(q="x" * 150)
        self.assertIn("Search keyword must be 100 characters or fewer.", response.context["form_errors"])

    def test_deactivated_products_never_returned(self):
        response = self.browse(q="Archive")
        self.assertEqual(self.names(response), [])

    # category
    def test_category_negative_invalid(self):
        response = self.browse(category="-2")
        self.assertIn("Select a valid category.", response.context["form_errors"])

    def test_category_text_invalid(self):
        response = self.browse(category="jackets")
        self.assertIn("Category must be a number.", response.context["form_errors"])

    def test_category_not_found_invalid(self):
        response = self.browse(category="999")
        self.assertIn("Category does not exist.", response.context["form_errors"])

    def test_category_valid(self):
        response = self.browse(category=str(self.jackets.pk))
        self.assertEqual(self.names(response), ["Denim Trucker Jacket"])

    # price range
    def test_min_price_negative_invalid(self):
        response = self.browse(min_price="-10.00")
        self.assertIn("Minimum price cannot be negative.", response.context["form_errors"])

    def test_min_price_text_invalid(self):
        response = self.browse(min_price="cheap")
        self.assertIn("Minimum price must be a number.", response.context["form_errors"])

    def test_max_below_min_invalid(self):
        response = self.browse(min_price="50.00", max_price="20.00")
        self.assertIn(
            "Invalid price range: the minimum price is greater than the maximum price.",
            response.context["form_errors"],
        )

    def test_price_range_valid(self):
        response = self.browse(min_price="20.00", max_price="80.00")
        self.assertEqual(self.names(response), ["Essential Crew Tee"])

    # sort
    def test_sort_unknown_invalid(self):
        response = self.browse(sort="rating_high")
        self.assertIn("Unknown sort option.", response.context["form_errors"])

    def test_sort_price_asc_valid(self):
        response = self.browse(sort="price_asc")
        self.assertEqual(self.names(response), ["Essential Crew Tee", "Denim Trucker Jacket"])

    def test_sort_price_desc_valid(self):
        response = self.browse(sort="price_desc")
        self.assertEqual(self.names(response), ["Denim Trucker Jacket", "Essential Crew Tee"])

    # filters by variant attributes
    def test_size_and_color_filters(self):
        self.assertEqual(self.names(self.browse(size="S")), ["Essential Crew Tee"])
        self.assertEqual(self.names(self.browse(color="indigo")), ["Denim Trucker Jacket"])

    # page
    def test_page_zero_invalid(self):
        response = self.browse(page="0")
        self.assertIn("Page number must be 1 or greater.", response.context["form_errors"])

    def test_page_beyond_last_invalid(self):
        response = self.browse(page="2")
        self.assertIn("Page 2 does not exist.", response.context["form_errors"])

    def test_page_valid(self):
        response = self.browse(page="1")
        self.assertEqual(response.context["form_errors"], [])

    def test_login_not_required(self):
        self.assertEqual(self.browse().status_code, 200)


class HomePageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name="Knitwear", slug="knitwear")
        cls.sweater = Product.objects.create(
            category=category, name="Merino Crew Sweater", description="Merino", brand="Atelier North",
            price=Decimal("88.00"), image="products/merino-crew-sweater.jpg",
        )
        Variant.objects.create(product=cls.sweater, size="M", color="Navy", stock_qty=3)
        Product.objects.create(
            category=category, name="Hidden Sweater", description="Old", brand="Atelier North",
            price=Decimal("40.00"), active=False,
        )

    def test_home_shows_categories_and_new_arrivals(self):
        response = self.client.get(reverse("catalog:home"))
        self.assertContains(response, "Shop by category")
        self.assertContains(response, "Knitwear")
        self.assertContains(response, "Merino Crew Sweater")
        self.assertNotContains(response, "Hidden Sweater")

    def test_product_photo_and_placeholder(self):
        self.assertEqual(self.sweater.image_url, "/media/products/merino-crew-sweater.jpg")
        no_photo = Product.objects.get(name="Hidden Sweater")
        self.assertTrue(no_photo.image_url.endswith("img/placeholder.svg"))


class ProductDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name="Shirts", slug="shirts")
        cls.product = Product.objects.create(
            category=category, name="Oxford Shirt", description="Cotton oxford", brand="Atelier North",
            price=Decimal("54.00"),
        )
        Variant.objects.create(product=cls.product, size="M", color="White", stock_qty=4)
        Variant.objects.create(product=cls.product, size="L", color="White", stock_qty=0)

    def test_detail_shows_variants_and_stock(self):
        response = self.client.get(reverse("catalog:detail", args=[self.product.pk]))
        self.assertContains(response, "Oxford Shirt")
        self.assertContains(response, "In stock")
        self.assertContains(response, "Out of stock")

    def test_deactivated_product_not_available(self):
        self.product.active = False
        self.product.save()
        response = self.client.get(reverse("catalog:detail", args=[self.product.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Product no longer available", status_code=404)

    def test_missing_product_not_available(self):
        response = self.client.get(reverse("catalog:detail", args=[9999]))
        self.assertEqual(response.status_code, 404)
