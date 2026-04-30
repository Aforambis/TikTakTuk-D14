from __future__ import annotations

import secrets
from collections import Counter
from decimal import Decimal

from django import forms
from django.db.models import Count, Q, Sum
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .data import get_data


ALLOWED_ROLES = {"guest", "admin", "organizer", "customer"}


def set_role(request, role_name: str):
    role_name = (role_name or "").strip().lower()
    if role_name not in ALLOWED_ROLES:
        return HttpResponseBadRequest(
            f"Invalid role '{role_name}'. Allowed: {', '.join(sorted(ALLOWED_ROLES))}"
        )

    request.session["role"] = role_name
    return redirect(request.META.get("HTTP_REFERER", "/"))


def _current_role(request) -> str:
    role = (request.session.get("role") or "guest").strip().lower()
    return role if role in ALLOWED_ROLES else "guest"


def _require_roles(request, allowed: set[str]):
    if _current_role(request) not in allowed:
        raise Http404()


# ---------------------------------------------------------------------
# Dashboard + ticketing pages (dummy-data driven, UI-focused for TK03)
# ---------------------------------------------------------------------


def _get_current_user_for_dummy_pages(request):
    role = _current_role(request)
    # Dashboard/ticketing is meant for logged-in roles; keep it usable for demos.
    if role == "guest":
        role = "admin"

    data = get_data()
    return data["users"][role]


def _seat_status_map(data):
    used_ids = {item["seat_id"] for item in data["has_relationship"]}
    return {
        seat["seat_id"]: ("Terisi" if seat["seat_id"] in used_ids else "Tersedia")
        for seat in data["seats"]
    }


def _build_seat_rows(data):
    status_map = _seat_status_map(data)
    rows = []
    for seat in data["seats"]:
        seat = seat.copy()
        seat["status"] = status_map.get(seat["seat_id"], "Tersedia")
        rows.append(seat)
    return rows


def _build_ticket_rows(data):
    seat_lookup = {item["ticket_id"]: item["seat_id"] for item in data["has_relationship"]}
    seats = {seat["seat_id"]: seat for seat in data["seats"]}
    rows = []

    for ticket in data["tickets"]:
        ticket = ticket.copy()
        seat_id = seat_lookup.get(ticket["ticket_id"])

        if seat_id and seat_id in seats:
            seat = seats[seat_id]
            ticket["seat_label"] = (
                f'{seat["section"]} - Baris {seat["row_number"]}, No. {seat["seat_number"]}'
            )
        else:
            ticket["seat_label"] = "Tanpa kursi"

        rows.append(ticket)
    return rows


def _filter_ticket_rows(rows, user):
    if user["role"] == "customer":
        return [row for row in rows if row.get("customer_id") == user.get("customer_id")]
    if user["role"] == "organizer":
        return [row for row in rows if row.get("organizer_id") == user.get("organizer_id")]
    return rows


def dashboard(request):
    data = get_data()
    user = _get_current_user_for_dummy_pages(request)
    ticket_rows = _filter_ticket_rows(_build_ticket_rows(data), user)

    if user["role"] == "admin":
        paid_orders = [o for o in data["orders"] if o["payment_status"] == "Lunas"]
        pending_orders = [o for o in data["orders"] if o["payment_status"] == "Pending"]

        stats = [
            {"label": "Total User", "value": 12, "icon": "users", "trend": "12"},
            {"label": "Total Acara", "value": len(data["events"]), "icon": "calendar", "trend": "8"},
            {
                "label": "Omzet Platform",
                "value": "Rp {:.1f}M".format(sum(o["total_amount"] for o in paid_orders) / 1_000_000),
                "icon": "trending-up",
                "trend": "24",
            },
            {"label": "Promosi Aktif", "value": 3, "icon": "tag"},
        ]

        context = {
            "user": user,
            "role": user["role"],
            "current_page": "dashboard",
            "stats": stats,
            "venue_count": len(data["venues"]),
            "reserved_venue_count": sum(1 for v in data["venues"] if v.get("has_reserved_seating")),
            "event_count": len(data["events"]),
            "paid_order_count": len(paid_orders),
            "pending_order_count": len(pending_orders),
        }
    elif user["role"] == "organizer":
        own_events = [e for e in data["events"] if e["organizer_id"] == user["organizer_id"]]
        own_orders = [o for o in data["orders"] if o["organizer_id"] == user["organizer_id"]]
        paid_own = [o for o in own_orders if o["payment_status"] == "Lunas"]

        stats = [
            {"label": "Total Event", "value": len(own_events), "icon": "calendar"},
            {"label": "Tiket Terjual", "value": len(ticket_rows), "icon": "ticket"},
            {
                "label": "Revenue",
                "value": "Rp {:.1f}M".format(sum(o["total_amount"] for o in paid_own) / 1_000_000),
                "icon": "trending-up",
            },
            {"label": "Venue Aktif", "value": len({e["venue_id"] for e in own_events}), "icon": "map-pin"},
        ]

        context = {
            "user": user,
            "role": user["role"],
            "current_page": "dashboard",
            "stats": stats,
            "event_count": len(own_events),
            "recent_items": own_events,
        }
    else:  # customer
        own_orders = [o for o in data["orders"] if o["customer_id"] == user["customer_id"]]

        stats = [
            {"label": "Tiket Saya", "value": len(ticket_rows), "icon": "ticket"},
            {"label": "Event Diikuti", "value": len({t["event_id"] for t in ticket_rows}), "icon": "music"},
            {"label": "Transaksi", "value": len(own_orders), "icon": "shopping-bag"},
            {
                "label": "Pengeluaran",
                "value": "Rp {:.1f}M".format(sum(o["total_amount"] for o in own_orders) / 1_000_000),
                "icon": "credit-card",
            },
        ]

        context = {
            "user": user,
            "role": user["role"],
            "current_page": "dashboard",
            "stats": stats,
            "recent_items": ticket_rows,
        }

    return render(request, "main/dashboard.html", context)


def seats_page(request):
    data = get_data()
    user = _get_current_user_for_dummy_pages(request)
    rows = _build_seat_rows(data)

    q = request.GET.get("q", "").strip().lower()
    status = request.GET.get("status", "")

    if q:
        rows = [
            r
            for r in rows
            if q in r["section"].lower()
            or q in r["row_number"].lower()
            or q in r["seat_number"].lower()
            or q in r["venue_name"].lower()
        ]

    if status:
        rows = [r for r in rows if r["status"] == status]

    all_rows = _build_seat_rows(data)
    counts = Counter(r["status"] for r in all_rows)

    context = {
        "user": user,
        "role": user["role"],
        "current_page": "kursi",
        "page_title": "Manajemen Kursi",
        "rows": rows,
        "total_count": len(all_rows),
        "available_count": counts.get("Tersedia", 0),
        "used_count": counts.get("Terisi", 0),
        "q": request.GET.get("q", ""),
        "status": status,
        "all_venues": data["venues"],
    }
    return render(request, "main/seats.html", context)


def tickets_page(request):
    data = get_data()
    user = _get_current_user_for_dummy_pages(request)
    rows = _filter_ticket_rows(_build_ticket_rows(data), user)

    q = request.GET.get("q", "").strip().lower()
    status_filter = request.GET.get("status_filter", "Semua")

    if q:
        rows = [r for r in rows if q in r["ticket_code"].lower() or q in r["event_title"].lower()]

    if status_filter and status_filter != "Semua":
        rows = [r for r in rows if r.get("status") == status_filter]

    all_rows_for_stats = _filter_ticket_rows(_build_ticket_rows(data), user)
    valid_count = sum(1 for r in all_rows_for_stats if r.get("status") == "Valid")
    used_count = sum(1 for r in all_rows_for_stats if r.get("status") == "Used")

    context = {
        "user": user,
        "role": user["role"],
        "current_page": "tiket",
        "page_title": "Manajemen Tiket" if user["role"] != "customer" else "Tiket Saya",
        "rows": rows,
        "total_count": len(all_rows_for_stats),
        "valid_count": valid_count,
        "used_count": used_count,
        "q": request.GET.get("q", ""),
        "status_filter": status_filter,
        "all_orders": data["orders"],
        "all_categories": data["ticket_categories"],
    }
    return render(request, "main/tickets.html", context)


def create_ticket(request):
    return redirect("tickets")


def update_ticket(request, ticket_id):
    return redirect("tickets")


def delete_ticket(request, ticket_id):
    return redirect("tickets")


def create_seat(request):
    return redirect("seats")


def update_seat(request, seat_id):
    return redirect("seats")


def delete_seat(request, seat_id):
    return redirect("seats")


# ---------------------------------------------------------------------
# Yellow features (DB-backed)
# ---------------------------------------------------------------------
import secrets
from datetime import datetime
from decimal import Decimal

from django import forms
from django.db.models import Count, Q, Sum
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone


ALLOWED_ROLES = {"guest", "admin", "organizer", "customer"}


def set_role(request, role_name: str):
    role_name = (role_name or "").strip().lower()
    if role_name not in ALLOWED_ROLES:
        return HttpResponseBadRequest(
            f"Invalid role '{role_name}'. Allowed: {', '.join(sorted(ALLOWED_ROLES))}"
        )

    request.session["role"] = role_name

    # Send user back to where they came from (nice for manual testing).
    return redirect(request.META.get("HTTP_REFERER", "/"))


def _current_role(request) -> str:
    role = (request.session.get("role") or "guest").strip().lower()
    return role if role in ALLOWED_ROLES else "guest"


def _require_roles(request, allowed: set[str]):
    if _current_role(request) not in allowed:
        raise Http404()


def _get_current_organizer(request):
    """
    Lightweight session binding for organizer context:
    - if session has organizer_id, use it
    - else fall back to first organizer in DB (so pages are usable quickly)
    """

    from .models import Organizer

    organizer_id = request.session.get("organizer_id")
    if organizer_id:
        return get_object_or_404(Organizer, organizer_id=organizer_id)
    organizer = Organizer.objects.order_by("organizer_name").first()
    if not organizer:
        raise Http404("No organizer data available. Create one via /admin.")
    request.session["organizer_id"] = str(organizer.organizer_id)
    return organizer


def _get_current_customer(request):
    """
    Lightweight session binding for customer context.
    """

    from .models import Customer

    customer_id = request.session.get("customer_id")
    if customer_id:
        return get_object_or_404(Customer, customer_id=customer_id)
    customer = Customer.objects.order_by("full_name").first()
    if not customer:
        raise Http404("No customer data available. Create one via /admin.")
    request.session["customer_id"] = str(customer.customer_id)
    return customer


# -----------------------
# Events (R + CU)
# -----------------------


class EventFilterForm(forms.Form):
    venue = forms.UUIDField(required=False)
    artist = forms.UUIDField(required=False)
    q = forms.CharField(required=False, max_length=200)


class EventForm(forms.Form):
    event_title = forms.CharField(max_length=200)
    event_datetime = forms.DateTimeField(
        input_formats=["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"],
        help_text="Format: YYYY-MM-DD HH:MM",
    )
    venue_id = forms.UUIDField()
    organizer_id = forms.UUIDField(required=False)


def event_list(request):
    """
    R - Event (Semua role): list + filter by venue/artist.
    """

    from .models import Event, EventArtist, Venue

    form = EventFilterForm(request.GET)
    form.is_valid()

    qs = (
        Event.objects.select_related("venue", "organizer")
        .prefetch_related("ticket_categories")
        .order_by("-event_datetime")
    )

    q = (form.cleaned_data.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(event_title__icontains=q)
            | Q(event_artists__artist__name__icontains=q)
        ).distinct()

    venue_id = form.cleaned_data.get("venue")
    if venue_id:
        qs = qs.filter(venue_id=venue_id)

    artist_id = form.cleaned_data.get("artist")
    if artist_id:
        qs = qs.filter(event_artists__artist_id=artist_id).distinct()

    venues = Venue.objects.order_by("venue_name")
    artists = EventArtist.objects.select_related("artist").values(
        "artist__artist_id", "artist__name"
    ).distinct().order_by("artist__name")

    return render(
        request,
        "events/event_list.html",
        {
            "events": qs,
            "venues": venues,
            "artists": artists,
            "filter_form": form,
        },
    )


def my_events(request):
    """
    CU - Event (Admin & Organizer)
    - admin: sees all events
    - organizer: sees only their events (filtered by organizer_id)
    """

    _require_roles(request, {"admin", "organizer"})
    from .models import Event

    qs = Event.objects.select_related("venue", "organizer").order_by("-event_datetime")
    if _current_role(request) == "organizer":
        organizer = _get_current_organizer(request)
        qs = qs.filter(organizer=organizer)

    return render(request, "events/my_events.html", {"events": qs})


def event_create(request):
    _require_roles(request, {"admin", "organizer"})
    from .models import Event, Organizer, Venue

    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            venue = get_object_or_404(Venue, venue_id=form.cleaned_data["venue_id"])

            if _current_role(request) == "organizer":
                organizer = _get_current_organizer(request)
            else:
                organizer_id = form.cleaned_data.get("organizer_id")
                if organizer_id:
                    organizer = get_object_or_404(Organizer, organizer_id=organizer_id)
                else:
                    organizer = _get_current_organizer(request)

            Event.objects.create(
                event_title=form.cleaned_data["event_title"],
                event_datetime=form.cleaned_data["event_datetime"],
                venue=venue,
                organizer=organizer,
            )
            return redirect("my_events")
    else:
        initial = {}
        if _current_role(request) == "organizer":
            initial["organizer_id"] = _get_current_organizer(request).organizer_id
        form = EventForm(initial=initial)

    return render(
        request,
        "events/event_form.html",
        {
            "form": form,
            "venues": Venue.objects.order_by("venue_name"),
            "organizers": Organizer.objects.order_by("organizer_name"),
            "current_role": _current_role(request),
            "current_organizer": _get_current_organizer(request) if _current_role(request) == "organizer" else None,
            "mode": "create",
        },
    )


def event_update(request, event_id):
    _require_roles(request, {"admin", "organizer"})
    from .models import Event, Organizer, Venue

    event = get_object_or_404(Event, event_id=event_id)
    if _current_role(request) == "organizer":
        organizer = _get_current_organizer(request)
        if event.organizer_id != organizer.organizer_id:
            raise Http404()

    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            venue = get_object_or_404(Venue, venue_id=form.cleaned_data["venue_id"])
            event.event_title = form.cleaned_data["event_title"]
            event.event_datetime = form.cleaned_data["event_datetime"]
            event.venue = venue
            if _current_role(request) == "admin":
                organizer_id = form.cleaned_data.get("organizer_id")
                if organizer_id:
                    event.organizer = get_object_or_404(Organizer, organizer_id=organizer_id)
            event.save()
            return redirect("my_events")
    else:
        form = EventForm(
            initial={
                "event_title": event.event_title,
                "event_datetime": event.event_datetime,
                "venue_id": event.venue_id,
                "organizer_id": event.organizer_id,
            }
        )

    return render(
        request,
        "events/event_form.html",
        {
            "form": form,
            "venues": Venue.objects.order_by("venue_name"),
            "organizers": Organizer.objects.order_by("organizer_name"),
            "current_role": _current_role(request),
            "current_organizer": _get_current_organizer(request) if _current_role(request) == "organizer" else None,
            "mode": "update",
            "event": event,
        },
    )


# -----------------------
# Venues (R + CUD)
# -----------------------


class VenueForm(forms.Form):
    venue_name = forms.CharField(max_length=100)
    capacity = forms.IntegerField(min_value=1)
    address = forms.CharField(widget=forms.Textarea)
    city = forms.CharField(max_length=100)


class VenueFilterForm(forms.Form):
    q = forms.CharField(required=False, max_length=200)
    city = forms.CharField(required=False, max_length=100)


def venue_list(request):
    from .models import Venue

    form = VenueFilterForm(request.GET)
    form.is_valid()

    qs = Venue.objects.order_by("venue_name")
    q = (form.cleaned_data.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(venue_name__icontains=q) | Q(address__icontains=q))

    city = (form.cleaned_data.get("city") or "").strip()
    if city:
        qs = qs.filter(city__iexact=city)

    cities = Venue.objects.values_list("city", flat=True).distinct().order_by("city")

    can_manage = _current_role(request) in {"admin", "organizer"}
    return render(
        request,
        "venues/venue_list.html",
        {"venues": qs, "filter_form": form, "cities": cities, "can_manage": can_manage},
    )


def venue_create(request):
    _require_roles(request, {"admin", "organizer"})
    from .models import Venue

    if request.method == "POST":
        form = VenueForm(request.POST)
        if form.is_valid():
            Venue.objects.create(
                venue_name=form.cleaned_data["venue_name"],
                capacity=form.cleaned_data["capacity"],
                address=form.cleaned_data["address"],
                city=form.cleaned_data["city"],
            )
            return redirect("venue_list")
    else:
        form = VenueForm()

    return render(request, "venues/venue_form.html", {"form": form, "mode": "create"})


def venue_update(request, venue_id):
    _require_roles(request, {"admin", "organizer"})
    from .models import Venue

    venue = get_object_or_404(Venue, venue_id=venue_id)
    if request.method == "POST":
        form = VenueForm(request.POST)
        if form.is_valid():
            venue.venue_name = form.cleaned_data["venue_name"]
            venue.capacity = form.cleaned_data["capacity"]
            venue.address = form.cleaned_data["address"]
            venue.city = form.cleaned_data["city"]
            venue.save()
            return redirect("venue_list")
    else:
        form = VenueForm(
            initial={
                "venue_name": venue.venue_name,
                "capacity": venue.capacity,
                "address": venue.address,
                "city": venue.city,
            }
        )

    return render(
        request,
        "venues/venue_form.html",
        {"form": form, "mode": "update", "venue": venue},
    )


def venue_delete(request, venue_id):
    _require_roles(request, {"admin", "organizer"})
    from .models import Venue

    venue = get_object_or_404(Venue, venue_id=venue_id)
    if request.method == "POST":
        venue.delete()
        return redirect("venue_list")
    return render(request, "venues/venue_delete.html", {"venue": venue})


# -----------------------
# Artist CRUD (Admin only)
# -----------------------


class ArtistForm(forms.Form):
    name = forms.CharField(max_length=100)
    genre = forms.CharField(max_length=100, required=False)


def artist_list(request):
    from .models import Artist

    role = _current_role(request)
    artists = Artist.objects.order_by("name")
    return render(
        request,
        "artists/artist_list.html",
        {"artists": artists, "can_manage": role == "admin"},
    )


def artist_create(request):
    _require_roles(request, {"admin"})
    from .models import Artist

    if request.method == "POST":
        form = ArtistForm(request.POST)
        if form.is_valid():
            Artist.objects.create(
                name=form.cleaned_data["name"],
                genre=(form.cleaned_data.get("genre") or "").strip() or None,
            )
            return redirect("artist_list")
    else:
        form = ArtistForm()

    return render(request, "artists/artist_form.html", {"form": form, "mode": "create"})


def artist_update(request, artist_id):
    _require_roles(request, {"admin"})
    from .models import Artist

    artist = get_object_or_404(Artist, artist_id=artist_id)
    if request.method == "POST":
        form = ArtistForm(request.POST)
        if form.is_valid():
            artist.name = form.cleaned_data["name"]
            artist.genre = (form.cleaned_data.get("genre") or "").strip() or None
            artist.save()
            return redirect("artist_list")
    else:
        form = ArtistForm(initial={"name": artist.name, "genre": artist.genre})

    return render(
        request,
        "artists/artist_form.html",
        {"form": form, "mode": "update", "artist": artist},
    )


def artist_delete(request, artist_id):
    _require_roles(request, {"admin"})
    from .models import Artist

    artist = get_object_or_404(Artist, artist_id=artist_id)
    if request.method == "POST":
        artist.delete()
        return redirect("artist_list")
    return render(request, "artists/artist_delete.html", {"artist": artist})


# -----------------------
# Orders (R + Checkout)
# -----------------------


class OrderFilterForm(forms.Form):
    status = forms.ChoiceField(
        required=False,
        choices=[
            ("", "Semua"),
            ("Paid", "Lunas"),
            ("Pending", "Pending"),
            ("Cancelled", "Dibatalkan"),
        ],
    )
    q = forms.CharField(required=False, max_length=200)


class CheckoutForm(forms.Form):
    category_id = forms.UUIDField()
    quantity = forms.IntegerField(min_value=1, max_value=10)
    promo_code = forms.CharField(required=False, max_length=50)


def order_list(request):
    """
    R - Order (Semua role):
    - admin: all orders
    - organizer: orders filtered by events owned by organizer via ticket chain
    - customer: only their orders
    """

    _require_roles(request, {"admin", "organizer", "customer"})
    from .models import Order, Ticket

    form = OrderFilterForm(request.GET)
    form.is_valid()

    qs = Order.objects.select_related("customer").order_by("-order_date")

    role = _current_role(request)
    if role == "customer":
        customer = _get_current_customer(request)
        qs = qs.filter(customer=customer)
    elif role == "organizer":
        organizer = _get_current_organizer(request)
        qs = qs.filter(
            tickets__category__event__organizer=organizer
        ).distinct()

    status = form.cleaned_data.get("status") or ""
    if status:
        qs = qs.filter(payment_status=status)

    q = (form.cleaned_data.get("q") or "").strip()
    if q:
        qs = qs.filter(order_id__icontains=q)

    summary = qs.aggregate(
        total_orders=Count("order_id", distinct=True),
        paid_orders=Count("order_id", filter=Q(payment_status="Paid"), distinct=True),
        pending_orders=Count("order_id", filter=Q(payment_status="Pending"), distinct=True),
        total_revenue=Sum("total_amount", filter=Q(payment_status="Paid")),
    )
    summary["total_revenue"] = summary["total_revenue"] or Decimal("0.00")

    return render(
        request,
        "orders/order_list.html",
        {"orders": qs, "summary": summary, "filter_form": form},
    )


def checkout(request, event_id):
    """
    Customer checkout:
    - choose a ticket category + quantity (+ optional promo code)
    - creates Order (Pending) and Ticket rows
    """

    _require_roles(request, {"customer"})
    from .models import Event, Order, Promotion, Ticket, TicketCategory

    event = get_object_or_404(
        Event.objects.select_related("venue", "organizer").prefetch_related("ticket_categories"),
        event_id=event_id,
    )
    customer = _get_current_customer(request)

    categories = event.ticket_categories.order_by("category_name")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            category = get_object_or_404(
                TicketCategory, category_id=form.cleaned_data["category_id"], event=event
            )
            qty = form.cleaned_data["quantity"]
            subtotal = (category.price or Decimal("0.00")) * qty

            discount = Decimal("0.00")
            promo_code = (form.cleaned_data.get("promo_code") or "").strip()
            promo = None
            if promo_code:
                today = timezone.localdate()
                promo = Promotion.objects.filter(
                    promo_code__iexact=promo_code,
                    start_date__lte=today,
                    end_date__gte=today,
                ).first()
                if promo:
                    if promo.discount_type == "NOMINAL":
                        discount = min(Decimal(promo.discount_value), subtotal)
                    elif promo.discount_type == "PERCENTAGE":
                        discount = (subtotal * Decimal(promo.discount_value) / Decimal("100")).quantize(
                            Decimal("0.01")
                        )
                        discount = min(discount, subtotal)

            total = (subtotal - discount).quantize(Decimal("0.01"))

            order = Order.objects.create(
                order_date=timezone.now(),
                payment_status=Order.PaymentStatus.PENDING,
                total_amount=total,
                customer=customer,
            )

            tickets = []
            for _ in range(qty):
                code = f"TKT-{secrets.token_hex(4).upper()}"
                tickets.append(
                    Ticket(ticket_code=code, category=category, order=order)
                )
            Ticket.objects.bulk_create(tickets)

            return redirect("order_list")
    else:
        form = CheckoutForm()

    return render(
        request,
        "orders/checkout.html",
        {"event": event, "categories": categories, "form": form},
    )
