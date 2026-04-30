from copy import deepcopy

VENUES = [
    {"venue_id": "ven_001", "venue_name": "Jakarta Convention Center", "city": "Jakarta", "has_reserved_seating": True},
    {"venue_id": "ven_002", "venue_name": "Bandung Hall Center", "city": "Bandung", "has_reserved_seating": False},
]

EVENTS = [
    {
        "event_id": "evt_001",
        "event_title": "Konser Melodi Senja",
        "event_datetime": "2026-05-12 19:00",
        "venue_id": "ven_001",
        "venue_name": "Jakarta Convention Center",
        "organizer_id": "org_001",
        "organizer_name": "Andi Wijaya",
    },
    {
        "event_id": "evt_002",
        "event_title": "Festival Seni Budaya",
        "event_datetime": "2026-05-20 18:30",
        "venue_id": "ven_002",
        "venue_name": "Bandung Hall Center",
        "organizer_id": "org_002",
        "organizer_name": "Raka Event Co",
    },
]

TICKET_CATEGORIES = [
    {"category_id": "cat_001", "category_name": "VIP", "quota": 50, "price": 750000, "event_id": "evt_001"},
    {"category_id": "cat_002", "category_name": "Regular", "quota": 200, "price": 250000, "event_id": "evt_001"},
    {"category_id": "cat_003", "category_name": "General Admission", "quota": 500, "price": 150000, "event_id": "evt_002"},
]

ORDERS = [
    {
        "order_id": "ord_001",
        "order_date": "2026-04-10 10:00",
        "payment_status": "Lunas",
        "total_amount": 750000,
        "customer_id": "cust_001",
        "customer_name": "Budi Santoso",
        "event_id": "evt_001",
        "event_title": "Konser Melodi Senja",
        "organizer_id": "org_001",
    },
    {
        "order_id": "ord_002",
        "order_date": "2026-04-11 14:30",
        "payment_status": "Pending",
        "total_amount": 150000,
        "customer_id": "cust_002",
        "customer_name": "Siti Rahayu",
        "event_id": "evt_002",
        "event_title": "Festival Seni Budaya",
        "organizer_id": "org_002",
    },
    {
        "order_id": "ord_003",
        "order_date": "2026-04-12 09:15",
        "payment_status": "Lunas",
        "total_amount": 500000,
        "customer_id": "cust_001",
        "customer_name": "Budi Santoso",
        "event_id": "evt_001",
        "event_title": "Konser Melodi Senja",
        "organizer_id": "org_001",
    },
    {
        "order_id": "ord_004",
        "order_date": "2026-04-13 11:00",
        "payment_status": "Dibatalkan",
        "total_amount": 300000,
        "customer_id": "cust_002",
        "customer_name": "Siti Rahayu",
        "event_id": "evt_002",
        "event_title": "Festival Seni Budaya",
        "organizer_id": "org_002",
    },
]

SEATS = [
    {"seat_id": "seat_001", "section": "VIP", "row_number": "A", "seat_number": "1", "venue_id": "ven_001", "venue_name": "Jakarta Convention Center"},
    {"seat_id": "seat_002", "section": "VIP", "row_number": "A", "seat_number": "2", "venue_id": "ven_001", "venue_name": "Jakarta Convention Center"},
    {"seat_id": "seat_003", "section": "VIP", "row_number": "B", "seat_number": "1", "venue_id": "ven_001", "venue_name": "Jakarta Convention Center"},
    {"seat_id": "seat_004", "section": "Regular", "row_number": "C", "seat_number": "7", "venue_id": "ven_001", "venue_name": "Jakarta Convention Center"},
    {"seat_id": "seat_005", "section": "Regular", "row_number": "C", "seat_number": "8", "venue_id": "ven_001", "venue_name": "Jakarta Convention Center"},
]

TICKETS = [
    {
        "ticket_id": "tix_001",
        "ticket_code": "TT-0001",
        "category_id": "cat_001",
        "category_name": "VIP",
        "order_id": "ord_001",
        "event_id": "evt_001",
        "event_title": "Konser Melodi Senja",
        "customer_id": "cust_001",
        "customer_name": "Budi Santoso",
        "organizer_id": "org_001",
        "venue_name": "Jakarta Convention Center",
    },
    {
        "ticket_id": "tix_002",
        "ticket_code": "TT-0002",
        "category_id": "cat_003",
        "category_name": "General Admission",
        "order_id": "ord_002",
        "event_id": "evt_002",
        "event_title": "Festival Seni Budaya",
        "customer_id": "cust_002",
        "customer_name": "Siti Rahayu",
        "organizer_id": "org_002",
        "venue_name": "Bandung Hall Center",
    },
]

HAS_RELATIONSHIP = [
    {"seat_id": "seat_001", "ticket_id": "tix_001"},
]

PROMOTIONS = [
    {
        "promo_id": "promo_001",
        "promo_code": "TIKTAK20",
        "discount_type": "Persentase",
        "discount_value": 20,
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "usage_limit": 100,
        "usage_count": 45,
    },
    {
        "promo_id": "promo_002",
        "promo_code": "HEMAT50K",
        "discount_type": "Nominal",
        "discount_value": 50000,
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "usage_limit": 50,
        "usage_count": 12,
    },
    {
        "promo_id": "promo_003",
        "promo_code": "NEWUSER30",
        "discount_type": "Persentase",
        "discount_value": 30,
        "start_date": "2024-03-01",
        "end_date": "2024-06-30",
        "usage_limit": 200,
        "usage_count": 87,
    },
]

# Credentials for login: username -> password + role mapping
USER_CREDENTIALS = {
    "admin": {"password": "admin123", "role": "admin"},
    "organizer": {"password": "organizer123", "role": "organizer"},
    "customer": {"password": "customer123", "role": "customer"},
}

USERS = {
    "admin": {"role": "admin", "name": "Admin Utama", "user_id": "adm_001"},
    "organizer": {"role": "organizer", "name": "Andi Wijaya", "organizer_id": "org_001", "user_id": "org_user_001"},
    "customer": {"role": "customer", "name": "Budi Santoso", "customer_id": "cust_001", "user_id": "cust_user_001"},
}


def get_data():
    return {
        "venues": deepcopy(VENUES),
        "events": deepcopy(EVENTS),
        "ticket_categories": deepcopy(TICKET_CATEGORIES),
        "orders": deepcopy(ORDERS),
        "seats": deepcopy(SEATS),
        "tickets": deepcopy(TICKETS),
        "has_relationship": deepcopy(HAS_RELATIONSHIP),
        "users": deepcopy(USERS),
        "promotions": deepcopy(PROMOTIONS),
        "user_credentials": deepcopy(USER_CREDENTIALS),
    }