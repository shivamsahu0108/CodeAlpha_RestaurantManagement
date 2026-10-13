
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MenuItemViewSet,
    RestaurantTableViewSet,
    ReservationViewSet,
    InventoryItemViewSet,
    MenuItemIngredientViewSet,
    OrderViewSet,
    daily_sales_report,
)

router = DefaultRouter()
router.register("menu", MenuItemViewSet, basename="menu")
router.register("tables", RestaurantTableViewSet, basename="tables")
router.register("reservations", ReservationViewSet, basename="reservations")
router.register("inventory", InventoryItemViewSet, basename="inventory")
router.register("recipes", MenuItemIngredientViewSet, basename="recipes")
router.register("orders", OrderViewSet, basename="orders")

urlpatterns = [
    path("", include(router.urls)),
    path("reports/daily-sales/", daily_sales_report, name="daily-sales"),
]
