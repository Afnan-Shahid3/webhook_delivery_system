from django import forms
from .models import Event, Delivery, DeliveryAttempt


class addEvent(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['name']
        