import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobility.settings')
django.setup()

from transnet_mobility.models import WagonSpec

print('=== ALL WAGONS (including inactive) ===\n')
all_wagons = WagonSpec.objects.all()
print(f'Total wagons in database: {all_wagons.count()}\n')

for wagon in all_wagons:
    print(f'Wagon: {wagon.wagon_number}')
    print(f'  ID: {wagon.id}')
    print(f'  Type: {wagon.wagon_type}')
    print(f'  Active: {wagon.is_active}')
    print(f'  Status: {wagon.status}')
    print(f'  Assigned: {wagon.is_assigned}')
    print(f'  Tare Weight: {wagon.tare_weight}')
    print(f'  Payload: {wagon.payload_capacity}')
    print()
