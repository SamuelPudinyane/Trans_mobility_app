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
                if username in user['Email']:
                    if password in user['Employee Number']:
                       
                        request.session['user']=user
                        if user['Account Type']=="Train Driver":
                            Account_type="Train Driver"
                            return render(request,'transnet_mobility/trip_data.html',{'Account_type':"Train Driver"})
                        
                        elif user['Account Type']=="Assistant Driver":
                            Account_type="Assistant Drivers"
                            print("something crazy here ")
                            return render(request,'transnet_mobility/trip_data.html',{'Account_type':"Assistant Drivers"})
                        elif user['Account Type']=="Operational Managers":
                            Account_type="Operational Managers"
                            return redirect('trip_data')
                        elif user['Account Type']=="Corridor Managers":
                            Account_type="Corridor Managers"
                            return redirect('trip_data')
                        elif user['Account Type']=="IT Technicians":
                            Account_type="IT Technicians"
                            return redirect('trip_data')
                        elif user['Account Type']=="Logistics Coordinators":
                            Account_type="Logistics Coordinators"
                            return redirect('trip_data')
                        elif user['Account Type']=="Electrical Maintenance Team":
                            Account_type="Electrical Maintenance Team"
                            return redirect('trip_data')
                        elif user['Account Type']=="Mechanical Maintenance Team":
                            Account_type="Mechanical Maintenance Team"
                            return redirect('trip_data')
                        elif user['Account Type']=="Emergency Response Team":
                            Account_type="Emergency Response Team"
                            return redirect('trip_data')
                        elif user['Account Type']=="Locomotive Specialists":
                            Account_type="Locomotive Specialists"
                            return redirect('trip_data')
                        
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

def cargo_specs(request):
    return render(request, 'transnet_mobility/cargo_specs.html')


def wheelset(request):
    return render(request, 'transnet_mobility/wheelset.html')

def driver_assignment(request):
    return render(request, 'transnet_mobility/driver_assignment.html')


def all_users(request):
    return render(request, 'transnet_mobility/all_users.html')



def notifications(request):
    return render(request, 'transnet_mobility/notifications.html')


def trip_data(request):
    
    user=request.session['user']
   
    if user['Account Type']=="Train Driver" or user['Account Type']=="Assistant Driver":   
        return render(request,'transnet_mobility/trip_data.html',{'Account_type':"Assistant Drivers"})
    

def driver_request(request):
    user=request.session['user']
    
    if user['Account Type']=="Train Driver" or user['Account Type']=="Assistant Driver":
        return render(request,'transnet_mobility/driver_request.html',{'Account_type':"Train Driver"})




def map_location(request):
    return render(request, 'transnet_mobility/map_location.html')

def map_location_railway(request):
    return render(request, 'transnet_mobility/map_location_railway.html')










