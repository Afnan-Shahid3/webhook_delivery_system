from celery import shared_task
import requests

from .models import Event, Delivery, DeliveryAttempt, Endpoint

from rest_framework.response import Response


@shared_task
def send_animal_name(delivery_id):
    delivery = Delivery.objects.get(id = delivery_id)
    try:
        response = requests.post(delivery.endpoint.url, json = delivery.event.data, timeout = 5)
        DA = DeliveryAttempt.objects.create(delivery = delivery, response_status_code = response.status_code, attempt_number = 1, response_body = response.text)
        if 200 <= response.status_code < 300:
            print("You have selected an animal")
            DA.attempt_status = "SU"
            DA.save()
            delivery.delivery_status = "deliver"
            delivery.save()
        elif 400 <= response.status_code < 500:
            DA.attempt_status = "CE"
            DA.save()
            delivery.delivery_status = "fail"
            delivery.save()
        else:
            DA.attempt_status = "SE"
            DA.save()
            delivery.delivery_status = "fail"
            delivery.save()
    except requests.exceptions.Timeout:
        DA = DeliveryAttempt.objects.create(delivery = delivery, response_status_code = None, attempt_number = 1, attempt_status= "TO")
        delivery.delivery_status = "fail"
        delivery.save()
    except requests.exceptions.ConnectionError:
        DA = DeliveryAttempt.objects.create(delivery = delivery, response_status_code = None, attempt_number = 1, attempt_status= "COE")
        delivery.delivery_status = "fail"
        delivery.save()   