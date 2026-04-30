from django.urls import path

from . import views

urlpatterns = [
    # Dashboard + ticketing (dummy UI)
    path("", views.dashboard, name="dashboard"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("tickets/", views.tickets_page, name="tickets"),
    path("seats/", views.seats_page, name="seats"),

    path("tickets/create/", views.create_ticket, name="create_ticket"),
    path("tickets/<str:ticket_id>/update/", views.update_ticket, name="update_ticket"),
    path("tickets/<str:ticket_id>/delete/", views.delete_ticket, name="delete_ticket"),

    path("seats/create/", views.create_seat, name="create_seat"),
    path("seats/<str:seat_id>/update/", views.update_seat, name="update_seat"),
    path("seats/<str:seat_id>/delete/", views.delete_seat, name="delete_seat"),

    path("set-role/<str:role_name>/", views.set_role, name="set_role"),
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
    # Orders
    path("orders/", views.order_list, name="order_list"),
    path("events/<uuid:event_id>/checkout/", views.checkout, name="checkout"),
]
