from django.contrib import admin

from .models import (
    AccountRole,
    Artist,
    Customer,
    Event,
    EventArtist,
    HasRelationship,
    Order,
    OrderPromotion,
    Organizer,
    Promotion,
    Role,
    Seat,
    Ticket,
    TicketCategory,
    UserAccount,
    Venue,
)


def _all_field_names(model_cls):
    return [field.name for field in model_cls._meta.fields]


@admin.register(UserAccount)
class UserAccountAdmin(admin.ModelAdmin):
    list_display = _all_field_names(UserAccount)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = _all_field_names(Role)


@admin.register(AccountRole)
class AccountRoleAdmin(admin.ModelAdmin):
    list_display = _all_field_names(AccountRole)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = _all_field_names(Customer)


@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = _all_field_names(Organizer)


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = _all_field_names(Venue)


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = _all_field_names(Seat)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = _all_field_names(Event)


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = _all_field_names(Artist)


@admin.register(EventArtist)
class EventArtistAdmin(admin.ModelAdmin):
    list_display = _all_field_names(EventArtist)


@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = _all_field_names(TicketCategory)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = _all_field_names(Order)


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = _all_field_names(Promotion)


@admin.register(OrderPromotion)
class OrderPromotionAdmin(admin.ModelAdmin):
    list_display = _all_field_names(OrderPromotion)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = _all_field_names(Ticket)


@admin.register(HasRelationship)
class HasRelationshipAdmin(admin.ModelAdmin):
    list_display = _all_field_names(HasRelationship)
