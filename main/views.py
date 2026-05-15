from __future__ import annotations

import secrets
import uuid
from collections import Counter
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .data import get_data


ALLOWED_ROLES = {"guest", "admin", "organizer", "customer"}
LOGIN_ROLES = {"admin", "organizer", "customer"}


# =========================================================
# Auth + role helpers
# =========================================================

def _authenticate_dummy_account(request, username: str, password: str):
    username = (username or "").strip()
    password = (password or "").strip()

    if not username or not password:
        return None

    data = get_data()
    credentials = data.get("user_credentials", {})
    registered_accounts = request.session.get("registered_accounts", {})
    credentials = {**credentials, **registered_accounts}

    # Username dibuat case-insensitive agar input seperti "Admin" tetap valid.
    for stored_username, account in credentials.items():
        if stored_username.lower() != username.lower():
            continue

        if account.get("password") != password:
            return None

        role = str(account.get("role", "customer")).strip().lower()
        if role not in LOGIN_ROLES:
            return None

        return {
            "username": stored_username,
            "role": role,
            "name": account.get("name") or stored_username,
        }

    return None



def _clear_auth_session(request):
    for key in ("role", "username", "display_name", "organizer_id", "customer_id"):
        request.session.pop(key, None)


def _username_exists(request, username: str) -> bool:
    username = (username or "").strip().lower()
    if not username:
        return False

    credentials = get_data().get("user_credentials", {})
    registered_accounts = request.session.get("registered_accounts", {})

    return any(stored_username.lower() == username for stored_username in credentials) or any(
        stored_username.lower() == username for stored_username in registered_accounts
    )

def login_view(request):
    if _current_role(request) in LOGIN_ROLES:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        account = _authenticate_dummy_account(request, username, password)

        if account:
            _clear_auth_session(request)
            request.session["role"] = account["role"]
            request.session["username"] = account["username"]
            request.session["display_name"] = account["name"]

            return redirect("dashboard")

        messages.error(request, "Username atau password salah.")

    return render(request, "main/login.html")



def _validate_registration_form(request):
    selected_role = (request.POST.get("role") or "customer").strip().lower()
    required_fields = ["role", "full_name", "email", "phone_number", "username"]
    password = request.POST.get("password", "")
    confirm_password = request.POST.get("confirm_password", "")
    terms = request.POST.get("terms")

    if selected_role not in LOGIN_ROLES:
        return selected_role, "Pilih role akun yang valid."

    if any(not (request.POST.get(field) or "").strip() for field in required_fields):
        return selected_role, "Harap mengisi semua field."

    username = request.POST.get("username", "").strip()
    if _username_exists(request, username):
        return selected_role, "Username sudah digunakan. Pilih username lain."

    if not password or not confirm_password:
        return selected_role, "Password dan konfirmasi password wajib diisi."

    if password != confirm_password:
        return selected_role, "Konfirmasi password tidak sesuai."

    if not terms:
        return selected_role, "Anda harus menyetujui Syarat & Ketentuan."

    return selected_role, None


def register_view(request):
    if _current_role(request) in LOGIN_ROLES:
        return redirect("dashboard")

    selected_role = (request.GET.get("role") or request.POST.get("role") or "customer").strip().lower()
    if selected_role not in LOGIN_ROLES:
        selected_role = "customer"

    if request.method == "POST":
        selected_role, error = _validate_registration_form(request)

        if error:
            messages.error(request, error)
        else:
            username = request.POST.get("username", "").strip()
            registered_accounts = request.session.get("registered_accounts", {})
            registered_accounts[username] = {
                "password": request.POST.get("password", ""),
                "role": selected_role,
                "name": request.POST.get("full_name", "").strip() or username,
            }
            request.session["registered_accounts"] = registered_accounts
            request.session.modified = True
            messages.success(request, "Registrasi berhasil. Silakan login dengan akun yang sudah dibuat.")
            return redirect("login")

    return render(
        request,
        "main/register.html",
        {
            "selected_role": selected_role,
        },
    )

def logout_view(request):
    _clear_auth_session(request)
    messages.info(request, "Anda berhasil logout.")
    return redirect("login")


def set_role(request, role_name: str):
    # Endpoint lama dipertahankan agar URL tidak error, tetapi tidak lagi
    # mengubah role secara langsung. Role hanya berubah lewat login.
    role_name = (role_name or "").strip().lower()

    if role_name not in ALLOWED_ROLES:
        return HttpResponseBadRequest(
            f"Invalid role '{role_name}'. Allowed: {', '.join(sorted(ALLOWED_ROLES))}"
        )

    current_role = _current_role(request)

    if role_name == current_role:
        return redirect(request.META.get("HTTP_REFERER", "/"))

    _clear_auth_session(request)

    if role_name == "guest":
        messages.info(request, "Anda sudah keluar dari akun. Mode guest aktif.")
        return redirect("landing_page")

    messages.info(request, f"Silakan login dengan akun {role_name} untuk memakai role tersebut.")
    return redirect("login")


def _current_role(request) -> str:
    role = str(request.session.get("role", "guest")).strip().lower()

    return role if role in ALLOWED_ROLES else "guest"


def _require_roles(request, allowed: set[str]):
    if _current_role(request) not in allowed:
        raise Http404()


def _get_current_user_for_dummy_pages(request):
    role = _current_role(request)

    if role == "guest":
        return {"role": "guest", "name": "Guest"}

    data = get_data()
    users = data.get("users", {})

    user = users.get(role, {"role": role, "name": request.session.get("display_name", role.title())}).copy()
    if request.session.get("display_name"):
        user["name"] = request.session.get("display_name")
    return user


def get_current_user(request):
    role = _current_role(request)

    if role == "guest":
        return {"role": "guest"}

    data = get_data()
    return data["users"].get(role, {"role": "guest"})


def landing_page(request):
    user = get_current_user(request)

    if user.get("role") != "guest":
        return redirect("dashboard")

    return render(
        request,
        "main/landing.html",
        {
            "role": "guest",
            "current_role": "guest",
            "current_page": "home",
        },
    )


def _get_current_organizer(request):
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
    from .models import Customer

    customer_id = request.session.get("customer_id")
    if customer_id:
        return get_object_or_404(Customer, customer_id=customer_id)

    customer = Customer.objects.order_by("full_name").first()
    if not customer:
        raise Http404("No customer data available. Create one via /admin.")

    request.session["customer_id"] = str(customer.customer_id)
    return customer


# =========================================================
# Dummy helpers for dashboard, seats, tickets
# =========================================================

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
    seat_lookup = {
        item["ticket_id"]: item["seat_id"]
        for item in data["has_relationship"]
    }
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
        return [
            row for row in rows
            if row.get("customer_id") == user.get("customer_id")
        ]

    if user["role"] == "organizer":
        return [
            row for row in rows
            if row.get("organizer_id") == user.get("organizer_id")
        ]

    return rows


# =========================================================
# Dashboard
# =========================================================

def dashboard(request):
    if _current_role(request) == "guest":
        return redirect("landing_page")

    data = get_data()
    user = _get_current_user_for_dummy_pages(request)
    ticket_rows = _filter_ticket_rows(_build_ticket_rows(data), user)

    if user["role"] == "admin":
        paid_orders = [
            o for o in data["orders"]
            if o["payment_status"] in {"Lunas", "Paid"}
        ]
        pending_orders = [
            o for o in data["orders"]
            if o["payment_status"] == "Pending"
        ]

        stats = [
            {
                "label": "Total User",
                "value": 12,
                "icon": "users",
                "trend": "12",
            },
            {
                "label": "Total Acara",
                "value": len(data["events"]),
                "icon": "calendar",
                "trend": "8",
            },
            {
                "label": "Omzet Platform",
                "value": "Rp {:.1f}M".format(
                    sum(o["total_amount"] for o in paid_orders) / 1_000_000
                ),
                "icon": "trending-up",
                "trend": "24",
            },
            {
                "label": "Promosi Aktif",
                "value": len(data["promotions"]),
                "icon": "tag",
            },
        ]

        context = {
            "user": user,
            "role": user["role"],
            "current_role": user["role"],
            "current_page": "dashboard",
            "stats": stats,
            "venue_count": len(data["venues"]),
            "reserved_venue_count": sum(
                1 for v in data["venues"]
                if v.get("has_reserved_seating")
            ),
            "event_count": len(data["events"]),
            "paid_order_count": len(paid_orders),
            "pending_order_count": len(pending_orders),
        }

    elif user["role"] == "organizer":
        own_events = [
            e for e in data["events"]
            if e["organizer_id"] == user["organizer_id"]
        ]
        own_orders = [
            o for o in data["orders"]
            if o["organizer_id"] == user["organizer_id"]
        ]
        paid_own = [
            o for o in own_orders
            if o["payment_status"] in {"Lunas", "Paid"}
        ]

        stats = [
            {
                "label": "Total Event",
                "value": len(own_events),
                "icon": "calendar",
            },
            {
                "label": "Tiket Terjual",
                "value": len(ticket_rows),
                "icon": "ticket",
            },
            {
                "label": "Revenue",
                "value": "Rp {:.1f}M".format(
                    sum(o["total_amount"] for o in paid_own) / 1_000_000
                ),
                "icon": "trending-up",
            },
            {
                "label": "Venue Aktif",
                "value": len({e["venue_id"] for e in own_events}),
                "icon": "map-pin",
            },
        ]

        context = {
            "user": user,
            "role": user["role"],
            "current_role": user["role"],
            "current_page": "dashboard",
            "stats": stats,
            "event_count": len(own_events),
            "recent_items": own_events,
        }

    else:
        own_orders = [
            o for o in data["orders"]
            if o["customer_id"] == user["customer_id"]
        ]

        stats = [
            {
                "label": "Tiket Saya",
                "value": len(ticket_rows),
                "icon": "ticket",
            },
            {
                "label": "Event Diikuti",
                "value": len({t["event_id"] for t in ticket_rows}),
                "icon": "music",
            },
            {
                "label": "Transaksi",
                "value": len(own_orders),
                "icon": "shopping-bag",
            },
            {
                "label": "Pengeluaran",
                "value": "Rp {:.1f}M".format(
                    sum(o["total_amount"] for o in own_orders) / 1_000_000
                ),
                "icon": "credit-card",
            },
        ]

        context = {
            "user": user,
            "role": user["role"],
            "current_role": user["role"],
            "current_page": "dashboard",
            "stats": stats,
            "recent_items": ticket_rows,
        }

    return render(request, "main/dashboard.html", context)


# =========================================================
# Seats
# =========================================================

def seats_page(request):
    _require_roles(request, {"admin", "organizer", "customer"})

    data = get_data()
    user = _get_current_user_for_dummy_pages(request)
    rows = _build_seat_rows(data)

    q = request.GET.get("q", "").strip().lower()
    status = request.GET.get("status", "")

    if q:
        rows = [
            r for r in rows
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
        "current_role": user["role"],
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


def create_seat(request):
    _require_roles(request, {"admin", "organizer"})
    return redirect("seats")


def update_seat(request, seat_id):
    _require_roles(request, {"admin", "organizer"})
    return redirect("seats")


def delete_seat(request, seat_id):
    _require_roles(request, {"admin", "organizer"})
    return redirect("seats")


# =========================================================
# Tickets
# =========================================================

def tickets_page(request):
    _require_roles(request, {"admin", "organizer", "customer"})

    data = get_data()
    user = _get_current_user_for_dummy_pages(request)
    rows = _filter_ticket_rows(_build_ticket_rows(data), user)

    q = request.GET.get("q", "").strip().lower()
    status_filter = request.GET.get("status_filter", "Semua")

    if q:
        rows = [
            r for r in rows
            if q in r["ticket_code"].lower()
            or q in r["event_title"].lower()
        ]

    if status_filter and status_filter != "Semua":
        rows = [
            r for r in rows
            if r.get("status") == status_filter
        ]

    all_rows_for_stats = _filter_ticket_rows(_build_ticket_rows(data), user)
    valid_count = sum(
        1 for r in all_rows_for_stats
        if r.get("status") == "Valid"
    )
    used_count = sum(
        1 for r in all_rows_for_stats
        if r.get("status") == "Used"
    )

    context = {
        "user": user,
        "role": user["role"],
        "current_role": user["role"],
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
    _require_roles(request, {"admin", "organizer"})
    return redirect("tickets")


def update_ticket(request, ticket_id):
    _require_roles(request, {"admin", "organizer"})
    return redirect("tickets")


def delete_ticket(request, ticket_id):
    _require_roles(request, {"admin", "organizer"})
    return redirect("tickets")


# =========================================================
# Event
# =========================================================

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
    artists = (
        EventArtist.objects.select_related("artist")
        .values("artist__artist_id", "artist__name")
        .distinct()
        .order_by("artist__name")
    )

    return render(
        request,
        "events/event_list.html",
        {
            "events": qs,
            "venues": venues,
            "artists": artists,
            "filter_form": form,
            "current_role": _current_role(request),
            "role": _current_role(request),
        },
    )


def my_events(request):
    _require_roles(request, {"admin", "organizer"})

    from .models import Event

    qs = Event.objects.select_related("venue", "organizer").order_by("-event_datetime")

    if _current_role(request) == "organizer":
        organizer = _get_current_organizer(request)
        qs = qs.filter(organizer=organizer)

    return render(
        request,
        "events/my_events.html",
        {
            "events": qs,
            "current_role": _current_role(request),
            "role": _current_role(request),
        },
    )


def event_create(request):
    _require_roles(request, {"admin", "organizer"})

    from .models import Event, Organizer, Venue

    if request.method == "POST":
        form = EventForm(request.POST)

        if form.is_valid():
            venue = get_object_or_404(
                Venue,
                venue_id=form.cleaned_data["venue_id"],
            )

            if _current_role(request) == "organizer":
                organizer = _get_current_organizer(request)
            else:
                organizer_id = form.cleaned_data.get("organizer_id")
                if organizer_id:
                    organizer = get_object_or_404(
                        Organizer,
                        organizer_id=organizer_id,
                    )
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
            "role": _current_role(request),
            "current_organizer": (
                _get_current_organizer(request)
                if _current_role(request) == "organizer"
                else None
            ),
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
            venue = get_object_or_404(
                Venue,
                venue_id=form.cleaned_data["venue_id"],
            )

            event.event_title = form.cleaned_data["event_title"]
            event.event_datetime = form.cleaned_data["event_datetime"]
            event.venue = venue

            if _current_role(request) == "admin":
                organizer_id = form.cleaned_data.get("organizer_id")
                if organizer_id:
                    event.organizer = get_object_or_404(
                        Organizer,
                        organizer_id=organizer_id,
                    )

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
            "role": _current_role(request),
            "current_organizer": (
                _get_current_organizer(request)
                if _current_role(request) == "organizer"
                else None
            ),
            "mode": "update",
            "event": event,
        },
    )


# =========================================================
# Venue
# =========================================================

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
        qs = qs.filter(
            Q(venue_name__icontains=q)
            | Q(address__icontains=q)
        )

    city = (form.cleaned_data.get("city") or "").strip()
    if city:
        qs = qs.filter(city__iexact=city)

    cities = (
        Venue.objects.values_list("city", flat=True)
        .distinct()
        .order_by("city")
    )

    can_manage = _current_role(request) in {"admin", "organizer"}

    return render(
        request,
        "venues/venue_list.html",
        {
            "venues": qs,
            "filter_form": form,
            "cities": cities,
            "can_manage": can_manage,
            "current_role": _current_role(request),
            "role": _current_role(request),
        },
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

    return render(
        request,
        "venues/venue_form.html",
        {
            "form": form,
            "mode": "create",
        },
    )


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
        {
            "form": form,
            "mode": "update",
            "venue": venue,
        },
    )


def venue_delete(request, venue_id):
    _require_roles(request, {"admin", "organizer"})

    from .models import Venue

    venue = get_object_or_404(Venue, venue_id=venue_id)

    if request.method == "POST":
        venue.delete()
        return redirect("venue_list")

    return render(
        request,
        "venues/venue_delete.html",
        {
            "venue": venue,
        },
    )


# =========================================================
# Artist
# =========================================================

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
        {
            "artists": artists,
            "can_manage": role == "admin",
            "current_role": role,
            "role": role,
        },
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

    return render(
        request,
        "artists/artist_form.html",
        {
            "form": form,
            "mode": "create",
        },
    )


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
        form = ArtistForm(
            initial={
                "name": artist.name,
                "genre": artist.genre,
            }
        )

    return render(
        request,
        "artists/artist_form.html",
        {
            "form": form,
            "mode": "update",
            "artist": artist,
        },
    )


def artist_delete(request, artist_id):
    _require_roles(request, {"admin"})

    from .models import Artist

    artist = get_object_or_404(Artist, artist_id=artist_id)

    if request.method == "POST":
        artist.delete()
        return redirect("artist_list")

    return render(
        request,
        "artists/artist_delete.html",
        {
            "artist": artist,
        },
    )


# =========================================================
# Orders + checkout
# =========================================================

class OrderFilterForm(forms.Form):
    status = forms.ChoiceField(
        required=False,
        choices=[
            ("", "Semua"),
            ("Paid", "Paid"),
            ("Pending", "Pending"),
            ("Cancelled", "Cancelled"),
        ],
    )
    q = forms.CharField(required=False, max_length=200)


class CheckoutForm(forms.Form):
    category_id = forms.UUIDField()
    quantity = forms.IntegerField(min_value=1, max_value=10)
    promo_code = forms.CharField(required=False, max_length=50)


def order_list(request):
    _require_roles(request, {"admin", "organizer", "customer"})

    from .models import Order

    form = OrderFilterForm(request.GET)
    form.is_valid()

    role = _current_role(request)
    qs = Order.objects.select_related("customer").order_by("-order_date")

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
        qs = qs.filter(
            Q(order_id__icontains=q) | Q(customer__full_name__icontains=q)
        )

    # Use separate base queryset for accurate summary (unaffected by search/filter)
    base_qs = Order.objects.select_related("customer")
    if role == "customer":
        base_qs = base_qs.filter(customer=_get_current_customer(request))
    elif role == "organizer":
        base_qs = base_qs.filter(
            tickets__category__event__organizer=_get_current_organizer(request)
        ).distinct()

    summary = base_qs.aggregate(
        total_orders=Count("order_id", distinct=True),
        paid_orders=Count(
            "order_id",
            filter=Q(payment_status="Paid"),
            distinct=True,
        ),
        pending_orders=Count(
            "order_id",
            filter=Q(payment_status="Pending"),
            distinct=True,
        ),
        total_revenue=Sum(
            "total_amount",
            filter=Q(payment_status="Paid"),
        ),
    )
    summary["total_revenue"] = summary["total_revenue"] or Decimal("0.00")

    return render(
        request,
        "orders/order_list.html",
        {
            "orders": qs,
            "summary": summary,
            "filter_form": form,
            "current_role": role,
            "role": role,
        },
    )


def orders_page(request):
    return order_list(request)


def update_order(request, order_id):
    _require_roles(request, {"admin"})

    from .models import Order

    order = get_object_or_404(Order, order_id=order_id)

    if request.method == "POST":
        new_status = request.POST.get("payment_status", "").strip()

        status_map = {
            "Lunas": "Paid",
            "Paid": "Paid",
            "Pending": "Pending",
            "Dibatalkan": "Cancelled",
            "Cancelled": "Cancelled",
        }

        if new_status in status_map:
            order.payment_status = status_map[new_status]
            order.save()
            messages.success(request, "Status order berhasil diperbarui.")

    return redirect("order_list")


def delete_order(request, order_id):
    _require_roles(request, {"admin"})

    from .models import Order

    order = get_object_or_404(Order, order_id=order_id)

    if request.method == "POST":
        order.delete()
        messages.success(request, "Order berhasil dihapus.")

    return redirect("order_list")


def checkout(request, event_id):
    _require_roles(request, {"customer"})

    from .models import Event, Order, OrderPromotion, Promotion, Ticket, TicketCategory

    event = get_object_or_404(
        Event.objects.select_related("venue", "organizer")
        .prefetch_related("ticket_categories"),
        event_id=event_id,
    )
    customer = _get_current_customer(request)
    categories = event.ticket_categories.order_by("category_name")

    if request.method == "POST":
        form = CheckoutForm(request.POST)

        if form.is_valid():
            category = get_object_or_404(
                TicketCategory,
                category_id=form.cleaned_data["category_id"],
                event=event,
            )

            qty = form.cleaned_data["quantity"]
            subtotal = (category.price or Decimal("0.00")) * qty
            discount = Decimal("0.00")
            promo_obj = None
            promo_code = (form.cleaned_data.get("promo_code") or "").strip()

            if promo_code:
                # Check 1: Promotion exists
                promo_obj = Promotion.objects.filter(
                    promo_code__iexact=promo_code,
                ).first()

                if not promo_obj:
                    messages.error(
                        request,
                        f'ERROR: Promotion dengan ID {promo_code} tidak ditemukan.',
                    )
                    return render(request, "orders/checkout.html", {
                        "event": event, "categories": categories, "form": form,
                        "current_role": _current_role(request), "role": _current_role(request),
                    })

                # Check 2: Usage limit not exceeded
                usage_count = OrderPromotion.objects.filter(promotion=promo_obj).count()
                if usage_count >= promo_obj.usage_limit:
                    messages.error(
                        request,
                        f'ERROR: Promotion "{promo_obj.promo_code}" telah mencapai batas maksimum penggunaan.',
                    )
                    return render(request, "orders/checkout.html", {
                        "event": event, "categories": categories, "form": form,
                        "current_role": _current_role(request), "role": _current_role(request),
                    })

                # Check 3: Event date within promotion period
                event_date = event.event_datetime.date()
                if not (promo_obj.start_date <= event_date <= promo_obj.end_date):
                    messages.error(
                        request,
                        f'ERROR: Promotion "{promo_obj.promo_code}" tidak berlaku untuk tanggal event ini.',
                    )
                    return render(request, "orders/checkout.html", {
                        "event": event, "categories": categories, "form": form,
                        "current_role": _current_role(request), "role": _current_role(request),
                    })

                # Apply discount
                if promo_obj.discount_type == "NOMINAL":
                    discount = min(Decimal(promo_obj.discount_value), subtotal)
                elif promo_obj.discount_type == "PERCENTAGE":
                    discount = (
                        subtotal * Decimal(promo_obj.discount_value) / Decimal("100")
                    ).quantize(Decimal("0.01"))
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
                tickets.append(Ticket(ticket_code=code, category=category, order=order))
            Ticket.objects.bulk_create(tickets)

            # Create OrderPromotion record if promo was used
            if promo_obj:
                OrderPromotion.objects.create(promotion=promo_obj, order=order)

            messages.success(request, "Pesanan berhasil dibuat!")
            return redirect("order_list")
    else:
        form = CheckoutForm()

    return render(
        request,
        "orders/checkout.html",
        {
            "event": event,
            "categories": categories,
            "form": form,
            "current_role": _current_role(request),
            "role": _current_role(request),
        },
    )


# =========================================================
# Promotions
# =========================================================

def _promo_type_to_db(value: str) -> str:
    value = (value or "").strip()

    if value in {"Persentase", "PERCENTAGE", "Percentage"}:
        return "PERCENTAGE"

    if value in {"Nominal", "NOMINAL"}:
        return "NOMINAL"

    return value


def _promo_type_to_label(value: str) -> str:
    if value == "PERCENTAGE":
        return "Persentase"

    if value == "NOMINAL":
        return "Nominal"

    return value or "-"


def promotions_page(request):
    from .models import OrderPromotion, Promotion

    role = _current_role(request)

    qs = Promotion.objects.order_by("-start_date", "promo_code")

    q = request.GET.get("q", "").strip()
    type_filter = request.GET.get("type_filter", "Semua").strip()

    if q:
        qs = qs.filter(promo_code__icontains=q)

    if type_filter and type_filter != "Semua":
        qs = qs.filter(discount_type=_promo_type_to_db(type_filter))

    # Real usage_count from OrderPromotion table
    usage_counts = {}
    for op in OrderPromotion.objects.values("promotion_id").annotate(cnt=Count("promotion_id")):
        usage_counts[str(op["promotion_id"])] = op["cnt"]

    rows = []
    for promo in qs:
        rows.append(
            {
                "promo_id": str(promo.promotion_id),
                "promo_code": promo.promo_code,
                "discount_type": _promo_type_to_label(promo.discount_type),
                "discount_value": promo.discount_value,
                "start_date": promo.start_date,
                "end_date": promo.end_date,
                "usage_limit": promo.usage_limit,
                "usage_count": usage_counts.get(str(promo.promotion_id), 0),
            }
        )

    all_promos = Promotion.objects.all()
    total_usage = OrderPromotion.objects.count()
    percentage_count = all_promos.filter(discount_type="PERCENTAGE").count()

    context = {
        "user": None,
        "role": role,
        "current_role": role,
        "current_page": "promosi",
        "page_title": "Manajemen Promosi",
        "rows": rows,
        "total_count": all_promos.count(),
        "total_usage": total_usage,
        "percentage_count": percentage_count,
        "q": q,
        "type_filter": type_filter,
    }

    return render(request, "main/promotions.html", context)


def create_promotion(request):
    _require_roles(request, {"admin"})

    from .models import Promotion

    if request.method == "POST":
        promo_code = request.POST.get("promo_code", "").strip().upper()
        discount_type = _promo_type_to_db(request.POST.get("discount_type", ""))
        discount_value = request.POST.get("discount_value", "0").strip()
        start_date = request.POST.get("start_date", "").strip()
        end_date = request.POST.get("end_date", "").strip()
        usage_limit = request.POST.get("usage_limit", "1").strip()

        errors = []

        if not promo_code:
            errors.append("Kode promo wajib diisi.")
        elif Promotion.objects.filter(promo_code=promo_code).exists():
            errors.append("Kode promo sudah digunakan.")

        if discount_type not in {"PERCENTAGE", "NOMINAL"}:
            errors.append("Tipe diskon tidak valid.")

        try:
            discount_value = Decimal(discount_value)
            if discount_value <= 0:
                raise ValueError
        except Exception:
            errors.append("Nilai diskon harus bilangan positif.")

        if not start_date:
            errors.append("Tanggal mulai wajib diisi.")

        if not end_date:
            errors.append("Tanggal berakhir wajib diisi.")

        try:
            usage_limit = int(usage_limit)
            if usage_limit <= 0:
                raise ValueError
        except Exception:
            errors.append("Batas penggunaan harus bilangan bulat positif.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            Promotion.objects.create(
                promo_code=promo_code,
                discount_type=discount_type,
                discount_value=discount_value,
                start_date=start_date,
                end_date=end_date,
                usage_limit=usage_limit,
            )
            messages.success(request, f"Promo {promo_code} berhasil dibuat.")

    return redirect("promotions")


def update_promotion(request, promo_id):
    _require_roles(request, {"admin"})

    from .models import Promotion

    promo = get_object_or_404(Promotion, promotion_id=promo_id)

    if request.method == "POST":
        promo_code = request.POST.get("promo_code", "").strip().upper()
        discount_type = _promo_type_to_db(request.POST.get("discount_type", ""))
        discount_value = request.POST.get("discount_value", "0").strip()
        start_date = request.POST.get("start_date", "").strip()
        end_date = request.POST.get("end_date", "").strip()
        usage_limit = request.POST.get("usage_limit", "1").strip()

        errors = []

        if not promo_code:
            errors.append("Kode promo wajib diisi.")
        elif Promotion.objects.filter(promo_code=promo_code).exclude(
            promotion_id=promo.promotion_id
        ).exists():
            errors.append("Kode promo sudah digunakan promo lain.")

        if discount_type not in {"PERCENTAGE", "NOMINAL"}:
            errors.append("Tipe diskon tidak valid.")

        try:
            discount_value = Decimal(discount_value)
            if discount_value <= 0:
                raise ValueError
        except Exception:
            errors.append("Nilai diskon harus bilangan positif.")

        try:
            usage_limit = int(usage_limit)
            if usage_limit <= 0:
                raise ValueError
        except Exception:
            errors.append("Batas penggunaan harus bilangan bulat positif.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            promo.promo_code = promo_code
            promo.discount_type = discount_type
            promo.discount_value = discount_value
            promo.start_date = start_date
            promo.end_date = end_date
            promo.usage_limit = usage_limit
            promo.save()

            messages.success(request, f"Promo {promo_code} berhasil diperbarui.")

    return redirect("promotions")


def delete_promotion(request, promo_id):
    _require_roles(request, {"admin"})

    from .models import Promotion

    promo = get_object_or_404(Promotion, promotion_id=promo_id)

    if request.method == "POST":
        promo.delete()
        messages.success(request, "Promo berhasil dihapus.")

    return redirect("promotions")


# =========================================================
# Ticket Categories from Pengguna_Hijau
# =========================================================

TICKET_CATEGORIES_MEMORY = None


def get_ticket_categories_memory():
    global TICKET_CATEGORIES_MEMORY

    if TICKET_CATEGORIES_MEMORY is None:
        TICKET_CATEGORIES_MEMORY = get_data()["ticket_categories"]

    return TICKET_CATEGORIES_MEMORY


@csrf_exempt
def category_page(request):
    data = get_data()
    user = get_current_user(request)

    categories_mem = get_ticket_categories_memory()
    error_message = None
    success_message = None

    if request.method == "POST":
        if user.get("role") != "admin":
            error_message = "Akses ditolak. Hanya Admin yang dapat mengelola kategori tiket."
        else:
            action = request.POST.get("action")

            if action == "hapus":
                category_id = request.POST.get("category_id")
                categories_mem[:] = [
                    cat for cat in categories_mem
                    if cat["category_id"] != category_id
                ]
                success_message = "Data kategori tiket berhasil dihapus."

            elif action in ["tambah", "edit"]:
                event_id = request.POST.get("event_id")
                category_name = request.POST.get("category_name")
                price_str = request.POST.get("price")
                quota_str = request.POST.get("quota")
                category_id = request.POST.get("category_id")

                if not event_id or not category_name or not price_str or not quota_str:
                    error_message = "Gagal. Seluruh field wajib diisi."
                else:
                    try:
                        price = int(price_str)
                        new_quota = int(quota_str)
                    except ValueError:
                        error_message = "Harga dan kuota harus berupa angka."
                    else:
                        if new_quota <= 0:
                            error_message = "Gagal. Kuota tiket harus lebih dari 0."
                        elif price < 0:
                            error_message = "Gagal. Harga tiket tidak boleh negatif."
                        else:
                            event = next(
                                (e for e in data["events"] if e["event_id"] == event_id),
                                None,
                            )
                            venue = None

                            if event:
                                venue = next(
                                    (v for v in data["venues"] if v["venue_id"] == event["venue_id"]),
                                    None,
                                )

                            venue_capacity = venue.get("capacity", 0) if venue else 0

                            current_event_quota = 0
                            for cat in categories_mem:
                                if cat["event_id"] == event_id:
                                    if action == "edit" and cat["category_id"] == category_id:
                                        continue
                                    current_event_quota += cat["quota"]

                            if current_event_quota + new_quota > venue_capacity:
                                venue_name = venue["venue_name"] if venue else "venue terkait"
                                error_message = (
                                    f"Gagal menyimpan. Total kuota tiket "
                                    f"({current_event_quota + new_quota}) melebihi kapasitas "
                                    f"{venue_name} ({venue_capacity} kursi)."
                                )

                if not error_message:
                    if action == "tambah":
                        categories_mem.append(
                            {
                                "category_id": str(uuid.uuid4()),
                                "category_name": category_name,
                                "event_id": event_id,
                                "price": price,
                                "quota": new_quota,
                            }
                        )
                        success_message = f"Kategori tiket '{category_name}' berhasil ditambahkan."

                    elif action == "edit":
                        for cat in categories_mem:
                            if cat["category_id"] == category_id:
                                cat["event_id"] = event_id
                                cat["category_name"] = category_name
                                cat["price"] = price
                                cat["quota"] = new_quota
                                break

                        success_message = f"Kategori tiket '{category_name}' berhasil diperbarui."

    event_map = {
        e["event_id"]: e["event_title"]
        for e in data["events"]
    }

    categories = []
    total_quota = 0
    max_price = 0

    for cat in categories_mem:
        item = cat.copy()
        item["event_name"] = event_map.get(cat["event_id"], "-")
        categories.append(item)

        total_quota += item["quota"]
        max_price = max(max_price, item["price"])

    categories.sort(
        key=lambda item: (
            item["event_name"].lower(),
            item["category_name"].lower(),
        )
    )

    return render(
        request,
        "main/ticket_categories.html",
        {
            "user": user,
            "role": user.get("role", "guest"),
            "current_role": user.get("role", "guest"),
            "current_page": "kategori",
            "page_title": "Kategori Tiket",
            "categories": categories,
            "events": data["events"],
            "total_quota": total_quota,
            "max_price": max_price,
            "error_message": error_message,
            "success_message": success_message,
        },
    )
