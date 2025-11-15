import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobility.settings')
django.setup()

from transnet_mobility.models import WagonSpec, LocomotiveWagonAssignment
from django.db.models import Count

print('=== FIXING DUPLICATE WAGON ASSIGNMENTS ===\n')

# Find wagons assigned to multiple locomotives
duplicate_assignments = (
    LocomotiveWagonAssignment.objects
    .values('wagon')
    .annotate(count=Count('wagon'))
    .filter(count__gt=1)
)

if duplicate_assignments.exists():
    print(f'Found {duplicate_assignments.count()} wagon(s) assigned to multiple locomotives:\n')
    
    for dup in duplicate_assignments:
        wagon_id = dup['wagon']
        wagon = WagonSpec.objects.get(id=wagon_id)
        assignments = LocomotiveWagonAssignment.objects.filter(wagon=wagon).select_related('locomotive')
        
        print(f'Wagon: {wagon.wagon_number}')
        print(f'  Currently assigned to {assignments.count()} locomotives:')
        for i, assignment in enumerate(assignments, 1):
            print(f'    {i}. {assignment.locomotive.locomotive} (assigned {assignment.assigned_at})')
        
        # Keep only the FIRST assignment (oldest one), delete the rest
        assignments_to_delete = list(assignments[1:])
        if assignments_to_delete:
            print(f'  Removing {len(assignments_to_delete)} duplicate assignment(s)...')
            for assignment in assignments_to_delete:
                print(f'    Removed: {assignment.locomotive.locomotive}')
                assignment.delete()
            print(f'  ✓ Kept oldest assignment: {assignments[0].locomotive.locomotive}\n')
else:
    print('No duplicate wagon assignments found.\n')

print('=== VERIFYING FINAL STATE ===\n')
all_wagons = WagonSpec.objects.all()
for wagon in all_wagons:
    assignments = LocomotiveWagonAssignment.objects.filter(wagon=wagon)
    print(f'Wagon {wagon.wagon_number}: {assignments.count()} assignment(s)')
    if assignments.exists():
        for a in assignments:
            print(f'  -> {a.locomotive.locomotive}')

print('\n✓ Database cleaned successfully!')
