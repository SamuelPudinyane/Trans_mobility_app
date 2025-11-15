"""
Quick script to check user status
Run with: python check_user.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobility.settings')
django.setup()

from transnet_mobility.models import CustomUser

# Check malva@gmail.com
email = 'malva@gmail.com'
try:
    user = CustomUser.objects.get(email=email)
    print(f"✅ User found: {email}")
    print(f"   - Is active: {user.is_active}")
    print(f"   - Role: {user.role}")
    print(f"   - Has password: {bool(user.password)}")
    print(f"   - User ID: {user.User_id}")
    print(f"   - Name: {user.first_name} {user.last_name}")
    
    if not user.is_active:
        print("\n⚠️  ISSUE: User account is NOT active (pending admin approval)")
        print("   Solution: An admin needs to activate this account from the 'Manage Users' page")
    
    if not user.password:
        print("\n⚠️  ISSUE: User has no password set")
        print("   Solution: User needs to register or reset password")
    
except CustomUser.DoesNotExist:
    print(f"❌ User NOT found: {email}")
    print("   Solution: User needs to register first")
except Exception as e:
    print(f"❌ Error: {e}")
