import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobility.settings')
django.setup()

from transnet_mobility.models import LocomotiveSpec

print('=== CHECKING FOR BLANK LOCOMOTIVE NAMES ===')

blank_locomotives = LocomotiveSpec.objects.filter(locomotive__isnull=True) | LocomotiveSpec.objects.filter(locomotive='')

if blank_locomotives.exists():
    print(f'Found {blank_locomotives.count()} locomotives with blank names.')
    for loco in blank_locomotives:
        loco.locomotive = f'LOCO-{loco.id}'
        loco.save()
        print(f'Updated LocomotiveSpec id={loco.id} to name LOCO-{loco.id}')
    print('✓ All blank locomotive names have been fixed.')
else:
    print('No blank locomotive names found. All records are valid.')
