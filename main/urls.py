from django.urls import path
from . import views

app_name = "main"

urlpatterns = [
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
]