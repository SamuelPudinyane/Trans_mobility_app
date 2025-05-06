from django.shortcuts import render

# Create your views here.
def login(request):
    return render(request, 'transnet_mobility/login.html')


def home(request):
    return render(request, 'transnet_mobility/edit_user.html')

def register_user(request):
    return render(request, 'transnet_mobility/register_user.html')

def locomotive_config(request):
    return render(request, 'transnet_mobility/locomotive_config.html')

def wagon_spec(request):
    return render(request, 'transnet_mobility/wagon_spec.html')


def wheelset(request):
    return render(request, 'transnet_mobility/wheelset.html')

def driver_assignment(request):
    return render(request, 'transnet_mobility/driver_assignment.html')


def all_users(request):
    return render(request, 'transnet_mobility/all_users.html')



def notifications(request):
    return render(request, 'transnet_mobility/notifications.html')


def trip_data(request):
    return render(request, 'transnet_mobility/trip_data.html')

def driver_request(request):
    return render(request, 'transnet_mobility/driver_request.html')







