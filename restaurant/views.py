
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDate
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .models import (
    MenuItem,
    RestaurantTable,
    Reservation,
    InventoryItem,
    MenuItemIngredient,
    Order,
    OrderItem,
)
from .permissions import StaffWritePermission
from .serializers import (
    MenuItemSerializer,
    RestaurantTableSerializer,
    ReservationSerializer,
    InventoryItemSerializer,
    MenuItemIngredientSerializer,
    OrderSerializer,
    OrderCreateSerializer,
)


class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.all().order_by("name")
    serializer_class = MenuItemSerializer
    permission_classes = [StaffWritePermission]
    search_fields = ["name", "category", "description"]
    filterset_fields = ["category", "is_available"]
    ordering_fields = ["name", "price", "created_at"]


class RestaurantTableViewSet(viewsets.ModelViewSet):
    queryset = RestaurantTable.objects.all().order_by("table_number")
    serializer_class = RestaurantTableSerializer
    permission_classes = [IsAdminUser]


class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationSerializer

    def get_queryset(self):
        queryset = Reservation.objects.select_related("table").order_by(
            "-reservation_time"
        )
        if self.request.user.is_staff:
            return queryset
        return queryset.none()

    def get_permissions(self):
        if self.action == "create":
            return []
        return [IsAdminUser()]

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def cancel(self, request, pk=None):
        reservation = self.get_object()

        if reservation.status != Reservation.Status.CONFIRMED:
            return Response(
                {"detail": "Only confirmed reservations can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reservation.status = Reservation.Status.CANCELLED
        reservation.save(update_fields=["status"])

        return Response(
            ReservationSerializer(reservation).data,
            status=status.HTTP_200_OK,
        )


class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all().order_by("name")
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAdminUser]
    search_fields = ["name"]

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        items = self.get_queryset().filter(
            quantity__lte=F("low_stock_threshold")
        )
        return Response(self.get_serializer(items, many=True).data)


class MenuItemIngredientViewSet(viewsets.ModelViewSet):
    queryset = MenuItemIngredient.objects.select_related(
        "menu_item", "inventory_item"
    )
    serializer_class = MenuItemIngredientSerializer
    permission_classes = [IsAdminUser]


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related(
        "items__menu_item"
    ).select_related("table", "created_by").order_by("-created_at")
    serializer_class = OrderSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )


    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        order = self.get_object()

        if set(request.data.keys()) != {"status"}:
            return Response(
                {"detail": "Only the status field can be updated here."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_status = request.data["status"]

        allowed_transitions = {
            Order.Status.PENDING: [
                Order.Status.CONFIRMED,
                Order.Status.CANCELLED,
            ],
            Order.Status.CONFIRMED: [
                Order.Status.PREPARING,
                Order.Status.CANCELLED,
            ],
            Order.Status.PREPARING: [
                Order.Status.READY,
                Order.Status.CANCELLED,
            ],
            Order.Status.READY: [Order.Status.COMPLETED],
        }

        if new_status not in Order.Status.values:
            return Response(
                {"detail": "Invalid order status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status == order.status:
            return Response(OrderSerializer(order).data)

        if new_status not in allowed_transitions.get(order.status, []):
            return Response(
                {"detail": "Invalid status transition."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status == Order.Status.CONFIRMED and not order.stock_deducted:
            required = {}

            for item in order.items.all():
                for recipe in item.menu_item.ingredients.all():
                    inventory_id = recipe.inventory_item_id
                    required[inventory_id] = (
                        required.get(inventory_id, Decimal("0"))
                        + recipe.quantity_required * item.quantity
                    )

            inventory_items = {
                item.pk: item
                for item in InventoryItem.objects.select_for_update().filter(
                    pk__in=required.keys()
                )
            }

            for inventory_id, amount in required.items():
                inventory = inventory_items[inventory_id]
                if inventory.quantity < amount:
                    return Response(
                        {"detail": f"Insufficient stock for {inventory.name}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            for inventory_id, amount in required.items():
                inventory = inventory_items[inventory_id]
                inventory.quantity -= amount
                inventory.save(update_fields=["quantity", "updated_at"])

            order.stock_deducted = True

        elif new_status == Order.Status.CANCELLED and order.stock_deducted:
            required = {}

            for item in order.items.all():
                for recipe in item.menu_item.ingredients.all():
                    inventory_id = recipe.inventory_item_id
                    required[inventory_id] = (
                        required.get(inventory_id, Decimal("0"))
                        + recipe.quantity_required * item.quantity
                    )

            inventory_items = {
                item.pk: item
                for item in InventoryItem.objects.select_for_update().filter(
                    pk__in=required.keys()
                )
            }

            for inventory_id, amount in required.items():
                inventory = inventory_items[inventory_id]
                inventory.quantity += amount
                inventory.save(update_fields=["quantity", "updated_at"])

            order.stock_deducted = False

        order.status = new_status
        order.save(update_fields=["status", "stock_deducted"])

        return Response(OrderSerializer(order).data)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def daily_sales_report(request):
    if not request.user.is_staff:
        return Response(
            {"detail": "Staff access required."},
            status=status.HTTP_403_FORBIDDEN,
        )

    today = timezone.localdate()
    start = timezone.make_aware(
        timezone.datetime.combine(today, timezone.datetime.min.time())
    )
    end = start + timedelta(days=1)

    completed = Order.objects.filter(
        status=Order.Status.COMPLETED,
        created_at__gte=start,
        created_at__lt=end,
    )

    totals = completed.aggregate(
        total_sales=Sum("total_amount"),
        completed_orders=Count("id"),
    )

    return Response({
        "date": str(today),
        "completed_orders": totals["completed_orders"] or 0,
        "total_sales": totals["total_sales"] or Decimal("0.00"),
    })
