from django.shortcuts import render
import requests

from .models import Event, Delivery, DeliveryAttempt, Endpoint
from .tasks import send_animal_name

from rest_framework.response import Response
from rest_framework.decorators import api_view, action
from rest_framework import status
from .forms import addEvent
from django.shortcuts import redirect
# Create your views here.

@api_view(['POST'])
def animal(request):
    animals = ['cat', 'dog', 'elephant', 'lion', 'tiger', 'monkey', 'giraffe']
    try:
        data = request.data
        name = data.get('name')

        if name in animals:
            return Response({'status' : 200, 'message' : "OK"}, status=status.HTTP_200_OK)

        return Response({'status' : 404, 'message' : "Wrong"}, status = status.HTTP_404_NOT_FOUND)

    except Exception as e:
        print(e)
    return Response({
        'status' : 400,
        'message' : 'Something went wrong'
    }, status = status.HTTP_400_BAD_REQUEST)


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