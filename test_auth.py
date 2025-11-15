"""
Test authentication for malva@gmail.com
Run with: python test_auth.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobility.settings')
django.setup()

from django.contrib.auth import authenticate
from transnet_mobility.models import CustomUser

email = 'malva@gmail.com'
print("=" * 60)
print("Testing Authentication for:", email)
print("=" * 60)

# Check if user exists
try:
    user = CustomUser.objects.get(email=email)
    print(f"✅ User found in database")
    print(f"   - Email: {user.email}")
    print(f"   - Is active: {user.is_active}")
    print(f"   - Role: {user.role}")
    print(f"   - Has password: {bool(user.password)}")
    print(f"   - Password hash: {user.password[:50]}...")
    print()
    
    # Test with common passwords
    test_passwords = ['password', 'Password123', 'admin', 'malva', '12345', 'Malva@123']
    
    print("Testing authentication with common passwords:")
    print("-" * 60)
    
    for pwd in test_passwords:
        print(f"\nTrying password: '{pwd}'")
        
        # Method 1: Using authenticate with username param
        user_auth1 = authenticate(username=email, password=pwd)
        print(f"   authenticate(username=email): {'✅ SUCCESS' if user_auth1 else '❌ FAILED'}")
        
        # Method 2: Using authenticate with email param
        user_auth2 = authenticate(email=email, password=pwd)
        print(f"   authenticate(email=email): {'✅ SUCCESS' if user_auth2 else '❌ FAILED'}")
        
        # Method 3: Direct password check
        is_valid = user.check_password(pwd)
        print(f"   user.check_password(): {'✅ MATCH' if is_valid else '❌ NO MATCH'}")
        
        if user_auth1 or is_valid:
            print(f"\n🎉 FOUND WORKING PASSWORD: '{pwd}'")
            break
    else:
        print("\n❌ None of the test passwords worked.")
        print("\n💡 SOLUTION:")
        print("   1. Try resetting the password, OR")
        print("   2. Register a new account, OR")
        print("   3. Run this to set a test password:")
        print(f"      python manage.py shell -c \"from transnet_mobility.models import CustomUser; u=CustomUser.objects.get(email='{email}'); u.set_password('Malva@123'); u.save(); print('Password set to: Malva@123')\"")
    
except CustomUser.DoesNotExist:
    print(f"❌ User NOT found: {email}")
    print("   Solution: Register first at the registration page")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
