from collections import Counter
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from .data import get_data


def get_current_user(request):
    role = request.GET.get("role") or request.POST.get("role") or request.session.get("active_role") or "admin"
    if role not in ["admin", "organizer", "customer"]:
        role = "admin"
    request.session["active_role"] = role
    return get_data()["users"][role]


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


def dashboard(request):
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


def tickets_page(request):
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


def create_seat(request):
    return HttpResponseRedirect(reverse("main:seats") + f'?role={request.session.get("active_role", "admin")}')


def update_seat(request, seat_id):
    return HttpResponseRedirect(reverse("main:seats") + f'?role={request.session.get("active_role", "admin")}')


def delete_seat(request, seat_id):
    return HttpResponseRedirect(reverse("main:seats") + f'?role={request.session.get("active_role", "admin")}')
