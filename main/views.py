from collections import Counter
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from .data import get_data, ORDERS, PROMOTIONS, HAS_RELATIONSHIP, TICKETS


# ─── Auth helpers ──────────────────────────────────────────────────────────────

def login_view(request):
    if request.session.get("active_role"):
        return redirect(reverse("main:dashboard"))

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        data = get_data()
        creds = data["user_credentials"]

        if username in creds and creds[username]["password"] == password:
            role = creds[username]["role"]
            request.session["active_role"] = role
            request.session["username"] = username
            return redirect(reverse("main:dashboard"))
        else:
            messages.error(request, "Username atau password salah.")

    return render(request, "main/login.html")


def logout_view(request):
    request.session.flush()
    return redirect(reverse("main:login"))


def get_current_user(request):
    role = request.session.get("active_role") or request.GET.get("role") or request.POST.get("role") or "admin"
    if role not in ["admin", "organizer", "customer"]:
        role = "admin"
    request.session["active_role"] = role
    return get_data()["users"][role]


def login_required_redirect(request):
    """Returns redirect response if not logged in, else None."""
    if not request.session.get("active_role"):
        return redirect(reverse("main:login"))
    return None


# ─── Seat / Ticket helpers ─────────────────────────────────────────────────────

def seat_status_map(data):
    used_ids = {item["seat_id"] for item in data["has_relationship"]}
    return {
        seat["seat_id"]: ("Terisi" if seat["seat_id"] in used_ids else "Tersedia")
        for seat in data["seats"]
    }


def build_seat_rows(data):
    status_map = seat_status_map(data)
    rows = []
    for seat in data["seats"]:
        seat = seat.copy()
        seat["status"] = status_map[seat["seat_id"]]
        rows.append(seat)
    return rows


def build_ticket_rows(data):
    seat_lookup = {item["ticket_id"]: item["seat_id"] for item in data["has_relationship"]}
    seats = {seat["seat_id"]: seat for seat in data["seats"]}
    rows = []

    for ticket in data["tickets"]:
        ticket = ticket.copy()
        seat_id = seat_lookup.get(ticket["ticket_id"])

        if seat_id and seat_id in seats:
            seat = seats[seat_id]
            ticket["seat_label"] = f'{seat["section"]} - Baris {seat["row_number"]}, No. {seat["seat_number"]}'
        else:
            ticket["seat_label"] = "Tanpa kursi"

        rows.append(ticket)
    return rows


def filter_ticket_rows(rows, user):
    if user["role"] == "customer":
        return [row for row in rows if row["customer_id"] == user["customer_id"]]
    if user["role"] == "organizer":
        return [row for row in rows if row["organizer_id"] == user["organizer_id"]]
    return rows


# ─── Dashboard ─────────────────────────────────────────────────────────────────

def dashboard(request):
    guard = login_required_redirect(request)
    if guard:
        return guard

    data = get_data()
    user = get_current_user(request)
    ticket_rows = filter_ticket_rows(build_ticket_rows(data), user)

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
            {"label": "Promosi Aktif", "value": len(data["promotions"]), "icon": "tag"},
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


# ─── Seats ─────────────────────────────────────────────────────────────────────

def seats_page(request):
    guard = login_required_redirect(request)
    if guard:
        return guard

    data = get_data()
    user = get_current_user(request)
    rows = build_seat_rows(data)

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

    all_rows = build_seat_rows(data)
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


def create_seat(request):
    return HttpResponseRedirect(reverse("main:seats") + f'?role={request.session.get("active_role", "admin")}')


def update_seat(request, seat_id):
    return HttpResponseRedirect(reverse("main:seats") + f'?role={request.session.get("active_role", "admin")}')


def delete_seat(request, seat_id):
    return HttpResponseRedirect(reverse("main:seats") + f'?role={request.session.get("active_role", "admin")}')


# ─── Tickets ───────────────────────────────────────────────────────────────────

def tickets_page(request):
    guard = login_required_redirect(request)
    if guard:
        return guard

    data = get_data()
    user = get_current_user(request)
    rows = filter_ticket_rows(build_ticket_rows(data), user)

    q = request.GET.get("q", "").strip().lower()
    status_filter = request.GET.get("status_filter", "Semua")

    if q:
        rows = [
            r for r in rows
            if q in r["ticket_code"].lower()
            or q in r["event_title"].lower()
        ]

    if status_filter and status_filter != "Semua":
        rows = [r for r in rows if r.get("status") == status_filter]

    all_rows_for_stats = filter_ticket_rows(build_ticket_rows(data), user)
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
    return HttpResponseRedirect(reverse("main:tickets") + f'?role={request.session.get("active_role", "admin")}')


def update_ticket(request, ticket_id):
    return HttpResponseRedirect(reverse("main:tickets") + f'?role={request.session.get("active_role", "admin")}')


def delete_ticket(request, ticket_id):
    return HttpResponseRedirect(reverse("main:tickets") + f'?role={request.session.get("active_role", "admin")}')


# ─── Orders ────────────────────────────────────────────────────────────────────

def _filter_orders(orders, user):
    """Filter orders based on role."""
    if user["role"] == "customer":
        return [o for o in orders if o["customer_id"] == user["customer_id"]]
    if user["role"] == "organizer":
        return [o for o in orders if o["organizer_id"] == user["organizer_id"]]
    return orders  # admin sees all


def orders_page(request):
    guard = login_required_redirect(request)
    if guard:
        return guard

    data = get_data()
    user = get_current_user(request)
    rows = _filter_orders(data["orders"], user)

    # Sort by order_date descending
    rows = sorted(rows, key=lambda o: o["order_date"], reverse=True)

    # Search & filter
    q = request.GET.get("q", "").strip().lower()
    status_filter = request.GET.get("status_filter", "Semua")

    if q:
        rows = [r for r in rows if q in r["order_id"].lower() or q in r["customer_name"].lower()]

    if status_filter and status_filter != "Semua":
        rows = [r for r in rows if r["payment_status"] == status_filter]

    all_rows = _filter_orders(data["orders"], user)
    paid_count = sum(1 for o in all_rows if o["payment_status"] == "Lunas")
    pending_count = sum(1 for o in all_rows if o["payment_status"] == "Pending")
    total_revenue = sum(o["total_amount"] for o in all_rows if o["payment_status"] == "Lunas")

    context = {
        "user": user,
        "role": user["role"],
        "current_page": "order",
        "page_title": "Daftar Order",
        "rows": rows,
        "total_count": len(all_rows),
        "paid_count": paid_count,
        "pending_count": pending_count,
        "total_revenue": total_revenue,
        "q": request.GET.get("q", ""),
        "status_filter": status_filter,
    }
    return render(request, "main/orders.html", context)


def update_order(request, order_id):
    guard = login_required_redirect(request)
    if guard:
        return guard

    user = get_current_user(request)
    if user["role"] != "admin":
        return redirect(reverse("main:orders"))

    if request.method == "POST":
        new_status = request.POST.get("payment_status", "").strip()
        valid_statuses = ["Lunas", "Pending", "Dibatalkan"]
        if new_status in valid_statuses:
            for order in ORDERS:
                if order["order_id"] == order_id:
                    order["payment_status"] = new_status
                    break
        messages.success(request, f"Status order {order_id} berhasil diperbarui.")

    return HttpResponseRedirect(reverse("main:orders"))


def delete_order(request, order_id):
    guard = login_required_redirect(request)
    if guard:
        return guard

    user = get_current_user(request)
    if user["role"] != "admin":
        return redirect(reverse("main:orders"))

    if request.method == "POST":
        global ORDERS
        ORDERS[:] = [o for o in ORDERS if o["order_id"] != order_id]
        messages.success(request, f"Order {order_id} berhasil dihapus.")

    return HttpResponseRedirect(reverse("main:orders"))


# ─── Promotions ────────────────────────────────────────────────────────────────

def promotions_page(request):
    # Promotions page is viewable by everyone (including guests not logged in)
    data = get_data()
    role = request.session.get("active_role", "")
    user = data["users"].get(role) if role else None

    promos = data["promotions"]

    q = request.GET.get("q", "").strip().lower()
    type_filter = request.GET.get("type_filter", "Semua")

    if q:
        promos = [p for p in promos if q in p["promo_code"].lower()]

    if type_filter and type_filter != "Semua":
        promos = [p for p in promos if p["discount_type"] == type_filter]

    all_promos = data["promotions"]
    total_usage = sum(p["usage_count"] for p in all_promos)
    percentage_count = sum(1 for p in all_promos if p["discount_type"] == "Persentase")

    context = {
        "user": user,
        "role": role,
        "current_page": "promosi",
        "page_title": "Manajemen Promosi",
        "rows": promos,
        "total_count": len(all_promos),
        "total_usage": total_usage,
        "percentage_count": percentage_count,
        "q": request.GET.get("q", ""),
        "type_filter": type_filter,
    }
    return render(request, "main/promotions.html", context)


def create_promotion(request):
    guard = login_required_redirect(request)
    if guard:
        return guard

    user = get_current_user(request)
    if user["role"] != "admin":
        return redirect(reverse("main:promotions"))

    if request.method == "POST":
        promo_code = request.POST.get("promo_code", "").strip().upper()
        discount_type = request.POST.get("discount_type", "").strip()
        discount_value = request.POST.get("discount_value", "0").strip()
        start_date = request.POST.get("start_date", "").strip()
        end_date = request.POST.get("end_date", "").strip()
        usage_limit = request.POST.get("usage_limit", "1").strip()

        # Validation
        errors = []
        if not promo_code:
            errors.append("Kode promo wajib diisi.")
        elif any(p["promo_code"] == promo_code for p in PROMOTIONS):
            errors.append("Kode promo sudah digunakan.")
        if discount_type not in ["Persentase", "Nominal"]:
            errors.append("Tipe diskon tidak valid.")
        try:
            discount_value = float(discount_value)
            if discount_value <= 0:
                raise ValueError
        except ValueError:
            errors.append("Nilai diskon harus bilangan positif.")
        if not start_date:
            errors.append("Tanggal mulai wajib diisi.")
        if not end_date:
            errors.append("Tanggal berakhir wajib diisi.")
        if start_date and end_date and end_date < start_date:
            errors.append("Tanggal berakhir harus sama dengan atau setelah tanggal mulai.")
        try:
            usage_limit = int(usage_limit)
            if usage_limit <= 0:
                raise ValueError
        except ValueError:
            errors.append("Batas penggunaan harus bilangan bulat positif.")

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            new_id = f"promo_{len(PROMOTIONS) + 1:03d}"
            PROMOTIONS.append({
                "promo_id": new_id,
                "promo_code": promo_code,
                "discount_type": discount_type,
                "discount_value": discount_value,
                "start_date": start_date,
                "end_date": end_date,
                "usage_limit": usage_limit,
                "usage_count": 0,
            })
            messages.success(request, f"Promo {promo_code} berhasil dibuat.")

    return redirect(reverse("main:promotions"))


def update_promotion(request, promo_id):
    guard = login_required_redirect(request)
    if guard:
        return guard

    user = get_current_user(request)
    if user["role"] != "admin":
        return redirect(reverse("main:promotions"))

    if request.method == "POST":
        promo_code = request.POST.get("promo_code", "").strip().upper()
        discount_type = request.POST.get("discount_type", "").strip()
        discount_value = request.POST.get("discount_value", "0").strip()
        start_date = request.POST.get("start_date", "").strip()
        end_date = request.POST.get("end_date", "").strip()
        usage_limit = request.POST.get("usage_limit", "1").strip()

        errors = []
        if not promo_code:
            errors.append("Kode promo wajib diisi.")
        else:
            # Allow same code for same promo
            duplicate = [p for p in PROMOTIONS if p["promo_code"] == promo_code and p["promo_id"] != promo_id]
            if duplicate:
                errors.append("Kode promo sudah digunakan promo lain.")
        if discount_type not in ["Persentase", "Nominal"]:
            errors.append("Tipe diskon tidak valid.")
        try:
            discount_value = float(discount_value)
            if discount_value <= 0:
                raise ValueError
        except ValueError:
            errors.append("Nilai diskon harus bilangan positif.")
        if not start_date:
            errors.append("Tanggal mulai wajib diisi.")
        if not end_date:
            errors.append("Tanggal berakhir wajib diisi.")
        if start_date and end_date and end_date < start_date:
            errors.append("Tanggal berakhir harus sama dengan atau setelah tanggal mulai.")
        try:
            usage_limit = int(usage_limit)
            if usage_limit <= 0:
                raise ValueError
        except ValueError:
            errors.append("Batas penggunaan harus bilangan bulat positif.")

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            for p in PROMOTIONS:
                if p["promo_id"] == promo_id:
                    p["promo_code"] = promo_code
                    p["discount_type"] = discount_type
                    p["discount_value"] = discount_value
                    p["start_date"] = start_date
                    p["end_date"] = end_date
                    p["usage_limit"] = usage_limit
                    break
            messages.success(request, f"Promo {promo_code} berhasil diperbarui.")

    return redirect(reverse("main:promotions"))


def delete_promotion(request, promo_id):
    guard = login_required_redirect(request)
    if guard:
        return guard

    user = get_current_user(request)
    if user["role"] != "admin":
        return redirect(reverse("main:promotions"))

    if request.method == "POST":
        global PROMOTIONS
        PROMOTIONS[:] = [p for p in PROMOTIONS if p["promo_id"] != promo_id]
        messages.success(request, "Promo berhasil dihapus.")

    return redirect(reverse("main:promotions"))