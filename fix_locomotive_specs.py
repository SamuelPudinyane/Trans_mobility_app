import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobility.settings')
django.setup()

from transnet_mobility.models import LocomotiveSpec

print('=== UPDATING LOCOMOTIVE SPECIFICATIONS ===\n')

locos = LocomotiveSpec.objects.all()

# Realistic specifications for South African freight locomotives
spec_updates = [
    {
        'capacity_in_tons': '5000',
        'tractive_effort': '500',
        'distributed_power': 'Yes',
        'engine_supply': 'Electric - 3000V DC',
    },
    {
        'capacity_in_tons': '7500',
        'tractive_effort': '650',
        'distributed_power': 'Yes',
        'engine_supply': 'Electric - 3000V DC',
    }
]

for i, loco in enumerate(locos):
    print(f'Updating: {loco.locomotive}')
    print(f'  Old Capacity: {loco.capacity_in_tons}')
    print(f'  Old Tractive Effort: {loco.tractive_effort}')
    
    # Use the spec updates if available, otherwise use default values
    if i < len(spec_updates):
        specs = spec_updates[i]
    else:
        specs = spec_updates[0]  # Default to first spec
    
    loco.capacity_in_tons = specs['capacity_in_tons']
    loco.tractive_effort = specs['tractive_effort']
    loco.distributed_power = specs['distributed_power']
    loco.engine_supply = specs['engine_supply']
    loco.save()
    
    print(f'  New Capacity: {loco.capacity_in_tons} tons')
    print(f'  New Tractive Effort: {loco.tractive_effort} kN')
    print(f'  Distributed Power: {loco.distributed_power}')
    print(f'  Engine Supply: {loco.engine_supply}')
    print('  ✓ Updated successfully!\n')

print('=== VERIFICATION ===\n')
for loco in LocomotiveSpec.objects.all():
    print(f'{loco.locomotive}:')
    print(f'  Capacity: {loco.capacity_in_tons} tons')
    print(f'  Tractive Effort: {loco.tractive_effort} kN')
    print()

print('✓ All locomotives updated with realistic specifications!')
