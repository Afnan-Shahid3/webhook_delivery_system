from django.shortcuts import render
import requests

from .models import Event, Delivery, DeliveryAttempt, Endpoint, ProcessedIdempotentKeys
from .tasks import send_animal_name

from rest_framework.response import Response
from rest_framework.decorators import api_view, action
from rest_framework import status
from .forms import addEvent
from django.shortcuts import redirect
from django.conf import settings
import json, hmac, hashlib

from django.utils import timezone
# Create your views here.

@api_view(['POST'])
def animal(request):
    body = request.body
    signature = request.headers.get('X-Webhook-Signature')
    expected_signature = hmac.new(settings.WEBHOOK_SECRET.encode(), request.body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
        return Response({'status':401, 'message' : 'Invalid signature'}, status = status.HTTP_401_UNAUTHORIZED)


    animals = ['cat', 'dog', 'elephant', 'lion', 'tiger', 'monkey', 'giraffe']
    new_key = request.headers.get("Idempotency-key")
    
    if not ProcessedIdempotentKeys.objects.filter(key = new_key).exists():
        try:
            data = request.data
            name = data.get('name')



            if name in animals:
                ProcessedIdempotentKeys.objects.create(key = new_key)
                return Response({'status' : 200, 'message' : "OK"}, status=status.HTTP_200_OK)

            return Response({'status' : 404, 'message' : "Wrong"}, status = status.HTTP_404_NOT_FOUND)

        except Exception as e:
            print("Idempotency Key not available")
        return Response({
            'status' : 400,
            'message' : 'Something went wrong'
        }, status = status.HTTP_400_BAD_REQUEST)

    else:
        return Response({"status" : 200, "message": "Already Processed"}, status = status.HTTP_200_OK)

def animal_web(request):
    if request.method == "POST":
        form = addEvent(request.POST)
        if form.is_valid():
            event = form.save(commit = False)
            event.type = "create"
            event.data = {"name" : event.name}
            event.save()

            ##creating deliveries
            endpoints = Endpoint.objects.filter(is_active= True)

            for i in endpoints:
                #timeout check
                if i.circuit_broken_until and i.circuit_broken_until > timezone.now():
                    continue
                delivery = Delivery.objects.create(event = event, endpoint = i, delivery_status= 'process')

                ##sending requests
                send_animal_name.delay(delivery.id)
                 
            return redirect('Event')
    else:
        form = addEvent()

    context = {
        'form' : form
    }

    return render(request, 'add_event.html', context)


def dashboard(request):
    deliveries = Delivery.objects.all().order_by('-created_at')

    context = {
        'deliveries' : deliveries
    }

    return render(request, 'Dashboard.html', context)


def delivery_detail(request, delivery_id):
    delivery = Delivery.objects.get(id = delivery_id)
    attempts = delivery.attempts.all().order_by('attempt_number')

    context = {
        'delivery' : delivery,
        'attempts' : attempts
    }

    return render(request, 'detail.html', context)


def endpoint_details(request, endpoint_id):
    endpoint = Endpoint.objects.get(id = endpoint_id)
    delivery = Delivery.objects.filter(endpoint = endpoint)

    context = {
        'endpoint' : endpoint,
        'delivery' : delivery,
    }

    return render(request, 'endpoint_detail.html', context)


