import uuid

from django.core.validators import DecimalValidator, MinValueValidator
from django.db import models
from django.db.models import CheckConstraint, F, Q, UniqueConstraint

class UserAccount(models.Model):
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)

    class Meta:
        db_table = "user_account"

    def __str__(self) -> str:
        return self.username

class Role(models.Model):
    role_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role_name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "role"

    def __str__(self) -> str:
        return self.role_name


class AccountRole(models.Model):
    account_role_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="account_roles")
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name="account_roles")

    class Meta:
        db_table = "account_role"
        constraints = [
            UniqueConstraint(fields=["role", "user"], name="uq_account_role_role_user"),
        ]


class Customer(models.Model):
    customer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    user = models.OneToOneField(
        UserAccount,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )

    class Meta:
        db_table = "customer"

    def __str__(self) -> str:
        return self.full_name


class Organizer(models.Model):
    organizer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizer_name = models.CharField(max_length=100)
    contact_email = models.CharField(max_length=100, blank=True, null=True)
    user = models.OneToOneField(
        UserAccount,
        on_delete=models.CASCADE,
        related_name="organizer_profile",
    )

    class Meta:
        db_table = "organizer"

    def __str__(self) -> str:
        return self.organizer_name


class Venue(models.Model):
    venue_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue_name = models.CharField(max_length=100)
    capacity = models.IntegerField(validators=[MinValueValidator(1)])
    address = models.TextField()
    city = models.CharField(max_length=100)

    class Meta:
        db_table = "venue"

    def __str__(self) -> str:
        return self.venue_name


class Seat(models.Model):
    seat_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.CharField(max_length=50)
    seat_number = models.CharField(max_length=10)
    row_number = models.CharField(max_length=10)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="seats")

    class Meta:
        db_table = "seat"
        constraints = [
            UniqueConstraint(
                fields=["venue", "section", "row_number", "seat_number"],
                name="uq_seat_venue_section_row_seatnum",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.venue.venue_name} - {self.section} {self.row_number}{self.seat_number}"


class Event(models.Model):
    event_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_datetime = models.DateTimeField()
    event_title = models.CharField(max_length=200)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="events")
    organizer = models.ForeignKey(Organizer, on_delete=models.CASCADE, related_name="events")

    class Meta:
        db_table = "event"

    def __str__(self) -> str:
        return self.event_title


class Artist(models.Model):
    artist_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    genre = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = "artist"

    def __str__(self) -> str:
        return self.name


class EventArtist(models.Model):
    event_artist_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="event_artists")
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="event_artists")
    role = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = "event_artist"
        constraints = [
            UniqueConstraint(fields=["event", "artist"], name="uq_event_artist_event_artist"),
        ]


class TicketCategory(models.Model):
    category_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category_name = models.CharField(max_length=50)
    quota = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
            DecimalValidator(max_digits=12, decimal_places=2),
        ],
    )
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="ticket_categories")

    class Meta:
        db_table = "ticket_category"

    def __str__(self) -> str:
        return f"{self.category_name} ({self.event.event_title})"


class Order(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = "Pending", "Pending"
        PAID = "Paid", "Paid"
        CANCELLED = "Cancelled", "Cancelled"

    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_date = models.DateTimeField()
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices)
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
            DecimalValidator(max_digits=12, decimal_places=2),
        ],
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")

    class Meta:
        db_table = "order"

    def __str__(self) -> str:
        return f"Order {self.order_id} - {self.payment_status}"


class Promotion(models.Model):
    class DiscountType(models.TextChoices):
        NOMINAL = "NOMINAL", "NOMINAL"
        PERCENTAGE = "PERCENTAGE", "PERCENTAGE"

    promotion_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promo_code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    discount_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(0.01),
            DecimalValidator(max_digits=12, decimal_places=2),
        ],
    )
    start_date = models.DateField()
    end_date = models.DateField()
    usage_limit = models.IntegerField(validators=[MinValueValidator(1)])

    class Meta:
        db_table = "promotion"
        constraints = [
            CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="ck_promotion_end_gte_start",
            ),
        ]

    def __str__(self) -> str:
        return self.promo_code


class OrderPromotion(models.Model):
    order_promotion_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name="order_promotions")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_promotions")

    class Meta:
        db_table = "order_promotion"
        constraints = [
            UniqueConstraint(fields=["promotion", "order"], name="uq_order_promotion_promotion_order"),
        ]

    def __str__(self) -> str:
        return f"{self.promotion.promo_code} → {self.order.order_id}"


class Ticket(models.Model):
    ticket_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_code = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(TicketCategory, on_delete=models.CASCADE, related_name="tickets")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tickets")

    class Meta:
        db_table = "ticket"

    def __str__(self) -> str:
        return self.ticket_code


class HasRelationship(models.Model):
    has_relationship_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name="seat_relationships")
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="seat_relationships")

    class Meta:
        db_table = "has_relationship"
        constraints = [
            UniqueConstraint(fields=["seat", "ticket"], name="uq_has_relationship_seat_ticket"),
            UniqueConstraint(fields=["seat"], name="uq_has_relationship_seat_once"),
        ]

    def __str__(self) -> str:
        return f"{self.seat} - {self.ticket.ticket_code}"