from django.urls import path

from . import views

urlpatterns = [
    path('slack/', views.slash_command, name='slash_command'),
    path('api-event/', views.event, name='event'),
    path('rest/', views.rest_api, name='rest'),
    path('', views.index)
]
