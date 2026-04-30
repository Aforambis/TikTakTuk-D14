from django.urls import path

from . import views

urlpatterns = [
    # Public / auth
    path("", views.landing_page, name="landing_page"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),

    # Demo role switcher
    path("set-role/<str:role_name>/", views.set_role, name="set_role"),

    # Tickets
    path("tickets/", views.tickets_page, name="tickets"),
    path("tickets/create/", views.create_ticket, name="create_ticket"),
    path("tickets/<uuid:ticket_id>/update/", views.update_ticket, name="update_ticket"),
    path("tickets/<uuid:ticket_id>/delete/", views.delete_ticket, name="delete_ticket"),

    # Seats
    path("seats/", views.seats_page, name="seats"),
    path("seats/create/", views.create_seat, name="create_seat"),
    path("seats/<uuid:seat_id>/update/", views.update_seat, name="update_seat"),
    path("seats/<uuid:seat_id>/delete/", views.delete_seat, name="delete_seat"),

    # Venues
    path("venues/", views.venue_list, name="venue_list"),
    path("venues/create/", views.venue_create, name="venue_create"),
    path("venues/<uuid:venue_id>/update/", views.venue_update, name="venue_update"),
    path("venues/<uuid:venue_id>/delete/", views.venue_delete, name="venue_delete"),

    # Events
    path("events/", views.event_list, name="event_list"),
    path("my-events/", views.my_events, name="my_events"),
    path("my-events/create/", views.event_create, name="event_create"),
    path("my-events/<uuid:event_id>/update/", views.event_update, name="event_update"),

    # Artists
    path("artists/", views.artist_list, name="artist_list"),
    path("artists/create/", views.artist_create, name="artist_create"),
    path("artists/<uuid:artist_id>/update/", views.artist_update, name="artist_update"),
    path("artists/<uuid:artist_id>/delete/", views.artist_delete, name="artist_delete"),

    # Ticket Categories from Pengguna_Hijau
    path("ticket-categories/", views.category_page, name="ticket_categories"),

    # Orders
    path("orders/", views.order_list, name="order_list"),
    path("orders/", views.order_list, name="orders"),
    path("orders/<uuid:order_id>/update/", views.update_order, name="update_order"),
    path("orders/<uuid:order_id>/delete/", views.delete_order, name="delete_order"),
    path("events/<uuid:event_id>/checkout/", views.checkout, name="checkout"),

    # Promotions
    path("promotions/", views.promotions_page, name="promotions"),
    path("promotions/create/", views.create_promotion, name="create_promotion"),
    path("promotions/<uuid:promo_id>/update/", views.update_promotion, name="update_promotion"),
    path("promotions/<uuid:promo_id>/delete/", views.delete_promotion, name="delete_promotion"),
]