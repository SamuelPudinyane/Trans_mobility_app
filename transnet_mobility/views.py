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
import logging
from .user_dummy_data import users
from .models import UserLocation,CustomUser,LocomotiveSpec
from .models import CargoSpec, WheelsetSpec
from .models import RoutePreferenceSpec, LocomotiveAssignment
from .models import FuelSpec
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


@login_required
def password_reset(request):
    return render(request, 'password_reset.html')


@login_required
def home(request):
    return render(request, 'edit_user.html')


@login_required
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
            # Basic required-field validation
            if not email or not password:
                messages.error(request, "Email and password are required.")
                return render(request, 'register_user.html')

            # Map human-friendly account_type values from the template to the model choice codes
            account_type_map = {
                'Driver': 'DRIVER',
                'Electrical Maintenance Team': 'ELECTICAL_MAINTENANCE_TEAM',
                'Mechanical Maintenance Team': 'MECHANICAL_MAINTENANCE_TEAM',
                'Emergency Response Team': 'EMERGENCY_RESPONSE_TEAM',
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
            )
            user.save()
            messages.success(request, "User registered successfully!")
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
                    survey_raw = survey_raw
                )
                messages.success(request, 'Locomotive specification saved')
            return redirect('locomotive_config')
        except Exception as e:
            logging.exception('Failed to save locomotive spec')
            messages.error(request, 'Failed to save locomotive specification')

    return render(request, 'locomotive_config.html',{'Account_type':"ADMIN", 'locomotives': locomotives})


@login_required
def cargo_specs(request):
    account_type=request.session.get('account_type')

    if account_type!="ADMIN":
        return redirect('login')

    # list recent cargo specs for select
    cargo_qs = CargoSpec.objects.exclude(cargo_type__isnull=True).exclude(cargo_type__exact='').order_by('-created_at').values('id','cargo_type')
    cargos = []
    _seen = set()
    for row in cargo_qs:
        nm = row.get('cargo_type')
        if nm and nm not in _seen:
            _seen.add(nm)
            cargos.append({'id': row.get('id'), 'name': nm})

    if request.method == 'POST':
        try:
            cargo_type = request.POST.get('cargo_type') or ''
            cargo_volume = request.POST.get('cargo_volume') or ''
            special_handling = request.POST.get('special_handling') or ''

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

            if not existing and cargo_type:
                existing = CargoSpec.objects.filter(cargo_type__iexact=cargo_type).order_by('-created_at').first()

            if existing:
                if cargo_type:
                    existing.cargo_type = cargo_type
                existing.cargo_volume = cargo_volume
                existing.special_handling = special_handling
                existing.survey_raw = survey_raw
                existing.save()
                messages.success(request, f'Cargo "{cargo_type}" updated')
            else:
                CargoSpec.objects.create(
                    created_by=request.user,
                    cargo_type=cargo_type,
                    cargo_volume=cargo_volume,
                    special_handling=special_handling,
                    survey_raw=survey_raw
                )
                messages.success(request, 'Cargo saved')
            return redirect('cargo_specs')
        except Exception:
            logging.exception('Failed to save cargo spec')
            messages.error(request, 'Failed to save cargo specification')

    return render(request, 'cargo_specs.html', {'Account_type': 'ADMIN', 'cargos': cargos})


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
        'cargo_type': spec.cargo_type,
        'cargo_volume': spec.cargo_volume,
        'special_handling': spec.special_handling,
        'survey_raw': spec.survey_raw,
    })

@login_required
def wheelset(request):
    account_type=request.session.get('account_type')
    # Allow both DRIVER and ADMIN users to view and save route preferences
    if account_type not in ("ADMIN", "DRIVER"):
        return redirect('login')

    wheel_qs = WheelsetSpec.objects.exclude(wheel_profile__isnull=True).exclude(wheel_profile__exact='').order_by('-created_at').values('id','wheel_profile')
    wheels = []
    _seen = set()
    for row in wheel_qs:
        nm = row.get('wheel_profile')
        if nm and nm not in _seen:
            _seen.add(nm)
            wheels.append({'id': row.get('id'), 'name': nm})

    if request.method == 'POST':
        try:
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
                    existing = WheelsetSpec.objects.filter(id=int(selected_id)).first()
                except Exception:
                    existing = None

            if not existing and wheel_profile:
                existing = WheelsetSpec.objects.filter(wheel_profile__iexact=wheel_profile).order_by('-created_at').first()

            if existing:
                if wheel_profile:
                    existing.wheel_profile = wheel_profile
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

    return render(request, 'wheelset.html', {'Account_type': 'ADMIN', 'wheels': wheels})


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
def api_get_route_preference_spec(request):
    spec_id = request.GET.get('id')
    if not spec_id:
        return JsonResponse({'error': 'id required'}, status=400)
    spec = RoutePreferenceSpec.objects.filter(id=int(spec_id)).first()
    if not spec:
        return JsonResponse({}, status=204)
    return JsonResponse({
        'id': spec.id,
        'preferred_route_corridor': spec.preferred_route_corridor,
        'transshipment_required': spec.transshipment_required,
        'delivery_node': spec.delivery_node,
        'receiving_facility': spec.receiving_facility,
        'survey_raw': spec.survey_raw,
    })

@login_required
def driver_assignment(request):
    account_type = request.session.get('account_type')
    if account_type != "ADMIN":
        return redirect('login')

    # Pull distinct locomotive names (with latest spec id) to populate select
    loc_qs = LocomotiveSpec.objects.exclude(locomotive__isnull=True).exclude(locomotive__exact='').order_by('-created_at').values('id','locomotive')
    locomotives = []
    _seen = set()
    for row in loc_qs:
        nm = row.get('locomotive')
        if nm and nm not in _seen:
            _seen.add(nm)
            locomotives.append({'id': row.get('id'), 'name': nm})

    # Pull available drivers: users with role DRIVER who are NOT assigned to any locomotive
    # Use User model (CustomUser) and filter by role
    assigned_driver_ids = LocomotiveAssignment.objects.values_list('driver__User_id', flat=True)
    available_drivers = CustomUser.objects.filter(role='DRIVER').exclude(User_id__in=list(assigned_driver_ids)).values('User_id','email','first_name','last_name')

    # Handle assignment POSTs (create, unassign, reassign)
    if request.method == 'POST':
        action = request.POST.get('action')

        # Unassign (delete) an assignment
        if action == 'unassign':
            assignment_id = request.POST.get('assignment_id')
            if assignment_id:
                try:
                    a = LocomotiveAssignment.objects.filter(id=int(assignment_id)).first()
                except Exception:
                    a = None
                if a:
                    a.delete()
                    messages.success(request, 'Assignment removed')
                else:
                    messages.error(request, 'Assignment not found')
            return redirect('driver_assignment')

        # Reassign driver to another locomotive
        if action == 'reassign':
            assignment_id = request.POST.get('assignment_id')
            new_loco_id = request.POST.get('new_locomotive_id')
            if not assignment_id or not new_loco_id:
                messages.error(request, 'Invalid reassign request')
                return redirect('driver_assignment')
            try:
                a = LocomotiveAssignment.objects.filter(id=int(assignment_id)).first()
                new_loco = LocomotiveSpec.objects.filter(id=int(new_loco_id)).first()
            except Exception:
                a = None
                new_loco = None
            if not a or not new_loco:
                messages.error(request, 'Assignment or locomotive not found')
                return redirect('driver_assignment')

            # ensure target loco will not exceed 2 drivers after move
            existing_count = LocomotiveAssignment.objects.filter(locomotive=new_loco).exclude(id=a.id).count()
            if existing_count >= 2:
                messages.error(request, 'Cannot reassign: target locomotive already has 2 drivers')
                return redirect('driver_assignment')

            a.locomotive = new_loco
            a.save()
            messages.success(request, 'Assignment updated')
            return redirect('driver_assignment')

        # default: create new assignments from checkbox list
        locomotive_id = request.POST.get('locomotive_id')
        selected_driver_ids = request.POST.getlist('driver_ids[]') or request.POST.getlist('driver_ids')
        if not locomotive_id:
            messages.error(request, 'Please select a locomotive')
            return redirect('driver_assignment')
        try:
            loco = LocomotiveSpec.objects.filter(id=int(locomotive_id)).first()
        except Exception:
            loco = None
        if not loco:
            messages.error(request, 'Selected locomotive not found')
            return redirect('driver_assignment')

        # enforce maximum of 2 drivers
        if len(selected_driver_ids) == 0:
            messages.error(request, 'Please select at least one driver to assign')
            return redirect('driver_assignment')
        if len(selected_driver_ids) > 2:
            messages.error(request, 'You can assign a maximum of 2 drivers to a locomotive')
            return redirect('driver_assignment')

        # check existing assignments count for this locomotive
        existing_count = LocomotiveAssignment.objects.filter(locomotive=loco).count()
        if existing_count + len(selected_driver_ids) > 2:
            messages.error(request, 'Assigning these drivers would exceed the maximum of 2 drivers for this locomotive')
            return redirect('driver_assignment')

        # create assignment rows, skip duplicates
        created = 0
        for did in selected_driver_ids:
            try:
                driver = CustomUser.objects.filter(User_id=did).first()
            except Exception:
                driver = None
            if not driver:
                continue
            # create if not exists
            obj, created_flag = LocomotiveAssignment.objects.get_or_create(locomotive=loco, driver=driver)
            if created_flag:
                created += 1

        if created:
            messages.success(request, f'Assigned {created} driver(s) to {loco.locomotive or "(unnamed)"}')
        else:
            messages.info(request, 'Selected drivers were already assigned')
        return redirect('driver_assignment')

    # Also load current assignments to show in the assignments table
    assignments_qs = LocomotiveAssignment.objects.select_related('driver', 'locomotive').order_by('-assigned_at')
    assignments = []
    for a in assignments_qs:
        assignments.append({
            'id': a.id,
            'driver_id': getattr(a.driver, 'User_id', ''),
            'driver_name': f"{getattr(a.driver,'first_name','') } {getattr(a.driver,'last_name','') }".strip(),
            'driver_email': getattr(a.driver, 'email', ''),
            'locomotive_id': getattr(a.locomotive, 'id', ''),
            'locomotive_name': getattr(a.locomotive, 'locomotive', ''),
            'assigned_at': a.assigned_at,
        })

    return render(request, 'driver_assignment.html', {
        'Account_type': 'ADMIN',
        'locomotives': locomotives,
        'available_drivers': available_drivers,
        'assignments': assignments,
    })


@login_required
def all_users(request):
    return render(request, 'all_users.html')


@login_required
def notifications(request):
    return render(request, 'notifications.html')

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
def driver_request(request):
    account_type=request.session.get('account_type')
    
    if account_type=="DRIVER":
        return render(request, 'driver_request.html',{'Account_type':"DRIVER"})
    elif account_type=="DRIVER":
        return render(request, 'driver_request.html',{'Account_type':"DRIVER"})


    else:
        return redirect('login')


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
        # DB-agnostic: order by user then newest timestamp, then pick the first row per user in Python
        qs = UserLocation.objects.select_related('user').order_by('user__User_id', '-timestamp')
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
    })


@login_required
def map_location(request):
    
        account_type=request.session.get('account_type')
        if account_type=="DRIVER":
            return render(request, 'map_location.html',{'Account_type':"DRIVER"})
        elif account_type=="DRIVER":
            return render(request, 'map_location.html',{'Account_type':"DRIVER"})
        elif account_type=="ADMIN":
            return render(request, 'map_location.html',{'Account_type':"ADMIN"})
    
        else:
            return redirect('login')
    

@login_required
def map_location_railway(request):
    account_type=request.session.get('account_type')
    
    if account_type=="DRIVER":
        return render(request, 'map_location_railway.html',{'Account_type':"DRIVER"})
    elif account_type=="DRIVER":
        return render(request, 'map_location_railway.html',{'Account_type':"DRIVER"})
    elif account_type=="ADMIN":
        return render(request, 'map_location_railway.html',{'Account_type':"ADMIN"})

    else:
        return redirect('login')


@login_required
def fuel_matrics(request):
    account_type=request.session.get('account_type')
    
    if account_type=="DRIVER":
        # list recent fuel specs to populate select/table
        fuel_qs = FuelSpec.objects.order_by('-created_at').values('id','daily_fuel_consumption','fuel_cost_per_litre','average_load_per_trip','fuel_type')
        fuels = []
        for row in fuel_qs:
            fuels.append({
                'id': row.get('id'),
                'daily_fuel_consumption': row.get('daily_fuel_consumption'),
                'fuel_cost_per_litre': row.get('fuel_cost_per_litre'),
                'average_load_per_trip': row.get('average_load_per_trip'),
                'fuel_type': row.get('fuel_type'),
            })

        if request.method == 'POST':
            try:
                daily = request.POST.get('daily_fuel_consumption') or ''
                cost = request.POST.get('fuel_cost_per_litre') or ''
                avg_load = request.POST.get('average_load_per_trip') or ''
                ftype = request.POST.get('fuel_type') or ''

                # simple survey passthrough if present
                survey_meta = request.POST.getlist('survey_questions[]')
                parts = []
                for idx, meta_json in enumerate(survey_meta):
                    try:
                        meta = json.loads(meta_json)
                    except Exception:
                        continue
                    qtext = meta.get('text','')
                    qtype = meta.get('type','')
                    # note: answers are not parsed here for brevity
                    parts.append(','.join([qtext, qtype]))
                survey_raw = ','.join(parts)

                existing = None
                selected_id = request.POST.get('selected_spec_id')
                if selected_id:
                    try:
                        existing = FuelSpec.objects.filter(id=int(selected_id)).first()
                    except Exception:
                        existing = None

                if existing:
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

        return render(request, 'fuel_matrics.html', {'Account_type': 'DRIVER', 'fuels': fuels})
    elif account_type=="DRIVER":
        return render(request, 'fuel_matrics.html',{'Account_type':"DRIVER"})

    else:
        return redirect('login')


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
        'daily_fuel_consumption': spec.daily_fuel_consumption,
        'fuel_cost_per_litre': spec.fuel_cost_per_litre,
        'average_load_per_trip': spec.average_load_per_trip,
        'fuel_type': spec.fuel_type,
        'survey_raw': spec.survey_raw,
    })


@login_required
def route_and_node_preference(request):
    account_type = request.session.get('account_type')
    # Allow both ADMIN and DRIVER users to view and save route preferences
    if account_type not in ("ADMIN", "DRIVER"):
        return redirect('login')

    # recent route prefs for select
    # include the key fields so the template can render them in the table
    rp_qs = RoutePreferenceSpec.objects.exclude(preferred_route_corridor__isnull=True).exclude(preferred_route_corridor__exact='').order_by('-created_at').values(
        'id', 'preferred_route_corridor', 'transshipment_required', 'delivery_node', 'receiving_facility'
    )
    prefs = []
    _seen = set()
    for row in rp_qs:
        nm = row.get('preferred_route_corridor')
        if nm and nm not in _seen:
            _seen.add(nm)
            prefs.append({
                'id': row.get('id'),
                'name': nm,
                'transshipment_required': row.get('transshipment_required'),
                'delivery_node': row.get('delivery_node'),
                'receiving_facility': row.get('receiving_facility'),
            })

    if request.method == 'POST':
        try:
            preferred_route_corridor = request.POST.get('preferred_route_corridor') or ''
            transshipment_required = request.POST.get('transshipment_required') or ''
            delivery_node = request.POST.get('delivery_node') or ''
            receiving_facility = request.POST.get('receiving_facility') or ''

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
                    existing = RoutePreferenceSpec.objects.filter(id=int(selected_id)).first()
                except Exception:
                    existing = None

            if not existing and preferred_route_corridor:
                existing = RoutePreferenceSpec.objects.filter(preferred_route_corridor__iexact=preferred_route_corridor).order_by('-created_at').first()

            if existing:
                if preferred_route_corridor:
                    existing.preferred_route_corridor = preferred_route_corridor
                existing.transshipment_required = transshipment_required
                existing.delivery_node = delivery_node
                existing.receiving_facility = receiving_facility
                existing.survey_raw = survey_raw
                existing.save()
                messages.success(request, f'Route Preference "{preferred_route_corridor}" updated')
            else:
                RoutePreferenceSpec.objects.create(
                    created_by=request.user,
                    preferred_route_corridor=preferred_route_corridor,
                    transshipment_required=transshipment_required,
                    delivery_node=delivery_node,
                    receiving_facility=receiving_facility,
                    survey_raw=survey_raw
                )
                messages.success(request, 'Route preference saved')
            return redirect('route_and_node_preference')
        except Exception:
            logging.exception('Failed to save route preference')
            messages.error(request, 'Failed to save route preference')

        # Pass the actual Account_type so templates can adapt for DRIVER vs ADMIN
        return render(request, 'route_and_node_preference.html', {'Account_type': account_type, 'prefs': prefs})

    # For GET (or if no POST-related return happened) render the page
    return render(request, 'route_and_node_preference.html', {'Account_type': account_type, 'prefs': prefs})

@login_required
def load_strategic(request):
    account_type=request.session.get('account_type')

    if account_type=="DRIVER":
        return render(request, 'load_strategic.html',{'Account_type':"DRIVER"})
    elif account_type=="DRIVER":
        return render(request, 'load_strategic.html',{'Account_type':"DRIVER"})

    else:
        return redirect('login')


@login_required
def route_corridor(request):
    return render(request, 'route_corridor.html')

@login_required
def profile(request):
    profile=request.session.get('account_type')
  
    Account_type=profile

    return render(request,'profile.html',{"profile":profile,"Account_type":Account_type})

@login_required
def security_guard_report(request):
    account_type=request.session.get('account_type')
    
    return render(request, 'security_guard_report.html',{'Account_type':"Security"})

@login_required
def security_emergency_call(request):
    account_type=request.session.get('account_type')
   
    return render(request, 'security_emergency_call.html',{'Account_type':"Security"})


@login_required
def security_supervisor(request):
    account_type=request.session.get('account_type')
  
    return render(request, 'security_supervisor.html',{'Account_type':"Security Supervisor"})


@login_required
def security_supervisor_call(request):
    account_type=request.session.get('account_type')

    return render(request, 'security_supervisor_call.html',{'Account_type':"Security Supervisor"})



def logout(request):
    request.session.pop('account_type',None)
    return render(request,'login.html')














