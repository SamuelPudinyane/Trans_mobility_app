import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobility.settings')
django.setup()

from transnet_mobility.models import CustomUser, DispatchNotification, DispatchLog, UserLocation

# Check the mechanical maintenance user
print("=" * 60)
print("CHECKING MECHANICAL MAINTENANCE USER")
print("=" * 60)

try:
    malva_user = CustomUser.objects.get(email='malva@gmail.com')
    print(f"✓ User found: {malva_user.email}")
    print(f"  Role: {malva_user.role}")
    print(f"  User ID: {malva_user.User_id}")
    print(f"  Active: {malva_user.is_active}")
    
    # Check user location
    print("\n" + "=" * 60)
    print("CHECKING USER LOCATION DATA")
    print("=" * 60)
    
    user_locations = UserLocation.objects.filter(user=malva_user).order_by('-timestamp')
    if user_locations.exists():
        print(f"✓ Found {user_locations.count()} location record(s)")
        latest = user_locations.first()
        print(f"  Latest location: ({latest.latitude}, {latest.longitude})")
        print(f"  Timestamp: {latest.timestamp}")
    else:
        print("✗ NO LOCATION DATA FOUND!")
        print("  This is why notifications aren't being created!")
        print("  Solution: User needs to share their location from the app")
    
    # Check dispatch logs
    print("\n" + "=" * 60)
    print("CHECKING DISPATCH LOGS")
    print("=" * 60)
    
    dispatch_logs = DispatchLog.objects.filter(
        response_team='MECHANICAL_MAINTENANCE'
    ).order_by('-dispatched_at')
    
    if dispatch_logs.exists():
        print(f"✓ Found {dispatch_logs.count()} dispatch log(s) for MECHANICAL_MAINTENANCE")
        for i, log in enumerate(dispatch_logs[:3], 1):
            print(f"\n  Dispatch #{i}:")
            print(f"    ID: {log.id}")
            print(f"    Response Team: {log.response_team}")
            print(f"    Dispatched at: {log.dispatched_at}")
            print(f"    Dispatched by: {log.dispatched_by.email if log.dispatched_by else 'N/A'}")
            print(f"    Request ID: {log.driver_request.id}")
    else:
        print("✗ No dispatch logs found for MECHANICAL_MAINTENANCE")
    
    # Check notifications for this user
    print("\n" + "=" * 60)
    print("CHECKING NOTIFICATIONS FOR MALVA")
    print("=" * 60)
    
    notifications = DispatchNotification.objects.filter(
        recipient=malva_user
    ).order_by('-created_at')
    
    if notifications.exists():
        print(f"✓ Found {notifications.count()} notification(s)")
        unread = notifications.filter(is_read=False).count()
        print(f"  Unread: {unread}")
        print(f"  Read: {notifications.count() - unread}")
        
        print("\n  Latest notifications:")
        for i, notif in enumerate(notifications[:5], 1):
            print(f"\n  Notification #{i}:")
            print(f"    ID: {notif.id}")
            print(f"    Created: {notif.created_at}")
            print(f"    Is Read: {notif.is_read}")
            print(f"    Distance: {notif.distance_km} km")
            print(f"    Request ID: {notif.dispatch_log.driver_request.id}")
    else:
        print("✗ NO NOTIFICATIONS FOUND!")
        print("\n  Possible reasons:")
        print("  1. No location data for user (most likely)")
        print("  2. User wasn't logged in when dispatch was created")
        print("  3. Wrong role mapping")
    
    # Check all dispatch notifications
    print("\n" + "=" * 60)
    print("ALL DISPATCH NOTIFICATIONS IN DATABASE")
    print("=" * 60)
    
    all_notifications = DispatchNotification.objects.all().order_by('-created_at')
    if all_notifications.exists():
        print(f"Total notifications: {all_notifications.count()}")
        for notif in all_notifications[:10]:
            print(f"  - Recipient: {notif.recipient.email} ({notif.recipient.role})")
            print(f"    Team: {notif.dispatch_log.response_team}")
            print(f"    Created: {notif.created_at}")
            print()
    else:
        print("No notifications in database at all!")

except CustomUser.DoesNotExist:
    print("✗ User malva@gmail.com not found!")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
print("=" * 60)
