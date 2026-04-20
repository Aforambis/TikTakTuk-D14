from collections import Counter
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from .data import get_data


def get_current_user(request):
    role = request.GET.get("role") or request.session.get("active_role") or "admin"
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
        stats = [
            {"label": "Total User", "value": 12},
            {"label": "Total Venue", "value": len(data["venues"])},
            {"label": "Total Revenue", "value": f'Rp {sum(o["total_amount"] for o in data["orders"]):,}'.replace(",", ".")},
            {"label": "Total Organizer", "value": 2},
        ]
        recent_items = data["orders"]

    elif user["role"] == "organizer":
        own_events = [e for e in data["events"] if e["organizer_id"] == user["organizer_id"]]
        own_orders = [o for o in data["orders"] if o["organizer_id"] == user["organizer_id"]]

        stats = [
            {"label": "Total Event", "value": len(own_events)},
            {"label": "Tiket Terjual", "value": len(ticket_rows)},
            {"label": "Revenue", "value": f'Rp {sum(o["total_amount"] for o in own_orders):,}'.replace(",", ".")},
            {"label": "Venue Aktif", "value": len({e["venue_id"] for e in own_events})},
        ]
        recent_items = own_events

    else:
        own_orders = [o for o in data["orders"] if o["customer_id"] == user["customer_id"]]

        stats = [
            {"label": "Tiket Saya", "value": len(ticket_rows)},
            {"label": "Event Diikuti", "value": len({t["event_id"] for t in ticket_rows})},
            {"label": "Transaksi", "value": len(own_orders)},
            {"label": "Pengeluaran", "value": f'Rp {sum(o["total_amount"] for o in own_orders):,}'.replace(",", ".")},
        ]
        recent_items = own_orders

    context = {
        "user": user,
        "stats": stats,
        "recent_items": recent_items,
        "page_title": "Dashboard",
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
        "page_title": "Manajemen Kursi",
        "rows": rows,
        "total_count": len(all_rows),
        "available_count": counts.get("Tersedia", 0),
        "used_count": counts.get("Terisi", 0),
        "q": request.GET.get("q", ""),
        "status": status,
    }
    return render(request, "main/seats.html", context)


def tickets_page(request):
    data = get_data()
    user = get_current_user(request)
    rows = filter_ticket_rows(build_ticket_rows(data), user)

    q = request.GET.get("q", "").strip().lower()
    if q:
        rows = [
            r for r in rows
            if q in r["ticket_code"].lower()
            or q in r["event_title"].lower()
        ]

    context = {
        "user": user,
        "page_title": "Manajemen Tiket" if user["role"] != "customer" else "Tiket Saya",
        "rows": rows,
        "total_count": len(rows),
        "event_count": len({r["event_id"] for r in rows}),
        "seat_count": sum(1 for r in rows if r["seat_label"] != "Tanpa kursi"),
        "q": request.GET.get("q", ""),
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