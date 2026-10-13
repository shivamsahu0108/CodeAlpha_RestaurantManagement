from django.db import transaction
from rest_framework import serializers

from .models import (
    MenuItem,
    RestaurantTable,
    Reservation,
    InventoryItem,
    MenuItemIngredient,
    Order,
    OrderItem,
)


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class RestaurantTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantTable
        fields = "__all__"
        read_only_fields = ("id",)


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = "__all__"
        read_only_fields = ("id", "created_at", "status")

    def validate(self, attrs):
        from datetime import timedelta
        from django.utils import timezone

        table = attrs.get("table", getattr(self.instance, "table", None))
        start = attrs.get(
            "reservation_time",
            getattr(self.instance, "reservation_time", None),
        )
        guests = attrs.get("guests", getattr(self.instance, "guests", None))

        if start and start < timezone.now():
            raise serializers.ValidationError(
                {"reservation_time": "Reservation must be in the future."}
            )

        if table and guests and guests > table.capacity:
            raise serializers.ValidationError(
                {"guests": "Guest count exceeds table capacity."}
            )

        if table and start:
            end = start + timedelta(hours=2)
            overlapping = Reservation.objects.filter(
                table=table,
                status=Reservation.Status.CONFIRMED,
                reservation_time__lt=end,
                reservation_time__gt=start - timedelta(hours=2),
            )
            if self.instance:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            if overlapping.exists():
                raise serializers.ValidationError(
                    {"table": "This table is already reserved near that time."}
                )

        if table and not table.is_active:
            raise serializers.ValidationError(
                {"table": "This table is not active."}
            )

        return attrs


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = "__all__"
        read_only_fields = ("id", "updated_at")


class MenuItemIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItemIngredient
        fields = "__all__"
        read_only_fields = ("id",)


class OrderItemReadSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(
        source="menu_item.name",
        read_only=True,
    )

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "menu_item",
            "menu_item_name",
            "quantity",
            "unit_price",
            "subtotal",
        )


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemReadSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "customer_name",
            "table",
            "created_by",
            "status",
            "total_amount",
            "items",
            "created_at",
        )
        read_only_fields = fields


class OrderCreateItemSerializer(serializers.Serializer):
    menu_item = serializers.PrimaryKeyRelatedField(
        queryset=MenuItem.objects.filter(is_available=True)
    )
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=150)
    table = serializers.PrimaryKeyRelatedField(
        queryset=RestaurantTable.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    items = OrderCreateItemSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        table = attrs.get("table")
        if table and not table.is_active:
            raise serializers.ValidationError(
                {"table": "This table is not active."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        order = Order.objects.create(
            customer_name=validated_data["customer_name"],
            table=validated_data.get("table"),
            created_by=request.user if request.user.is_authenticated else None,
        )

        total = 0
        for item in validated_data["items"]:
            menu_item = item["menu_item"]
            quantity = item["quantity"]
            price = menu_item.price
            subtotal = price * quantity

            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=quantity,
                unit_price=price,
                subtotal=subtotal,
            )
            total += subtotal

        order.total_amount = total
        order.save(update_fields=["total_amount"])
        return order
