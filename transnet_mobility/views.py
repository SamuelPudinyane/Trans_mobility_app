from django.http import JsonResponse
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as django_logout
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST
from django.core.mail import send_mail
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Count, Q
import json
from decimal import Decimal
from datetime import datetime, date
from django.contrib import messages
import logging
import os
import requests
from datetime import timedelta
from django.utils import timezone
from .user_dummy_data import users
from .models import (
    UserLocation, CustomUser, LocomotiveSpec, CargoSpec, WheelsetSpec, WagonSpec,
    RoutePreferenceSpec, LocomotiveAssignment, FuelSpec, DriverRequest, DispatchLog, DispatchNotification,
    DriverAssignmentNotification, MaintenanceSchedule, MaintenanceStatusUpdate, LocomotiveWagonAssignment,
    PrivateMessage, MessageRecipient, OptimizerRequest, OptimizerResponse, OptimizationLog, Schedule
)
from django.utils import timezone
from math import radians, cos, sin, asin, sqrt
from transnet_mobility.create_or_update_schedule import create_or_update_schedule
from .geocode_utils import get_location_name
from .models import CargoSpec, WheelsetSpec, WagonSpec
from .models import RoutePreferenceSpec, LocomotiveAssignment
from .models import FuelSpec, DriverRequest, DispatchLog, DispatchNotification
from .models import DriverAssignmentNotification
from .models import MaintenanceSchedule, MaintenanceStatusUpdate, LocomotiveWagonAssignment
from .models import PrivateMessage, MessageRecipient
from .models import OptimizerRequest, OptimizerResponse, OptimizationLog
from django.contrib.auth import get_user_model
from django.utils import timezone
from math import radians, cos, sin, asin, sqrt
from transnet_mobility.serializers import ScheduleSerializer
User = get_user_model()

def logout(request):
    """Properly log out the user and clear all session data"""
    auth_logout(request)
    request.session.flush()  # Clear all session data
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')

# Notifications Dashboard
@login_required
def notifications_dashboard(request):
    return render(request, 'notifications_dashboard.html', {'Account_type': request.session.get('account_type', 'ADMIN')})

# Settings Page
@login_required
def settings(request):
    return render(request, 'settings.html', {'Account_type': request.session.get('account_type', 'ADMIN')})

# Data Request Page
@login_required
def data_request(request):
    return render(request, 'data_request.html', {'Account_type': request.session.get('account_type', 'ADMIN')})

@require_GET
def dashboard_stats_api(request):
    from django.utils import timezone
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    locomotives_under_maintenance = MaintenanceSchedule.objects.filter(
        item_type='LOCOMOTIVE',
        status__in=['SCHEDULED', 'IN_PROGRESS']
    ).count()
    pending_tasks = MaintenanceSchedule.objects.filter(
        status='SCHEDULED'
    ).count()
    completed_today = MaintenanceSchedule.objects.filter(
        status='COMPLETED',
        actual_completion_date__gte=today_start
    ).count()
    return JsonResponse({
        'locomotives_under_maintenance': locomotives_under_maintenance,
        'pending_tasks': pending_tasks,
        'completed_today': completed_today
    })


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    Returns distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r

@require_GET
def maintenance_detail_api(request, schedule_id):
    from .models import MaintenanceSchedule, MaintenanceStatusUpdate, CustomUser
    from django.utils.dateformat import format as date_format
    try:
        sched = MaintenanceSchedule.objects.select_related('locomotive','wagon','scheduled_by').get(id=schedule_id)
        # Item name
        if sched.item_type == 'LOCOMOTIVE' and sched.locomotive:
            item_name = sched.locomotive.locomotive
        elif sched.item_type == 'WAGON' and sched.wagon:
            item_name = sched.wagon.wagon_number
        else:
            item_name = 'N/A'
        # Status updates (admin to maintenance response)
        status_updates = [
            {
                'previous_status': su.previous_status,
                'new_status': su.new_status,
                'updated_by': str(su.updated_by) if su.updated_by else 'System',
                'updated_at': date_format(su.created_at, 'Y-m-d H:i'),
                'notes': su.update_notes
            }
            for su in sched.status_updates.all().order_by('created_at')
        ]
        # Attendance log (who viewed/handled)
        attendance = []
        if hasattr(sched, 'attendance_set'):
            for att in sched.attendance_set.all().order_by('timestamp'):
                attendance.append({
                    'user': str(att.user),
                    'role': getattr(att.user, 'role', ''),
                    'timestamp': date_format(att.timestamp, 'Y-m-d H:i')
                })
        # Fallback: no attendance model, skip
        data = {
            'id': sched.id,
            'item_type': sched.item_type,
            'item_name': item_name,
            'status': sched.status,
            'reason': sched.reason,
            'scheduled_by': str(sched.scheduled_by) if sched.scheduled_by else 'N/A',
            'scheduled_date': date_format(sched.scheduled_date, 'Y-m-d H:i'),
            'expected_completion_date': date_format(sched.expected_completion_date, 'Y-m-d H:i'),
            'actual_completion_date': date_format(sched.actual_completion_date, 'Y-m-d H:i') if sched.actual_completion_date else None,
            'status_updates': status_updates,
            'attendance': attendance,
        }
        return JsonResponse(data)
    except MaintenanceSchedule.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)



@login_required
def fuel_matrics(request):
    account_type=request.session.get('account_type')
    
    if account_type=="DRIVER":
        # Get driver's assigned locomotives
        assigned_locos = LocomotiveAssignment.objects.filter(driver=request.user).select_related('locomotive')
        assigned_loco_ids = [a.locomotive.id for a in assigned_locos]
        
        # Filter fuel specs by assigned locomotives only
        fuel_qs = FuelSpec.objects.filter(locomotive_id__in=assigned_loco_ids).select_related('locomotive').order_by('-created_at')
        fuels = []
        for f in fuel_qs:
            fuels.append({
                'id': f.id,
                'daily_fuel_consumption': f.daily_fuel_consumption,
                'fuel_cost_per_litre': f.fuel_cost_per_litre,
                'average_load_per_trip': f.average_load_per_trip,
                'fuel_type': f.fuel_type,
                'locomotive_name': f.locomotive.locomotive if f.locomotive else '',
            })

        if request.method == 'POST':
            try:
                locomotive_id = request.POST.get('locomotive_id')
                if not locomotive_id:
                    messages.error(request, 'Please select a locomotive')
                    return redirect('fuel_matrics')
                
                # Validate driver is assigned to this locomotive
                if int(locomotive_id) not in assigned_loco_ids:
                    messages.error(request, 'You are not assigned to this locomotive')
                    return redirect('fuel_matrics')
                
                locomotive = LocomotiveSpec.objects.filter(id=int(locomotive_id)).first()
                if not locomotive:
                    messages.error(request, 'Invalid locomotive selected')
                    return redirect('fuel_matrics')

                daily = request.POST.get('daily_fuel_consumption') or ''
                cost = request.POST.get('fuel_cost_per_litre') or ''
                avg_load = request.POST.get('average_load_per_trip') or ''
                ftype = request.POST.get('fuel_type') or ''

                # simple survey passthrough if present
                survey_meta = request.POST.getlist('survey_questions[]')
                answers_map = {}
                for key in request.POST:
                    if key.startswith('survey_answers['):
                        base = key.split(']')[0] + ']'
                        vals = request.POST.getlist(key)
                        answers_map[base] = vals

                parts = []
                for idx, meta_json in enumerate(survey_meta):
                    try:
                        meta = json.loads(meta_json)
                    except Exception:
                        continue
                    qtext = meta.get('text','')
                    qtype = meta.get('type','')
                    key1 = f'survey_answers[{idx}]'
                    key2 = f'survey_answers[{idx}][]'
                    ans_list = answers_map.get(key1) or answers_map.get(key2) or []
                    answers_joined = ','.join([str(a) for a in ans_list])
                    block = ','.join([qtext, qtype, answers_joined])
                    parts.append(block)
                survey_raw = ','.join(parts)

                existing = None
                selected_id = request.POST.get('selected_spec_id')
                if selected_id:
                    try:
                        # Only allow editing own entries for assigned locomotives
                        existing = FuelSpec.objects.filter(
                            id=int(selected_id),
                            created_by=request.user,
                            locomotive_id__in=assigned_loco_ids
                        ).first()
                    except Exception:
                        existing = None

                if existing:
                    existing.locomotive = locomotive
                    existing.daily_fuel_consumption = daily
                    existing.fuel_cost_per_litre = cost
                    existing.average_load_per_trip = avg_load
                    existing.fuel_type = ftype
                    existing.survey_raw = survey_raw
                    existing.save()
                    messages.success(request, 'Fuel entry updated')
                else:
                    FuelSpec.objects.create(
                        created_by=request.user,
                        locomotive=locomotive,
                        daily_fuel_consumption=daily,
                        fuel_cost_per_litre=cost,
                        average_load_per_trip=avg_load,
                        fuel_type=ftype,
                        survey_raw=survey_raw,
                    )
                    messages.success(request, 'Fuel entry saved')
                return redirect('fuel_matrics')
            except Exception:
                logging.exception('Failed to save fuel spec')
                messages.error(request, 'Failed to save fuel data')

        # Pass assigned locomotives to template
        locomotives = [{'id': a.locomotive.id, 'name': a.locomotive.locomotive} for a in assigned_locos]
        return render(request, 'fuel_matrics.html', {'Account_type': 'DRIVER', 'fuels': fuels, 'locomotives': locomotives})
    elif account_type=="DRIVER":
        return render(request, 'fuel_matrics.html',{'Account_type':"DRIVER"})

    else:
        return redirect('login')


@login_required
def scheduling_dashboard(request):
    """Render the scheduling dashboard for admins, showing calendar and driver status."""
    context = {}
    return render(request, 'scheduling_dashboard.html', context)

@login_required
def maintanance_scheduling(request):
    account_type = request.session.get('account_type')
    
    # Only allow admin access
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('login')
    
    # Handle POST request for creating new maintenance schedule
    if request.method == 'POST':
        try:
            item_type = request.POST.get('item_type')  # LOCOMOTIVE or WAGON
            item_id = request.POST.get('item_id')
            reason = request.POST.get('reason')
            scheduled_date = request.POST.get('scheduled_date')
            expected_completion_date = request.POST.get('expected_completion_date')
            maintenance_notes = request.POST.get('maintenance_notes', '')
            
            # Validate required fields
            if not all([item_type, item_id, reason, scheduled_date, expected_completion_date]):
                messages.error(request, 'All required fields must be filled.')
                return redirect('maintanance_scheduling')
            
            # Parse dates
            from django.utils.dateparse import parse_datetime
            scheduled_dt = parse_datetime(scheduled_date)
            expected_completion_dt = parse_datetime(expected_completion_date)
            
            if not scheduled_dt or not expected_completion_dt:
                messages.error(request, 'Invalid date format.')
                return redirect('maintanance_scheduling')
            
            if expected_completion_dt <= scheduled_dt:
                messages.error(request, 'Expected completion date must be after scheduled date.')
                return redirect('maintanance_scheduling')
            
            # Create maintenance schedule
            if item_type == 'LOCOMOTIVE':
                locomotive = LocomotiveSpec.objects.get(id=item_id)
                maintenance = MaintenanceSchedule.objects.create(
                    item_type='LOCOMOTIVE',
                    locomotive=locomotive,
                    reason=reason,
                    scheduled_by=request.user,
                    scheduled_date=scheduled_dt,
                    expected_completion_date=expected_completion_dt,
                    maintenance_notes=maintenance_notes,
                    status='SCHEDULED'
                )
                # Update locomotive status
                locomotive.status = 'IN_MAINTENANCE'
                locomotive.maintenance_status = 'UNDER_MAINTENANCE'
                locomotive.save()
                
                messages.success(request, f'Maintenance scheduled for locomotive {locomotive.locomotive}')
                
            elif item_type == 'WAGON':
                wagon = WagonSpec.objects.get(id=item_id)
                maintenance = MaintenanceSchedule.objects.create(
                    item_type='WAGON',
                    wagon=wagon,
                    reason=reason,
                    scheduled_by=request.user,
                    scheduled_date=scheduled_dt,
                    expected_completion_date=expected_completion_dt,
                    maintenance_notes=maintenance_notes,
                    status='SCHEDULED'
                )
                # Update wagon status
                wagon.status = 'IN_MAINTENANCE'
                wagon.save()
                
                messages.success(request, f'Maintenance scheduled for wagon {wagon.wagon_number}')
            
            return redirect('maintanance_scheduling')
            
        except (LocomotiveSpec.DoesNotExist, WagonSpec.DoesNotExist):
            messages.error(request, 'Selected item not found.')
            return redirect('maintanance_scheduling')
        except Exception as e:
            messages.error(request, f'Error scheduling maintenance: {str(e)}')
            return redirect('maintanance_scheduling')
    
    # GET request - display maintenance scheduling page
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    item_type_filter = request.GET.get('item_type', 'all')
    sort_by = request.GET.get('sort_by', 'scheduled_date')
    
    # Get all maintenance schedules (filtered and sorted)
    maintenance_query = MaintenanceSchedule.objects.select_related(
        'locomotive', 'wagon', 'scheduled_by', 'activated_by'
    ).all()

    # Apply filters
    if status_filter != 'all':
        maintenance_query = maintenance_query.filter(status=status_filter)

    if item_type_filter != 'all':
        maintenance_query = maintenance_query.filter(item_type=item_type_filter)

    # Apply sorting
    if sort_by == 'scheduled_date':
        maintenance_query = maintenance_query.order_by('-scheduled_date')
    elif sort_by == 'expected_completion':
        maintenance_query = maintenance_query.order_by('expected_completion_date')
    elif sort_by == 'status':
        maintenance_query = maintenance_query.order_by('status', '-scheduled_date')
    else:
        maintenance_query = maintenance_query.order_by('-scheduled_date')

    maintenance_schedules = list(maintenance_query)

    for schedule in maintenance_schedules:
        last_maintenance = None
        if schedule.item_type == 'LOCOMOTIVE' and schedule.locomotive:
            last_maintenance = MaintenanceSchedule.objects.filter(
                locomotive=schedule.locomotive,
                status='COMPLETED',
                actual_completion_date__isnull=False
            ).order_by('-actual_completion_date').first()
        elif schedule.item_type == 'WAGON' and schedule.wagon:
            last_maintenance = MaintenanceSchedule.objects.filter(
                wagon=schedule.wagon,
                status='COMPLETED',
                actual_completion_date__isnull=False
            ).order_by('-actual_completion_date').first()

        if last_maintenance and last_maintenance.actual_completion_date:
            days_since = (timezone.now() - last_maintenance.actual_completion_date).days
            months_since = days_since / 30.44
            if months_since >= 12:
                schedule.urgency_level = 'CRITICAL'
                schedule.urgency_color = '#dc3545'
            elif months_since >= 9:
                schedule.urgency_level = 'HIGH'
                schedule.urgency_color = '#fd7e14'
            elif months_since >= 6:
                schedule.urgency_level = 'MEDIUM'
                schedule.urgency_color = '#ffc107'
            elif months_since >= 3:
                schedule.urgency_level = 'LOW'
                schedule.urgency_color = '#90ee90'
            else:
                schedule.urgency_level = 'GOOD'
                schedule.urgency_color = '#28a745'
            schedule.days_since_maintenance = days_since
            schedule.last_maintenance_date = last_maintenance.actual_completion_date
        else:
            schedule.urgency_level = 'CRITICAL'
            schedule.urgency_color = '#dc3545'
            schedule.days_since_maintenance = None
            schedule.last_maintenance_date = None

    # Get available locomotives (not in maintenance)
    available_locomotives = LocomotiveSpec.objects.filter(
        is_active=True
    ).exclude(
        status='IN_MAINTENANCE'
    ).order_by('locomotive')

    available_wagons = WagonSpec.objects.filter(
        is_active=True
    ).exclude(
        status='IN_MAINTENANCE'
    ).order_by('wagon_number')

    # Get statistics (avoid repetition by using filtered query only)
    total_schedules = len(maintenance_schedules)
    scheduled_count = sum(1 for s in maintenance_schedules if s.status == 'SCHEDULED')
    in_progress_count = sum(1 for s in maintenance_schedules if s.status == 'IN_PROGRESS')
    completed_count = sum(1 for s in maintenance_schedules if s.status == 'COMPLETED')
    ready_for_activation_count = sum(1 for s in maintenance_schedules if s.status == 'READY_FOR_ACTIVATION')
    locomotive_maintenance_count = sum(1 for s in maintenance_schedules if s.item_type == 'LOCOMOTIVE')
    wagon_maintenance_count = sum(1 for s in maintenance_schedules if s.item_type == 'WAGON')

    context = {
        'Account_type': account_type,
        'maintenance_schedules': maintenance_schedules,
        'available_locomotives': available_locomotives,
        'available_wagons': available_wagons,
        'status_filter': status_filter,
        'item_type_filter': item_type_filter,
        'sort_by': sort_by,
        'total_schedules': total_schedules,
        'scheduled_count': scheduled_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'ready_for_activation_count': ready_for_activation_count,
        'locomotive_maintenance_count': locomotive_maintenance_count,
        'wagon_maintenance_count': wagon_maintenance_count,
    }
    return render(request, 'maintanance_scheduling.html', context)


@login_required
def incident_heatmap(request):
    """Display heatmap of all resolved incidents to identify crime hotspots"""
    account_type = request.session.get('account_type')
    
    # Only admins can view the heatmap
    if account_type != 'ADMIN':
        messages.error(request, 'Only administrators can access the incident heatmap')
        return redirect('login')
    
    # Get filter parameters
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    incident_category = request.GET.get('category', 'all')
    locomotive_filter = request.GET.get('locomotive', '')
    
    # Validate date range
    date_error = None
    if start_date and end_date:
        from django.utils.dateparse import parse_date
        parsed_start = parse_date(start_date)
        parsed_end = parse_date(end_date)
        if parsed_start and parsed_end and parsed_end < parsed_start:
            date_error = "End date cannot be before start date"
            end_date = ''  # Reset end date
    
    # Fetch all requests with location data
    incidents = DriverRequest.objects.select_related('user', 'locomotive').filter(
        latitude__isnull=False,
        longitude__isnull=False
    ).exclude(
        latitude=0,
        longitude=0
    )
    
    # Apply date filters
    if start_date:
        from django.utils.dateparse import parse_date
        parsed_start = parse_date(start_date)
        if parsed_start:
            incidents = incidents.filter(created_at__date__gte=parsed_start)
    
    if end_date:
        from django.utils.dateparse import parse_date
        parsed_end = parse_date(end_date)
        if parsed_end:
            incidents = incidents.filter(created_at__date__lte=parsed_end)
    
    if locomotive_filter:
        incidents = incidents.filter(locomotive_id=locomotive_filter)
    
    # Prepare data for heatmap
    incidents_data = []
    category_counts = {
        'crime': 0,
        'safety': 0,
        'mechanical': 0,
        'other': 0
    }
    
    for incident in incidents:
        # Use driver-selected category (convert to lowercase for consistency)
        incident_type = incident.incident_category.lower() if incident.incident_category else 'other'
        
        # Count by category
        if incident_type in category_counts:
            category_counts[incident_type] += 1
        else:
            category_counts['other'] += 1
        
        # Apply category filter
        if incident_category != 'all' and incident_type != incident_category:
            continue
        
        incidents_data.append({
            'id': incident.id,
            'latitude': float(incident.latitude),
            'longitude': float(incident.longitude),
            'description': incident.issue_description,
            'category': incident_type,
            'status': incident.status,
            'priority': incident.priority,
            'user': f"{incident.user.first_name} {incident.user.last_name}".strip() or incident.user.email,
            'locomotive': incident.locomotive.locomotive if incident.locomotive else 'N/A',
            'created_at': incident.created_at.strftime('%Y-%m-%d %H:%M'),
        })
    
    # Get all locomotives for filter dropdown
    locomotives = LocomotiveSpec.objects.filter(is_active=True).order_by('locomotive')
    
    # Convert incidents data to JSON
    import json
    incidents_json = json.dumps(incidents_data)
    
    context = {
        'Account_type': account_type,
        'incidents': incidents_json,
        'total_incidents': len(incidents_data),
        'category_counts': category_counts,
        'locomotives': locomotives,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'category': incident_category,
            'locomotive': locomotive_filter,
        },
        'date_error': date_error,
    }
    
    return render(request, 'incident_heatmap.html', context)

@login_required
def dispatch_assistance(request, request_id):
    account_type = request.session.get('account_type')
    
    # Only admins can dispatch assistance
    if account_type != 'ADMIN':
        messages.error(request, 'Only administrators can dispatch assistance')
        return redirect('emergency_alerts')
    
    # Get the driver request
    try:
        driver_request = DriverRequest.objects.select_related('user').get(id=request_id)
    except DriverRequest.DoesNotExist:
        messages.error(request, 'Request not found')
        return redirect('emergency_alerts')
    
    if request.method == 'POST':
        try:
            response_team = request.POST.get('response_team')
            estimated_arrival = request.POST.get('estimated_arrival', '')
            response_notes = request.POST.get('response_notes', '')
            new_status = request.POST.get('new_status')
            
            # Update the request status
            driver_request.status = new_status
            driver_request.save()
            
            # Create dispatch log (assigned_personnel removed)
            dispatch_log = DispatchLog.objects.create(
                driver_request=driver_request,
                dispatched_by=request.user,
                response_team=response_team,
                assigned_personnel='',  # Empty since we dispatch to team, not individuals
                estimated_arrival=estimated_arrival if estimated_arrival else None,
                response_notes=response_notes
            )
            
            # Map response team to role
            team_role_map = {
                'ELECTRICAL_MAINTENANCE': 'ELECTRICAL_MAINTENANCE_TEAM',
                'MECHANICAL_MAINTENANCE': 'MECHANICAL_MAINTENANCE_TEAM',
                'EMERGENCY_RESPONSE': 'EMERGENCY_RESPONSE_TEAM',
                'SECURITY': 'SECURITY_TEAM',
                'MEDICAL': 'MEDICAL_TEAM',
                'TOWING': 'TOWING_SERVICE',
            }
            
            target_role = team_role_map.get(response_team)
            
            if target_role:
                # Get active users with this role
                from django.contrib.sessions.models import Session
                from django.utils import timezone
                from datetime import timedelta
                
                # Get active sessions
                active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
                active_user_ids = set()
                
                for session in active_sessions:
                    try:
                        session_data = session.get_decoded()
                        user_pk = session_data.get('_auth_user_id')
                        if user_pk:
                            active_user_ids.add(str(user_pk))
                    except:
                        continue
                
                # Get all response team members (active or not, with or without location)
                team_members = CustomUser.objects.filter(role=target_role, is_active=True)
                
                # Calculate distance for each team member and create notifications
                notifications_created = 0
                nearest_distance = None
                nearest_member = None
                
                for member in team_members:
                    distance = None
                    
                    # Try to get member's location if emergency has coordinates
                    if driver_request.latitude and driver_request.longitude:
                        member_location = UserLocation.objects.filter(
                            user=member
                        ).order_by('-timestamp').first()
                        
                        if member_location:
                            # Calculate distance
                            distance = calculate_distance(
                                driver_request.latitude,
                                driver_request.longitude,
                                member_location.latitude,
                                member_location.longitude
                            )
                            
                            # Track nearest member
                            if nearest_distance is None or distance < nearest_distance:
                                nearest_distance = distance
                                nearest_member = member
                    
                    # Create notification regardless of location data
                    DispatchNotification.objects.create(
                        dispatch_log=dispatch_log,
                        recipient=member,
                        distance_km=distance  # Can be None if no location
                    )
                    notifications_created += 1
                
                if notifications_created > 0:
                    nearest_info = f" Nearest team member: {nearest_member.email} ({nearest_distance:.2f} km away)" if nearest_member and nearest_distance else ""
                    messages.success(
                        request,
                        f'Dispatch successful! {notifications_created} {response_team.replace("_", " ").title()} team member(s) notified.{nearest_info}'
                    )
                else:
                    messages.warning(
                        request,
                        f'{response_team.replace("_", " ").title()} team has no active members.'
                    )
            else:
                messages.success(
                    request,
                    f'{response_team.replace("_", " ").title()} dispatched successfully!'
                )
            
            # Log the dispatch action
            logging.info(f"Admin {request.user.email} dispatched {response_team} for request #{request_id}. ETA: {estimated_arrival}, Notes: {response_notes}")
            
            return redirect('emergency_alerts')
            
        except Exception as e:
            logging.exception('Failed to dispatch assistance')
            messages.error(request, f'Failed to dispatch assistance: {str(e)}')
    
    # Format request data for template
    status_display = driver_request.status.replace('_', ' ')
    status_class = driver_request.status.lower().replace('_', '-')
    
    request_data = {
        'id': driver_request.id,
        'user_email': driver_request.user.email,
        'user_name': f"{driver_request.user.first_name} {driver_request.user.last_name}".strip() or driver_request.user.email,
        'user_role': driver_request.user.role,
        'user_phone': driver_request.user.phone_number or 'N/A',
        'issue_description': driver_request.issue_description,
        'captured_image': driver_request.captured_image.url if driver_request.captured_image else None,
        'latitude': driver_request.latitude,
        'longitude': driver_request.longitude,
        'status': driver_request.status,
        'status_display': status_display,
        'status_class': status_class,
        'created_at': driver_request.created_at,
        'updated_at': driver_request.updated_at,
    }
    
    return render(request, 'dispatch_assistance.html', {
        'Account_type': account_type,
        'request': request_data
    })

@login_required
def dispatch_response(request, notification_id):
    """
    View for dispatch team members to see emergency details and location on map
    """
    account_type = request.session.get('account_type')
    
    try:
        # Get the notification
        notification = DispatchNotification.objects.select_related(
            'dispatch_log__driver_request__user',
            'dispatch_log__dispatched_by',
            'recipient'
        ).get(id=notification_id, recipient=request.user)
        
        # Mark as read if not already
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
        
        driver_request = notification.dispatch_log.driver_request
        dispatch_log = notification.dispatch_log
        
        # Handle status update
        if request.method == 'POST':
            new_status = request.POST.get('status_update')
            response_comment = request.POST.get('response_comment', '')
            
            if new_status in ['IN_PROGRESS', 'RESOLVED']:
                driver_request.status = new_status
                driver_request.save()
                
                messages.success(
                    request,
                    f'Status updated to {new_status.replace("_", " ")}!'
                )
                
                # Log the response
                logging.info(f"Response team member {request.user.email} updated request #{driver_request.id} status to {new_status}. Comment: {response_comment}")
            
            return redirect('dispatch_response', notification_id=notification_id)
        
        # Format data for template
        response_data = {
            'notification_id': notification.id,
            'request_id': driver_request.id,
            'distance_km': notification.distance_km,
            'dispatched_at': dispatch_log.dispatched_at,
            'dispatched_by': f"{dispatch_log.dispatched_by.first_name} {dispatch_log.dispatched_by.last_name}".strip() or dispatch_log.dispatched_by.email,
            'response_team': dispatch_log.response_team.replace('_', ' ').title(),
            'assigned_personnel': dispatch_log.assigned_personnel,
            'estimated_arrival': dispatch_log.estimated_arrival,
            'response_notes': dispatch_log.response_notes,
            'requester_name': f"{driver_request.user.first_name} {driver_request.user.last_name}".strip() or driver_request.user.email,
            'requester_email': driver_request.user.email,
            'requester_phone': driver_request.user.phone_number or 'N/A',
            'requester_role': driver_request.user.role,
            'issue_description': driver_request.issue_description,
            'captured_image': driver_request.captured_image.url if driver_request.captured_image else None,
            'latitude': driver_request.latitude,
            'longitude': driver_request.longitude,
            'status': driver_request.status,
            'status_display': driver_request.status.replace('_', ' '),
            'status_class': driver_request.status.lower().replace('_', '-'),
            'created_at': driver_request.created_at,
            'updated_at': driver_request.updated_at,
        }
        
        return render(request, 'dispatch_response.html', {
            'Account_type': account_type,
            'response': response_data
        })
        
    except DispatchNotification.DoesNotExist:
        messages.error(request, 'Notification not found or you do not have permission to view it.')
        return redirect('my_notifications')

@login_required
def my_notifications(request):
    """View notifications for response team members and drivers"""
    account_type = request.session.get('account_type')
    
    # Get dispatch notifications for response team members
    dispatch_notifications = DispatchNotification.objects.filter(
        recipient=request.user
    ).select_related(
        'dispatch_log__driver_request__user',
        'dispatch_log__dispatched_by'
    ).order_by('-created_at')
    
    # Get assignment notifications for drivers
    assignment_notifications = DriverAssignmentNotification.objects.filter(
        driver=request.user
    ).select_related(
        'assignment__locomotive',
        'assignment__driver'
    ).order_by('-created_at')
    
    # Mark notification as read if requested
    if request.method == 'POST':
        notification_id = request.POST.get('notification_id')
        notification_type = request.POST.get('notification_type')  # 'dispatch' or 'assignment'
        
        if notification_id and notification_type:
            try:
                from django.utils import timezone
                if notification_type == 'dispatch':
                    notif = DispatchNotification.objects.get(id=notification_id, recipient=request.user)
                elif notification_type == 'assignment':
                    notif = DriverAssignmentNotification.objects.get(id=notification_id, driver=request.user)
                else:
                    notif = None
                
                if notif:
                    notif.is_read = True
                    notif.read_at = timezone.now()
                    notif.save()
                    messages.success(request, 'Notification marked as read')
            except (DispatchNotification.DoesNotExist, DriverAssignmentNotification.DoesNotExist):
                pass
        return redirect('my_notifications')
    
    # Format dispatch notification data
    dispatch_data = []
    assignment_data = []
    unread_count = 0
    
    for notif in dispatch_notifications:
        if not notif.is_read:
            unread_count += 1
        
        dr = notif.dispatch_log.driver_request
        dispatch_data.append({
            'id': notif.id,
            'type': 'dispatch',
            'is_read': notif.is_read,
            'created_at': notif.created_at,
            'distance_km': notif.distance_km,
            'request_id': dr.id,
            'request_issue': dr.issue_description,
            'request_latitude': dr.latitude,
            'request_longitude': dr.longitude,
            'request_status': dr.status,
            'requester_name': f"{dr.user.first_name} {dr.user.last_name}".strip() or dr.user.email,
            'requester_email': dr.user.email,
            'requester_phone': dr.user.phone_number or 'N/A',
            'response_team': notif.dispatch_log.response_team.replace('_', ' ').title(),
            'assigned_personnel': notif.dispatch_log.assigned_personnel,
            'response_notes': notif.dispatch_log.response_notes,
            'estimated_arrival': notif.dispatch_log.estimated_arrival,
            'dispatched_by': notif.dispatch_log.dispatched_by.email if notif.dispatch_log.dispatched_by else 'System',
            'dispatched_at': notif.dispatch_log.dispatched_at,
        })
    
    # Format assignment notification data
    for notif in assignment_notifications:
        if not notif.is_read:
            unread_count += 1
        
        assignment_data.append({
            'id': notif.id,
            'type': 'assignment',
            'is_read': notif.is_read,
            'created_at': notif.created_at,
            'notification_type': notif.notification_type,
            'message': notif.message,
            'locomotive_name': notif.assignment.locomotive.locomotive if notif.assignment.locomotive else 'Unknown',
            'locomotive_id': notif.assignment.locomotive.id if notif.assignment.locomotive else None,
        })
    
    # Combine and sort all notifications by creation date
    all_notifications = dispatch_data + assignment_data
    all_notifications.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render(request, 'my_notifications.html', {
        'Account_type': account_type,
        'notifications': all_notifications,
        'unread_count': unread_count,
        'total_count': len(all_notifications),
    })

@login_required
def manage_users(request):
    """
    Admin page to manage user accounts - view, filter, search, and activate pending users
    """
    account_type = request.session.get('account_type')
    
    # Only admins can access
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('login')
    
    # Get filter parameters from GET request
    activation_status = request.GET.get('activation_status', 'all')
    role_filter = request.GET.get('role', 'all')
    search_query = request.GET.get('search', '').strip()
    login_date = request.GET.get('login_date', '')
    
    # Start with all users
    users = CustomUser.objects.all()
    
    # Apply activation status filter
    if activation_status == 'pending':
        users = users.filter(is_active=False)
    elif activation_status == 'active':
        users = users.filter(is_active=True)
    
    # Apply role filter
    if role_filter != 'all':
        users = users.filter(role=role_filter)
    
    # Apply search filter (email or employee number)
    if search_query:
        from django.db.models import Q
        users = users.filter(
            Q(email__icontains=search_query) | 
            Q(employee_number__icontains=search_query)
        )
    
    # Apply login date filter
    if login_date:
        try:
            from datetime import datetime
            filter_date = datetime.strptime(login_date, '%Y-%m-%d').date()
            users = users.filter(last_login__date=filter_date)
        except ValueError:
            messages.warning(request, 'Invalid date format. Please use YYYY-MM-DD.')
    
    # Order by date joined (newest first)
    users = users.order_by('-date_joined')
    
    # Get all users count (without filters)
    total_count = CustomUser.objects.count()
    
    # Separate filtered results into active and pending
    pending_users = users.filter(is_active=False)
    active_users = users.filter(is_active=True)
    
    # Format user data
    pending_users_data = []
    for user in pending_users:
        # Use get_role_display() for human-readable role
        role_display = user.get_role_display() if hasattr(user, 'get_role_display') else (user.role.replace('_', ' ').title() if user.role else 'Other')
        pending_users_data.append({
            'id': user.User_id,
            'email': user.email,
            'full_name': f"{user.first_name} {user.last_name}".strip() or 'N/A',
            'role': role_display,
            'role_value': user.role,
            'employee_number': user.employee_number or 'N/A',
            'mobile_number': user.mobile_number or 'N/A',
            'date_joined': user.date_joined,
            'is_active': user.is_active,
            'driver_status': user.driver_status if hasattr(user, 'driver_status') else None,
            'on_leave_until': user.on_leave_until if hasattr(user, 'on_leave_until') else None,
        })

    active_users_data = []
    for user in active_users:
        # Use get_role_display() for human-readable role
        role_display = user.get_role_display() if hasattr(user, 'get_role_display') else (user.role.replace('_', ' ').title() if user.role else 'Other')
        active_users_data.append({
            'id': user.User_id,
            'email': user.email,
            'full_name': f"{user.first_name} {user.last_name}".strip() or 'N/A',
            'role': role_display,
            'role_value': user.role,
            'employee_number': user.employee_number or 'N/A',
            'mobile_number': user.mobile_number or 'N/A',
            'date_joined': user.date_joined,
            'is_active': user.is_active,
            'last_login': user.last_login,
            'driver_status': user.driver_status if hasattr(user, 'driver_status') else None,
            'on_leave_until': user.on_leave_until if hasattr(user, 'on_leave_until') else None,
        })
    
    # Get available roles for filter dropdown
    role_choices = [
        ('ADMIN', 'Admin'),
        ('DRIVER', 'Driver'),
        ('ELECTRICAL_MAINTENANCE_TEAM', 'Electrical Maintenance Team'),
        ('MECHANICAL_MAINTENANCE_TEAM', 'Mechanical Maintenance Team'),
        ('EMERGENCY_RESPONSE_TEAM', 'Emergency Response Team'),
        ('SECURITY_TEAM', 'Security Team'),
        ('MEDICAL_TEAM', 'Medical Team'),
        ('TOWING_SERVICE', 'Towing Service'),
        ('OTHER', 'Other'),
    ]
    
    return render(request, 'manage_users.html', {
        'Account_type': account_type,
        'pending_users': pending_users_data,
        'active_users': active_users_data,
        'pending_count': len(pending_users_data),
        'active_count': len(active_users_data),
        'total_count': total_count,
        'filtered_count': len(pending_users_data) + len(active_users_data),
        'role_choices': role_choices,
        'current_activation_status': activation_status,
        'current_role': role_filter,
        'current_search': search_query,
        'current_login_date': login_date,
    })

@login_required
def activate_user(request, user_id):
    """
    Activate a user account (admin only)
    """
    account_type = request.session.get('account_type')
    
    # Only admins can activate
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('login')
    
    try:
        user = CustomUser.objects.get(User_id=user_id)
        user.is_active = True
        user.save()
        
        messages.success(
            request,
            f'Account activated successfully! {user.email} can now log in.'
        )
        logging.info(f"Admin {request.user.email} activated account for {user.email}")
        
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found.')
    except Exception as e:
        logging.exception('Failed to activate user')
        messages.error(request, f'Failed to activate user: {str(e)}')
    
    return redirect('manage_users')
@login_required
def deactivate_user(request, user_id):
    """
    Deactivate a user account (admin only)
    """
    account_type = request.session.get('account_type')
    
    # Only admins can deactivate
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('login')
    
    try:
        user = CustomUser.objects.get(User_id=user_id)
        
        # Prevent deactivating yourself
        if user.User_id == request.user.User_id:
            messages.error(request, 'You cannot deactivate your own account.')
            return redirect('manage_users')
        
        user.is_active = False
        user.save()
        
        messages.success(
            request,
            f'Account deactivated successfully! {user.email} can no longer log in.'
        )
        logging.info(f"Admin {request.user.email} deactivated account for {user.email}")
        
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found.')
    except Exception as e:
        logging.exception('Failed to deactivate user')
        messages.error(request, f'Failed to deactivate user: {str(e)}')
    
    return redirect('manage_users')

@login_required
def edit_user_admin(request, user_id):
    """
    Edit user details (admin only)
    """
    account_type = request.session.get('account_type')
    
    # Only admins can edit
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('login')
    
    try:
        user = CustomUser.objects.get(User_id=user_id)
        
        if request.method == 'POST':
            # Get form data
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()
            mobile_number = request.POST.get('mobile_number', '').strip()
            employee_number = request.POST.get('employee_number', '').strip()
            id_number = request.POST.get('id_number', '').strip()
            staff_number = request.POST.get('staff_number', '').strip()
            profession = request.POST.get('profession', '').strip()
            role = request.POST.get('role', '')
            is_active = request.POST.get('is_active') == 'on'
            
            # Validate email uniqueness (except for current user)
            if email != user.email and CustomUser.objects.filter(email=email).exists():
                messages.error(request, 'Email address is already in use by another user.')
                return render(request, 'edit_user_admin.html', {
                    'Account_type': account_type,
                    'edit_user': user,
                    'roles': [
                        ('ADMIN', 'Admin'),
                        ('DRIVER', 'Driver'),
                        ('ELECTRICAL_MAINTENANCE_TEAM', 'Electrical Maintenance Team'),
                        ('MECHANICAL_MAINTENANCE_TEAM', 'Mechanical Maintenance Team'),
                        ('EMERGENCY_RESPONSE_TEAM', 'Emergency Response Team'),
                        ('SECURITY_TEAM', 'Security Team'),
                        ('MEDICAL_TEAM', 'Medical Team'),
                        ('TOWING_SERVICE', 'Towing Service'),
                        ('OTHER', 'Other'),
                    ]
                })
            
            # Update user fields
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.phone_number = phone_number if phone_number else None
            user.mobile_number = mobile_number if mobile_number else None
            user.employee_number = employee_number if employee_number else None
            user.id_number = id_number if id_number else None
            user.staff_number = staff_number if staff_number else None
            user.profession = profession if profession else None
            user.role = role
            user.account_type = role  # Keep role and account_type in sync
            user.is_active = is_active
            
            user.save()
            
            messages.success(
                request,
                f'User {user.email} updated successfully!'
            )
            logging.info(f"Admin {request.user.email} updated user {user.email}")
            
            return redirect('manage_users')
        
        # GET request - show form
        return render(request, 'edit_user_admin.html', {
            'Account_type': account_type,
            'edit_user': user,
            'roles': [
                ('ADMIN', 'Admin'),
                ('DRIVER', 'Driver'),
                ('ELECTRICAL_MAINTENANCE_TEAM', 'Electrical Maintenance Team'),
                ('MECHANICAL_MAINTENANCE_TEAM', 'Mechanical Maintenance Team'),
                ('EMERGENCY_RESPONSE_TEAM', 'Emergency Response Team'),
                ('SECURITY_TEAM', 'Security Team'),
                ('MEDICAL_TEAM', 'Medical Team'),
                ('TOWING_SERVICE', 'Towing Service'),
                ('OTHER', 'Other'),
            ]
        })
        
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('manage_users')
    except Exception as e:
        logging.exception('Failed to edit user')
        messages.error(request, f'Failed to edit user: {str(e)}')
        return redirect('manage_users')

@login_required
def locomotive_dashboard(request):
    """Admin dashboard for managing locomotives and cargo maintenance"""
    account_type = request.session.get('account_type', 'OTHER')
    
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('cargo_specs')
    
    # Get filter parameters
    sort_by = request.GET.get('sort_by', 'urgency')  # urgency, date_asc, date_desc
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Validate date range
    date_error = None
    if start_date and end_date:
        try:
            start_date_obj = timezone.datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = timezone.datetime.strptime(end_date, '%Y-%m-%d')
            if end_date_obj.date() < start_date_obj.date():
                date_error = "End date cannot be before start date"
                messages.warning(request, date_error)
                end_date = ''  # Reset end date
        except ValueError:
            pass
    
    # Get all locomotives with their status
    all_locomotives = LocomotiveSpec.objects.all()
    
    # Categorize locomotives by status
    available_locomotives = all_locomotives.filter(status='AVAILABLE', is_active=True)
    on_duty_locomotives = all_locomotives.filter(status='ON_DUTY')
    in_maintenance_locomotives = all_locomotives.filter(status='IN_MAINTENANCE')
    ready_for_activation = all_locomotives.filter(status='READY_FOR_ACTIVATION')
    
    # Get all cargo with their status
    all_cargo = CargoSpec.objects.all()
    
    # Categorize cargo by status
    available_cargo = all_cargo.filter(status='AVAILABLE', is_active=True)
    in_use_cargo = all_cargo.filter(status='IN_USE')
    in_maintenance_cargo = all_cargo.filter(status='IN_MAINTENANCE')
    ready_cargo = all_cargo.filter(status='READY_FOR_ACTIVATION')
    
    # Get maintenance schedules with filtering - LOCOMOTIVES ONLY
    maintenance_query = MaintenanceSchedule.objects.select_related(
        'locomotive', 'scheduled_by'
    ).filter(
        item_type='LOCOMOTIVE'  # Only show locomotive maintenance
    )
    
    # Apply date range filter
    if start_date:
        try:
            start_date_obj = timezone.datetime.strptime(start_date, '%Y-%m-%d')
            maintenance_query = maintenance_query.filter(scheduled_date__gte=start_date_obj)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = timezone.datetime.strptime(end_date, '%Y-%m-%d')
            end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)
            maintenance_query = maintenance_query.filter(scheduled_date__lte=end_date_obj)
        except ValueError:
            pass
    
    # Get all maintenance records
    all_maintenance = maintenance_query.filter(
        status__in=['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'READY_FOR_ACTIVATION']
    )
    
    # Calculate last maintenance and urgency for each item
    from datetime import timedelta
    from django.db.models import Max
    
    maintenance_list = []
    for maintenance in all_maintenance:
        maintenance.duration = maintenance.get_duration_in_maintenance()
        
        # Get the locomotive
        if not maintenance.locomotive:
            continue
        
        # Get last completed maintenance for this locomotive
        last_maintenance = MaintenanceSchedule.objects.filter(
            locomotive=maintenance.locomotive,
            status='COMPLETED',
            actual_completion_date__isnull=False
        ).order_by('-actual_completion_date').first()
        
        # Calculate days since last maintenance
        if last_maintenance and last_maintenance.actual_completion_date:
            days_since_maintenance = (timezone.now().date() - last_maintenance.actual_completion_date.date()).days
            maintenance.days_since_last = days_since_maintenance
            maintenance.last_maintenance_date = last_maintenance.actual_completion_date
        else:
            # No previous maintenance - consider as very old (365+ days)
            maintenance.days_since_last = 365
            maintenance.last_maintenance_date = None
        
        # Calculate urgency level and color (12 months = 365 days critical threshold)
        if maintenance.days_since_last >= 365:
            maintenance.urgency_level = 'CRITICAL'
            maintenance.urgency_color = '#dc3545'  # Red
            maintenance.urgency_score = 5
        elif maintenance.days_since_last >= 270:
            maintenance.urgency_level = 'HIGH'
            maintenance.urgency_color = '#fd7e14'  # Orange
            maintenance.urgency_score = 4
        elif maintenance.days_since_last >= 180:
            maintenance.urgency_level = 'MEDIUM'
            maintenance.urgency_color = '#ffc107'  # Yellow
            maintenance.urgency_score = 3
        elif maintenance.days_since_last >= 90:
            maintenance.urgency_level = 'LOW'
            maintenance.urgency_color = '#90ee90'  # Light Green
            maintenance.urgency_score = 2
        else:
            maintenance.urgency_level = 'GOOD'
            maintenance.urgency_color = '#28a745'  # Green
            maintenance.urgency_score = 1
        
        maintenance_list.append(maintenance)
    
    # Apply sorting
    if sort_by == 'urgency':
        maintenance_list.sort(key=lambda x: (x.urgency_score, x.scheduled_date), reverse=True)
    elif sort_by == 'date_asc':
        maintenance_list.sort(key=lambda x: x.scheduled_date)
    elif sort_by == 'date_desc':
        maintenance_list.sort(key=lambda x: x.scheduled_date, reverse=True)
    else:
        # Default to urgency if invalid sort_by value
        maintenance_list.sort(key=lambda x: (x.urgency_score, x.scheduled_date), reverse=True)
    
    # Get assignments for on-duty locomotives
    assignments = LocomotiveAssignment.objects.select_related('locomotive', 'driver').all()
    
    # Create a dict of locomotive assignments
    locomotive_assignments = {}
    for assignment in assignments:
        loco_id = assignment.locomotive.id
        if loco_id not in locomotive_assignments:
            locomotive_assignments[loco_id] = []
        locomotive_assignments[loco_id].append({
            'driver_name': f"{assignment.driver.first_name} {assignment.driver.last_name}",
            'driver_email': assignment.driver.email,
            'assigned_at': assignment.assigned_at
        })
    
    # Calculate critical maintenance stats
    critical_count = sum(1 for m in maintenance_list if m.urgency_level == 'CRITICAL')
    high_count = sum(1 for m in maintenance_list if m.urgency_level == 'HIGH')
    
    context = {
        'Account_type': account_type,
        'available_locomotives': available_locomotives,
        'on_duty_locomotives': on_duty_locomotives,
        'in_maintenance_locomotives': in_maintenance_locomotives,
        'ready_for_activation_locomotives': ready_for_activation,
        'available_cargo': available_cargo,
        'in_use_cargo': in_use_cargo,
        'in_maintenance_cargo': in_maintenance_cargo,
        'ready_cargo': ready_cargo,
        'active_maintenance': maintenance_list,
        'locomotive_assignments': locomotive_assignments,
        'sort_by': sort_by,
        'start_date': start_date,
        'end_date': end_date,
        'critical_count': critical_count,
        'high_count': high_count,
    }
    
    return render(request, 'locomotive_dashboard.html', context)

@login_required
def schedule_maintenance(request):
    """Schedule locomotive or cargo for maintenance"""
    account_type = request.session.get('account_type', 'OTHER')
    
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('cargo_specs')
    
    if request.method == 'POST':
        item_type = request.POST.get('item_type')
        item_id = request.POST.get('item_id')
        reason = request.POST.get('reason')
        expected_completion = request.POST.get('expected_completion_date')
        maintenance_notes = request.POST.get('maintenance_notes', '')
        
        try:
            # Get the item being scheduled
            if item_type == 'LOCOMOTIVE':
                locomotive = LocomotiveSpec.objects.get(id=item_id)
                cargo = None
                item_name = locomotive.locomotive or f"Locomotive #{locomotive.id}"
                
                # Update locomotive status
                locomotive.status = 'IN_MAINTENANCE'
                locomotive.maintenance_status = 'UNDER_MAINTENANCE'
                locomotive.save()
                
            elif item_type == 'CARGO':
                cargo = CargoSpec.objects.get(id=item_id)
                locomotive = None
                item_name = cargo.cargo_type or f"Cargo #{cargo.id}"
                
                # Update cargo status
                cargo.status = 'IN_MAINTENANCE'
                cargo.maintenance_status = 'UNDER_MAINTENANCE'
                cargo.save()
            else:
                messages.error(request, 'Invalid item type.')
                return redirect('locomotive_dashboard')
            
            # Create maintenance schedule
            maintenance = MaintenanceSchedule.objects.create(
                item_type=item_type,
                locomotive=locomotive,
                cargo=cargo,
                reason=reason,
                scheduled_by=request.user,
                scheduled_date=timezone.now(),
                expected_completion_date=expected_completion,
                status='IN_PROGRESS',
                maintenance_notes=maintenance_notes
            )
            
            # Create status update record
            MaintenanceStatusUpdate.objects.create(
                maintenance_schedule=maintenance,
                updated_by=request.user,
                previous_status='OPERATIONAL',
                new_status='IN_PROGRESS',
                update_notes=f"Scheduled for maintenance. Reason: {reason}"
            )
            
            messages.success(request, f'{item_name} has been scheduled for maintenance.')
            return redirect('locomotive_dashboard')
            
        except (LocomotiveSpec.DoesNotExist, CargoSpec.DoesNotExist):
            messages.error(request, 'Item not found.')
            return redirect('locomotive_dashboard')
        except Exception as e:
            logging.exception('Failed to schedule maintenance')
            messages.error(request, f'Failed to schedule maintenance: {str(e)}')
            return redirect('locomotive_dashboard')
    
    # GET request - show form
    locomotives = LocomotiveSpec.objects.filter(
        status__in=['AVAILABLE', 'ON_DUTY']
    )
    cargo = CargoSpec.objects.filter(
        status__in=['AVAILABLE', 'IN_USE']
    )
    
    context = {
        'Account_type': account_type,
        'locomotives': locomotives,
        'cargo': cargo,
    }
    
    return render(request, 'schedule_maintenance.html', context)


@login_required
def update_maintenance_status(request, maintenance_id):
    """Update the status of a maintenance schedule"""
    account_type = request.session.get('account_type', 'OTHER')
    
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('cargo_specs')
    
    try:
        maintenance = MaintenanceSchedule.objects.get(id=maintenance_id)
        
        if request.method == 'POST':
            new_status = request.POST.get('new_status')
            update_notes = request.POST.get('update_notes', '')
            
            previous_status = maintenance.status
            
            # Update maintenance status
            maintenance.status = new_status
            
            # If marked as completed, set completion date
            if new_status == 'COMPLETED':
                maintenance.actual_completion_date = timezone.now()
                maintenance.completion_notes = update_notes
                
                # Update item status to READY_FOR_ACTIVATION
                if maintenance.item_type == 'LOCOMOTIVE' and maintenance.locomotive:
                    maintenance.locomotive.status = 'READY_FOR_ACTIVATION'
                    maintenance.locomotive.save()
                elif maintenance.item_type == 'CARGO' and maintenance.cargo:
                    maintenance.cargo.status = 'READY_FOR_ACTIVATION'
                    maintenance.cargo.save()
            
            maintenance.save()
            
            # Create status update record
            MaintenanceStatusUpdate.objects.create(
                maintenance_schedule=maintenance,
                updated_by=request.user,
                previous_status=previous_status,
                new_status=new_status,
                update_notes=update_notes
            )
            
            messages.success(request, f'Maintenance status updated to {new_status}.')
            return redirect('locomotive_dashboard')
        
        # GET request - show update form
        context = {
            'Account_type': account_type,
            'maintenance': maintenance,
            'status_choices': [
                ('SCHEDULED', 'Scheduled'),
                ('IN_PROGRESS', 'In Progress'),
                ('COMPLETED', 'Completed'),
            ]
        }
        
        return render(request, 'update_maintenance_status.html', context)
        
    except MaintenanceSchedule.DoesNotExist:
        messages.error(request, 'Maintenance schedule not found.')
        return redirect('locomotive_dashboard')
    except Exception as e:
        logging.exception('Failed to update maintenance status')
        messages.error(request, f'Failed to update status: {str(e)}')
        return redirect('locomotive_dashboard')
@login_required
def activate_item(request, item_type, item_id):
    """Activate a locomotive or cargo after maintenance"""
    account_type = request.session.get('account_type', 'OTHER')
    
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('cargo_specs')
    
    try:
        if item_type == 'locomotive':
            item = LocomotiveSpec.objects.get(id=item_id)
            item.status = 'AVAILABLE'
            item.maintenance_status = 'OPERATIONAL'
            item.is_active = True
            item.save()
            item_name = item.locomotive or f"Locomotive #{item.id}"
            
            # Update maintenance schedule
            maintenance = MaintenanceSchedule.objects.filter(
                locomotive=item,
                status='READY_FOR_ACTIVATION'
            ).first()
            
        elif item_type == 'cargo':
            item = CargoSpec.objects.get(id=item_id)
            item.status = 'AVAILABLE'
            item.maintenance_status = 'OPERATIONAL'
            item.is_active = True
            item.save()
            item_name = item.cargo_type or f"Cargo #{item.id}"
            
            # Update maintenance schedule
            maintenance = MaintenanceSchedule.objects.filter(
                cargo=item,
                status='READY_FOR_ACTIVATION'
            ).first()
        else:
            messages.error(request, 'Invalid item type.')
            return redirect('locomotive_dashboard')
        
        if maintenance:
            maintenance.status = 'ACTIVATED'
            maintenance.activated_by = request.user
            maintenance.activated_at = timezone.now()
            maintenance.save()
            
            # Create status update record
            MaintenanceStatusUpdate.objects.create(
                maintenance_schedule=maintenance,
                updated_by=request.user,
                previous_status='READY_FOR_ACTIVATION',
                new_status='ACTIVATED',
                update_notes=f'Activated by admin and returned to service.'
            )
        
        messages.success(request, f'{item_name} has been activated and is now available for use.')
        return redirect('locomotive_dashboard')
        
    except (LocomotiveSpec.DoesNotExist, CargoSpec.DoesNotExist):
        messages.error(request, 'Item not found.')
        return redirect('locomotive_dashboard')
    except Exception as e:
        logging.exception('Failed to activate item')
        messages.error(request, f'Failed to activate item: {str(e)}')
        return redirect('locomotive_dashboard')


@login_required
def maintenance_details(request, maintenance_id):
    """View detailed maintenance history and status updates"""
    account_type = request.session.get('account_type', 'OTHER')
    
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('cargo_specs')
    
    try:
        maintenance = MaintenanceSchedule.objects.select_related(
            'locomotive', 'cargo', 'scheduled_by', 'activated_by'
        ).get(id=maintenance_id)
        
        # Get all status updates
        status_updates = maintenance.status_updates.select_related('updated_by').all()
        
        # Calculate duration
        duration = maintenance.get_duration_in_maintenance()
        
        context = {
            'Account_type': account_type,
            'maintenance': maintenance,
            'status_updates': status_updates,
            'duration': duration,
        }
        
        return render(request, 'maintenance_details.html', context)
        
    except MaintenanceSchedule.DoesNotExist:
        messages.error(request, 'Maintenance schedule not found.')
        return redirect('locomotive_dashboard')
@login_required
def write_off_locomotive(request, loco_id):
    """Write off a locomotive (mark as no longer in use)"""
    account_type = request.session.get('account_type')
    
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('locomotive_config')
    
    try:
        locomotive = LocomotiveSpec.objects.get(id=loco_id)
        
        # Check if locomotive is currently assigned to drivers
        assignments = LocomotiveAssignment.objects.filter(locomotive=locomotive)
        if assignments.exists():
            messages.error(request, f'Cannot write off {locomotive.locomotive} - it is currently assigned to drivers. Complete trips first.')
            return redirect('locomotive_config')
        
        # Check if locomotive has wagons assigned
        from .models import LocomotiveWagonAssignment
        wagon_assignments = LocomotiveWagonAssignment.objects.filter(locomotive=locomotive)
        if wagon_assignments.exists():
            messages.warning(request, f'Unassigning {wagon_assignments.count()} wagon(s) from {locomotive.locomotive}')
            # Release wagons
            for wa in wagon_assignments:
                wagon = wa.wagon
                wagon.is_assigned = False
                wagon.status = 'AVAILABLE'
                wagon.save()
            wagon_assignments.delete()
        
        # Mark as written off
        locomotive.status = 'WRITTEN_OFF'
        locomotive.maintenance_status = 'WRITTEN_OFF'
        locomotive.is_active = False
        locomotive.save()
        
        messages.success(request, f'Locomotive {locomotive.locomotive} has been written off successfully.')
        return redirect('locomotive_config')
        
    except LocomotiveSpec.DoesNotExist:
        messages.error(request, 'Locomotive not found.')
        return redirect('locomotive_config')
    except Exception as e:
        logging.exception('Failed to write off locomotive')
        messages.error(request, f'Failed to write off locomotive: {str(e)}')
        return redirect('locomotive_config')


@login_required
def delete_locomotive(request, loco_id):
    """Permanently delete a locomotive"""
    account_type = request.session.get('account_type')
    
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('locomotive_config')
    
    try:
        locomotive = LocomotiveSpec.objects.get(id=loco_id)
        
        # Check if locomotive is currently assigned
        assignments = LocomotiveAssignment.objects.filter(locomotive=locomotive)
        if assignments.exists():
            messages.error(request, f'Cannot delete {locomotive.locomotive} - it is currently assigned to drivers. Complete trips and write off first.')
            return redirect('locomotive_config')
        
        loco_name = locomotive.locomotive
        locomotive.delete()
        
        messages.success(request, f'Locomotive {loco_name} has been permanently deleted.')
        return redirect('locomotive_config')
        
    except LocomotiveSpec.DoesNotExist:
        messages.error(request, 'Locomotive not found.')
        return redirect('locomotive_config')
    except Exception as e:
        logging.exception('Failed to delete locomotive')
        messages.error(request, f'Failed to delete locomotive: {str(e)}')
        return redirect('locomotive_config')


@login_required
def write_off_wagon(request, wagon_id):
    """Write off a wagon (mark as no longer in use)"""
    account_type = request.session.get('account_type')
    
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('wagon_specs')
    
    try:
        wagon = WagonSpec.objects.get(id=wagon_id)
        
        # Check if wagon is currently assigned
        from .models import LocomotiveWagonAssignment
        assignment = LocomotiveWagonAssignment.objects.filter(wagon=wagon).first()
        if assignment:
            messages.error(request, f'Cannot write off {wagon.wagon_number} - it is currently assigned to locomotive {assignment.locomotive.locomotive}. Unassign it first.')
            return redirect('wagon_specs')
        
        # Mark as written off
        wagon.status = 'WRITTEN_OFF'
        wagon.is_active = False
        wagon.is_assigned = False
        wagon.save()
        
        messages.success(request, f'Wagon {wagon.wagon_number} has been written off successfully.')
        return redirect('wagon_specs')
        
    except WagonSpec.DoesNotExist:
        messages.error(request, 'Wagon not found.')
        return redirect('wagon_specs')
    except Exception as e:
        logging.exception('Failed to write off wagon')
        messages.error(request, f'Failed to write off wagon: {str(e)}')
        return redirect('wagon_specs')


@login_required
def delete_wagon(request, wagon_id):
    """Permanently delete a wagon"""
    account_type = request.session.get('account_type')
    
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('wagon_specs')
    
    try:
        wagon = WagonSpec.objects.get(id=wagon_id)
        
        # Check if wagon is currently assigned
        from .models import LocomotiveWagonAssignment
        assignment = LocomotiveWagonAssignment.objects.filter(wagon=wagon).first()
        if assignment:
            messages.error(request, f'Cannot delete {wagon.wagon_number} - it is currently assigned. Unassign and write off first.')
            return redirect('wagon_specs')
        
        wagon_number = wagon.wagon_number
        wagon.delete()
        
        messages.success(request, f'Wagon {wagon_number} has been permanently deleted.')
        return redirect('wagon_specs')
        
    except WagonSpec.DoesNotExist:
        messages.error(request, 'Wagon not found.')
        return redirect('wagon_specs')
    except Exception as e:
        logging.exception('Failed to delete wagon')
        messages.error(request, f'Failed to delete wagon: {str(e)}')
        return redirect('wagon_specs')
@login_required
def wagon_dashboard(request):
    """Admin dashboard for managing wagons and maintenance"""
    account_type = request.session.get('account_type', 'OTHER')
    
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('wagon_specs')
    
    # Get filter parameters
    item_type_filter = request.GET.get('item_type', 'ALL')  # ALL, WAGON, LOCOMOTIVE
    sort_by = request.GET.get('sort_by', 'urgency')  # urgency, date_asc, date_desc
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    locomotive_filter = request.GET.get('locomotive', '')  # Filter by locomotive
    
    # Validate date range
    date_error = None
    if start_date and end_date:
        try:
            start_date_obj = timezone.datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = timezone.datetime.strptime(end_date, '%Y-%m-%d')
            if end_date_obj.date() < start_date_obj.date():
                date_error = "End date cannot be before start date"
                messages.warning(request, date_error)
                end_date = ''  # Reset end date
        except ValueError:
            pass
    
    # Get all wagons with their status
    all_wagons = WagonSpec.objects.all()
    
    # Apply locomotive filter to in-use wagons
    if locomotive_filter:
        # Get wagon IDs assigned to the filtered locomotive
        filtered_wagon_ids = LocomotiveWagonAssignment.objects.filter(
            locomotive_id=locomotive_filter,
            wagon__isnull=False
        ).values_list('wagon_id', flat=True)
        
        # Filter wagons
        in_use_wagons = all_wagons.filter(status='IN_USE', id__in=filtered_wagon_ids)
    else:
        in_use_wagons = all_wagons.filter(status='IN_USE')
    
    # Categorize wagons by status
    available_wagons = all_wagons.filter(status='AVAILABLE', is_active=True)
    in_maintenance_wagons = all_wagons.filter(status='IN_MAINTENANCE')
    ready_for_activation = all_wagons.filter(status='READY_FOR_ACTIVATION')
    written_off_wagons = all_wagons.filter(is_active=False)
    
    # Get active wagon assignments
    wagon_assignments = LocomotiveWagonAssignment.objects.select_related(
        'locomotive', 'wagon'
    ).filter(wagon__isnull=False)
    
    # Group assignments by wagon
    wagon_assignment_map = {}
    for assignment in wagon_assignments:
        wagon_id = assignment.wagon.id
        if wagon_id not in wagon_assignment_map:
            from django.shortcuts import get_object_or_404
            def wagon_dashboard(request, wagon_id=None):
                """Admin dashboard for managing wagons and maintenance. If wagon_id is provided, show only that wagon's details and maintenance history."""
                account_type = request.session.get('account_type', 'OTHER')
                if account_type != 'ADMIN':
                    messages.error(request, 'Access denied. Admin privileges required.')
                    return redirect('wagon_specs')

                # Get filter parameters
                item_type_filter = request.GET.get('item_type', 'ALL')
                sort_by = request.GET.get('sort_by', 'urgency')
                start_date = request.GET.get('start_date', '')
                end_date = request.GET.get('end_date', '')
                locomotive_filter = request.GET.get('locomotive', '')

                # Validate date range
                if start_date and end_date:
                    try:
                        start_date_obj = timezone.datetime.strptime(start_date, '%Y-%m-%d')
                        end_date_obj = timezone.datetime.strptime(end_date, '%Y-%m-%d')
                        if end_date_obj.date() < start_date_obj.date():
                            messages.warning(request, "End date cannot be before start date")
                            end_date = ''
                    except ValueError:
                        pass

                # If wagon_id is provided, filter for that wagon only
                if wagon_id:
                    all_wagons = WagonSpec.objects.filter(id=wagon_id)
                else:
                    all_wagons = WagonSpec.objects.all()

                # Apply locomotive filter to in-use wagons
                if locomotive_filter:
                    filtered_wagon_ids = LocomotiveWagonAssignment.objects.filter(
                        locomotive_id=locomotive_filter,
                        wagon__isnull=False
                    ).values_list('wagon_id', flat=True)
                    in_use_wagons = all_wagons.filter(status='IN_USE', id__in=filtered_wagon_ids)
                else:
                    in_use_wagons = all_wagons.filter(status='IN_USE')

                available_wagons = all_wagons.filter(status='AVAILABLE', is_active=True)
                in_maintenance_wagons = all_wagons.filter(status='IN_MAINTENANCE')
                ready_for_activation = all_wagons.filter(status='READY_FOR_ACTIVATION')
                written_off_wagons = all_wagons.filter(is_active=False)

                wagon_assignments = LocomotiveWagonAssignment.objects.select_related('locomotive', 'wagon').filter(wagon__isnull=False)
                wagon_assignment_map = {}
                for assignment in wagon_assignments:
                    wagon_id_map = assignment.wagon.id
                    if wagon_id_map not in wagon_assignment_map:
                        wagon_assignment_map[wagon_id_map] = []
                    wagon_assignment_map[wagon_id_map].append({
                        'locomotive': assignment.locomotive.locomotive,
                        'assigned_at': assignment.assigned_at,
                        'assigned_by': assignment.assigned_by
                    })

                total_wagons = all_wagons.count()
                total_capacity = sum([w.payload_capacity for w in all_wagons if w.payload_capacity])
                total_in_use_capacity = sum([w.payload_capacity for w in in_use_wagons if w.payload_capacity])

                for wagon in in_use_wagons:
                    wagon.assignments = wagon_assignment_map.get(wagon.id, [])

                wagon_types_qs = all_wagons.values('wagon_type').annotate(count=Count('id')).order_by('-count')
                wagon_types = [{'wagon_type': w['wagon_type'], 'count': w['count']} for w in wagon_types_qs]

                from django.utils import timezone
                from datetime import timedelta

                # Maintenance schedules: if wagon_id, filter for that wagon only
                maintenance_query = MaintenanceSchedule.objects.select_related('wagon', 'scheduled_by').filter(item_type='WAGON')
                if wagon_id:
                    maintenance_query = maintenance_query.filter(wagon_id=wagon_id)
                else:
                    maintenance_query = maintenance_query.filter(status__in=['SCHEDULED', 'IN_PROGRESS'])

                if start_date:
                    try:
                        start_date_obj = timezone.datetime.strptime(start_date, '%Y-%m-%d')
                        maintenance_query = maintenance_query.filter(scheduled_date__gte=start_date_obj)
                    except ValueError:
                        pass
                if end_date:
                    try:
                        end_date_obj = timezone.datetime.strptime(end_date, '%Y-%m-%d')
                        end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)
                        maintenance_query = maintenance_query.filter(scheduled_date__lte=end_date_obj)
                    except ValueError:
                        pass

                all_maintenance = list(maintenance_query)
                maintenance_list = []
                critical_count = 0
                high_count = 0
                for schedule in all_maintenance:
                    last_maintenance = MaintenanceSchedule.objects.filter(
                        wagon=schedule.wagon,
                        status='COMPLETED',
                        actual_completion_date__isnull=False
                    ).order_by('-actual_completion_date').first()
                    if last_maintenance and last_maintenance.actual_completion_date:
                        last_maintenance_date = last_maintenance.actual_completion_date
                        days_since_last = (timezone.now() - last_maintenance_date).days
                    else:
                        last_maintenance_date = None
                        days_since_last = 999
                    if days_since_last >= 365:
                        urgency_level = 'CRITICAL'
                        urgency_color = '#dc3545'
                        critical_count += 1
                    elif days_since_last >= 270:
                        urgency_level = 'HIGH'
                        urgency_color = '#fd7e14'
                        high_count += 1
                    elif days_since_last >= 180:
                        urgency_level = 'MEDIUM'
                        urgency_color = '#ffc107'
                    elif days_since_last >= 90:
                        urgency_level = 'LOW'
                        urgency_color = '#90ee90'
                    else:
                        urgency_level = 'GOOD'
                        urgency_color = '#28a745'
                    maintenance_list.append({
                        'id': schedule.id,
                        'wagon': schedule.wagon,
                        'reason': schedule.reason,
                        'scheduled_date': schedule.scheduled_date,
                        'expected_completion_date': schedule.expected_completion_date,
                        'status': schedule.status,
                        'get_status_display': schedule.get_status_display(),
                        'urgency_level': urgency_level,
                        'urgency_color': urgency_color,
                        'last_maintenance_date': last_maintenance_date,
                        'days_since_last': days_since_last if days_since_last != 999 else 'Never',
                    })

                if sort_by == 'urgency':
                    urgency_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'GOOD': 4}
                    maintenance_list.sort(key=lambda x: (urgency_order.get(x['urgency_level'], 5), x['scheduled_date']))
                elif sort_by == 'date_asc':
                    maintenance_list.sort(key=lambda x: x['scheduled_date'])
                elif sort_by == 'date_desc':
                    maintenance_list.sort(key=lambda x: x['scheduled_date'], reverse=True)
                else:
                    urgency_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'GOOD': 4}
                    maintenance_list.sort(key=lambda x: (urgency_order.get(x['urgency_level'], 5), x['scheduled_date']))

                locomotives_with_wagons = LocomotiveSpec.objects.filter(
                    is_active=True,
                    id__in=LocomotiveWagonAssignment.objects.filter(
                        wagon__isnull=False
                    ).values_list('locomotive_id', flat=True).distinct()
                ).order_by('locomotive')

                context = {
                    'Account_type': account_type,
                    'available_wagons': available_wagons,
                    'in_use_wagons': in_use_wagons,
                    'in_maintenance_wagons': in_maintenance_wagons,
                    'ready_for_activation_wagons': ready_for_activation,
                    'written_off_wagons': written_off_wagons,
                    'wagon_assignment_map': wagon_assignment_map,
                    'total_wagons': total_wagons,
                    'total_capacity': total_capacity,
                    'total_in_use_capacity': total_in_use_capacity,
                    'maintenance_schedules': maintenance_list,
                    'wagon_types': wagon_types,
                    'item_type_filter': item_type_filter,
                    'sort_by': sort_by,
                    'start_date': start_date,
                    'end_date': end_date,
                    'critical_count': critical_count,
                    'high_count': high_count,
                    'locomotives': locomotives_with_wagons,
                    'locomotive_filter': locomotive_filter,
                    'single_wagon': all_wagons.first() if wagon_id else None,
                    'show_single_wagon': bool(wagon_id),
                }
                return render(request, 'wagon_dashboard.html', context)
    wagons = WagonSpec.objects.filter(
        status__in=['AVAILABLE', 'IN_USE'],
        is_active=True
    )
    
    context = {
        'Account_type': account_type,
        'wagons': wagons,
    }
    
    return render(request, 'schedule_wagon_maintenance.html', context)


@login_required
def update_wagon_maintenance_status(request, maintenance_id):
    """Update wagon maintenance status"""
    account_type = request.session.get('account_type', 'OTHER')
    
    if account_type not in ['ADMIN', 'MECHANICAL_MAINTENANCE_TEAM']:
        messages.error(request, 'Access denied. Insufficient privileges.')
        return redirect('wagon_dashboard')
    
    if request.method == 'POST':
        new_status = request.POST.get('new_status')
        update_notes = request.POST.get('update_notes', '')
        
        try:
            maintenance = MaintenanceSchedule.objects.get(id=maintenance_id, item_type='WAGON')
            previous_status = maintenance.status
            
            # Update maintenance status
            maintenance.status = new_status
            
            if new_status == 'COMPLETED':
                maintenance.actual_completion_date = timezone.now()
                # Update wagon status
                if maintenance.wagon:
                    maintenance.wagon.status = 'READY_FOR_ACTIVATION'
                    maintenance.wagon.maintenance_status = 'OPERATIONAL'
                    maintenance.wagon.save()
            
            elif new_status == 'READY_FOR_ACTIVATION':
                # Wagon is ready to be put back in service
                if maintenance.wagon:
                    maintenance.wagon.status = 'READY_FOR_ACTIVATION'
                    maintenance.wagon.save()
            
            maintenance.save()
            
            # Create status update record
            MaintenanceStatusUpdate.objects.create(
                maintenance_schedule=maintenance,
                updated_by=request.user,
                previous_status=previous_status,
                new_status=new_status,
                update_notes=update_notes
            )
            
            messages.success(request, f'Maintenance status updated to {new_status}')
            return redirect('wagon_dashboard')
            
        except MaintenanceSchedule.DoesNotExist:
            messages.error(request, 'Maintenance schedule not found.')
            return redirect('wagon_dashboard')
        except Exception as e:
            logging.exception('Failed to update wagon maintenance status')
            messages.error(request, f'Failed to update status: {str(e)}')
            return redirect('wagon_dashboard')
    
    return redirect('wagon_dashboard')


@login_required
def activate_wagon(request, wagon_id):
    """Activate a wagon that is ready for activation"""
    account_type = request.session.get('account_type', 'OTHER')
    
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('wagon_dashboard')
    
    try:
        wagon = WagonSpec.objects.get(id=wagon_id)
        
        if wagon.status == 'READY_FOR_ACTIVATION':
            wagon.status = 'AVAILABLE'
            wagon.is_active = True
            wagon.maintenance_status = 'OPERATIONAL'
            wagon.save()
            
            messages.success(request, f'Wagon {wagon.wagon_number} has been activated and is now available.')
        else:
            messages.warning(request, f'Wagon is not ready for activation. Current status: {wagon.status}')
        
        return redirect('wagon_dashboard')
        
    except WagonSpec.DoesNotExist:
        messages.error(request, 'Wagon not found.')
        return redirect('wagon_dashboard')
    except Exception as e:
        logging.exception('Failed to activate wagon')
        messages.error(request, f'Failed to activate wagon: {str(e)}')
        return redirect('wagon_dashboard')


@login_required
def wagon_maintenance_details(request, maintenance_id):
    """View detailed information about a wagon maintenance schedule"""
    account_type = request.session.get('account_type', 'OTHER')
    
    try:
        maintenance = MaintenanceSchedule.objects.select_related(
            'wagon', 'scheduled_by'
        ).get(id=maintenance_id, item_type='WAGON')
        
        # Get all status updates for this maintenance
        status_updates = MaintenanceStatusUpdate.objects.filter(
            maintenance_schedule=maintenance
        ).select_related('updated_by').order_by('-created_at')
        
        # Calculate duration
        maintenance.duration = maintenance.get_duration_in_maintenance()
        
        context = {
            'Account_type': account_type,
            'maintenance': maintenance,
            'status_updates': status_updates,
        }
        
        return render(request, 'wagon_maintenance_details.html', context)
        
    except MaintenanceSchedule.DoesNotExist:
        messages.error(request, 'Maintenance schedule not found.')
        return redirect('wagon_dashboard')
    except Exception as e:
        logging.exception('Failed to load wagon maintenance details')
        messages.error(request, f'Failed to load details: {str(e)}')
        return redirect('wagon_dashboard')

# Private Messaging Views
@login_required
def search_users(request):
    """API endpoint to search users by name, email, or employee number"""
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'users': []})
    
    # Search users by first name, last name, email, or employee number
    users = User.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query) |
        Q(employee_number__icontains=query)
    ).exclude(pk=request.user.pk).values(
        'User_id', 'first_name', 'last_name', 'email', 'employee_number', 'role'
    )[:10]  # Limit to 10 results
    
    users_list = [{
        'id': user['User_id'],
        'name': f"{user['first_name']} {user['last_name']}".strip() or user['email'],
        'email': user['email'],
        'employee_number': user['employee_number'] or 'N/A',
        'role': user['role']
    } for user in users]
    
    return JsonResponse({'users': users_list})

@login_required
def send_message(request):
    """Send a private message to one or more users"""
    from .models import PrivateMessage, MessageRecipient
    
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        recipient_ids = request.POST.getlist('recipient_ids[]')
        is_group = request.POST.get('is_group') == 'true'
        target_role = request.POST.get('target_role', '')
        parent_id = request.POST.get('parent_id')  # For replies
        
        if not message:
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'}, status=400)
        
        try:
            # Create the message
            private_message = PrivateMessage.objects.create(
                sender=request.user,
                subject=subject or 'No Subject',
                message=message,
                is_group_message=is_group,
                target_role=target_role if is_group else None,
                parent_message_id=parent_id if parent_id else None
            )
            
            # Create recipients
            recipients = []
            if is_group and target_role:
                # Admin sending to a role/group
                if target_role == 'ALL':
                    users = User.objects.exclude(pk=request.user.pk)
                else:
                    users = User.objects.filter(role=target_role).exclude(pk=request.user.pk)
                
                for user in users:
                    MessageRecipient.objects.create(
                        message=private_message,
                        recipient=user
                    )
                    recipients.append(user.email)
            else:
                # Individual message(s)
                for recipient_id in recipient_ids:
                    try:
                        recipient = User.objects.get(User_id=recipient_id)
                        MessageRecipient.objects.create(
                            message=private_message,
                            recipient=recipient
                        )
                        recipients.append(recipient.email)
                    except User.DoesNotExist:
                        pass
            
            return JsonResponse({
                'success': True,
                'message': f'Message sent to {len(recipients)} recipient(s)',
                'recipients': recipients
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required
def get_messages(request):
    """Get all messages for the current user (inbox)"""
    from .models import MessageRecipient
    
    # Get messages where user is a recipient
    message_recipients = MessageRecipient.objects.filter(
        recipient=request.user,
        is_deleted_by_recipient=False
    ).select_related(
        'message__sender',
        'message__parent_message__sender'
    ).order_by('-message__created_at')
    
    messages_list = []
    unread_count = 0
    
    for mr in message_recipients:
        msg = mr.message
        if not mr.is_read:
            unread_count += 1
        
        messages_list.append({
            'id': msg.id,
            'recipient_id': mr.id,
            'subject': msg.subject,
            'message': msg.message,
            'sender_name': f"{msg.sender.first_name} {msg.sender.last_name}".strip() or msg.sender.email,
            'sender_email': msg.sender.email,
            'sender_id': msg.sender.User_id,
            'is_read': mr.is_read,
            'read_at': mr.read_at.isoformat() if mr.read_at else None,
            'created_at': msg.created_at.isoformat(),
            'is_group_message': msg.is_group_message,
            'target_role': msg.target_role if msg.is_group_message else None,
            'is_reply': msg.parent_message is not None,
            'parent_id': msg.parent_message.id if msg.parent_message else None,
            'parent_subject': msg.parent_message.subject if msg.parent_message else None,
        })
    
    return JsonResponse({
        'messages': messages_list,
        'unread_count': unread_count,
        'total_count': len(messages_list)
    })


@login_required
def get_sent_messages(request):
    """Get messages sent by the current user"""
    from .models import PrivateMessage, MessageRecipient
    
    # Get messages sent by user
    sent_messages = PrivateMessage.objects.filter(
        sender=request.user
    ).prefetch_related('recipients').order_by('-created_at')
    
    messages_list = []
    
    for msg in sent_messages:
        # Get recipients info
        recipients = MessageRecipient.objects.filter(message=msg).select_related('recipient')
        recipient_names = [
            f"{r.recipient.first_name} {r.recipient.last_name}".strip() or r.recipient.email
            for r in recipients
        ]
        
        messages_list.append({
            'id': msg.id,
            'subject': msg.subject,
            'message': msg.message,
            'recipients': recipient_names,
            'recipient_count': recipients.count(),
            'created_at': msg.created_at.isoformat(),
            'is_group_message': msg.is_group_message,
            'target_role': msg.target_role if msg.is_group_message else None,
            'is_reply': msg.parent_message is not None,
        })
    
    return JsonResponse({
        'messages': messages_list,
        'total_count': len(messages_list)
    })


@login_required
def mark_message_read(request, recipient_id):
    """Mark a message as read"""
    from .models import MessageRecipient
    
    if request.method == 'POST':
        try:
            mr = MessageRecipient.objects.get(id=recipient_id, recipient=request.user)
            if not mr.is_read:
                mr.is_read = True
                mr.read_at = timezone.now()
                mr.save()
            return JsonResponse({'success': True, 'message': 'Message marked as read'})
        except MessageRecipient.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Message not found'}, status=404)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required
def delete_message(request, recipient_id):
    """Delete a message (marks as deleted for recipient)"""
    from .models import MessageRecipient
    
    if request.method == 'POST':
        try:
            mr = MessageRecipient.objects.get(id=recipient_id, recipient=request.user)
            mr.is_deleted_by_recipient = True
            mr.save()
            return JsonResponse({'success': True, 'message': 'Message deleted'})
        except MessageRecipient.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Message not found'}, status=404)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)



@login_required
@csrf_exempt
def request_optimization(request):
    """
    API endpoint to request optimization from external system
    POST /api/optimizer/request/
    Body: {
        "optimization_type": "ROUTE_OPTIMIZATION" | "LOAD_BALANCING" | etc.,
        "parameters": {...}  // optional specific parameters
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Check if user is admin
    if request.session.get('account_type') != 'ADMIN':
        return JsonResponse({'error': 'Unauthorized. Admin access required.'}, status=403)
    
    try:
        data = json.loads(request.body)
        optimization_type = data.get('optimization_type', 'FULL_SYSTEM')
        custom_parameters = data.get('parameters', {})
        
        # Collect system data
        system_data = collect_system_data(optimization_type)
        system_data.update(custom_parameters)
        
        # Create optimizer request record
        optimizer_request = OptimizerRequest.objects.create(
            optimization_type=optimization_type,
            requested_by=request.user,
            request_payload=system_data,
            status='PENDING'
        )
        
        # Log the request
        OptimizationLog.objects.create(
            optimizer_request=optimizer_request,
            log_type='REQUEST',
            message=f'Optimization request created for {optimization_type}',
            details={'request_id': optimizer_request.request_id}
        )
        
        # Send request to external optimizer API
        try:
            headers = {
                'Authorization': f'Bearer {OPTIMIZER_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            external_response = requests.post(
                f'{OPTIMIZER_API_BASE_URL}/optimize',
                json={
                    'request_id': optimizer_request.request_id,
                    'data': system_data
                },
                headers=headers,
                timeout=30
            )
            
            optimizer_request.optimizer_endpoint = f'{OPTIMIZER_API_BASE_URL}/optimize'
            optimizer_request.status = 'PROCESSING'
            
            if external_response.status_code == 200:
                response_data = external_response.json()
                optimizer_request.external_request_id = response_data.get('external_request_id')
                optimizer_request.save()
                
                OptimizationLog.objects.create(
                    optimizer_request=optimizer_request,
                    log_type='INFO',
                    message='Request successfully sent to external optimizer',
                    details={'status_code': external_response.status_code}
                )
                
                return JsonResponse({
                    'success': True,
                    'request_id': optimizer_request.request_id,
                    'status': 'PROCESSING',
                    'message': 'Optimization request submitted successfully',
                    'external_request_id': optimizer_request.external_request_id
                })
            else:
                optimizer_request.status = 'FAILED'
                optimizer_request.save()
                
                OptimizationLog.objects.create(
                    optimizer_request=optimizer_request,
                    log_type='ERROR',
                    message='External optimizer returned error',
                    details={
                        'status_code': external_response.status_code,
                        'response': external_response.text
                    }
                )
                
                return JsonResponse({
                    'success': False,
                    'error': 'External optimizer error',
                    'details': external_response.text
                }, status=500)
                
        except requests.exceptions.RequestException as e:
            # If external API fails, we can still process locally or queue for later
            optimizer_request.status = 'FAILED'
            optimizer_request.save()
            
            OptimizationLog.objects.create(
                optimizer_request=optimizer_request,
                log_type='ERROR',
                message=f'Failed to connect to external optimizer: {str(e)}',
                details={'error': str(e)}
            )
            
            return JsonResponse({
                'success': False,
                'error': 'Failed to connect to external optimizer',
                'request_id': optimizer_request.request_id,
                'message': 'Request saved for retry. You will be notified when results are available.'
            }, status=500)
            
    except Exception as e:
        logging.exception('Error creating optimization request')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def receive_optimization_results(request):
    """
    Webhook endpoint for external optimizer to send results
    POST /api/optimizer/results/
    Body: {
        "request_id": "uuid",
        "suggestions": [...],
        "metrics": {...}
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        request_id = data.get('request_id')
        
        # Verify API key or authentication
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer ') or auth_header.split(' ')[1] != OPTIMIZER_API_KEY:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        # Find the optimizer request
        try:
            optimizer_request = OptimizerRequest.objects.get(request_id=request_id)
        except OptimizerRequest.DoesNotExist:
            return JsonResponse({'error': 'Request not found'}, status=404)
        
        # Update request status
        optimizer_request.status = 'COMPLETED'
        optimizer_request.processed_at = timezone.now()
        optimizer_request.save()
        
        # Process suggestions
        suggestions = data.get('suggestions', [])
        for suggestion in suggestions:
            OptimizerResponse.objects.create(
                optimizer_request=optimizer_request,
                suggestion_type=suggestion.get('type', 'GENERAL'),
                title=suggestion.get('title', 'Optimization Suggestion'),
                description=suggestion.get('description', ''),
                priority=suggestion.get('priority', 'MEDIUM'),
                expected_improvement=suggestion.get('expected_improvement', {}),
                current_metrics=suggestion.get('current_metrics', {}),
                projected_metrics=suggestion.get('projected_metrics', {}),
                implementation_steps=suggestion.get('implementation_steps', []),
                raw_response=suggestion
            )
        
        # Log the response
        OptimizationLog.objects.create(
            optimizer_request=optimizer_request,
            log_type='RESPONSE',
            message=f'Received {len(suggestions)} optimization suggestions',
            details={'suggestion_count': len(suggestions)}
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Results received and processed',
            'suggestions_count': len(suggestions)
        })
        
    except Exception as e:
        logging.exception('Error processing optimization results')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def get_optimization_suggestions(request):
    """
    API endpoint to retrieve optimization suggestions for admin
    GET /api/optimizer/suggestions/
    Query params: ?status=PENDING_REVIEW&priority=HIGH
    """
    if request.session.get('account_type') != 'ADMIN':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        # Filter parameters
        status = request.GET.get('status', None)
        priority = request.GET.get('priority', None)
        suggestion_type = request.GET.get('type', None)
        
        suggestions = OptimizerResponse.objects.select_related(
            'optimizer_request', 'reviewed_by'
        ).all()
        
        if status:
            suggestions = suggestions.filter(implementation_status=status)
        if priority:
            suggestions = suggestions.filter(priority=priority)
        if suggestion_type:
            suggestions = suggestions.filter(suggestion_type=suggestion_type)
        
        # Limit to recent suggestions
        suggestions = suggestions[:50]
        
        results = []
        for suggestion in suggestions:
            results.append({
                'id': suggestion.id,
                'request_id': suggestion.optimizer_request.request_id,
                'optimization_type': suggestion.optimizer_request.optimization_type,
                'suggestion_type': suggestion.suggestion_type,
                'title': suggestion.title,
                'description': suggestion.description,
                'priority': suggestion.priority,
                'implementation_status': suggestion.implementation_status,
                'expected_improvement': suggestion.expected_improvement,
                'current_metrics': suggestion.current_metrics,
                'projected_metrics': suggestion.projected_metrics,
                'implementation_steps': suggestion.implementation_steps,
                'created_at': suggestion.created_at.isoformat(),
                'reviewed_by': suggestion.reviewed_by.email if suggestion.reviewed_by else None,
                'reviewed_at': suggestion.reviewed_at.isoformat() if suggestion.reviewed_at else None,
                'review_notes': suggestion.review_notes
            })
        
        return JsonResponse({
            'success': True,
            'suggestions': results,
            'count': len(results)
        })
        
    except Exception as e:
        logging.exception('Error retrieving optimization suggestions')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
def update_suggestion_status(request, suggestion_id):
    """
    API endpoint to update the status of an optimization suggestion
    POST /api/optimizer/suggestions/<id>/update/
    Body: {
        "status": "APPROVED" | "REJECTED" | "IMPLEMENTED",
        "notes": "Review notes..."
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    if request.session.get('account_type') != 'ADMIN':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        suggestion = OptimizerResponse.objects.get(id=suggestion_id)
        
        data = json.loads(request.body)
        new_status = data.get('status')
        notes = data.get('notes', '')
        
        suggestion.implementation_status = new_status
        suggestion.review_notes = notes
        suggestion.reviewed_by = request.user
        suggestion.reviewed_at = timezone.now()
        suggestion.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Suggestion status updated',
            'suggestion_id': suggestion.id,
            'new_status': new_status
        })
        
    except OptimizerResponse.DoesNotExist:
        return JsonResponse({'error': 'Suggestion not found'}, status=404)
    except Exception as e:
        logging.exception('Error updating suggestion status')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def optimization_dashboard(request):
    """
    Dashboard view for optimization suggestions and requests
    """
    if request.session.get('account_type') != 'ADMIN':
        messages.error(request, 'Unauthorized access')
        return redirect('login')
    
    account_type = request.session.get('account_type', 'OTHER')
    
    # Get optimization requests
    recent_requests = OptimizerRequest.objects.select_related('requested_by').order_by('-created_at')[:10]
    
    # Get pending suggestions
    pending_suggestions = OptimizerResponse.objects.filter(
        implementation_status='PENDING_REVIEW'
    ).select_related('optimizer_request').order_by('-priority', '-created_at')
    
    # Get high priority suggestions
    high_priority = OptimizerResponse.objects.filter(
        priority='HIGH',
        implementation_status__in=['PENDING_REVIEW', 'APPROVED']
    ).select_related('optimizer_request')[:5]
    
    # Statistics
    stats = {
        'total_requests': OptimizerRequest.objects.count(),
        'pending_requests': OptimizerRequest.objects.filter(status='PENDING').count(),
        'processing_requests': OptimizerRequest.objects.filter(status='PROCESSING').count(),
        'completed_requests': OptimizerRequest.objects.filter(status='COMPLETED').count(),
        'total_suggestions': OptimizerResponse.objects.count(),
        'pending_suggestions': OptimizerResponse.objects.filter(implementation_status='PENDING_REVIEW').count(),
        'approved_suggestions': OptimizerResponse.objects.filter(implementation_status='APPROVED').count(),
        'implemented_suggestions': OptimizerResponse.objects.filter(implementation_status='IMPLEMENTED').count(),
    }
    
    context = {
        'Account_type': account_type,
        'recent_requests': recent_requests,
        'pending_suggestions': pending_suggestions,
        'high_priority': high_priority,
        'stats': stats,
    }
    
    return render(request, 'optimization_dashboard.html', context)
@csrf_exempt
def map_location_railway(request):
    # Pass through emergency marker context if present
    highlight_lat = request.GET.get('lat')
    highlight_lng = request.GET.get('lng')
    highlight_user = request.GET.get('user')
    highlight_issue = request.GET.get('issue')
    context = {}
    if highlight_lat and highlight_lng:
        context['highlight_lat'] = highlight_lat
        context['highlight_lng'] = highlight_lng
        context['highlight_user'] = highlight_user
        context['highlight_issue'] = highlight_issue
    return render(request, 'map_location_railway.html', context)

@login_required
def get_all_driver_details(request):
    drivers = CustomUser.objects.filter(role='DRIVER').values('User_id', 'email', 'first_name', 'last_name', 'driver_status')
    return JsonResponse({'drivers': list(drivers)})

# --- User status change handler ---
@login_required
@require_POST
def change_user_status(request, user_id):
   
    if not request.user.is_superuser and request.session.get('account_type') != 'ADMIN':
        messages.error(request, 'Only admins can change user status.')
        return redirect('manage_users')
    try:
        user = CustomUser.objects.get(User_id=user_id)
        new_status = request.POST.get('driver_status')
        if new_status not in ['available', 'on_leave', 'emergency']:
            messages.error(request, 'Invalid status.')
            return redirect('manage_users')

        old_status = user.driver_status
        # Handle on_leave_until logic for both on_leave and emergency
        if new_status in ['on_leave', 'emergency']:
            on_leave_until_str = request.POST.get('on_leave_until')
            print(f"[DEBUG] on_leave_until_str: {on_leave_until_str}")
            if on_leave_until_str:
                try:
                    on_leave_until = datetime.strptime(on_leave_until_str, '%Y-%m-%d').date()
                except Exception as e:
                    print(f"[DEBUG] Exception parsing on_leave_until_str: {e}")
                    on_leave_until = None
            else:
                on_leave_until = None
            print(f"[DEBUG] on_leave_until (parsed): {on_leave_until}")
            print(f"[DEBUG] timezone.now().date(): {timezone.now().date()}")
            user.on_leave_until = on_leave_until
            # If the date is today or in the past, set status to available immediately
            if on_leave_until and on_leave_until <= timezone.now().date():
                print("[DEBUG] Setting status to available (on_leave_until is today or past)")
                user.driver_status = 'available'
                user.on_leave_until = None
            else:
                print(f"[DEBUG] Setting status to {new_status} (on_leave_until is future or not set)")
                user.driver_status = new_status
        else:
            user.on_leave_until = None
            user.driver_status = new_status
        user.save(update_fields=['driver_status', 'on_leave_until'])

        # If status is on_leave or emergency, unassign from schedules/assignments
        if user.driver_status in ['on_leave', 'emergency']:
            # Remove from future schedules as driver or assistant
            Schedule.objects.filter(
                (Q(driver=user) | Q(assistant=user)),
                date__gte=timezone.now().date(),
                status__in=['available', 'assigned']
            ).update(status='cancelled')
            # Remove from locomotive assignments
            LocomotiveAssignment.objects.filter(
                Q(driver=user) | Q(assistant=user),
                status='assigned'
            ).update(status='cancelled')

        # Send notification to user and admin
        subject = 'Your availability status has changed'
        message = f'Hello {user.get_full_name() or user.email},\n\nYour availability status has been changed to: {new_status}. If this was not expected, please contact your admin.'
        send_mail(subject, message, 'noreply@transnet.com', [user.email])
        # Notify all admins
        admin_emails = list(CustomUser.objects.filter(account_type='ADMIN').values_list('email', flat=True))
        if admin_emails:
            send_mail(f'User {user.get_full_name() or user.email} status changed',
                      f'{user.get_full_name() or user.email} status changed from {old_status} to {new_status}.',
                      'noreply@transnet.com', admin_emails)

        messages.success(request, f"Status for {user.get_full_name() or user.email} updated to {new_status}.")
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found.')
    return redirect('manage_users')

# Restore load_strategic view to render the load_strategic.html template
@login_required
def load_strategic(request):
    # You can add context with strategic load data if needed
    return render(request, 'load_strategic.html', {})


# Restore route_corridor view to render the route_corridor.html template
@login_required
def route_corridor(request):
    # You can add context with corridor data if needed
    return render(request, 'route_corridor.html', {})

# Notification dashboard for all users
@login_required
def notifications_dashboard(request):
    from .models import DispatchNotification
    notifications = DispatchNotification.objects.filter(recipient=request.user).order_by('-created_at')
    return render(request, 'notifications.html', {'notifications': notifications})



@csrf_exempt
def map_location(request):
    # Restore: render map_location.html with emergency marker context if present
    highlight_lat = request.GET.get('lat')
    highlight_lng = request.GET.get('lng')
    highlight_user = request.GET.get('user')
    highlight_issue = request.GET.get('issue')
    context = {}
    if highlight_lat and highlight_lng:
        context['highlight_lat'] = highlight_lat
        context['highlight_lng'] = highlight_lng
        context['highlight_user'] = highlight_user
        context['highlight_issue'] = highlight_issue
    return render(request, 'map_location.html', context)


# --- Wagon-Locomotive Assignment (Many-to-Many) ---
@login_required
@require_http_methods(["GET", "POST"])
def wagon_locomotive_assignment(request):
    """Admin interface to assign/remove multiple locomotives per wagon and show total power."""
    account_type = request.session.get('account_type')
    if account_type != "ADMIN":
        return redirect('login')

    from .models import LocomotiveSpec, WagonSpec, LocomotiveWagonAssignment
    from django.contrib import messages

    wagons = WagonSpec.objects.filter(is_active=True).order_by('wagon_number')
    locomotives = LocomotiveSpec.objects.filter(is_active=True, maintenance_status='OPERATIONAL').order_by('locomotive')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'assign':
            wagon_id = request.POST.get('wagon_id')
            locomotive_ids = request.POST.getlist('locomotive_ids[]') or request.POST.getlist('locomotive_ids')
            if not wagon_id or not locomotive_ids:
                messages.error(request, 'Please select a wagon and at least one locomotive.')
                return redirect('wagon_locomotive_assignment')
            try:
                wagon = WagonSpec.objects.get(id=int(wagon_id))
            except Exception:
                messages.error(request, 'Selected wagon not found.')
                return redirect('wagon_locomotive_assignment')
            assigned_count = 0
            for loco_id in locomotive_ids:
                try:
                    loco = LocomotiveSpec.objects.get(id=int(loco_id))
                    # Prevent duplicate assignment
                    if LocomotiveWagonAssignment.objects.filter(wagon=wagon, locomotive=loco).exists():
                        continue
                    LocomotiveWagonAssignment.objects.create(wagon=wagon, locomotive=loco, assigned_by=request.user)
                    assigned_count += 1
                except Exception:
                    continue
            if assigned_count:
                messages.success(request, f'Assigned {assigned_count} locomotive(s) to wagon {wagon.wagon_number}.')
            return redirect('wagon_locomotive_assignment')
        elif action == 'unassign':
            assignment_id = request.POST.get('assignment_id')
            if assignment_id:
                try:
                    assignment = LocomotiveWagonAssignment.objects.get(id=int(assignment_id))
                    assignment.delete()
                    messages.success(request, f'Removed locomotive assignment.')
                except Exception:
                    messages.error(request, 'Failed to remove assignment.')
            return redirect('wagon_locomotive_assignment')

    # Prefetch assignments for template efficiency
    for wagon in wagons:
        # Attach helper properties for template
        wagon.locomotive_assignments = wagon.locomotivewagonassignment_set.select_related('locomotive')
        wagon.get_assigned_locomotives = [a.locomotive for a in wagon.locomotive_assignments]
        wagon.get_total_locomotive_power = getattr(wagon, 'get_total_locomotive_power', lambda: 0)()

    return render(request, 'wagon_locomotive_assignment.html', {
        'Account_type': 'ADMIN',
        'wagons': wagons,
        'locomotives': locomotives,
    })

# Restore route_and_node_preference view to render the route_and_node_preference.html template
@login_required
def route_and_node_preference(request):
    # You can add context with route/node preference data if needed
    return render(request, 'route_and_node_preference.html', {})


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('username')  # form field is named 'username' but contains email
        password = request.POST.get('password')
        
        # Authenticate the user using email
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            # Check if account is active
            if not user.is_active:
                messages.error(request, "Your account is pending admin approval. Please wait for activation.")
                return render(request, 'login.html')
            
            # Log the user in
            login(request, user)
            # Persist useful user info in the session so other endpoints (e.g. update_location)
            # can read it without extra lookups. Keys are short and safe to store.
            request.session['account_type'] = user.role
            request.session['user_id'] = getattr(user, 'User_id', None)
            request.session['user_email'] = getattr(user, 'email', '')
            # full name fallback
            fullname = ' '.join(filter(None, [getattr(user, 'first_name', ''), getattr(user, 'last_name', '')])).strip()
            request.session['user_fullname'] = fullname or getattr(user, 'email', '')
            request.session['user_phone'] = getattr(user, 'phone_number', '') if hasattr(user, 'phone_number') else ''
            
            # Redirect based on role/account_type
            account_type = user.role
            if account_type == "DRIVER":
                return redirect('cargo_specs')
            elif account_type == "ADMIN":
                return redirect('driver_assignment')
            elif account_type == "STAFF":
                return redirect('staff_dashboard')
            elif account_type == "ELECTRICAL_MAINTENANCE_TEAM":
                return redirect('electrical_maintenance_dashboard')
            elif account_type == "MECHANICAL_MAINTENANCE_TEAM":
                return redirect('mechanical_maintenance_dashboard')
            elif account_type == "EMERGENCY_RESPONSE_TEAM":
                return redirect('emergency_response_dashboard')
            elif account_type == "SECURITY_TEAM":
                return redirect('security_team_dashboard')
            elif account_type == "MEDICAL_TEAM":
                return redirect('medical_team_dashboard')
            elif account_type == "TOWING_SERVICE":
                return redirect('towing_service_dashboard')
            elif account_type == "Security":
                return redirect('security_guard_report')
            elif account_type == "Security Supervisor":
                return redirect('security_supervisor')
            else:
                return redirect('cargo_specs')  # fallback to cargo specs
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, 'login.html')


@login_required
def password_reset(request):
    return render(request, 'password_reset.html')


@login_required
def home(request):
    return render(request, 'edit_user.html')


@login_required
def electrical_maintenance_dashboard(request):
    # Get unread notifications for this user
    unread_notifications = DispatchNotification.objects.filter(
        recipient=request.user,
        is_read=False
    ).select_related(
        'dispatch_log__driver_request__user'
    ).order_by('-created_at')[:5]  # Show latest 5
    
    # Format notifications with area name
    from .geocode_utils import get_location_name
    notifications_data = []
    for notif in unread_notifications:
        dr = notif.dispatch_log.driver_request
        area_name = get_location_name(dr.latitude, dr.longitude) if dr.latitude and dr.longitude else 'Unknown location'
        notifications_data.append({
            'id': notif.id,
            'request_id': dr.id,
            'issue': dr.issue_description,
            'requester': f"{dr.user.first_name} {dr.user.last_name}".strip() or dr.user.email,
            'distance_km': notif.distance_km,
            'created_at': notif.created_at,
            'latitude': dr.latitude,
            'longitude': dr.longitude,
            'area_name': area_name,
        })
    
    return render(request, 'electrical_maintenance_dashboard.html', {
        'notifications': notifications_data,
        'unread_count': len(notifications_data)
    })


@login_required
def mechanical_maintenance_dashboard(request):
    # Get maintenance assignments for mechanical maintenance user
    # Count locomotives currently under maintenance
    locomotives_under_maintenance = MaintenanceSchedule.objects.filter(
        item_type='LOCOMOTIVE',
        status__in=['SCHEDULED', 'IN_PROGRESS']
    ).count()
    
    print(f"DEBUG: locomotives_under_maintenance = {locomotives_under_maintenance}")
    
    # Count pending tasks (scheduled but not started)
    pending_tasks = MaintenanceSchedule.objects.filter(
        status='SCHEDULED'
    ).count()
    
    print(f"DEBUG: pending_tasks = {pending_tasks}")
    
    # Count tasks completed today
    from django.utils import timezone
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = MaintenanceSchedule.objects.filter(
        status='COMPLETED',
        actual_completion_date__gte=today_start
    ).count()
    
    print(f"DEBUG: completed_today = {completed_today}")
    print(f"DEBUG: Total MaintenanceSchedule count = {MaintenanceSchedule.objects.count()}")
    
    # Get all active maintenance tasks assigned to/visible by mechanical maintenance
    active_maintenance = MaintenanceSchedule.objects.filter(
        status__in=['SCHEDULED', 'IN_PROGRESS']
    ).select_related('locomotive', 'cargo', 'scheduled_by').order_by('-created_at')
    
    # Get maintenance tasks in progress (for quick access)
    in_progress_tasks = MaintenanceSchedule.objects.filter(
        status='IN_PROGRESS'
    ).select_related('locomotive', 'cargo', 'scheduled_by').order_by('-updated_at')
    
    # Get recently completed tasks
    completed_tasks = MaintenanceSchedule.objects.filter(
        status__in=['COMPLETED', 'READY_FOR_ACTIVATION']
    ).select_related('locomotive', 'cargo', 'scheduled_by').order_by('-updated_at')[:5]
    
    # Get unread notifications for this user
    unread_notifications = DispatchNotification.objects.filter(
        recipient=request.user,
        is_read=False
    ).select_related(
        'dispatch_log__driver_request__user'
    ).order_by('-created_at')[:5]
    
    # Format notifications
    notifications_data = []
    for notif in unread_notifications:
        dr = notif.dispatch_log.driver_request
        notifications_data.append({
            'id': notif.id,
            'request_id': dr.id,
            'issue': dr.issue_description,
            'requester': f"{dr.user.first_name} {dr.user.last_name}".strip() or dr.user.email,
            'distance_km': notif.distance_km,
            'created_at': notif.created_at,
            'latitude': dr.latitude,
            'longitude': dr.longitude,
        })
    
    return render(request, 'mechanical_maintenance_dashboard.html', {
        'locomotives_under_maintenance': locomotives_under_maintenance,
        'pending_tasks': pending_tasks,
        'completed_today': completed_today,
        'active_maintenance': active_maintenance,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
        'notifications': notifications_data,
        'unread_count': len(notifications_data),
        'Account_type': 'MECHANICAL_MAINTENANCE'
    })


@login_required
def emergency_response_dashboard(request):
    # Get unread notifications for this user
    unread_notifications = DispatchNotification.objects.filter(
        recipient=request.user,
        is_read=False
    ).select_related(
        'dispatch_log__driver_request__user'
    ).order_by('-created_at')[:5]  # Show latest 5
    
    # Format notifications
    notifications_data = []
    for notif in unread_notifications:
        dr = notif.dispatch_log.driver_request
        notifications_data.append({
            'id': notif.id,
            'request_id': dr.id,
            'issue': dr.issue_description,
            'requester': f"{dr.user.first_name} {dr.user.last_name}".strip() or dr.user.email,
            'distance_km': notif.distance_km,
            'created_at': notif.created_at,
            'latitude': dr.latitude,
            'longitude': dr.longitude,
        })
    
    return render(request, 'emergency_response_dashboard.html', {
        'notifications': notifications_data,
        'unread_count': len(notifications_data)
    })


@login_required
def mechanical_maintenance_update(request, maintenance_id):
    """Allow mechanical maintenance users to update maintenance status with progress tracking"""
    from django.utils import timezone
    
    maintenance = MaintenanceSchedule.objects.filter(id=maintenance_id).select_related(
        'locomotive', 'cargo', 'scheduled_by'
    ).first()
    
    if not maintenance:
        messages.error(request, 'Maintenance task not found')
        return redirect('mechanical_maintenance_dashboard')
    
    # Get all status updates for this maintenance (history/timeline)
    status_history = MaintenanceStatusUpdate.objects.filter(
        maintenance_schedule=maintenance
    ).select_related('updated_by').order_by('created_at')
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        update_notes = request.POST.get('update_notes', '').strip()
        
        if not new_status:
            messages.error(request, 'Please select a status')
            return redirect('mechanical_maintenance_update', maintenance_id=maintenance_id)
        
        # Validate status transition
        valid_transitions = {
            'SCHEDULED': ['IN_PROGRESS'],
            'IN_PROGRESS': ['COMPLETED'],
            'COMPLETED': [],  # Only admin can move to READY_FOR_ACTIVATION
        }
        
        if maintenance.status in valid_transitions:
            if new_status not in valid_transitions[maintenance.status]:
                messages.error(request, f'Invalid status transition from {maintenance.status} to {new_status}')
                return redirect('mechanical_maintenance_update', maintenance_id=maintenance_id)
        
        # Update maintenance status
        old_status = maintenance.status
        maintenance.status = new_status
        
        # If marking as completed, set completion date
        if new_status == 'COMPLETED' and not maintenance.actual_completion_date:
            maintenance.actual_completion_date = timezone.now()
            if update_notes:
                maintenance.completion_notes = update_notes
        
        # Update maintenance notes
        if update_notes and new_status != 'COMPLETED':
            if maintenance.maintenance_notes:
                maintenance.maintenance_notes += f"\n\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}]\n{update_notes}"
            else:
                maintenance.maintenance_notes = f"[{timezone.now().strftime('%Y-%m-%d %H:%M')}]\n{update_notes}"
        
        maintenance.save()
        
        # Create status update record for tracking
        MaintenanceStatusUpdate.objects.create(
            maintenance_schedule=maintenance,
            previous_status=old_status,
            new_status=new_status,
            updated_by=request.user,
            update_notes=update_notes or ''
        )
        
        messages.success(request, f'Maintenance status updated to {new_status}')
        return redirect('mechanical_maintenance_update', maintenance_id=maintenance_id)
    
    # Calculate duration so far
    if maintenance.status == 'IN_PROGRESS':
        time_in_progress = timezone.now() - maintenance.updated_at
        days_in_progress = time_in_progress.days
        hours_in_progress = time_in_progress.seconds // 3600
    else:
        days_in_progress = 0
        hours_in_progress = 0
    
    return render(request, 'mechanical_maintenance_update.html', {
        'maintenance': maintenance,
        'status_history': status_history,
        'days_in_progress': days_in_progress,
        'hours_in_progress': hours_in_progress,
        'Account_type': 'MECHANICAL_MAINTENANCE'
    })


@login_required
def security_team_dashboard(request):
    # Get unread notifications for this user
    unread_notifications = DispatchNotification.objects.filter(
        recipient=request.user,
        is_read=False
    ).select_related(
        'dispatch_log__driver_request__user'
    ).order_by('-created_at')[:5]  # Show latest 5
    
    # Format notifications
    notifications_data = []
    for notif in unread_notifications:
        dr = notif.dispatch_log.driver_request
        notifications_data.append({
            'id': notif.id,
            'request_id': dr.id,
            'issue': dr.issue_description,
            'requester': f"{dr.user.first_name} {dr.user.last_name}".strip() or dr.user.email,
            'distance_km': notif.distance_km,
            'created_at': notif.created_at,
            'latitude': dr.latitude,
            'longitude': dr.longitude,
        })
    
    return render(request, 'security_team_dashboard.html', {
        'notifications': notifications_data,
        'unread_count': len(notifications_data)
    })


@login_required
def medical_team_dashboard(request):
    # Get unread notifications for this user
    unread_notifications = DispatchNotification.objects.filter(
        recipient=request.user,
        is_read=False
    ).select_related(
        'dispatch_log__driver_request__user'
    ).order_by('-created_at')[:5]  # Show latest 5
    
    # Format notifications
    notifications_data = []
    for notif in unread_notifications:
        dr = notif.dispatch_log.driver_request
        notifications_data.append({
            'id': notif.id,
            'request_id': dr.id,
            'issue': dr.issue_description,
            'requester': f"{dr.user.first_name} {dr.user.last_name}".strip() or dr.user.email,
            'distance_km': notif.distance_km,
            'created_at': notif.created_at,
            'latitude': dr.latitude,
            'longitude': dr.longitude,
        })
    
    return render(request, 'medical_team_dashboard.html', {
        'notifications': notifications_data,
        'unread_count': len(notifications_data)
    })


@login_required
def towing_service_dashboard(request):
    # Get unread notifications for this user
    unread_notifications = DispatchNotification.objects.filter(
        recipient=request.user,
        is_read=False
    ).select_related(
        'dispatch_log__driver_request__user'
    ).order_by('-created_at')[:5]  # Show latest 5
    
    # Format notifications
    notifications_data = []
    for notif in unread_notifications:
        dr = notif.dispatch_log.driver_request
        notifications_data.append({
            'id': notif.id,
            'request_id': dr.id,
            'issue': dr.issue_description,
            'requester': f"{dr.user.first_name} {dr.user.last_name}".strip() or dr.user.email,
            'distance_km': notif.distance_km,
            'created_at': notif.created_at,
            'latitude': dr.latitude,
            'longitude': dr.longitude,
        })
    
    return render(request, 'towing_service_dashboard.html', {
        'notifications': notifications_data,
        'unread_count': len(notifications_data)
    })


@login_required
def staff_dashboard(request):
    return render(request, 'staff_dashboard.html')


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
        profile_picture = request.FILES.get("profile_picture")  # Get uploaded file

        # Password validation
        if password != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register_user.html')

        # Check if email already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email address is already in use.")
            return render(request, 'register_user.html')

        try:
            # Basic required-field validation
            if not email or not password:
                messages.error(request, "Email and password are required.")
                return render(request, 'register_user.html')

            # Map human-friendly account_type values from the template to the model choice codes
            account_type_map = {
                'Driver': 'DRIVER',
                'Electrical Maintenance Team': 'ELECTRICAL_MAINTENANCE_TEAM',
                'Mechanical Maintenance Team': 'MECHANICAL_MAINTENANCE_TEAM',
                'Emergency Response Team': 'EMERGENCY_RESPONSE_TEAM',
                'Security Team': 'SECURITY_TEAM',
                'Medical Team': 'MEDICAL_TEAM',
                'Towing Service': 'TOWING_SERVICE',
                'Locomotive Specialists': 'OTHER',
            }
            account_code = account_type_map.get(account_type, 'OTHER')

            # Create the user using the custom manager (email is the USERNAME_FIELD)
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                first_name=first_name or '',
                last_name=last_name or '',
                id_number=id_number or '',
                employee_number=employee_number or '',
                mobile_number=mobile_number or '',
                account_type=account_code,
                role=account_code,
                is_active=False  # Account needs admin approval
            )
            
            # Add profile picture if uploaded
            if profile_picture:
                user.profile_picture = profile_picture
            
            user.save()
            messages.success(request, "Registration successful! Your account is pending admin approval. You will be notified once activated.")
            return redirect('login')  # replace 'login' with your login URL name
        except IntegrityError:
            logging.exception("Integrity error while creating user")
            messages.error(request, "An error occurred. Please try again.")
            return render(request, 'register_user.html')
        except Exception:
            logging.exception("Unexpected error while creating user")
            messages.error(request, "An unexpected error occurred. Please contact the administrator.")
            return render(request, 'register_user.html')

    return render(request, 'register_user.html')

@login_required
def locomotive_config(request):
    account_type=request.session.get('account_type')

    if account_type!="ADMIN":
        return redirect('login')

    # Collect existing locomotive names (most recent first, unique)
    # Build a list of recent distinct locomotive names but capture the spec id for each
    loc_qs = LocomotiveSpec.objects.exclude(locomotive__isnull=True).exclude(locomotive__exact='').order_by('-created_at').values('id','locomotive')
    locomotives = []
    _seen = set()
    for row in loc_qs:
        nm = row.get('locomotive')
        if nm and nm not in _seen:
            _seen.add(nm)
            locomotives.append({'id': row.get('id'), 'name': nm})

    # Handle POST submission from locomotive form
    if request.method == 'POST':
        try:
            # Read simple named fields
            # Prefer a free-text locomotive name submitted in the form (locomotive_name)
            # if present. This makes a user-entered name the priority over the select value.
            locomotive = (request.POST.get('locomotive_name') or request.POST.get('locomotive') or '').strip()
            loc_type = request.POST.get('loc_type') or ''
            loc_class = request.POST.get('loc_class') or ''
            engine_supply = request.POST.get('engine_supply') or ''
            length = request.POST.get('length') or ''
            capacity_in_tons = request.POST.get('capacity_in_tons') or ''
            distributed_power = request.POST.get('distributed_power') or ''
            tractive_effort = request.POST.get('tractive_effort') or ''
            truck_circuit_spec = request.POST.get('truck_circuit_spec') or ''

            # Parse survey metadata and answers
            survey_meta = request.POST.getlist('survey_questions[]')  # JSON strings

            # Build a mapping of answers from POST keys like survey_answers[0], survey_answers[0][]
            answers_map = {}
            for key in request.POST:
                if key.startswith('survey_answers['):
                    # key example: survey_answers[0] or survey_answers[0][]
                    base = key.split(']')[0] + ']'
                    vals = request.POST.getlist(key)
                    # store as list of strings
                    answers_map[base] = vals

            # For each survey_meta item, decode JSON and assemble a comma-joined block
            # WARNING: User requested to use ','.join; this will create ambiguous strings if questions/answers contain commas.
            parts = []
            for idx, meta_json in enumerate(survey_meta):
                try:
                    meta = json.loads(meta_json)
                except Exception:
                    continue
                qtext = meta.get('text','')
                qtype = meta.get('type','')
                key1 = f'survey_answers[{idx}]'
                key2 = f'survey_answers[{idx}][]'
                ans_list = answers_map.get(key1) or answers_map.get(key2) or []
                # join answers with comma as requested
                answers_joined = ','.join([str(a) for a in ans_list])
                # assemble block: question,type,answers
                block = ','.join([qtext, qtype, answers_joined])
                parts.append(block)

            # final survey_raw is a comma-separated list of blocks (blocks themselves use commas per request)
            survey_raw = ','.join(parts)

            # Parse additional specifications (if any) as JSON
            additional_specs = []
            additional_labels = request.POST.getlist('additional_label[]')
            additional_values = request.POST.getlist('additional_value[]')
            if additional_labels and additional_values:
                # Combine label-value pairs as list of dictionaries
                for label, value in zip(additional_labels, additional_values):
                    if label.strip() and value.strip():
                        additional_specs.append({
                            'label': label.strip(),
                            'value': value.strip()
                        })

            # If a spec id was provided, update that record directly
            existing = None
            selected_spec_id = request.POST.get('selected_spec_id')
            if selected_spec_id:
                try:
                    existing = LocomotiveSpec.objects.filter(id=int(selected_spec_id)).first()
                except Exception:
                    existing = None

            # If no id provided, fallback to finding by locomotive name (old behavior)
            if not existing and locomotive:
                existing = LocomotiveSpec.objects.filter(locomotive__iexact=locomotive).order_by('-created_at').first()

            if existing:
                # Log previous and new locomotive name for debugging
                logging.debug(f"Existing LocomotiveSpec id={getattr(existing,'id',None)} current locomotive={existing.locomotive!r} form locomotive={locomotive!r}")
                # Update locomotive name only if the form provided one (avoid wiping it if empty)
                if locomotive:
                    existing.locomotive = locomotive
                    logging.debug(f"Updated LocomotiveSpec id={getattr(existing,'id',None)} locomotive set to {existing.locomotive!r}")
                existing.loc_type = loc_type
                existing.loc_class = loc_class
                existing.engine_supply = engine_supply
                existing.length = length
                existing.capacity_in_tons = capacity_in_tons
                existing.distributed_power = distributed_power
                existing.tractive_effort = tractive_effort
                existing.truck_circuit_spec = truck_circuit_spec
                existing.survey_raw = survey_raw
                existing.additional_specs = additional_specs
                # do not change created_by/created_at
                existing.save()
                messages.success(request, f'Locomotive "{locomotive}" updated')
            else:
                spec = LocomotiveSpec.objects.create(
                    created_by = request.user,
                    locomotive = locomotive,
                    loc_type = loc_type,
                    loc_class = loc_class,
                    engine_supply = engine_supply,
                    length = length,
                    capacity_in_tons = capacity_in_tons,
                    distributed_power = distributed_power,
                    tractive_effort = tractive_effort,
                    truck_circuit_spec = truck_circuit_spec,
                    survey_raw = survey_raw,
                    additional_specs = additional_specs
                )
                messages.success(request, 'Locomotive specification saved')
            return redirect('locomotive_config')
        except Exception as e:
            logging.exception('Failed to save locomotive spec')
            messages.error(request, 'Failed to save locomotive specification')

    # Get all locomotives for the list view
    all_locomotives = LocomotiveSpec.objects.all().order_by('-created_at')
    
    return render(request, 'locomotive_config.html',{
        'Account_type':"ADMIN", 
        'locomotives': locomotives,
        'all_locomotives': all_locomotives
    })

# Restore profile view to render the profile.html template with logged-in user info
@login_required
def profile(request):
    user = request.user
    # You can add more user-related context as needed
    return render(request, 'profile.html', {'user': user})


@login_required
def cargo_specs(request):
    account_type=request.session.get('account_type')

    if account_type not in ("ADMIN", "DRIVER"):
        return redirect('login')

    # Get all available wagons (not assigned to cargo yet)
    wagons_qs = WagonSpec.objects.filter(
        is_active=True,
        status='AVAILABLE',
        current_cargo__isnull=True  # No cargo assigned yet
    ).order_by('wagon_number')
    
    # Get all cargo specs
    cargo_qs = CargoSpec.objects.all().select_related('wagon').order_by('-created_at')

    cargos = []
    for c in cargo_qs:
        cargos.append({
            'id': c.id,
            'cargo_type': c.cargo_type,
            'cargo_volume': c.cargo_volume,
            'cargo_weight_tons': c.cargo_weight_tons,
            'special_handling': c.special_handling,
            'wagon_number': c.wagon.wagon_number if c.wagon else '',
            'wagon_type': c.wagon.get_wagon_type_display() if c.wagon else '',
        })

    if request.method == 'POST':
        try:
            wagon_id = request.POST.get('wagon_id')
            if not wagon_id:
                messages.error(request, 'Please select a wagon')
                return redirect('cargo_specs')
            
            wagon = WagonSpec.objects.filter(id=int(wagon_id)).first()
            if not wagon:
                messages.error(request, 'Invalid wagon selected')
                return redirect('cargo_specs')

            cargo_type = request.POST.get('cargo_type') or ''
            cargo_volume = request.POST.get('cargo_volume') or ''
            cargo_weight_str = request.POST.get('cargo_weight_tons') or '0'
            special_handling = request.POST.get('special_handling') or ''
            
            # Validate cargo weight doesn't exceed wagon capacity
            try:
                cargo_weight = float(cargo_weight_str) if cargo_weight_str else 0
                wagon_capacity = float(wagon.payload_capacity) if wagon.payload_capacity else 0
                
                if cargo_weight > wagon_capacity:
                    messages.error(request, f'Cargo weight ({cargo_weight}t) exceeds wagon capacity ({wagon_capacity}t)')
                    return redirect('cargo_specs')
            except ValueError:
                cargo_weight = 0

            # collect survey meta like locomotive view
            survey_meta = request.POST.getlist('survey_questions[]')
            answers_map = {}
            for key in request.POST:
                if key.startswith('survey_answers['):
                    base = key.split(']')[0] + ']'
                    vals = request.POST.getlist(key)
                    answers_map[base] = vals

            parts = []
            for idx, meta_json in enumerate(survey_meta):
                try:
                    meta = json.loads(meta_json)
                except Exception:
                    continue
                qtext = meta.get('text','')
                qtype = meta.get('type','')
                key1 = f'survey_answers[{idx}]'
                key2 = f'survey_answers[{idx}][]'
                ans_list = answers_map.get(key1) or answers_map.get(key2) or []
                answers_joined = ','.join([str(a) for a in ans_list])
                block = ','.join([qtext, qtype, answers_joined])
                parts.append(block)
            survey_raw = ','.join(parts)

            existing = None
            selected_id = request.POST.get('selected_spec_id')
            if selected_id:
                try:
                    existing = CargoSpec.objects.filter(id=int(selected_id)).first()
                except Exception:
                    existing = None

            if existing:
                # Check if changing wagon and if new wagon is available
                if existing.wagon != wagon:
                    if wagon.current_cargo and wagon.current_cargo != existing:
                        messages.error(request, f'Wagon {wagon.wagon_number} is already assigned to another cargo')
                        return redirect('cargo_specs')
                    
                    # Release old wagon if changing
                    if existing.wagon:
                        old_wagon = existing.wagon
                        old_wagon.current_cargo = None
                        old_wagon.status = 'AVAILABLE'
                        old_wagon.save()
                
                # Update cargo
                if cargo_type:
                    existing.cargo_type = cargo_type
                existing.wagon = wagon
                existing.cargo_volume = cargo_volume
                existing.cargo_weight_tons = cargo_weight
                existing.special_handling = special_handling
                existing.survey_raw = survey_raw
                existing.save()
                
                # Update wagon to link to this cargo
                wagon.current_cargo = existing
                wagon.status = 'IN_USE'
                wagon.save()
                
                messages.success(request, f'Cargo "{cargo_type}" updated and assigned to wagon {wagon.wagon_number}')
            else:
                # Check if wagon is already assigned to cargo
                if wagon.current_cargo:
                    messages.error(request, f'Wagon {wagon.wagon_number} is already assigned to cargo')
                    return redirect('cargo_specs')
                
                # Create new cargo
                cargo = CargoSpec.objects.create(
                    created_by=request.user,
                    wagon=wagon,
                    cargo_type=cargo_type,
                    cargo_volume=cargo_volume,
                    cargo_weight_tons=cargo_weight,
                    special_handling=special_handling,
                    survey_raw=survey_raw
                )
                
                # Update wagon to link to this cargo
                wagon.current_cargo = cargo
                wagon.status = 'IN_USE'
                wagon.save()
                
                messages.success(request, f'Cargo saved and assigned to wagon {wagon.wagon_number}')
            return redirect('cargo_specs')
        except Exception as e:
            logging.exception('Failed to save cargo spec')
            messages.error(request, f'Failed to save cargo specification: {str(e)}')

    # Build wagons list
    wagons = [{'id': w.id, 'wagon_number': w.wagon_number, 'wagon_type': w.get_wagon_type_display(), 'payload_capacity': w.payload_capacity} 
              for w in wagons_qs]
    
    return render(request, 'cargo_specs.html', {'Account_type': account_type, 'cargos': cargos, 'wagons': wagons})


@login_required
def api_get_fuel_spec(request):
    spec_id = request.GET.get('id')
    if not spec_id:
        return JsonResponse({'error': 'id required'}, status=400)
    spec = FuelSpec.objects.filter(id=int(spec_id)).first()
    if not spec:
        return JsonResponse({}, status=204)
    return JsonResponse({
        'id': spec.id,
        'locomotive_id': spec.locomotive.id if spec.locomotive else None,
        'daily_fuel_consumption': spec.daily_fuel_consumption,
        'fuel_cost_per_litre': spec.fuel_cost_per_litre,
        'average_load_per_trip': spec.average_load_per_trip,
        'fuel_type': spec.fuel_type,
        'survey_raw': spec.survey_raw,
    })


@login_required
def trip_data(request):
    
    account_type=request.session.get('account_type')
   
    if account_type=="DRIVER":
        return render(request, 'trip_data.html',{'Account_type':"DRIVER"})
    elif account_type=="DRIVER":
        return render(request, 'trip_data.html',{'Account_type':"DRIVER"})
    else:
        return redirect('login')

@login_required
def api_get_cargo_spec(request):
    spec_id = request.GET.get('id')
    if not spec_id:
        return JsonResponse({'error': 'id required'}, status=400)
    spec = CargoSpec.objects.filter(id=int(spec_id)).first()
    if not spec:
        return JsonResponse({}, status=204)
    return JsonResponse({
        'id': spec.id,
        'wagon_id': spec.wagon.id if spec.wagon else None,
        'cargo_type': spec.cargo_type,
        'cargo_volume': spec.cargo_volume,
        'cargo_weight_tons': str(spec.cargo_weight_tons) if spec.cargo_weight_tons else '',
        'special_handling': spec.special_handling,
        'survey_raw': spec.survey_raw,
    })

@login_required
def driver_request(request):
    account_type=request.session.get('account_type')
    
    if account_type not in ("DRIVER", "ADMIN"):
        return redirect('login')

    if request.method == 'POST':
        try:
            issue_description = request.POST.get('issue_description', '').strip()
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            captured_image = request.FILES.get('captured_image')
            locomotive_id = request.POST.get('locomotive_id')  # Get locomotive from form
            incident_category = request.POST.get('incident_category', 'OTHER')  # Get category from form

            if not issue_description:
                return JsonResponse({'error': 'Issue description is required'}, status=400)

            # Convert latitude/longitude to float if provided
            lat_float = float(latitude) if latitude else None
            lng_float = float(longitude) if longitude else None
            
            # Get locomotive object if provided
            locomotive = None
            if locomotive_id:
                try:
                    locomotive = LocomotiveSpec.objects.get(id=locomotive_id)
                except LocomotiveSpec.DoesNotExist:
                    pass
            
            # Check for duplicate requests (same user, same locomotive, same day, status PENDING or IN_PROGRESS)
            priority = 'NORMAL'
            if locomotive:
                from django.utils import timezone
                from datetime import timedelta
                
                today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timedelta(days=1)
                
                # Check if there's already a pending/in-progress request for this locomotive today
                existing_request = DriverRequest.objects.filter(
                    user=request.user,
                    locomotive=locomotive,
                    created_at__gte=today_start,
                    created_at__lt=today_end,
                    status__in=['PENDING', 'IN_PROGRESS']
                ).first()
                
                if existing_request:
                    # This is a duplicate - mark as CRITICAL
                    priority = 'CRITICAL'
                    logging.warning(f"CRITICAL: Duplicate request detected for user {request.user.email}, locomotive {locomotive.locomotive}")

            # Create driver request record
            driver_request_obj = DriverRequest.objects.create(
                user=request.user,
                locomotive=locomotive,
                issue_description=issue_description,
                captured_image=captured_image,
                latitude=lat_float,
                longitude=lng_float,
                incident_category=incident_category,
                status='PENDING',
                priority=priority
            )

            logging.info(f"Driver request created: ID={driver_request_obj.id}, User={request.user.email}, Category={incident_category}, Priority={priority}")
            
            response_data = {
                'status': 'success',
                'request_id': driver_request_obj.id,
                'message': 'Your request has been submitted successfully'
            }
            
            if priority == 'CRITICAL':
                response_data['warning'] = 'This is a duplicate request for the same locomotive today. Marked as CRITICAL priority.'
            
            return JsonResponse(response_data)

        except ValueError as e:
            logging.exception('Invalid latitude/longitude value')
            return JsonResponse({'error': 'Invalid location data'}, status=400)
        except Exception as e:
            logging.exception('Failed to create driver request')
            return JsonResponse({'error': 'Failed to submit request'}, status=500)

    # GET request - render the form
    # Get available locomotives for the dropdown
    locomotives = LocomotiveSpec.objects.filter(is_active=True, status='AVAILABLE').order_by('locomotive')
    
    return render(request, 'driver_request.html', {
        'Account_type': account_type,
        'locomotives': locomotives
    })


@login_required
def wagon_specs(request):
    account_type = request.session.get('account_type')

    if account_type != "ADMIN":
        messages.error(request, 'Only admins can manage wagon specifications')
        return redirect('login')

    # Get all wagons for admin
    wagons_qs = WagonSpec.objects.all().order_by('-created_at')
    
    wagons = []
    for w in wagons_qs:
        wagons.append({
            'id': w.id,
            'wagon_number': w.wagon_number,
            'wagon_type': w.get_wagon_type_display(),
            'payload_capacity': w.payload_capacity,
            'status': w.get_status_display(),
        })

    if request.method == 'POST':
        try:
            wagon_number = request.POST.get('wagon_number')
            if not wagon_number:
                messages.error(request, 'Wagon number is required')
                return redirect('wagon_specs')

            # Collect all form fields
            wagon_type = request.POST.get('wagon_type') or 'BOX'
            length_over_buffers = request.POST.get('length_over_buffers') or None
            width = request.POST.get('width') or None
            height = request.POST.get('height') or None
            track_gauge = request.POST.get('track_gauge') or '1067'
            tare_weight = request.POST.get('tare_weight') or None
            payload_capacity = request.POST.get('payload_capacity') or None
            gross_laden_weight = request.POST.get('gross_laden_weight') or None
            axle_load = request.POST.get('axle_load') or None
            maximum_speed = request.POST.get('maximum_speed') or None
            braking_system = request.POST.get('braking_system') or 'UIC'
            coupling_type = request.POST.get('coupling_type') or 'SA3'
            buffer_drawgear_capacity = request.POST.get('buffer_drawgear_capacity') or None
            body_material = request.POST.get('body_material') or ''
            frame_construction = request.POST.get('frame_construction') or ''
            suspension_system = request.POST.get('suspension_system') or 'COIL'
            bogie_type = request.POST.get('bogie_type') or 'TWO_AXLE'
            floor_type = request.POST.get('floor_type') or ''
            special_features = request.POST.get('special_features') or ''

            # Collect survey data (additional specs)
            survey_meta = request.POST.getlist('survey_questions[]')
            answers_map = {}
            for key in request.POST:
                if key.startswith('survey_answers['):
                    base = key.split(']')[0] + ']'
                    vals = request.POST.getlist(key)
                    answers_map[base] = vals

            parts = []
            for idx, meta_json in enumerate(survey_meta):
                try:
                    meta = json.loads(meta_json)
                except Exception:
                    continue
                qtext = meta.get('text', '')
                qtype = meta.get('type', '')
                key1 = f'survey_answers[{idx}]'
                key2 = f'survey_answers[{idx}][]'
                ans_list = answers_map.get(key1) or answers_map.get(key2) or []
                answers_joined = ','.join([str(a) for a in ans_list])
                block = ','.join([qtext, qtype, answers_joined])
                parts.append(block)
            survey_raw = ','.join(parts)

            # Check if editing existing wagon
            existing = None
            selected_id = request.POST.get('selected_spec_id')
            if selected_id:
                try:
                    existing = WagonSpec.objects.filter(id=int(selected_id)).first()
                except Exception:
                    existing = None

            if existing:
                # Update existing wagon
                existing.wagon_number = wagon_number
                existing.wagon_type = wagon_type
                existing.length_over_buffers = length_over_buffers
                existing.width = width
                existing.height = height
                existing.track_gauge = track_gauge
                existing.tare_weight = tare_weight
                existing.payload_capacity = payload_capacity
                existing.gross_laden_weight = gross_laden_weight
                existing.axle_load = axle_load
                existing.maximum_speed = maximum_speed
                existing.braking_system = braking_system
                existing.coupling_type = coupling_type
                existing.buffer_drawgear_capacity = buffer_drawgear_capacity
                existing.body_material = body_material
                existing.frame_construction = frame_construction
                existing.suspension_system = suspension_system
                existing.bogie_type = bogie_type
                existing.floor_type = floor_type
                existing.special_features = special_features
                existing.survey_raw = survey_raw
                existing.save()
                messages.success(request, f'Wagon "{wagon_number}" updated successfully')
            else:
                # Create new wagon
                WagonSpec.objects.create(
                    created_by=request.user,
                    wagon_number=wagon_number,
                    wagon_type=wagon_type,
                    length_over_buffers=length_over_buffers,
                    width=width,
                    height=height,
                    track_gauge=track_gauge,
                    tare_weight=tare_weight,
                    payload_capacity=payload_capacity,
                    gross_laden_weight=gross_laden_weight,
                    axle_load=axle_load,
                    maximum_speed=maximum_speed,
                    braking_system=braking_system,
                    coupling_type=coupling_type,
                    buffer_drawgear_capacity=buffer_drawgear_capacity,
                    body_material=body_material,
                    frame_construction=frame_construction,
                    suspension_system=suspension_system,
                    bogie_type=bogie_type,
                    floor_type=floor_type,
                    special_features=special_features,
                    survey_raw=survey_raw
                )
                messages.success(request, f'Wagon "{wagon_number}" saved successfully')
            return redirect('wagon_specs')
        except Exception as e:
            logging.exception('Failed to save wagon spec')
            messages.error(request, f'Failed to save wagon specification: {str(e)}')

    # Get all wagons for the list view
    all_wagons = WagonSpec.objects.all().order_by('-created_at')
    
    return render(request, 'wagon_specs.html', {
        'Account_type': account_type, 
        'wagons': wagons,
        'all_wagons': all_wagons
    })


@login_required
def api_get_wagon_spec(request):
    spec_id = request.GET.get('id')
    if not spec_id:
        return JsonResponse({'error': 'id required'}, status=400)
    spec = WagonSpec.objects.filter(id=int(spec_id)).first()
    if not spec:
        return JsonResponse({}, status=204)
    return JsonResponse({
        'id': spec.id,
        'wagon_number': spec.wagon_number,
        'wagon_type': spec.wagon_type,
        'length_over_buffers': str(spec.length_over_buffers) if spec.length_over_buffers else '',
        'width': str(spec.width) if spec.width else '',
        'height': str(spec.height) if spec.height else '',
        'track_gauge': spec.track_gauge,
        'tare_weight': str(spec.tare_weight) if spec.tare_weight else '',
        'payload_capacity': str(spec.payload_capacity) if spec.payload_capacity else '',
        'gross_laden_weight': str(spec.gross_laden_weight) if spec.gross_laden_weight else '',
        'axle_load': str(spec.axle_load) if spec.axle_load else '',
        'maximum_speed': spec.maximum_speed,
        'braking_system': spec.braking_system,
        'coupling_type': spec.coupling_type,
        'buffer_drawgear_capacity': spec.buffer_drawgear_capacity,
        'body_material': spec.body_material,
        'frame_construction': spec.frame_construction,
        'suspension_system': spec.suspension_system,
        'bogie_type': spec.bogie_type,
        'floor_type': spec.floor_type,
        'special_features': spec.special_features,
        'survey_raw': spec.survey_raw,
    })

@login_required
def wheelset(request):
    account_type=request.session.get('account_type')
    # Allow both DRIVER and ADMIN users to view and save route preferences
    if account_type not in ("ADMIN", "DRIVER"):
        return redirect('login')

    # Get assigned locomotives if DRIVER
    if account_type == "DRIVER":
        assigned_locos = LocomotiveAssignment.objects.filter(driver=request.user).select_related('locomotive')
        assigned_loco_ids = [a.locomotive.id for a in assigned_locos]
        wheel_qs = WheelsetSpec.objects.filter(locomotive_id__in=assigned_loco_ids).select_related('locomotive').order_by('-created_at')
    else:  # ADMIN
        assigned_locos = LocomotiveSpec.objects.all()
        assigned_loco_ids = [l.id for l in assigned_locos]
        wheel_qs = WheelsetSpec.objects.all().select_related('locomotive').order_by('-created_at')

    wheels = []
    for w in wheel_qs:
        wheels.append({
            'id': w.id,
            'wheel_profile': w.wheel_profile,
            'locomotive_name': w.locomotive.locomotive if w.locomotive else '',
        })

    if request.method == 'POST':
        try:
            locomotive_id = request.POST.get('locomotive_id')
            if not locomotive_id:
                messages.error(request, 'Please select a locomotive')
                return redirect('wheelset')
            
            if account_type == "DRIVER" and int(locomotive_id) not in assigned_loco_ids:
                messages.error(request, 'You are not assigned to this locomotive')
                return redirect('wheelset')
            
            locomotive = LocomotiveSpec.objects.filter(id=int(locomotive_id)).first()
            if not locomotive:
                messages.error(request, 'Invalid locomotive selected')
                return redirect('wheelset')

            wheel_profile = request.POST.get('wheel_profile') or ''
            diameter_differentials = request.POST.get('diameter_differentials') or ''
            symmetry = request.POST.get('symmetry') or ''
            radial_run_out = request.POST.get('radial_run_out') or ''
            axial_run_out = request.POST.get('axial_run_out') or ''
            witness_marks = request.POST.get('witness_marks') or ''
            surface_roughness = request.POST.get('surface_roughness') or ''
            stenciling = request.POST.get('stenciling') or ''
            main_machine_diameter = request.POST.get('main_machine_diameter') or ''

            survey_meta = request.POST.getlist('survey_questions[]')
            answers_map = {}
            for key in request.POST:
                if key.startswith('survey_answers['):
                    base = key.split(']')[0] + ']'
                    vals = request.POST.getlist(key)
                    answers_map[base] = vals

            parts = []
            for idx, meta_json in enumerate(survey_meta):
                try:
                    meta = json.loads(meta_json)
                except Exception:
                    continue
                qtext = meta.get('text','')
                qtype = meta.get('type','')
                key1 = f'survey_answers[{idx}]'
                key2 = f'survey_answers[{idx}][]'
                ans_list = answers_map.get(key1) or answers_map.get(key2) or []
                answers_joined = ','.join([str(a) for a in ans_list])
                block = ','.join([qtext, qtype, answers_joined])
                parts.append(block)
            survey_raw = ','.join(parts)

            existing = None
            selected_id = request.POST.get('selected_spec_id')
            if selected_id:
                try:
                    if account_type == "DRIVER":
                        existing = WheelsetSpec.objects.filter(
                            id=int(selected_id),
                            created_by=request.user,
                            locomotive_id__in=assigned_loco_ids
                        ).first()
                    else:
                        existing = WheelsetSpec.objects.filter(id=int(selected_id)).first()
                except Exception:
                    existing = None

            if existing:
                if wheel_profile:
                    existing.wheel_profile = wheel_profile
                existing.locomotive = locomotive
                existing.diameter_differentials = diameter_differentials
                existing.symmetry = symmetry
                existing.radial_run_out = radial_run_out
                existing.axial_run_out = axial_run_out
                existing.witness_marks = witness_marks
                existing.surface_roughness = surface_roughness
                existing.stenciling = stenciling
                existing.main_machine_diameter = main_machine_diameter
                existing.survey_raw = survey_raw
                existing.save()
                messages.success(request, f'Wheelset "{wheel_profile}" updated')
            else:
                WheelsetSpec.objects.create(
                    created_by=request.user,
                    locomotive=locomotive,
                    wheel_profile=wheel_profile,
                    diameter_differentials=diameter_differentials,
                    symmetry=symmetry,
                    radial_run_out=radial_run_out,
                    axial_run_out=axial_run_out,
                    witness_marks=witness_marks,
                    surface_roughness=surface_roughness,
                    stenciling=stenciling,
                    main_machine_diameter=main_machine_diameter,
                    survey_raw=survey_raw
                )
                messages.success(request, 'Wheelset saved')
            return redirect('wheelset')
        except Exception:
            logging.exception('Failed to save wheelset spec')
            messages.error(request, 'Failed to save wheelset specification')

    # Separate logic for DRIVER vs ADMIN to avoid AttributeError
    if account_type == "DRIVER":
        locomotives = [{'id': a.locomotive.id, 'name': a.locomotive.locomotive} 
                       for a in assigned_locos]
    else:  # ADMIN
        locomotives = [{'id': a.id, 'name': a.locomotive} 
                       for a in assigned_locos]
    
    return render(request, 'wheelset.html', {'Account_type': account_type, 'wheels': wheels, 'locomotives': locomotives})


@login_required
def api_get_wheelset_spec(request):
    spec_id = request.GET.get('id')
    if not spec_id:
        return JsonResponse({'error': 'id required'}, status=400)
    spec = WheelsetSpec.objects.filter(id=int(spec_id)).first()
    if not spec:
        return JsonResponse({}, status=204)
    return JsonResponse({
        'id': spec.id,
        'locomotive_id': spec.locomotive.id if spec.locomotive else None,
        'wheel_profile': spec.wheel_profile,
        'diameter_differentials': spec.diameter_differentials,
        'symmetry': spec.symmetry,
        'radial_run_out': spec.radial_run_out,
        'axial_run_out': spec.axial_run_out,
        'witness_marks': spec.witness_marks,
        'surface_roughness': spec.surface_roughness,
        'stenciling': spec.stenciling,
        'main_machine_diameter': spec.main_machine_diameter,
        'survey_raw': spec.survey_raw,
    })



@login_required
def emergency_alerts(request):
    account_type=request.session.get('account_type')
    
    # Get all driver requests ordered by most recent first
    driver_requests = DriverRequest.objects.select_related('user', 'locomotive').order_by('-created_at')
    
    requests_data = []
    pending_count = 0
    in_progress_count = 0
    resolved_count = 0
    
    for req in driver_requests:
        # Format status for display and CSS class
        status_display = req.status.replace('_', ' ')
        status_class = req.status.lower().replace('_', '-')
        
        # Priority class for color coding
        priority_class = 'priority-critical' if req.priority == 'CRITICAL' else 'priority-normal'
        
        # Category display
        category_display = req.incident_category.replace('_', ' ').title() if req.incident_category else 'Other'
        
        requests_data.append({
            'id': req.id,
            'user_email': req.user.email,
            'user_name': f"{req.user.first_name} {req.user.last_name}".strip() or req.user.email,
            'user_role': req.user.role,
            'user_phone': req.user.phone_number or 'N/A',
            'issue_description': req.issue_description,
            'captured_image': req.captured_image.url if req.captured_image else None,
            'latitude': req.latitude,
            'longitude': req.longitude,
            'status': req.status,
            'status_display': status_display,
            'status_class': status_class,
            'priority': req.priority,
            'priority_class': priority_class,
            'incident_category': req.incident_category,
            'category_display': category_display,
            'locomotive': req.locomotive.locomotive if req.locomotive else 'N/A',
            'locomotive_type': req.locomotive.loco_type if req.locomotive else 'N/A',
            'created_at': req.created_at,
            'updated_at': req.updated_at,
        })
        
        # Count by status
        if req.status == 'PENDING':
            pending_count += 1
        elif req.status == 'IN_PROGRESS':
            in_progress_count += 1
        elif req.status == 'RESOLVED':
            resolved_count += 1
    
    return render(request, 'emergency_alerts.html', {
        'Account_type': account_type,
        'requests': requests_data,
        'total_count': len(requests_data),
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
        'resolved_count': resolved_count,
    })   



@login_required
def api_get_route_preference_spec(request):
    spec_id = request.GET.get('id')
    if not spec_id:
        return JsonResponse({'error': 'id required'}, status=400)
    spec = RoutePreferenceSpec.objects.filter(id=int(spec_id)).first()
    if not spec:
        return JsonResponse({}, status=204)
    return JsonResponse({
        'id': spec.id,
        'locomotive_id': spec.locomotive.id if spec.locomotive else None,
        'preferred_route_corridor': spec.preferred_route_corridor,
        'transshipment_required': spec.transshipment_required,
        'delivery_node': spec.delivery_node,
        'receiving_facility': spec.receiving_facility,
        'survey_raw': spec.survey_raw,
    })

@login_required
def driver_assignment(request):
    # AJAX endpoint for dynamic date filtering
    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        selected_driver_ids = request.GET.getlist('driver_ids[]') or request.GET.getlist('driver_ids')
        today = timezone.now().date()
        filtered_dates = []
        if selected_driver_ids:
            filtered_dates = list(Schedule.objects.filter(
                driver_id__in=selected_driver_ids,
                date__gte=today
            ).values_list('date', flat=True).distinct().order_by('date'))
        return JsonResponse({'dates': filtered_dates})

    account_type = request.session.get('account_type')
    if account_type != "ADMIN":
        return redirect('login')


    # Query all drivers
    all_drivers = CustomUser.objects.filter(role='DRIVER', driver_status='available')
    # Get paired drivers from the schedule calendar (Schedule model)
    today = timezone.now().date()
    # Print all Schedule entries for debugging
    all_schedules = list(Schedule.objects.filter(date__gte=today).values('driver_id', 'date'))
    print("All future/present Schedule entries:", all_schedules)
    paired_driver_ids = set([s['driver_id'] for s in all_schedules])
    print(f"Paired driver IDs: {paired_driver_ids}")
    print("All available drivers (User_id, email):", list(all_drivers.values('User_id', 'email', 'first_name', 'last_name')))
    # Filter using User_id only (id is not a valid field)
    paired_drivers_qs = CustomUser.objects.filter(User_id__in=paired_driver_ids, role='DRIVER')
    print("Paired drivers (User_id, email):", list(paired_drivers_qs.values('User_id', 'email', 'first_name', 'last_name')))
    # Only show paired drivers who are available
    available_drivers_qs = paired_drivers_qs.filter(driver_status='available')
    print("Available paired drivers (User_id, email):", list(available_drivers_qs.values('User_id', 'email', 'first_name', 'last_name')))
    # Only show paired drivers who do NOT have a locomotive assigned in Schedule
    available_drivers = []

    schedules = Schedule.objects.filter(date__gte=today).select_related('driver', 'assistant').prefetch_related('locomotives')
    for s in schedules:
        if s.locomotives.count() == 0:
            d = s.driver
            d.is_paired = True
            d.assistant_name = (s.assistant.first_name + ' ' + s.assistant.last_name) if s.assistant else None
            d.assistant_email = s.assistant.email if s.assistant else None
            available_drivers.append(d)
            print(f"Driver: {d.first_name} {d.last_name}, Email: {d.email}, User_id: {d.User_id}, is_paired: {d.is_paired}, Assistant: {d.assistant_name}")
  

    # Query all locomotives
    locomotives = LocomotiveSpec.objects.all()

    # Query all assignments (example: LocomotiveAssignment model)
    assignments = LocomotiveAssignment.objects.select_related('locomotive', 'driver').all()

    # Prepare assignment data for template using Schedule (show only assigned pairs)
    assignment_list = []
    schedules = Schedule.objects.filter(date__gte=today, locomotives__isnull=False).distinct().select_related('driver', 'assistant').prefetch_related('locomotives')
    for s in schedules:
        assignment_list.append({
            'id': s.id,
            'locomotive_ids': [l.id for l in s.locomotives.all()],
            'locomotive_names': [l.locomotive for l in s.locomotives.all()],
            'driver_name': (s.driver.first_name + ' ' + s.driver.last_name) if s.driver else '',
            'driver_email': s.driver.email if s.driver else '',
            'assistant_name': (s.assistant.first_name + ' ' + s.assistant.last_name) if s.assistant else '',
            'assistant_email': s.assistant.email if s.assistant else '',
            'assigned_at': s.created_at if hasattr(s, 'created_at') else '',
        })

    # Handle POST for assignment (demo logic, adjust as needed)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'reassign':
            # ...existing code...
            return redirect('driver_assignment')
        elif action == 'unassign':
            assignment_id = request.POST.get('assignment_id')
            if assignment_id:
                try:
                    schedule = Schedule.objects.get(id=assignment_id)
                    schedule.locomotives.clear()
                    schedule.status = 'available'
                    schedule.save()
                    messages.success(request, 'Driver assignment removed successfully.')
                except Schedule.DoesNotExist:
                    messages.error(request, 'Assignment not found.')
            else:
                messages.error(request, 'No assignment selected for removal.')
            return redirect('driver_assignment')
        else:
            driver_ids = request.POST.getlist('driver_ids[]') or request.POST.getlist('driver_ids')
            locomotive_ids = request.POST.getlist('locomotive_ids')
            assistant_id = request.POST.get('assistant_id')
            if not driver_ids:
                messages.error(request, 'Please select at least one driver.')
                return redirect('driver_assignment')
            if not locomotive_ids:
                messages.error(request, 'Please select at least one locomotive.')
                return redirect('driver_assignment')
            selected_date = request.POST.get('selected_date')
            from django.core.mail import send_mail
            assigned_driver_emails = []
            assigned_driver_ids = []
            assigned_assistant_emails = []
            assigned_assistant_ids = []
            for driver_id in driver_ids:
                schedule = Schedule.objects.filter(driver_id=driver_id, date=selected_date).select_related('driver', 'assistant').prefetch_related('locomotives').first()
                if schedule:
                    # Assign all selected locomotives
                    schedule.locomotives.set(locomotive_ids)
                    schedule.status = 'assigned'
                    # Store assistant if selected and not already assigned
                    if assistant_id:
                        try:
                            assistant = CustomUser.objects.get(User_id=assistant_id)
                            schedule.assistant = assistant
                            assigned_assistant_emails.append(assistant.email)
                            assigned_assistant_ids.append(assistant.User_id)
                        except CustomUser.DoesNotExist:
                            pass
                    schedule.save()
                    # Collect driver email and id for notification
                    if schedule.driver and schedule.driver.email:
                        assigned_driver_emails.append(schedule.driver.email)
                    if schedule.driver:
                        assigned_driver_ids.append(schedule.driver.User_id)
            # Send notification to all assigned drivers and assistants
            if assigned_driver_emails or assigned_driver_ids or assigned_assistant_emails or assigned_assistant_ids:
                try:
                    loco_names = ', '.join([l.locomotive for l in LocomotiveSpec.objects.filter(id__in=locomotive_ids)])
                    subject = 'Locomotive Assignment Notification'
                    message = f'You have been assigned to locomotive(s) {loco_names} on {selected_date}. Please check your schedule for details.'
                    # Email notification
                    if assigned_driver_emails:
                        send_mail(subject, message, 'noreply@transnet.com', assigned_driver_emails)
                    if assigned_assistant_emails:
                        send_mail(subject, message, 'noreply@transnet.com', assigned_assistant_emails)
                    # App notification (template)
                    from .models import DispatchNotification
                    for driver_id in assigned_driver_ids:
                        try:
                            DispatchNotification.objects.create(
                                recipient_id=driver_id,
                                message=message,
                                is_read=False
                            )
                        except Exception as e:
                            print(f"[ERROR] Failed to create app notification for driver {driver_id}: {e}")
                    for assistant_id in assigned_assistant_ids:
                        try:
                            DispatchNotification.objects.create(
                                recipient_id=assistant_id,
                                message=message,
                                is_read=False
                            )
                        except Exception as e:
                            print(f"[ERROR] Failed to create app notification for assistant {assistant_id}: {e}")
                except Exception as e:
                    print(f"[ERROR] Failed to send assignment notification: {e}")
            messages.success(request, f'Drivers and assistant assigned to locomotive(s) for {selected_date}.')
            return redirect('driver_assignment')

    # --- Filter available_dates based on selected drivers (pair) ---
    selected_driver_ids = request.GET.getlist('driver_ids')
    filtered_dates = []
    if selected_driver_ids:
        # Only show dates for the selected drivers (pair), from today onwards
        filtered_dates = Schedule.objects.filter(
            driver_id__in=selected_driver_ids,
            date__gte=today
        ).values_list('date', flat=True).distinct().order_by('date')
    else:
        # Default: show all available drivers' future dates
        filtered_dates = Schedule.objects.filter(
            driver__in=[d.User_id for d in available_drivers],
            date__gte=today
        ).values_list('date', flat=True).distinct().order_by('date')

    # Collect available assistants (not already assigned for the selected date)
    assigned_assistant_ids = Schedule.objects.filter(date__gte=today, assistant__isnull=False).values_list('assistant_id', flat=True)
    available_assistants = CustomUser.objects.filter(role='DRIVER', driver_status='available').exclude(User_id__in=assigned_assistant_ids)
    return render(request, 'driver_assignment.html', {
        'Account_type': 'ADMIN',
        'available_drivers': available_drivers,
        'locomotives': locomotives,
        'assignments': assignment_list,
        'paired_driver_ids': list(paired_driver_ids),
        'available_dates': filtered_dates,
        'available_assistants': available_assistants,
    })


def count_assigned_drivers(request):
    try:
        # Count distinct locomotive_id entries
        count = LocomotiveAssignment.objects.values('locomotive_id').distinct().count()
        return JsonResponse({'count': count})
    except Exception as e:
        # Return error as JSON with status code 500
        return JsonResponse({'error': str(e)}, status=500)



@login_required
def locomotive_wagon_assignment(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'remove_locomotive':
            assignment_id = request.POST.get('assignment_id')
            if assignment_id:
                try:
                    assignment = LocomotiveWagonAssignment.objects.get(id=int(assignment_id))
                    assignment.delete()
                    # Optionally, update wagon status if needed
                    wagon = assignment.wagon
                    wagon.is_assigned = False
                    wagon.status = 'AVAILABLE'
                    wagon.is_active = True
                    wagon.save()
                    messages.success(request, f'Locomotive removed from wagon {wagon.wagon_number}.')
                except Exception as e:
                    messages.error(request, f'Failed to remove locomotive: {e}')
            else:
                messages.error(request, 'Missing assignment selection.')
            return redirect('locomotive_wagon_assignment')
        # ...other POST actions (assign, unassign, reassign) go here...

    # """Admin interface to assign wagons to locomotives"""
    account_type = request.session.get('account_type')
    if account_type != "ADMIN":
        return redirect('login')

    from .models import LocomotiveWagonAssignment
    from django.db.models import Sum
    # Locomotive Performance Analysis (loco_summaries)
    loco_summaries = {}
    assigned_loco_ids = LocomotiveWagonAssignment.objects.values_list('locomotive_id', flat=True).distinct()
    for loco in LocomotiveSpec.objects.filter(id__in=assigned_loco_ids):
        assigned_wagons = LocomotiveWagonAssignment.objects.filter(locomotive=loco).select_related('wagon')
        wagon_count = assigned_wagons.count()
        total_weight = 0
        for a in assigned_wagons:
            w = a.wagon
            tare = float(w.tare_weight or 0)
            payload = float(w.payload_capacity or 0)
            total_weight += tare + payload
        try:
            capacity = float(loco.capacity_in_tons) if loco.capacity_in_tons else None
        except (ValueError, TypeError):
            capacity = None
        loco_power_hp = float(getattr(loco, 'tractive_effort', 0)) * 745.7 / 33 if getattr(loco, 'tractive_effort', None) else None
        tractive_effort = float(getattr(loco, 'tractive_effort', 0)) if getattr(loco, 'tractive_effort', None) else None
        power_required_flat = total_weight if total_weight else 0
        power_required_grade = total_weight * 3 if total_weight else 0
        power_to_weight = (loco_power_hp / total_weight) if (loco_power_hp and total_weight) else None
        capacity_used_percent = (total_weight / capacity * 100) if (capacity and total_weight) else 0
        if capacity is not None and total_weight > capacity:
            can_handle_status = 'critical'
            can_handle_message = 'Overloaded!'
        elif capacity is not None and total_weight > 0.9 * capacity:
            can_handle_status = 'warning'
            can_handle_message = 'Near limit'
        elif capacity is not None:
            can_handle_status = 'optimal'
            can_handle_message = 'OK'
        else:
            can_handle_status = 'unknown'
            can_handle_message = 'No capacity info'
        loco_summaries[loco.id] = {
            'name': loco.locomotive,
            'wagon_count': wagon_count,
            'total_weight': total_weight,
            'capacity': capacity,
            'capacity_used_percent': capacity_used_percent,
            'can_handle_status': can_handle_status,
            'can_handle_message': can_handle_message,
            'loco_power_hp': loco_power_hp,
            'tractive_effort': tractive_effort,
            'power_required_flat': power_required_flat,
            'power_required_grade': power_required_grade,
            'power_to_weight': power_to_weight,
        }


    # --- Dropdown and assignment logic ---
    from collections import defaultdict
    from django.utils import timezone
    today = timezone.now().date()
    # Date filter support
    date_filter = request.GET.get('date', '')
    schedule_filter_kwargs = {
        'date__gte': today,
        'driver__isnull': False,
        'assistant__isnull': False,
        'locomotives__isnull': False,
    }
    if date_filter:
        schedule_filter_kwargs['date'] = date_filter
    schedules = Schedule.objects.filter(**schedule_filter_kwargs).distinct().prefetch_related('locomotives', 'driver', 'assistant')
    driver_pair_to_loco_ids = defaultdict(list)
    driver_pair_to_loco_names = defaultdict(list)
    for sched in schedules:
        driver_ids = [sched.driver_id]
        if sched.assistant_id:
            driver_ids.append(sched.assistant_id)
        driver_pair_key = tuple(sorted(driver_ids))
        loco_ids = list(sched.locomotives.values_list('id', flat=True))
        loco_names = list(sched.locomotives.values_list('locomotive', flat=True))
        driver_pair_to_loco_ids[driver_pair_key].extend(loco_ids)
        driver_pair_to_loco_names[driver_pair_key].extend(loco_names)
    for pair in driver_pair_to_loco_names:
        driver_pair_to_loco_names[pair] = list(sorted(set(driver_pair_to_loco_names[pair])))
    locomotives = []
    for pair, loco_ids in driver_pair_to_loco_ids.items():
        locos = LocomotiveSpec.objects.filter(id__in=loco_ids)
        names = [l.locomotive for l in locos if l.locomotive]
        ids = [l.id for l in locos]
        if not ids:
            continue
        display_name = ', '.join(names)
        locomotives.append({'id': ids[0], 'display_name': display_name, 'names': names})

    wagons = WagonSpec.objects.filter(
        is_active=True,
        status='AVAILABLE',
        is_assigned=False
    ).order_by('wagon_number')

    # Handle POST requests
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'assign':
            locomotive_id = request.POST.get('locomotive_id')
            wagon_ids = request.POST.getlist('wagon_ids[]') or request.POST.getlist('wagon_ids')
            if not locomotive_id:
                messages.error(request, 'Please select a locomotive')
                return redirect('locomotive_wagon_assignment')
            if not wagon_ids:
                messages.error(request, 'Please select at least one wagon')
                return redirect('locomotive_wagon_assignment')
            try:
                loco = LocomotiveSpec.objects.filter(id=int(locomotive_id)).first()
            except Exception:
                loco = None
            if not loco:
                messages.error(request, 'Selected locomotive not found')
                return redirect('locomotive_wagon_assignment')
            try:
                loco_capacity = float(loco.capacity_in_tons) if loco.capacity_in_tons else None
            except (ValueError, TypeError):
                loco_capacity = None
            current_assignments = LocomotiveWagonAssignment.objects.filter(locomotive=loco).select_related('wagon')
            current_total_weight = 0
            for ca in current_assignments:
                wagon = ca.wagon
                tare = float(wagon.tare_weight or 0)
                payload = float(wagon.payload_capacity or 0)
                current_total_weight += (tare + payload)
            assigned_count = 0
            already_assigned = 0
            duplicate_count = 0
            capacity_exceeded = False
            skipped_for_capacity = []
            for wagon_id in wagon_ids:
                try:
                    wagon = WagonSpec.objects.filter(id=int(wagon_id)).first()
                    if wagon:
                        if wagon.is_assigned:
                            already_assigned += 1
                            continue
                        if LocomotiveWagonAssignment.objects.filter(locomotive=loco, wagon=wagon).exists():
                            duplicate_count += 1
                            continue
                        wagon_tare = float(wagon.tare_weight or 0)
                        wagon_payload = float(wagon.payload_capacity or 0)
                        wagon_total_weight = wagon_tare + wagon_payload
                        if loco_capacity:
                            new_total_weight = current_total_weight + wagon_total_weight
                            if new_total_weight > loco_capacity:
                                capacity_exceeded = True
                                skipped_for_capacity.append(wagon.wagon_number)
                                continue
                        obj, created = LocomotiveWagonAssignment.objects.get_or_create(
                            locomotive=loco,
                            wagon=wagon,
                            defaults={'assigned_by': request.user}
                        )
                        if created:
                            wagon.is_assigned = True
                            wagon.status = 'IN_USE'
                            wagon.save()
                            assigned_count += 1
                            current_total_weight += wagon_total_weight
                except Exception as e:
                    logging.error(f"Failed to assign wagon {wagon_id}: {str(e)}")
                    continue
            if assigned_count > 0:
                messages.success(request, f'Assigned {assigned_count} wagon(s) to {loco.locomotive}. Total weight: {current_total_weight:.2f} tons' + (f' / {loco_capacity:.0f} tons capacity' if loco_capacity else ''))
            if already_assigned > 0:
                messages.warning(request, f'{already_assigned} wagon(s) were already assigned to other locomotives')
            if duplicate_count > 0:
                messages.info(request, f'{duplicate_count} wagon(s) were already assigned to this locomotive')
            if capacity_exceeded:
                messages.error(request, f'Could not assign {len(skipped_for_capacity)} wagon(s) - would exceed locomotive capacity: {", ".join(skipped_for_capacity)}')
            return redirect('locomotive_wagon_assignment')
        elif action == 'unassign':
            assignment_id = request.POST.get('assignment_id')
            if assignment_id:
                try:
                    assignment = LocomotiveWagonAssignment.objects.get(id=int(assignment_id))
                    wagon_id = assignment.wagon.id
                    assignment.delete()
                    # Refresh wagon from DB to avoid stale reference
                    wagon = WagonSpec.objects.get(id=wagon_id)
                    wagon.is_assigned = False
                    wagon.status = 'AVAILABLE'
                    wagon.is_active = True
                    wagon.save()
                    messages.success(request, f'Wagon {wagon.wagon_number} unassigned and is now available')
                except Exception:
                    messages.error(request, 'Failed to unassign wagon')
            return redirect('locomotive_wagon_assignment')
        elif action == 'reassign':
            assignment_id = request.POST.get('assignment_id')
            new_locomotive_id = request.POST.get('new_locomotive_id')
            if assignment_id and new_locomotive_id:
                try:
                    assignment = LocomotiveWagonAssignment.objects.get(id=int(assignment_id))
                    new_loco = LocomotiveSpec.objects.get(id=int(new_locomotive_id))
                    assignment.locomotive = new_loco
                    assignment.save()
                    messages.success(request, f'Locomotive changed for wagon {assignment.wagon.wagon_number}.')
                except Exception as e:
                    messages.error(request, f'Failed to change locomotive: {e}')
            else:
                messages.error(request, 'Missing assignment or locomotive selection.')
            return redirect('locomotive_wagon_assignment')


    # --- Group assignments by unique locomotive pairs (for filter and table) ---
    from collections import defaultdict
    assignments_qs = LocomotiveWagonAssignment.objects.select_related('locomotive', 'wagon', 'assigned_by').order_by('-assigned_at')
    # Map: frozenset of loco IDs -> list of assignment dicts
    group_assignments = defaultdict(list)
    # Map: frozenset of loco IDs -> display name (comma separated)
    group_display_names = {}

    # Calculate totals for each group
    group_assignments_with_totals = {}
    for group_key, group in group_assignments.items():
        total_tare = sum(item['tare_weight'] for item in group)
        total_payload = sum(item['payload_capacity'] for item in group)
        total_weight = sum(item['total_weight'] for item in group)
        group_assignments_with_totals[group_key] = {
            'assignments': group,
            'total_tare': total_tare,
            'total_payload': total_payload,
            'total_weight': total_weight,
        }

    # Prepare filter options: unique locomotive pairings
    filter_options = []
    for group_key, display_name in group_display_names.items():
        filter_options.append({
            'key': ','.join(str(i) for i in sorted(group_key)),
            'display': display_name,
        })

    available_wagons = WagonSpec.objects.filter(is_active=True, status='AVAILABLE', is_assigned=False)
    all_wagons = WagonSpec.objects.all()
    in_use_wagons = WagonSpec.objects.filter(status='IN_USE')
    in_maintenance_wagons = WagonSpec.objects.filter(status='MAINTENANCE')
    ready_for_activation = WagonSpec.objects.filter(status='READY_FOR_ACTIVATION')
    written_off_wagons = WagonSpec.objects.filter(status='WRITTEN_OFF')
    wagon_assignment_map = {}
    for a in LocomotiveWagonAssignment.objects.select_related('wagon', 'locomotive'):
        wagon_assignment_map.setdefault(a.wagon.id, []).append(a.locomotive.id)
    total_wagons = WagonSpec.objects.count()
    total_capacity = sum(float(w.payload_capacity or 0) for w in WagonSpec.objects.all())
    total_in_use_capacity = sum(float(w.payload_capacity or 0) for w in in_use_wagons)
    available_capacity = total_capacity - total_in_use_capacity
    in_use_capacity = total_in_use_capacity
    maintenance_list = []
    for schedule in MaintenanceSchedule.objects.filter(item_type='WAGON').select_related('wagon').order_by('-created_at'):
        last_maintenance = MaintenanceSchedule.objects.filter(
            wagon=schedule.wagon,
            status='COMPLETED',
            actual_completion_date__isnull=False
        ).order_by('-actual_completion_date').first()
        if last_maintenance and last_maintenance.actual_completion_date:
            days_since = (timezone.now() - last_maintenance.actual_completion_date).days
            months_since = days_since / 30.44
            if months_since >= 12:
                urgency_level = 'CRITICAL'
                urgency_color = '#dc3545'
            elif months_since >= 9:
                urgency_level = 'HIGH'
                urgency_color = '#fd7e14'
            elif months_since >= 6:
                urgency_level = 'MEDIUM'
                urgency_color = '#ffc107'
            elif months_since >= 3:
                urgency_level = 'LOW'
                urgency_color = '#90ee90'
            else:
                urgency_level = 'GOOD'
                urgency_color = '#28a745'
            last_maintenance_date = last_maintenance.actual_completion_date
        else:
            urgency_level = 'CRITICAL'
            urgency_color = '#dc3545'
            days_since = 'Never'
            last_maintenance_date = None
        schedule.urgency_level = urgency_level
        schedule.urgency_color = urgency_color
        schedule.days_since_last = days_since
        schedule.last_maintenance_date = last_maintenance_date
        maintenance_list.append(schedule)
    from django.db.models import Count
    wagon_type_distribution = WagonSpec.objects.values('wagon_type').annotate(count=Count('id'))
    item_type_filter = ''
    sort_by = ''
    start_date = None
    end_date = None
    locomotive_filter = request.GET.get('locomotive', '')
    critical_count = sum(1 for m in maintenance_list if m.urgency_level == 'CRITICAL')
    high_count = sum(1 for m in maintenance_list if m.urgency_level == 'HIGH')
    assignments_by_wagon = defaultdict(list)
    for a in LocomotiveWagonAssignment.objects.select_related('locomotive', 'wagon'):
        assignments_by_wagon[a.wagon.id].append({
            'locomotive': a.locomotive.locomotive if a.locomotive else '',
            'assigned_at': a.assigned_at,
        })
    for wagon in in_use_wagons:
        wagon.assignments = assignments_by_wagon.get(wagon.id, [])

    context = {
        'Account_type': account_type,
        'available_wagons': available_wagons,
        'in_use_wagons': in_use_wagons,
        'in_maintenance_wagons': in_maintenance_wagons,
        'ready_for_activation_wagons': ready_for_activation,
        'written_off_wagons': written_off_wagons,
        'wagon_assignment_map': wagon_assignment_map,
        'total_wagons': total_wagons,
        'total_capacity': total_capacity,
        'total_in_use_capacity': total_in_use_capacity,
        'available_capacity': available_capacity,
        'in_use_capacity': in_use_capacity,
        'maintenance_schedules': maintenance_list,
        'wagon_type_distribution': wagon_type_distribution,
        'item_type_filter': item_type_filter,
        'sort_by': sort_by,
        'start_date': start_date,
        'end_date': end_date,
        'critical_count': critical_count,
        'high_count': high_count,
        'locomotive_filter': locomotive_filter,
        'wagons': wagons,
        'locomotives_list': locomotives,  # Only use this for the dropdown
        'group_assignments': group_assignments_with_totals,  # For table display
        'filter_options': filter_options,  # For filter dropdown
        'loco_summaries': loco_summaries,
        'date_filter': date_filter,
    }
    return render(request, 'locomotive_wagon_assignment.html', context)


@login_required
def schedule_wagon_maintenance(request):
    """Schedule wagon for maintenance"""
    account_type = request.session.get('account_type', 'OTHER')
    
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('wagon_specs')
    
    if request.method == 'POST':
        wagon_id = request.POST.get('wagon_id')
        reason = request.POST.get('reason')
        expected_completion = request.POST.get('expected_completion_date')
        maintenance_notes = request.POST.get('maintenance_notes', '')
        
        try:
            # Get the wagon being scheduled
            wagon = WagonSpec.objects.get(id=wagon_id)
            wagon_name = wagon.wagon_number or f"Wagon #{wagon.id}"
            
            # Update wagon status
            wagon.status = 'IN_MAINTENANCE'
            wagon.maintenance_status = 'UNDER_MAINTENANCE'
            wagon.save()
            
                       
            # Create maintenance schedule
            maintenance = MaintenanceSchedule.objects.create(
                item_type='WAGON',
                wagon=wagon,
                reason=reason,
                scheduled_by=request.user,
                scheduled_date=timezone.now(),
                expected_completion_date=expected_completion,
                status='IN_PROGRESS',
                maintenance_notes=maintenance_notes
            )
            
            # Create status update record
            MaintenanceStatusUpdate.objects.create(
                maintenance_schedule=maintenance,
                updated_by=request.user,
                previous_status='OPERATIONAL',
                new_status='IN_PROGRESS',
                update_notes=f"Scheduled for maintenance. Reason: {reason}"
            )
            
            messages.success(request, f'{wagon_name} has been scheduled for maintenance.')
            return redirect('wagon_dashboard')
            
        except WagonSpec.DoesNotExist:
            messages.error(request, 'Wagon not found.')
            return redirect('wagon_dashboard')
        except Exception as e:
            logging.exception('Failed to schedule wagon maintenance')
            messages.error(request, f'Failed to schedule maintenance: {str(e)}')
            return redirect('wagon_dashboard')
    
    # GET request - show form
    wagons = WagonSpec.objects.filter(
        status__in=['AVAILABLE', 'IN_USE'],
        is_active=True
    )
    
    context = {
        'Account_type': account_type,
        'wagons': wagons,
    }
    
    return render(request, 'schedule_wagon_maintenance.html', context)


@login_required
def update_wagon_maintenance_status(request, maintenance_id):
    """Update wagon maintenance status"""
    account_type = request.session.get('account_type', 'OTHER')
    
    if account_type not in ['ADMIN', 'MECHANICAL_MAINTENANCE_TEAM']:
        messages.error(request, 'Access denied. Insufficient privileges.')
        return redirect('wagon_dashboard')
    
    if request.method == 'POST':
        new_status = request.POST.get('new_status')
        update_notes = request.POST.get('update_notes', '')
        
        try:
            maintenance = MaintenanceSchedule.objects.get(id=maintenance_id, item_type='WAGON')
            previous_status = maintenance.status
            
            # Update maintenance status
            maintenance.status = new_status
            
            if new_status == 'COMPLETED':
                maintenance.actual_completion_date = timezone.now()
                # Update wagon status
                if maintenance.wagon:
                    maintenance.wagon.status = 'READY_FOR_ACTIVATION'
                    maintenance.wagon.maintenance_status = 'OPERATIONAL'
                    maintenance.wagon.save()
            
            elif new_status == 'READY_FOR_ACTIVATION':
                # Wagon is ready to be put back in service
                if maintenance.wagon:
                    maintenance.wagon.status = 'READY_FOR_ACTIVATION'
                    maintenance.wagon.save()
            
            maintenance.save()
            
            # Create status update record
            MaintenanceStatusUpdate.objects.create(
                maintenance_schedule=maintenance,
                updated_by=request.user,
                previous_status=previous_status,
                new_status=new_status,
                update_notes=update_notes
            )
            
            messages.success(request, f'Maintenance status updated to {new_status}')
            return redirect('wagon_dashboard')
        
        except MaintenanceSchedule.DoesNotExist:
            messages.error(request, 'Maintenance schedule not found.')
            return redirect('wagon_dashboard')
        except Exception as e:
            logging.exception('Failed to update wagon maintenance status')
            messages.error(request, f'Failed to update status: {str(e)}')
            return redirect('wagon_dashboard')
    
    return redirect('wagon_dashboard')


@login_required
def activate_wagon(request, wagon_id):
    """Activate a wagon that is ready for activation"""
    account_type = request.session.get('account_type', 'OTHER')
    
    if account_type != 'ADMIN':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('wagon_dashboard')
    
    try:
        wagon = WagonSpec.objects.get(id=wagon_id)
        
        if wagon.status == 'READY_FOR_ACTIVATION':
            wagon.status = 'AVAILABLE'
            wagon.is_active = True
            wagon.maintenance_status = 'OPERATIONAL'
            wagon.save()
            
            messages.success(request, f'Wagon {wagon.wagon_number} has been activated and is now available.')
        else:
            messages.warning(request, f'Wagon is not ready for activation. Current status: {wagon.status}')
        
        return redirect('wagon_dashboard')
        
    except WagonSpec.DoesNotExist:
        messages.error(request, 'Wagon not found.')
        return redirect('wagon_dashboard')
    except Exception as e:
        logging.exception('Failed to activate wagon')
        messages.error(request, f'Failed to activate wagon: {str(e)}')
        return redirect('wagon_dashboard')


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
            logging.debug(f"Saved location for user {getattr(request.user,'email',request.user)}: {lat},{lng}")
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    elif request.method == "GET":
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        from datetime import timedelta
        
        # Get all active sessions (not expired)
        active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        active_user_ids = set()
        
        # Extract user IDs from active sessions
        # Sessions store the PK, which for CustomUser is User_id (string UUID)
        for session in active_sessions:
            try:
                session_data = session.get_decoded()
                # Django stores the user's PK in _auth_user_id
                user_pk = session_data.get('_auth_user_id')
                if user_pk:
                    active_user_ids.add(str(user_pk))
            except:
                continue
        
        # If no active users found, return empty array
        if not active_user_ids:
            return JsonResponse([], safe=False)
        
        # Get latest location for each active user (must have active session)
        qs = UserLocation.objects.select_related('user').filter(
            user__User_id__in=active_user_ids
        ).order_by('user__User_id', '-timestamp')
        
        seen = set()
        data = []
        for loc in qs:
            uid = getattr(loc.user, 'User_id', None)
            if not uid or uid in seen:
                continue
            seen.add(uid)
            user = loc.user
            data.append({
                "lat": loc.latitude,
                "lng": loc.longitude,
                "timestamp": loc.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "user": {
                    "id": getattr(user, 'User_id', None),
                    "email": user.email,
                    "fullname": getattr(user, 'full_name', ''),
                    "role": getattr(user, 'role', ''),
                    "phone": getattr(user, 'phone_number', ''),
                }
            })
        return JsonResponse(data, safe=False)

    return JsonResponse({"error": "Invalid request"}, status=400)
@login_required
def api_get_locomotive_spec(request):
    """Return the most recent LocomotiveSpec for a given locomotive name.
    GET parameter: name
    """
    spec_id = request.GET.get('id')
    name = request.GET.get('name')
    spec = None
    if spec_id:
        try:
            spec = LocomotiveSpec.objects.filter(id=int(spec_id)).first()
        except Exception:
            spec = None
    elif name:
        spec = LocomotiveSpec.objects.filter(locomotive__iexact=name).order_by('-created_at').first()
    else:
        return JsonResponse({'error': 'id or name required'}, status=400)
    if not spec:
        return JsonResponse({}, status=204)
    return JsonResponse({
        'id': spec.id,
        'locomotive': spec.locomotive,
        'loc_type': spec.loc_type,
        'loc_class': spec.loc_class,
        'engine_supply': spec.engine_supply,
        'length': spec.length,
        'capacity_in_tons': spec.capacity_in_tons,
        'distributed_power': spec.distributed_power,
        'tractive_effort': spec.tractive_effort,
        'truck_circuit_spec': spec.truck_circuit_spec,
        'survey_raw': spec.survey_raw,
        'additional_specs': spec.additional_specs or [],
    })

@login_required
def wagon_maintenance_details(request, maintenance_id):
    """View detailed information about a wagon maintenance schedule"""
    account_type = request.session.get('account_type', 'OTHER')
    
    try:
        maintenance = MaintenanceSchedule.objects.select_related(
            'wagon', 'scheduled_by'
        ).get(id=maintenance_id, item_type='WAGON')
        
        # Get all status updates for this maintenance
        status_updates = MaintenanceStatusUpdate.objects.filter(
            maintenance_schedule=maintenance
        ).select_related('updated_by').order_by('-update_date')
        
        # Calculate duration
        maintenance.duration = maintenance.get_duration_in_maintenance()
        
        context = {
            'Account_type': account_type,
            'maintenance': maintenance,
            'status_updates': status_updates,
        }
        
        return render(request, 'wagon_maintenance_details.html', context)
        
    except MaintenanceSchedule.DoesNotExist:
        messages.error(request, 'Maintenance schedule not found.')
        return redirect('wagon_dashboard')
    except Exception as e:
        logging.exception('Failed to load wagon maintenance details')
        messages.error(request, f'Failed to load details: {str(e)}')
        return redirect('wagon_dashboard')


# ========== OPTIMIZER API ENDPOINTS ==========

from datetime import datetime
from django.db.models import Avg, Sum, Max, Min, F

# Configure external optimizer endpoint (can be moved to settings)
OPTIMIZER_API_BASE_URL = os.getenv('OPTIMIZER_API_URL', 'http://external-optimizer-api.com/api/v1')
OPTIMIZER_API_KEY = os.getenv('OPTIMIZER_API_KEY', 'your-api-key-here')


def convert_to_serializable(obj):
    """
    Convert non-serializable objects (Decimal, datetime) to JSON-serializable formats
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    return obj


def collect_system_data(optimization_type='FULL_SYSTEM'):
    """
    Collect current system data for optimization
    Returns a dictionary with all relevant system metrics
    """
    data = {
        'timestamp': timezone.now().isoformat(),
        'optimization_type': optimization_type,
    }
    
    # Locomotive data
    locomotives = LocomotiveSpec.objects.all()
    data['locomotives'] = {
        'total': locomotives.count(),
        'operational': locomotives.filter(maintenance_status='OPERATIONAL').count(),
        'under_maintenance': locomotives.filter(maintenance_status='UNDER_MAINTENANCE').count(),
        'written_off': locomotives.filter(maintenance_status='WRITTEN_OFF').count(),
        'details': list(locomotives.values(
            'id', 'locomotive', 'loc_class', 'loc_type', 'capacity_in_tons',
            'status', 'maintenance_status', 'is_active', 'engine_supply', 'tractive_effort'
        ))
    }
    
    # Wagon data
    wagons = WagonSpec.objects.all()
    data['wagons'] = {
        'total': wagons.count(),
        'available': wagons.filter(is_assigned=False, status='AVAILABLE').count(),
        'assigned': wagons.filter(is_assigned=True).count(),
        'under_maintenance': wagons.filter(status='IN_MAINTENANCE').count(),
        'details': list(wagons.values(
            'id', 'wagon_number', 'wagon_type', 'payload_capacity', 'tare_weight',
            'is_assigned', 'status', 'is_active', 'maximum_speed'
        ))
    }
    
    # Cargo data
    cargo = CargoSpec.objects.all()
    data['cargo'] = {
        'total': cargo.count(),
        'available': cargo.filter(status='AVAILABLE').count(),
        'in_use': cargo.filter(status='IN_USE').count(),
        'operational': cargo.filter(maintenance_status='OPERATIONAL').count(),
        'total_weight': cargo.aggregate(total=Sum('cargo_weight_tons'))['total'] or 0,
        'details': list(cargo.values(
            'id', 'cargo_type', 'cargo_weight_tons', 'cargo_volume',
            'special_handling', 'status', 'maintenance_status', 'is_active'
        ))
    }
    
    # Route data
    routes = RoutePreferenceSpec.objects.all()
    data['routes'] = {
        'total': routes.count(),
        'details': list(routes.values(
            'id', 'preferred_route_corridor', 'transshipment_required',
            'delivery_node', 'receiving_facility', 'created_at'
        ))
    }
    
    # Fuel data
    fuel = FuelSpec.objects.all()
    data['fuel'] = {
        'total_entries': fuel.count(),
        'details': list(fuel.values(
            'id', 'fuel_type', 'daily_fuel_consumption',
            'fuel_cost_per_litre', 'average_load_per_trip', 'created_at'
        ))
    }
    
    # Assignment data
    assignments = LocomotiveAssignment.objects.select_related('locomotive', 'driver').all()
    data['assignments'] = {
        'total': assignments.count(),
        'details': list(assignments.values(
            'id', 'locomotive__locomotive', 'driver__email',
            'driver__first_name', 'driver__last_name', 'assigned_at'
        ))
    }

    # Wagon assignments
    wagon_assignments = LocomotiveWagonAssignment.objects.select_related('locomotive', 'wagon').all()
    data['wagon_assignments'] = {
        'total': wagon_assignments.count(),
        'details': list(wagon_assignments.values(
            'id', 'locomotive__locomotive', 'wagon__wagon_number'
        ))
    }
    
    # Maintenance schedules
    maintenance = MaintenanceSchedule.objects.filter(status='IN_PROGRESS')
    data['maintenance'] = {
        'active_schedules': maintenance.count(),
        'locomotives_in_maintenance': maintenance.filter(item_type='LOCOMOTIVE').count(),
        'wagons_in_maintenance': maintenance.filter(item_type='WAGON').count(),
        'details': list(maintenance.values(
            'id', 'item_type', 'reason', 'status',
            'scheduled_date', 'expected_completion_date', 'actual_completion_date'
        ))
    }
    
    # Driver requests
    driver_requests = DriverRequest.objects.filter(status='PENDING')
    data['driver_requests'] = {
        'pending': driver_requests.count(),
        'details': list(driver_requests.values(
            'id', 'user__email', 'user__first_name', 'user__last_name',
            'issue_description', 'incident_category', 'priority',
            'latitude', 'longitude', 'status', 'created_at'
        ))
    }
    
    # Convert all Decimal and datetime objects to JSON-serializable formats
    return convert_to_serializable(data)


def send_scheduling_to_optimizer_and_bi():
    # Collect all scheduling data
    schedules = Schedule.objects.all()
    serializer = ScheduleSerializer(schedules, many=True)
    schedule_data = serializer.data

    # Send to Optimizer
    optimizer_url = 'https://optimizer.example.com/api/optimize/'  # Replace with real endpoint
    optimizer_response = requests.post(optimizer_url, json={'schedules': schedule_data})
    optimizer_suggestions = optimizer_response.json().get('suggestions', [])

    # Store suggestions for admin review (could be in cache, DB, or session)
    # For demo, return them

    # Send to BI
    bi_url = 'https://bi.example.com/api/receive-data/'  # Replace with real endpoint
    bi_response = requests.post(bi_url, json={'schedules': schedule_data})

    return {
        'optimizer_suggestions': optimizer_suggestions,
        'bi_status': bi_response.status_code
    }

# Usage example (call this after admin configures scheduling):
# result = send_scheduling_to_optimizer_and_bi()
# optimizer_suggestions = result['optimizer_suggestions']
# Show these to admin in the UI for review/acceptance.

# --- API VIEWSETS ---

from rest_framework import viewsets
from .models import CustomUser, LocomotiveSpec, LocomotiveAssignment, Schedule
from .serializers import DriverSerializer, LocomotiveSerializer, LocomotiveAssignmentSerializer, ScheduleSerializer

class DriverViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.filter(role='DRIVER')
    serializer_class = DriverSerializer

class LocomotiveViewSet(viewsets.ModelViewSet):
    queryset = LocomotiveSpec.objects.all()
    serializer_class = LocomotiveSerializer

class LocomotiveAssignmentViewSet(viewsets.ModelViewSet):
    queryset = LocomotiveAssignment.objects.all()
    serializer_class = LocomotiveAssignmentSerializer

class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer

def all_users(request):
    User = get_user_model()
    users = User.objects.all().values('id', 'email', 'first_name', 'last_name', 'account_type', 'role')
    return JsonResponse(list(users), safe=False)

from django.contrib.auth import logout as auth_logout

def complete_trip(request):
    user = request.user
    # Mark all active Schedules and LocomotiveAssignments as completed for this user (driver or assistant)
    if user.is_authenticated:
        # Update Schedule
        from .models import Schedule, LocomotiveAssignment
        Schedule.objects.filter(
            (Q(driver=user) | Q(assistant=user)),
            status__in=['assigned']
        ).update(status='completed', updated_at=timezone.now())
        # Update LocomotiveAssignment
        LocomotiveAssignment.objects.filter(
            Q(driver=user) | Q(assistant=user),
            status='assigned'
        ).update(status='completed')
        # Log out the user
        auth_logout(request)
        messages.success(request, 'Trip marked as completed and you have been logged out.')
        return redirect('login')
    else:
        messages.error(request, 'You are not logged in.')
        return redirect('login')

# Restore security_guard_report view to render the security_guard_report.html template
@login_required
def security_guard_report(request):
    # You can add context with report data if needed
    return render(request, 'security_guard_report.html', {})

# Restore security_emergency_call view to render the security_emergency_call.html template
@login_required
def security_emergency_call(request):
    # You can add context with emergency call data if needed
    return render(request, 'security_emergency_call.html', {})

# Restore security_manager view to render the security_manager.html template
@login_required
def security_manager(request):
    # You can add context with manager data if needed
    return render(request, 'security_manager.html', {})

# Restore security_supervisor view to render the security_supervisor.html template
@login_required
def security_supervisor(request):
    # You can add context with supervisor data if needed
    return render(request, 'security_supervisor.html', {})

# Restore security_supervisor_call view to render the security_supervisor_call.html template
@login_required
def security_supervisor_call(request):
    # You can add context with supervisor call data if needed
    return render(request, 'security_supervisor_call.html', {})











