import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobility.settings')
django.setup()

from transnet_mobility.models import CustomUser, DispatchNotification, DispatchLog

print("=" * 60)
print("CREATING MISSING NOTIFICATIONS")
print("=" * 60)

# Get all dispatch logs that don't have notifications
dispatch_logs = DispatchLog.objects.all().order_by('-dispatched_at')

for log in dispatch_logs:
    print(f"\nChecking Dispatch Log #{log.id}:")
    print(f"  Response Team: {log.response_team}")
    print(f"  Dispatched at: {log.dispatched_at}")
    
    # Map response team to role
    team_role_map = {
        'ELECTRICAL_MAINTENANCE': 'ELECTRICAL_MAINTENANCE_TEAM',
        'MECHANICAL_MAINTENANCE': 'MECHANICAL_MAINTENANCE_TEAM',
        'EMERGENCY_RESPONSE': 'EMERGENCY_RESPONSE_TEAM',
        'SECURITY': 'SECURITY_TEAM',
        'MEDICAL': 'MEDICAL_TEAM',
        'TOWING': 'TOWING_SERVICE',
    }
    
    target_role = team_role_map.get(log.response_team)
    
    if not target_role:
        print(f"  ✗ No role mapping for {log.response_team}")
        continue
    
    # Get all active team members
    team_members = CustomUser.objects.filter(role=target_role, is_active=True)
    print(f"  Found {team_members.count()} active team member(s) with role {target_role}")
    
    # Check existing notifications for this dispatch
    existing_notifications = DispatchNotification.objects.filter(dispatch_log=log)
    print(f"  Existing notifications: {existing_notifications.count()}")
    
    if existing_notifications.count() == 0:
        print(f"  Creating notifications...")
        created = 0
        for member in team_members:
            # Check if notification already exists for this member
            if not DispatchNotification.objects.filter(dispatch_log=log, recipient=member).exists():
                DispatchNotification.objects.create(
                    dispatch_log=log,
                    recipient=member,
                    distance_km=None  # No distance calculation for retroactive notifications
                )
                print(f"    ✓ Created notification for {member.email}")
                created += 1
        print(f"  Total notifications created: {created}")
    else:
        print(f"  Notifications already exist, skipping")

print("\n" + "=" * 60)
print("DONE!")
print("=" * 60)
