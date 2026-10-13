
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    MenuItem,
    RestaurantTable,
    Reservation,
    InventoryItem,
    MenuItemIngredient,
    Order,
)


class RestaurantAPITests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.staff = User.objects.create_user(
            username="restaurant_admin",
            password="TestPassword123!",
            is_staff=True,
        )
        self.customer = User.objects.create_user(
            username="customer",
            password="TestPassword123!",
        )

        self.client = APIClient()

        self.menu_item = MenuItem.objects.create(
            name="Veg Burger",
            description="Fresh vegetable burger",
            price=Decimal("120.00"),
            category="Fast Food",
        )

        self.table = RestaurantTable.objects.create(
            table_number=1,
            capacity=4,
        )

    def test_public_can_view_menu(self):
        response = self.client.get("/api/menu/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_non_staff_cannot_create_menu_item(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            "/api/menu/",
            {
                "name": "Pizza",
                "description": "Cheese pizza",
                "price": "200.00",
                "category": "Pizza",
                "is_available": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_staff_can_create_menu_item(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.post(
            "/api/menu/",
            {
                "name": "Pizza",
                "description": "Cheese pizza",
                "price": "200.00",
                "category": "Pizza",
                "is_available": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

    def test_public_can_create_reservation(self):
        future = timezone.now() + timedelta(days=1)

        response = self.client.post(
            "/api/reservations/",
            {
                "customer_name": "Test Customer",
                "customer_email": "customer@example.com",
                "customer_phone": "9999999999",
                "table": self.table.id,
                "reservation_time": future.isoformat(),
                "guests": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

    def test_order_confirmation_deducts_inventory(self):
        inventory = InventoryItem.objects.create(
            name="Burger Buns",
            unit="pieces",
            quantity=Decimal("10.000"),
            low_stock_threshold=Decimal("2.000"),
        )

        MenuItemIngredient.objects.create(
            menu_item=self.menu_item,
            inventory_item=inventory,
            quantity_required=Decimal("2.000"),
        )

        self.client.force_authenticate(user=self.staff)

        response = self.client.post(
            "/api/orders/",
            {
                "customer_name": "Test Customer",
                "table": self.table.id,
                "items": [
                    {
                        "menu_item": self.menu_item.id,
                        "quantity": 2,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        order_id = response.data["id"]

        self.assertEqual(
            response.data["total_amount"],
            "240.00",
        )

        response = self.client.patch(
            f"/api/orders/{order_id}/",
            {"status": "CONFIRMED"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        inventory.refresh_from_db()
        order = Order.objects.get(pk=order_id)

        self.assertEqual(inventory.quantity, Decimal("6.000"))
        self.assertTrue(order.stock_deducted)

    def test_insufficient_inventory_blocks_confirmation(self):
        inventory = InventoryItem.objects.create(
            name="Limited Cheese",
            unit="grams",
            quantity=Decimal("1.000"),
            low_stock_threshold=Decimal("0.000"),
        )

        MenuItemIngredient.objects.create(
            menu_item=self.menu_item,
            inventory_item=inventory,
            quantity_required=Decimal("2.000"),
        )

        self.client.force_authenticate(user=self.staff)

        response = self.client.post(
            "/api/orders/",
            {
                "customer_name": "Test Customer",
                "items": [
                    {
                        "menu_item": self.menu_item.id,
                        "quantity": 1,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        order_id = response.data["id"]

        response = self.client.patch(
            f"/api/orders/{order_id}/",
            {"status": "CONFIRMED"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        inventory.refresh_from_db()
        order = Order.objects.get(pk=order_id)

        self.assertEqual(inventory.quantity, Decimal("1.000"))
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertFalse(order.stock_deducted)
