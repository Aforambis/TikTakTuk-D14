from django.db import models

class Venue(models.Model):
    name = models.CharField(max_length=255)
    capacity = models.IntegerField()
    city = models.CharField(max_length=100)
    has_reserved = models.BooleanField(default=False)

class Event(models.Model):
    name = models.CharField(max_length=255)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    date = models.DateField()
    category = models.CharField(max_length=100) # e.g., 'Music', 'Education'

class TicketCategory(models.Model):
    event = models.ForeignKey(Event, related_name='categories', on_delete=models.CASCADE)
    name = models.CharField(max_length=100) # e.g., 'VIP', 'Reguler'
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quota = models.IntegerField()