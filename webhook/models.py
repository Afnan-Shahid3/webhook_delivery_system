from django.db import models
from django.utils import timezone
import uuid
# Create your models here.

TYPE_CHOICES = [
    ('create', 'Created'),
    ('delete', 'Deleted'),
    ('update', 'Updated')
]


class Event(models.Model):
    name = models.CharField(max_length = 50)
    type = models.CharField(max_length= 10, choices= TYPE_CHOICES)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)


class Endpoint(models.Model):
    client = models.CharField(max_length= 25)
    url = models.URLField(unique= True)
    is_active = models.BooleanField(default = True)

DELIVERY_CHOICES = [
    ('process', "IN PROCESS"),
    ('deliver', "DELIVERED"),
    ('fail', "DELIVERY FAILED")
]

class Delivery(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null = False, blank = False)
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE, null = False, blank = False)
    delivery_status = models.CharField(max_length= 10, choices=DELIVERY_CHOICES )
    created_at = models.DateTimeField(auto_now_add=True)
    key = models.UUIDField(default = uuid.uuid4, editable = False, unique= True, null= True)

CHOICES_LIST = [
    ('SU', "Success"),
    ('CE', 'Failed - Client Error'),
    ('SE', "Failed - Server Error"),
    ('TO', 'Failed - Timeout'),
    ('COE', "Failed - Connection Error"),
]

class DeliveryAttempt(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, null = False, blank = False, related_name= 'attempts')
    attempted_at = models.DateTimeField(auto_now_add = True)
    attempt_number = models.IntegerField()
    response_body = models.JSONField(null = True, blank = True)
    response_status_code = models.IntegerField(null = True, blank = True)
    attempt_status = models.CharField(max_length = 5, choices = CHOICES_LIST)



# Client Side Models

class ProcessedIdempotentKeys(models.Model):
    key = models.UUIDField(unique = True)
    processed_at = models.DateTimeField(auto_now_add= True)

