import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobility.settings')
django.setup()

from transnet_mobility.models import WagonSpec, LocomotiveSpec, LocomotiveWagonAssignment, LocomotiveAssignment

print('=== WAGON STATUS ===')
wagons = WagonSpec.objects.all()
print(f'Total Wagons: {wagons.count()}')
for w in wagons:
    print(f'  {w.wagon_number}: is_active={w.is_active}, status={w.status}, is_assigned={w.is_assigned}')

print('\n=== LOCOMOTIVE STATUS ===')
locos = LocomotiveSpec.objects.all()
print(f'Total Locomotives: {locos.count()}')
for l in locos:
    print(f'  {l.locomotive}: maintenance_status={l.maintenance_status}, status={l.status}')
    driver_assignments = LocomotiveAssignment.objects.filter(locomotive=l)
    print(f'    Driver Assignments: {driver_assignments.count()}')
    for da in driver_assignments:
        print(f'      - Driver: {da.driver.email}, Assigned: {da.assigned_at}')

print('\n=== WAGON ASSIGNMENTS ===')
wagon_assignments = LocomotiveWagonAssignment.objects.all()
print(f'Total Wagon Assignments: {wagon_assignments.count()}')
for wa in wagon_assignments:
    print(f'  Loco: {wa.locomotive.locomotive} -> Wagon: {wa.wagon.wagon_number}')
