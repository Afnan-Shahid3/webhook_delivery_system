from django.shortcuts import render

from rest_framework.response import Response
from rest_framework.decorators import api_view, action
from rest_framework import status
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