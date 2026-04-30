from django.urls import path
from . import views

app_name = "main"

urlpatterns = [
    # Auth
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Dashboard & core pages
    path("", views.dashboard, name="dashboard"),
    path("dashboard/", views.dashboard, name="dashboard"),

    # Tickets
    path("tickets/", views.tickets_page, name="tickets"),
    path("tickets/create/", views.create_ticket, name="create_ticket"),
    path("tickets/<str:ticket_id>/update/", views.update_ticket, name="update_ticket"),
    path("tickets/<str:ticket_id>/delete/", views.delete_ticket, name="delete_ticket"),

    # Seats
    path("seats/", views.seats_page, name="seats"),
    path("seats/create/", views.create_seat, name="create_seat"),
    path("seats/<str:seat_id>/update/", views.update_seat, name="update_seat"),
    path("seats/<str:seat_id>/delete/", views.delete_seat, name="delete_seat"),

    # Orders
    path("orders/", views.orders_page, name="orders"),
    path("orders/<str:order_id>/update/", views.update_order, name="update_order"),
    path("orders/<str:order_id>/delete/", views.delete_order, name="delete_order"),

    # Promotions
    path("promotions/", views.promotions_page, name="promotions"),
    path("promotions/create/", views.create_promotion, name="create_promotion"),
    path("promotions/<str:promo_id>/update/", views.update_promotion, name="update_promotion"),
    path("promotions/<str:promo_id>/delete/", views.delete_promotion, name="delete_promotion"),
]