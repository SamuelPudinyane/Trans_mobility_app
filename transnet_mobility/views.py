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
                           
                            return render(request,'cargo_specs.html',{'Account_type':"Train Driver"})
                        
                        elif user['Account Type']=="Assistant Driver":
                           
                            return render(request,'cargo_specs.html',{'Account_type':"Assistant Drivers"})
                        
                        elif user['Account Type']=="Administrator":
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
    return render(request, 'login.html')


def password_reset(request):
    return render(request, 'password_reset.html')

def home(request):
    return render(request, 'edit_user.html')

def register_user(request):
    return render(request, 'register_user.html')

def locomotive_config(request):
    user=request.session['user']
    
    if user['Account Type']=="Train Driver":
        return render(request, 'locomotive_config.html',{'Account_type':"Train Driver"})
    elif user['Account Type']=="Assistant Driver":
        return render(request, 'locomotive_config.html',{'Account_type':"Assistant Drivers"})

def cargo_specs(request):
    user=request.session['user']
    
    if user['Account Type']=="Train Driver":
        return render(request, 'cargo_specs.html',{'Account_type':"Train Driver"})
    elif user['Account Type']=="Assistant Driver":
        return render(request, 'cargo_specs.html',{'Account_type':"Assistant Drivers"})


def wheelset(request):
    user=request.session['user']
    
    if user['Account Type']=="Train Driver":
        return render(request, 'wheelset.html',{'Account_type':"Train Driver"})
    elif user['Account Type']=="Assistant Driver":
        return render(request, 'wheelset.html',{'Account_type':"Assistant Drivers"})

def driver_assignment(request):
    return render(request, 'driver_assignment.html')


def all_users(request):
    return render(request, 'all_users.html')



def notifications(request):
    return render(request, 'notifications.html')


def trip_data(request):
    
    user=request.session['user']
   
    if user['Account Type']=="Train Driver":
        return render(request, 'trip_data.html',{'Account_type':"Train Driver"})
    elif user['Account Type']=="Assistant Driver":
        return render(request, 'trip_data.html',{'Account_type':"Assistant Drivers"})
    

def driver_request(request):
    user=request.session['user']
    
    if user['Account Type']=="Train Driver":
        return render(request, 'driver_request.html',{'Account_type':"Train Driver"})
    elif user['Account Type']=="Assistant Driver":
        return render(request, 'driver_request.html',{'Account_type':"Assistant Drivers"})




def map_location(request):
    user=request.session['user']
    
    if user['Account Type']=="Train Driver":
        return render(request, 'map_location.html',{'Account_type':"Train Driver"})
    elif user['Account Type']=="Assistant Driver":
        return render(request, 'map_location.html',{'Account_type':"Assistant Drivers"})
    
   

def map_location_railway(request):
    user=request.session['user']
    
    if user['Account Type']=="Train Driver":
        return render(request, 'map_location_railway.html',{'Account_type':"Train Driver"})
    elif user['Account Type']=="Assistant Driver":
        return render(request, 'map_location_railway.html',{'Account_type':"Assistant Drivers"})


def fuel_matrics(request):
    user=request.session['user']
    
    if user['Account Type']=="Train Driver":
        return render(request, 'fuel_matrics.html',{'Account_type':"Train Driver"})
    elif user['Account Type']=="Assistant Driver":
        return render(request, 'fuel_matrics.html',{'Account_type':"Assistant Drivers"})

def route_and_node_preference(request):
    user=request.session['user']
    
    if user['Account Type']=="Train Driver":
        return render(request, 'route_and_node_preference.html',{'Account_type':"Train Driver"})
    elif user['Account Type']=="Assistant Driver":
        return render(request, 'route_and_node_preference.html',{'Account_type':"Assistant Drivers"})

def load_strategic(request):
    user=request.session['user']

    if user['Account Type']=="Train Driver":
        return render(request, 'load_strategic.html',{'Account_type':"Train Driver"})
    elif user['Account Type']=="Assistant Driver":
        return render(request, 'load_strategic.html',{'Account_type':"Assistant Drivers"})


def route_corridor(request):
    return render(request, 'route_corridor.html')






