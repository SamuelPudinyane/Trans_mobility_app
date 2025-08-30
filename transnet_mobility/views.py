from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.db import IntegrityError
import json
from django.contrib import messages
from .user_dummy_data import users
from .models import UserLocation,CustomUser
from django.contrib.auth import get_user_model
User = get_user_model()

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('username')  # if using email as username
        password = request.POST.get('password')
        
        # Authenticate the user
        user = authenticate(request, email=email, password=password)  # make sure CustomUser backend supports email
        
        if user is not None:
            # Log the user in
            login(request, user)
            request.session['user']=user
            # Redirect based on role/account_type
            account_type = user.role  # or user.account_type
            if account_type == "DRIVER":
                return render(request,'cargo_specs.html',{'Account_type': account_type})
            elif account_type == "DRIVER":
                return render(request,'cargo_specs.html',{'Account_type': account_type})
            elif account_type == "ADMIN":
                return render(request,'driver_assignment.html',{'Account_type': account_type})
            elif account_type == "Security":
                return render(request, 'security_guard_report.html',{'Account_type': account_type})
            elif account_type == "Security Supervisor":
                return render(request, 'security_supervisor.html',{'Account_type': account_type})
            else:
                return render(request, 'login.html')  # fallback page
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, 'login.html')

def password_reset(request):
    return render(request, 'password_reset.html')

def home(request):
    return render(request, 'edit_user.html')

def register_user(request):
    if request.method == "POST":
        # Capture all fields from the form
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        id_number = request.POST.get("id_number")
        employee_number = request.POST.get("employee_number")
        mobile_number = request.POST.get("mobile_number")
        email = request.POST.get("email")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        account_type = request.POST.get("account_type")

        # Password validation
        if password != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register_user.html')

        # Check if email already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email address is already in use.")
            return render(request, 'register_user.html')

        try:
            # Create the user
            user = CustomUser.objects.create_user(
                username=email,  # usually use email as username
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                id_number=id_number,
                employee_number=employee_number,
                mobile_number=mobile_number,
                account_type=account_type
            )
            user.save()
            messages.success(request, "User registered successfully!")
            return redirect('login')  # replace 'login' with your login URL name
        except IntegrityError:
            messages.error(request, "An error occurred. Please try again.")
            return render(request, 'register_user.html')

    return render(request, 'register_user.html')


def locomotive_config(request):
    user=request.session['user']
    
    if user['account_type']=="ADMIN":
        return render(request, 'locomotive_config.html',{'Account_type':"ADMIN"})

def cargo_specs(request):
    user=request.session['user']
    
    if user['account_type']=="ADMIN":
        return render(request, 'cargo_specs.html',{'Account_type':"ADMIN"})


def wheelset(request):
    user=request.session['user']
    
    if user['account_type']=="ADMIN":
        return render(request, 'wheelset.html',{'Account_type':"ADMIN"})

def driver_assignment(request):
    user=request.session['user']
    if user['account_type']=="ADMIN":
        return render(request, 'driver_assignment.html',{'Account_type':"ADMIN"})


def all_users(request):
    return render(request, 'all_users.html')



def notifications(request):
    return render(request, 'notifications.html')


def trip_data(request):
    
    user=request.session['user']
   
    if user['account_type']=="DRIVER":
        return render(request, 'trip_data.html',{'Account_type':"DRIVER"})
    elif user['account_type']=="DRIVER":
        return render(request, 'trip_data.html',{'Account_type':"DRIVER"})
    

def driver_request(request):
    user=request.session['user']
    
    if user['account_type']=="DRIVER":
        return render(request, 'driver_request.html',{'Account_type':"DRIVER"})
    elif user['account_type']=="DRIVER":
        return render(request, 'driver_request.html',{'Account_type':"DRIVER"})


@csrf_exempt
@login_required
def update_location(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            lat = data.get("latitude")
            lng = data.get("longitude")

            UserLocation.objects.create(
                user=request.user,
                latitude=lat,
                longitude=lng
            )
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    elif request.method == "GET":
        latest_locs = UserLocation.objects.order_by("user_id", "-timestamp").distinct("user_id")
        data = []
        for loc in latest_locs:
            user = loc.user
            data.append({
                "lat": loc.latitude,
                "lng": loc.longitude,
                "timestamp": loc.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "user": {
                    "id": user.User_id,
                    "email": user.email,
                    "fullname": getattr(user, 'full_name', ''),
                    "role": getattr(user, 'role', ''),
                    "phone": getattr(user, 'phone_number', ''),
                }
            })
        return JsonResponse(data, safe=False)

    return JsonResponse({"error": "Invalid request"}, status=400)



def map_location(request):
    user=request.session['user']
    
    if user['account_type']=="DRIVER":
        return render(request, 'map_location.html',{'Account_type':"DRIVER"})
    elif user['account_type']=="DRIVER":
        return render(request, 'map_location.html',{'Account_type':"DRIVER"})
    elif user['account_type']=="ADMIN":
        return render(request, 'map_location.html',{'Account_type':"ADMIN"})
    
   

def map_location_railway(request):
    user=request.session['user']
    
    if user['account_type']=="DRIVER":
        return render(request, 'map_location_railway.html',{'Account_type':"DRIVER"})
    elif user['account_type']=="DRIVER":
        return render(request, 'map_location_railway.html',{'Account_type':"DRIVER"})
    elif user['account_type']=="ADMIN":
        return render(request, 'map_location_railway.html',{'Account_type':"ADMIN"})


def fuel_matrics(request):
    user=request.session['user']
    
    if user['account_type']=="DRIVER":
        return render(request, 'fuel_matrics.html',{'Account_type':"DRIVER"})
    elif user['account_type']=="DRIVER":
        return render(request, 'fuel_matrics.html',{'Account_type':"DRIVER"})

def route_and_node_preference(request):
    user=request.session['user']
    
    if user['account_type']=="DRIVER":
        return render(request, 'route_and_node_preference.html',{'Account_type':"DRIVER"})
    elif user['account_type']=="DRIVER":
        return render(request, 'route_and_node_preference.html',{'Account_type':"DRIVER"})

def load_strategic(request):
    user=request.session['user']

    if user['account_type']=="DRIVER":
        return render(request, 'load_strategic.html',{'Account_type':"DRIVER"})
    elif user['account_type']=="DRIVER":
        return render(request, 'load_strategic.html',{'Account_type':"DRIVER"})


def route_corridor(request):
    return render(request, 'route_corridor.html')


def profile(request):
    profile=request.session['user']
  
    Account_type=profile['account_type']

    return render(request,'profile.html',{"profile":profile,"Account_type":Account_type})


def security_guard_report(request):
    user=request.session['user']
    Account_type=user['account_type']
    return render(request, 'security_guard_report.html',{'Account_type':"Security"})

def security_emergency_call(request):
    user=request.session['user']
    Account_type=user['account_type']
    return render(request, 'security_emergency_call.html',{'Account_type':"Security"})

def security_supervisor(request):
    user=request.session['user']
    Account_type=user['account_type']
    return render(request, 'security_supervisor.html',{'Account_type':"Security Supervisor"})


def security_supervisor_call(request):
    user=request.session['user']
    Account_type=user['account_type']
    return render(request, 'security_supervisor_call.html',{'Account_type':"Security Supervisor"})



def logout(request):
    request.session.pop('user',None)
    return render(request,'login.html')














