from django.urls import path, include
from . import views

urlpatterns = [
    path('api/animal/', views.animal),
    path('add_event/', views.animal_web, name = "Event")
]