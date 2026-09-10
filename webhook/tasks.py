from celery import shared_task

import requests

from .models import Event, Delivery, DeliveryAttempt, Endpoint

from celery.exceptions import MaxRetriesExceededError

import json, hmac, hashlib

from django.utils import timezone
from datetime import timedelta
class ServerErrorRetry(Exception):
    pass


@shared_task(bind = True)
def send_animal_name(self, delivery_id):
    delay = 5 * (2 ** self.request.retries)
    delivery = Delivery.objects.get(id = delivery_id)
    try:
        payload = json.dumps(delivery.event.data)
        signature = hmac.new(delivery.endpoint.secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        response = requests.post(
            delivery.endpoint.url,
            data = payload,
            headers = {
                "Idempotency-Key" : str(delivery.key),
                "X-Webhook-Signature" : signature,
                "Content-Type" : "application/json",
            },
            timeout = 5
        )
        DA = DeliveryAttempt.objects.create(delivery = delivery, response_status_code = response.status_code, attempt_number = self.request.retries, response_body = response.text)
        if 200 <= response.status_code < 300:
            print("You have selected an animal")
            DA.attempt_status = "SU"
            DA.save()
            delivery.delivery_status = "deliver"
            delivery.save()
            delivery.endpoint.consecutive_failures = 0
            delivery.endpoint.save()
        elif 400 <= response.status_code < 500:
            DA.attempt_status = "CE"
            DA.save()
            delivery.delivery_status = "fail"
            delivery.save()
        else:
            DA.attempt_status = "SE"
            DA.save()
            try:
                raise self.retry(exc=ServerErrorRetry(f"Server returned {response.status_code}"), max_retries = 3, countdown = delay)
            except (MaxRetriesExceededError, ServerErrorRetry):
                delivery.delivery_status = "fail"
                delivery.save()
                delivery.endpoint.consecutive_failures += 1
                if delivery.endpoint.consecutive_failures >= 5:
                    delivery.endpoint.circuit_broken_until = timezone.now() + timedelta(minutes = 10)

                delivery.endpoint.save()
    except requests.exceptions.Timeout as time:
        DA = DeliveryAttempt.objects.create(delivery = delivery, response_status_code = None, attempt_number = self.request.retries, attempt_status= "TO")
        try:
            raise self.retry(exc = time, countdown = delay, max_retries = 3)
        except (MaxRetriesExceededError, requests.exceptions.Timeout):
            delivery.delivery_status = "fail"
            delivery.save()
            delivery.endpoint.consecutive_failures += 1
            if delivery.endpoint.consecutive_failures >= 5:
                delivery.endpoint.circuit_broken_until = timezone.now() + timedelta(minutes = 10)
            delivery.endpoint.save()
    except requests.exceptions.ConnectionError as Connection:
        DA = DeliveryAttempt.objects.create(delivery = delivery, response_status_code = None, attempt_number = self.request.retries, attempt_status= "COE")
        try:
            raise self.retry(exc = Connection, countdown = delay, max_retries = 3)
        except (MaxRetriesExceededError, requests.exceptions.ConnectionError):
            delivery.delivery_status = "fail"
            delivery.save()
            delivery.endpoint.consecutive_failures += 1
            if delivery.endpoint.consecutive_failures >= 5:
                delivery.endpoint.circuit_broken_until = timezone.now() + timedelta(minutes = 10)
            delivery.endpoint.save()