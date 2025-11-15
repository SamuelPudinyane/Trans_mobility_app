"""
Context processors to make common variables available to all templates
"""
from .models import LocomotiveSpec, CargoSpec, LocomotiveAssignment, WagonSpec
from .models import DispatchNotification, DriverAssignmentNotification
from django.db.models import Count, Avg
from datetime import datetime, timedelta

def account_type(request):
    """
    Add account_type to the context of every template
    """
    if request.user.is_authenticated:
        return {
            'Account_type': request.session.get('account_type', request.user.role if hasattr(request.user, 'role') else 'OTHER')
        }
    return {
        'Account_type': None
    }


def dashboard_stats(request):
    """
    Context processor to provide dashboard statistics to all templates
    """
    try:
        # Count trains in terminal (locomotives assigned to drivers)
        trains_in_terminal = LocomotiveAssignment.objects.values('locomotive').distinct().count()
        
        # Count wagons being processed (wagons assigned to locomotives and in use)
        wagons_processing = WagonSpec.objects.filter(
            is_assigned=True,
            status='IN_USE'
        ).count()
        
        # Calculate average dwell time (in minutes)
        # Using created_at to estimate time in system
        # Get cargo created in last 7 days and calculate average age
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_cargo = CargoSpec.objects.filter(
            created_at__gte=seven_days_ago,
            maintenance_status='OPERATIONAL'
        )
        
        if recent_cargo.exists():
            total_minutes = 0
            count = 0
            for cargo in recent_cargo:
                age = datetime.now() - cargo.created_at.replace(tzinfo=None)
                total_minutes += age.total_seconds() / 60
                count += 1
            avg_dwell_time = int(total_minutes / count) if count > 0 else 0
        else:
            avg_dwell_time = 0
        
        # Calculate throughput (wagons per hour)
        # Based on cargo processed in last 24 hours
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        wagons_last_24h = CargoSpec.objects.filter(
            created_at__gte=twenty_four_hours_ago
        ).count()
        throughput_value = wagons_last_24h  # wagons per 24 hours
        
        # Convert to per hour
        throughput_per_hour = round(throughput_value / 24, 1) if throughput_value > 0 else 0
        
        # Get written-off equipment (limit to 5 most recent for dashboard)
        written_off_locomotives = LocomotiveSpec.objects.filter(
            status='WRITTEN_OFF'
        ).order_by('-updated_at')[:5]
        
        written_off_wagons = WagonSpec.objects.filter(
            status='WRITTEN_OFF'
        ).order_by('-updated_at')[:5]
        
        return {
            'trains_in_terminal': trains_in_terminal,
            'wagons_processing': wagons_processing,
            'avg_dwell_time': avg_dwell_time,
            'throughput_value': throughput_per_hour,
            'written_off_locomotives': written_off_locomotives,
            'written_off_wagons': written_off_wagons,
        }
    except Exception as e:
        # Return default values if there's an error
        return {
            'trains_in_terminal': 0,
            'wagons_processing': 0,
            'avg_dwell_time': 0,
            'throughput_value': 0,
            'written_off_locomotives': [],
            'written_off_wagons': [],
        }


def unread_notifications_count(request):
    """
    Context processor to provide unread notifications count to all templates
    """
    if not request.user.is_authenticated:
        return {'unread_notifications_count': 0}
    
    try:
        # Count unread dispatch notifications (for response teams)
        dispatch_count = DispatchNotification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        # Count unread assignment notifications (for drivers)
        assignment_count = DriverAssignmentNotification.objects.filter(
            driver=request.user,
            is_read=False
        ).count()
        
        # Count unread private messages
        from .models import MessageRecipient
        message_count = MessageRecipient.objects.filter(
            recipient=request.user,
            is_read=False,
            is_deleted_by_recipient=False
        ).count()
        
        total_unread = dispatch_count + assignment_count + message_count
        
        return {'unread_notifications_count': total_unread}
    except Exception as e:
        return {'unread_notifications_count': 0}
