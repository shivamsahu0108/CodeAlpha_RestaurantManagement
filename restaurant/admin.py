from django.contrib import admin
from .models import (
    MenuItem,
    RestaurantTable,
    Reservation,
    InventoryItem,
    MenuItemIngredient,
    Order,
    OrderItem,
)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_available")
    list_filter = ("category", "is_available")
    search_fields = ("name",)


@admin.register(RestaurantTable)
class RestaurantTableAdmin(admin.ModelAdmin):
    list_display = ("table_number", "capacity", "is_active")
    list_filter = ("is_active",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "customer_name",
        "table",
        "reservation_time",
        "guests",
        "status",
    )
    list_filter = ("status", "reservation_time")
    search_fields = ("customer_name", "customer_email")


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "quantity", "unit", "low_stock_threshold")
    search_fields = ("name",)


admin.site.register(MenuItemIngredient)
admin.site.register(Order)
admin.site.register(OrderItem)