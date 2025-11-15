import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobility.settings')
django.setup()

from transnet_mobility.models import LocomotiveSpec, CustomUser

# Get admin user for created_by field
admin = CustomUser.objects.filter(role='ADMIN').first()
if not admin:
    print("❌ No admin user found. Please create an admin user first.")
    exit()

print('=== CREATING FAKE LOCOMOTIVE DATA ===\n')

# Realistic South African freight locomotive specifications
locomotives_data = [
    {
        'locomotive': 'TFR-19E-001',
        'loc_type': 'Electric Freight',
        'loc_class': 'Class 19E',
        'engine_supply': 'Electric - 3000V DC',
        'length': '19.2',
        'capacity_in_tons': '10000',
        'distributed_power': 'Yes',
        'tractive_effort': '750',
        'truck_circuit_spec': 'Bo-Bo-Bo',
    },
    {
        'locomotive': 'TFR-18E-045',
        'loc_type': 'Electric Freight',
        'loc_class': 'Class 18E',
        'engine_supply': 'Electric - 3000V DC',
        'length': '18.8',
        'capacity_in_tons': '7500',
        'distributed_power': 'Yes',
        'tractive_effort': '650',
        'truck_circuit_spec': 'Co-Co',
    },
    {
        'locomotive': 'TFR-15E-023',
        'loc_type': 'Electric Freight',
        'loc_class': 'Class 15E',
        'engine_supply': 'Electric - 3000V DC',
        'length': '17.5',
        'capacity_in_tons': '5000',
        'distributed_power': 'No',
        'tractive_effort': '450',
        'truck_circuit_spec': 'Bo-Bo',
    },
    {
        'locomotive': 'TFR-19E-002',
        'loc_type': 'Electric Freight',
        'loc_class': 'Class 19E',
        'engine_supply': 'Electric - 3000V DC',
        'length': '19.2',
        'capacity_in_tons': '10000',
        'distributed_power': 'Yes',
        'tractive_effort': '750',
        'truck_circuit_spec': 'Bo-Bo-Bo',
    },
    {
        'locomotive': 'TFR-34E-012',
        'loc_type': 'Electric Heavy Freight',
        'loc_class': 'Class 34E',
        'engine_supply': 'Electric - 25kV AC',
        'length': '20.1',
        'capacity_in_tons': '12000',
        'distributed_power': 'Yes',
        'tractive_effort': '850',
        'truck_circuit_spec': 'Bo-Bo-Bo',
    },
    {
        'locomotive': 'TFR-18E-067',
        'loc_type': 'Electric Freight',
        'loc_class': 'Class 18E',
        'engine_supply': 'Electric - 3000V DC',
        'length': '18.8',
        'capacity_in_tons': '7500',
        'distributed_power': 'Yes',
        'tractive_effort': '650',
        'truck_circuit_spec': 'Co-Co',
    },
    {
        'locomotive': 'TFR-15E-089',
        'loc_type': 'Electric Freight',
        'loc_class': 'Class 15E',
        'engine_supply': 'Electric - 3000V DC',
        'length': '17.5',
        'capacity_in_tons': '5000',
        'distributed_power': 'No',
        'tractive_effort': '450',
        'truck_circuit_spec': 'Bo-Bo',
    },
    {
        'locomotive': 'TFR-43D-022',
        'loc_type': 'Diesel Freight',
        'loc_class': 'Class 43',
        'engine_supply': 'Diesel-Electric',
        'length': '19.5',
        'capacity_in_tons': '6500',
        'distributed_power': 'No',
        'tractive_effort': '550',
        'truck_circuit_spec': 'Co-Co',
    },
]

created_count = 0
for loco_data in locomotives_data:
    # Check if locomotive already exists
    existing = LocomotiveSpec.objects.filter(locomotive=loco_data['locomotive']).first()
    if existing:
        print(f'⏭️  Skipping {loco_data["locomotive"]} - already exists')
        continue
    
    loco = LocomotiveSpec.objects.create(
        created_by=admin,
        locomotive=loco_data['locomotive'],
        loc_type=loco_data['loc_type'],
        loc_class=loco_data['loc_class'],
        engine_supply=loco_data['engine_supply'],
        length=loco_data['length'],
        capacity_in_tons=loco_data['capacity_in_tons'],
        distributed_power=loco_data['distributed_power'],
        tractive_effort=loco_data['tractive_effort'],
        truck_circuit_spec=loco_data['truck_circuit_spec'],
        status='AVAILABLE',
        is_active=True,
        maintenance_status='OPERATIONAL',
        survey_raw=f"Class: {loco_data['loc_class']}, Capacity: {loco_data['capacity_in_tons']}t, Tractive Effort: {loco_data['tractive_effort']}kN"
    )
    created_count += 1
    print(f'✅ Created: {loco.locomotive} (Class {loco.loc_class}, {loco.capacity_in_tons}t capacity, {loco.tractive_effort}kN)')

print(f'\n✓ Created {created_count} new locomotives!')
print(f'Total locomotives in database: {LocomotiveSpec.objects.count()}')
