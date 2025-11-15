import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobility.settings')
django.setup()

from transnet_mobility.models import WagonSpec, CustomUser

# Get admin user for created_by field
admin = CustomUser.objects.filter(role='ADMIN').first()
if not admin:
    print("❌ No admin user found. Please create an admin user first.")
    exit()

print('=== CREATING FAKE WAGON DATA ===\n')

# Realistic wagon specifications with different types
wagon_types = [
    {
        'type': 'BOX',
        'prefix': 'BX',
        'tare_range': (18, 25),
        'payload_range': (50, 70),
    },
    {
        'type': 'FLAT',
        'prefix': 'FL',
        'tare_range': (15, 22),
        'payload_range': (60, 80),
    },
    {
        'type': 'HOPPER',
        'prefix': 'HP',
        'tare_range': (20, 28),
        'payload_range': (70, 90),
    },
    {
        'type': 'TANK',
        'prefix': 'TK',
        'tare_range': (22, 30),
        'payload_range': (55, 75),
    },
    {
        'type': 'REFRIGERATED',
        'prefix': 'RF',
        'tare_range': (25, 32),
        'payload_range': (45, 65),
    },
]

created_count = 0

# Create 25 wagons (5 of each type)
for wagon_type in wagon_types:
    for i in range(1, 6):
        wagon_number = f"{wagon_type['prefix']}-{random.randint(1000, 9999)}"
        
        # Check if wagon already exists
        existing = WagonSpec.objects.filter(wagon_number=wagon_number).first()
        if existing:
            print(f'⏭️  Skipping {wagon_number} - already exists')
            continue
        
        # Generate random but realistic specifications
        tare_weight = round(random.uniform(*wagon_type['tare_range']), 2)
        payload_capacity = round(random.uniform(*wagon_type['payload_range']), 2)
        gross_laden_weight = round(tare_weight + payload_capacity, 2)
        
        # Random but realistic dimensions
        length = round(random.uniform(12.0, 18.0), 2)
        width = round(random.uniform(2.8, 3.2), 2)
        height = round(random.uniform(3.0, 4.5), 2)
        
        wagon = WagonSpec.objects.create(
            created_by=admin,
            wagon_number=wagon_number,
            wagon_type=wagon_type['type'],
            length_over_buffers=length,
            width=width,
            height=height,
            tare_weight=tare_weight,
            payload_capacity=payload_capacity,
            gross_laden_weight=gross_laden_weight,
            axle_load=round(gross_laden_weight / 4, 2),  # Assuming 4 axles
            maximum_speed=random.choice([80, 100, 120]),
            coupling_type=random.choice(['AAR', 'SA3']),
            braking_system=random.choice(['UIC', 'AAR']),
            suspension_system=random.choice(['COIL', 'LEAF']),
            bogie_type=random.choice(['TWO_AXLE', 'FOUR_AXLE']),
            track_gauge='1067',  # Cape gauge for South Africa
            buffer_drawgear_capacity=random.choice([850, 900, 950, 1000]),
            body_material='High-strength steel (Corten)',
            frame_construction='Welded steel underframe',
            status='AVAILABLE',
            is_active=True,
            is_assigned=False,
        )
        created_count += 1
        print(f'✅ Created: {wagon.wagon_number} ({wagon.wagon_type}) - Tare: {tare_weight}t, Payload: {payload_capacity}t, Total: {gross_laden_weight}t')

print(f'\n✓ Created {created_count} new wagons!')
print(f'Total wagons in database: {WagonSpec.objects.count()}')

# Show summary by type
print('\n=== WAGON SUMMARY BY TYPE ===')
for wagon_type in ['BOX', 'FLAT', 'HOPPER', 'TANK', 'REFRIGERATED']:
    count = WagonSpec.objects.filter(wagon_type=wagon_type).count()
    print(f'{wagon_type}: {count} wagon(s)')
