import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobility.settings')
django.setup()

from django.contrib.auth import authenticate
from transnet_mobility.models import CustomUser

email = 'malva@gmail.com'
password = 'Malva78*'

print("="*60)
print("Testing Login for malva@gmail.com")
print("="*60)

# First check if user exists
try:
    user = CustomUser.objects.get(email=email)
    print(f"\n✅ User found: {user.email}")
    print(f"   Name: {user.first_name} {user.last_name}")
    print(f"   Is Active: {user.is_active}")
    print(f"   Role: {user.role}")
except CustomUser.DoesNotExist:
    print(f"\n❌ User with email {email} does not exist")
    exit()

print("\n" + "-"*60)
print("Testing Authentication Methods")
print("-"*60)

# Method 1: authenticate with username parameter (EmailBackend)
print(f"\n1. Testing: authenticate(username='{email}', password='***')")
try:
    auth_user = authenticate(username=email, password=password)
    if auth_user:
        print("   ✅ SUCCESS - User authenticated")
        print(f"   Authenticated as: {auth_user.email}")
    else:
        print("   ❌ FAILED - Authentication returned None")
except Exception as e:
    print(f"   ❌ ERROR: {str(e)}")

# Method 2: authenticate with email parameter
print(f"\n2. Testing: authenticate(email='{email}', password='***')")
try:
    auth_user = authenticate(email=email, password=password)
    if auth_user:
        print("   ✅ SUCCESS - User authenticated")
        print(f"   Authenticated as: {auth_user.email}")
    else:
        print("   ❌ FAILED - Authentication returned None")
except Exception as e:
    print(f"   ❌ ERROR: {str(e)}")

# Method 3: Direct password check
print(f"\n3. Testing: user.check_password('***')")
try:
    if user.check_password(password):
        print("   ✅ SUCCESS - Password is correct")
    else:
        print("   ❌ FAILED - Password is incorrect")
except Exception as e:
    print(f"   ❌ ERROR: {str(e)}")

print("\n" + "="*60)
print("Summary")
print("="*60)

# Final authentication test
auth_user = authenticate(username=email, password=password)
if auth_user and user.check_password(password):
    print("\n✅ LOGIN SHOULD WORK")
    print(f"   Email: {email}")
    print(f"   Password: Malva78*")
    print(f"   User is active: {user.is_active}")
    print(f"\n   You can log in at: http://127.0.0.1:8000/login/")
elif user.check_password(password):
    print("\n⚠️  PASSWORD IS CORRECT BUT AUTHENTICATION FAILED")
    print("   This may indicate an issue with the authentication backend.")
else:
    print("\n❌ WRONG PASSWORD")
    print(f"   The password 'Malva78*' is not correct for {email}")
    print("\n   To set a new password, run:")
    print(f"   python manage.py shell -c \"from transnet_mobility.models import CustomUser; u=CustomUser.objects.get(email='{email}'); u.set_password('Malva78*'); u.save(); print('Password set')\"")

print("\n" + "="*60)
