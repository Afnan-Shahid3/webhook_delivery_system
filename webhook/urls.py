from django.urls import path, include
from . import views

urlpatterns = [
    path('api/animal/', views.animal),
    path('add_event/', views.animal_web, name = "Event"),
    path('',views.dashboard, name = 'Dashboard'),
    path('deliveries/<int:delivery_id>', views.delivery_detail, name = 'detail'),
    path('endpoints/<int:endpoint_id>', views.endpoint_details, name = 'endpoint')
    
]