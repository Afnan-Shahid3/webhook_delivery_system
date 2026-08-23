from django.contrib import admin
from .models import Event, Endpoint, Delivery, DeliveryAttempt
# register your models here.

admin.site.register(Event)
admin.site.register(Delivery)
admin.site.register(DeliveryAttempt)
admin.site.register(Endpoint)

