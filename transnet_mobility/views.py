from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .user_dummy_data import users

# Create your views here.
def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')  # or 'email' if using email-based auth
        password = request.POST.get('password')
        print("password ",password)
        print("username ",username)
        # Authenticate user
    #    user = authenticate(request, username=username, password=password)
        for user in users:
            if user is not None:
                login(request, user)
                return redirect('dashboard')  # Redirect to a dashboard or home page
            else:
                messages.error(request, "Invalid username or password.")
    return render(request, 'transnet_mobility/login.html')


def password_reset(request):
    return render(request, 'transnet_mobility/password_reset.html')

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



def map_location(request):
    return render(request, 'transnet_mobility/map_location.html')












