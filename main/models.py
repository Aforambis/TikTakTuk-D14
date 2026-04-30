from django.db import models
import uuid

class Venue(models.Model):
    name = models.CharField(max_length=255)
    capacity = models.IntegerField()
    city = models.CharField(max_length=100)
    has_reserved = models.BooleanField(default=False)

class Event(models.Model):
    name = models.CharField(max_length=255)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    date = models.DateField()
    category = models.CharField(max_length=100) # e.g., 'Music', 'Education'

class TicketCategory(models.Model):
    event = models.ForeignKey(Event, related_name='categories', on_delete=models.CASCADE)
    name = models.CharField(max_length=100) # e.g., 'VIP', 'Reguler'
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quota = models.IntegerField()

class Order(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ("Lunas", "Lunas"),
        ("Pending", "Pending"),
        ("Dibatalkan", "Dibatalkan"),
    ]

    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="Pending",
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"Order {self.order_id} - {self.payment_status}"

class Promotion(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ("NOMINAL", "Nominal"),
        ("PERCENTAGE", "Persentase"),
    ]

    promotion_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promo_code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    usage_limit = models.IntegerField()

    def __str__(self):
        return self.promo_code

class OrderPromotion(models.Model):
    order_promotion_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        related_name='order_promotions',
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='order_promotions',
    )

    class Meta:
        unique_together = ('promotion', 'order')

    def __str__(self):
        return f"{self.promotion.promo_code} → {self.order.order_id}"