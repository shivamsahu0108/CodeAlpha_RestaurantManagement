
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class MenuItem(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    category = models.CharField(max_length=100, db_index=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class RestaurantTable(models.Model):
    table_number = models.PositiveIntegerField(unique=True)
    capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Table {self.table_number}"


class Reservation(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    customer_name = models.CharField(max_length=150)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    table = models.ForeignKey(
        RestaurantTable,
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    reservation_time = models.DateTimeField(db_index=True)
    guests = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CONFIRMED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer_name} - {self.reservation_time}"


class InventoryItem(models.Model):
    name = models.CharField(max_length=150, unique=True)
    unit = models.CharField(max_length=30)
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(0)],
        default=0,
    )
    low_stock_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(0)],
        default=0,
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"


class MenuItemIngredient(models.Model):
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name="ingredients",
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="menu_usages",
    )
    quantity_required = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["menu_item", "inventory_item"],
                name="unique_menu_item_ingredient",
            ),
            models.CheckConstraint(
                condition=Q(quantity_required__gt=0),
                name="ingredient_quantity_positive",
            ),
        ]

    def __str__(self):
        return f"{self.menu_item} - {self.inventory_item}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        PREPARING = "PREPARING", "Preparing"
        READY = "READY", "Ready"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    customer_name = models.CharField(max_length=150)
    table = models.ForeignKey(
        RestaurantTable,
        on_delete=models.PROTECT,
        related_name="orders",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restaurant_orders",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        
    )
    stock_deducted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    def __str__(self):
        return f"{self.menu_item} x {self.quantity}"
