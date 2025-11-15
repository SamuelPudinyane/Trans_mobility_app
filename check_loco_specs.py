import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobility.settings')
django.setup()

from transnet_mobility.models import LocomotiveSpec

print('=== LOCOMOTIVE SPECIFICATIONS ===\n')
locos = LocomotiveSpec.objects.all()

for loco in locos:
    print(f'Locomotive: {loco.locomotive}')
    print(f'  Type: {loco.loc_type}')
    print(f'  Class: {loco.loc_class}')
    print(f'  Capacity: {loco.capacity_in_tons} tons')
    print(f'  Tractive Effort: {loco.tractive_effort}')
    print(f'  Distributed Power: {loco.distributed_power}')
    print(f'  Engine Supply: {loco.engine_supply}')
    print(f'  Length: {loco.length}')
    print(f'  Status: {loco.status}')
    print(f'  Maintenance Status: {loco.maintenance_status}')
    print()
