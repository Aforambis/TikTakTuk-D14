from collections import Counter
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from .data import get_data
from django.views.decorators.csrf import csrf_exempt
import random
import string
import uuid


def get_current_user(request):
    # Ambil role dari URL (?role=...), POST, atau Session. 
    role = request.GET.get("role") or request.POST.get("role") or request.session.get("active_role") or "guest"
    
    # Validasi: Izinkan 'guest' sebagai salah satu role yang sah
    if role not in ["admin", "organizer", "customer", "guest"]:
        role = "guest"
        
    # Simpan state login/logout di session
    request.session["active_role"] = role
    
    # Jika role adalah guest, kembalikan dictionary simpel agar tidak error saat mencari data di data.py
    if role == "guest":
        return {"role": "guest"}
        
    return get_data()["users"][role]

def landing_page(request):
    user = get_current_user(request)
    
    # Jika sudah login (bukan guest), langsung arahkan ke dashboard
    if user.get('role') != 'guest':
        return redirect('main:dashboard')
        
    # Jika guest, tampilkan landing page
    context = {
        "role": "guest",
        "current_page": "home"
    }
    return render(request, "main/landing.html", context)


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

    if user["role"] == "guest":
        return redirect("main:landing_page")

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


ARTISTS_MEMORY = None

def get_artists_memory():
    global ARTISTS_MEMORY
    if ARTISTS_MEMORY is None:
        ARTISTS_MEMORY = get_data()["artists"]
    return ARTISTS_MEMORY

@csrf_exempt
def artist_page(request):
    user = get_current_user(request)
    artists_mem = get_artists_memory()
    error_message = None
    success_message = None

    if request.method == "POST":
        # Pastikan hanya Admin yang memproses POST
        if user.get('role') == 'admin':
            action = request.POST.get("action")

            # --- AKSI HAPUS ---
            if action == "hapus":
                artist_id = request.POST.get("artist_id")
                artist_name = request.POST.get("artist_name")
                artists_mem[:] = [a for a in artists_mem if a["artist_id"] != artist_id]
                success_message = f"Data artis '{artist_name}' berhasil dihapus!"

            # --- AKSI TAMBAH & EDIT ---
            elif action in ["tambah", "edit"]:
                name = request.POST.get("name")
                genre = request.POST.get("genre") or "-" # Genre opsional, default "-"
                artist_id = request.POST.get("artist_id")

                # Validasi: Field Name wajib diisi
                if not name:
                    error_message = "Gagal menyimpan! Nama artis wajib diisi."
                else:
                    if action == "tambah":
                        # Generate UUID baru untuk artis
                        new_id = str(uuid.uuid4())
                        artists_mem.append({
                            "artist_id": new_id,
                            "name": name,
                            "genre": genre
                        })
                        success_message = f"Artis '{name}' berhasil ditambahkan!"
                        
                    elif action == "edit":
                        for a in artists_mem:
                            if a["artist_id"] == artist_id:
                                a["name"] = name
                                a["genre"] = genre
                                break
                        success_message = f"Data artis '{name}' berhasil diperbarui!"
        else:
            error_message = "Akses ditolak. Hanya Admin yang dapat mengelola artis."

    # Mengurutkan artis berdasarkan nama (Ascending A-Z)
    artists_mem.sort(key=lambda x: x["name"].lower())
    
    # Menghitung jumlah genre unik untuk kotak statistik
    unique_genres = len(set(a["genre"] for a in artists_mem if a["genre"] != "-"))

    context = {
        "user": user,
        "role": user.get("role", "guest"),
        "current_page": "artis",
        "page_title": "Daftar Artis",
        "artists": artists_mem,
        "unique_genres": unique_genres,
        "error_message": error_message,
        "success_message": success_message,
    }
    return render(request, "main/artists.html", context)



# Simpan kategori di memory (dummy, tidak persistent)
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
    success_message = None # Variabel baru untuk pesan sukses (Kriteria v)

    if request.method == "POST":
        action = request.POST.get("action")

        # --- AKSI HAPUS ---
        if action == "hapus":
            category_id = request.POST.get("category_id")
            categories_mem[:] = [cat for cat in categories_mem if cat["category_id"] != category_id]
            success_message = "Data kategori tiket berhasil dihapus!"

        # --- AKSI TAMBAH & EDIT ---
        elif action in ["tambah", "edit"]:
            event_id = request.POST.get("event_id")
            category_name = request.POST.get("category_name")
            price_str = request.POST.get("price")
            quota_str = request.POST.get("quota")
            category_id = request.POST.get("category_id")

            # Validasi i: Seluruh field wajib diisi
            if not event_id or not category_name or not price_str or not quota_str:
                error_message = "Gagal! Seluruh field wajib diisi."
            else:
                price = int(price_str)
                new_quota = int(quota_str)

                # Validasi ii: Quota harus bilangan bulat positif (> 0)
                if new_quota <= 0:
                    error_message = "Gagal! Kuota tiket harus lebih dari 0."
                
                # Validasi iii: Price harus bilangan tidak negatif (>= 0)
                elif price < 0:
                    error_message = "Gagal! Harga tiket tidak boleh negatif."
                
                # Validasi iv: Total kuota event <= Kapasitas Venue
                else:
                    event = next((e for e in data["events"] if e["event_id"] == event_id), None)
                    if event:
                        venue = next((v for v in data["venues"] if v["venue_id"] == event["venue_id"]), None)
                        venue_capacity = venue.get("capacity", 0) if venue else 0

                        current_event_quota = 0
                        for cat in categories_mem:
                            if cat["event_id"] == event_id:
                                if action == "edit" and cat["category_id"] == category_id:
                                    continue
                                current_event_quota += cat["quota"]

                        if (current_event_quota + new_quota) > venue_capacity:
                            error_message = f"Gagal menyimpan! Total kuota tiket ({current_event_quota + new_quota}) melebihi kapasitas {venue['venue_name']} ({venue_capacity} kursi)."

            # Validasi v: Jika semua valid, simpan data dan tampilkan pesan sukses
            if not error_message:
                if action == "tambah":
                    new_id = str(uuid.uuid4())
                    categories_mem.append({
                        "category_id": new_id,
                        "category_name": category_name,
                        "event_id": event_id,
                        "price": price,
                        "quota": new_quota,
                    })
                    success_message = f"Kategori tiket '{category_name}' berhasil ditambahkan!"
                elif action == "edit":
                    for cat in categories_mem:
                        if cat["category_id"] == category_id:
                            cat["event_id"] = event_id
                            cat["category_name"] = category_name
                            cat["price"] = price
                            cat["quota"] = new_quota
                            break
                    success_message = f"Kategori tiket '{category_name}' berhasil diperbarui!"

    # --- PERSIAPAN RENDER HALAMAN ---
    event_map = {e["event_id"]: e["event_title"] for e in data["events"]}
    categories = []
    total_quota = 0
    max_price = 0

    for cat in categories_mem:
        cat = cat.copy()
        cat["event_name"] = event_map.get(cat["event_id"], "-")
        categories.append(cat)
        
        total_quota += cat["quota"]
        if cat["price"] > max_price:
            max_price = cat["price"]

    # Urutkan berdasarkan event_name ascending, lalu category_name ascending
    categories.sort(key=lambda x: (x["event_name"].lower(), x["category_name"].lower()))

    context = {
        "user": user,
        "role": user["role"],
        "current_page": "kategori",
        "page_title": "Kategori Tiket",
        "categories": categories,
        "events": data["events"], 
        "total_quota": total_quota,
        "max_price": max_price,
        "error_message": error_message, 
        "success_message": success_message, # Kirim pesan sukses ke HTML
    }
    return render(request, "main/ticket_categories.html", context)