from django.shortcuts import render
import requests

from .models import Event, Delivery, DeliveryAttempt, Endpoint

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
                try:
                    response = requests.post(i.url, json = event.data, timeout = 5)
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
                    DA = DeliveryAttempt.objects.create(delivery = delivery, response_status_code = None, attempt_number = 1, attempt_status= "TO"
                    , response_body = response.text)
                    delivery.delivery_status = "fail"
                    delivery.save()

                except requests.exceptions.ConnectionError:
                    DA = DeliveryAttempt.objects.create(delivery = delivery, response_status_code = None, attempt_number = 1, attempt_status= "COE"
                    , response_body = response.text)
                    delivery.delivery_status = "fail"
                    delivery.save()   
            return redirect('Event')
    else:
        form = addEvent()

    context = {
        'form' : form
    }

    return render(request, 'add_event.html', context)