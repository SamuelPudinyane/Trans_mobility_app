from django.urls import path
from . import views

urlpatterns = [
    path('', views.login, name='login'),
    path('home/', views.home, name='edit_user'),
    path('register_user/',views.register_user,name='register_user'),
    path('locomotive_config/',views.locomotive_config,name='locomotive_config'),
    path('wagon_spec/',views.wagon_spec,name='wagon_spec'),
    path('wheelset/',views.wheelset,name='wheelset'),
    path('driver_assignment/',views.driver_assignment,name='driver_assignment'),
    path('all_users/',views.all_users,name='all_users'),
    path('notifications/',views.notifications,name='notifications'),
    path('trip_data/',views.trip_data,name='trip_data'),
    path('driver_request/',views.driver_request,name='driver_request'),
    path('map_location/',views.map_location,name='map_location'),
    path('password_reset/',views.password_reset,name='password_reset'),
]