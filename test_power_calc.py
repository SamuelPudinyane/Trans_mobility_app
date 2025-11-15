import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mobility.settings')
django.setup()

from transnet_mobility.models import LocomotiveSpec, WagonSpec, LocomotiveWagonAssignment
import re

print('=== TESTING POWER CALCULATIONS ===\n')

for loco in LocomotiveSpec.objects.filter(maintenance_status='OPERATIONAL'):
    print(f'🚂 Locomotive: {loco.locomotive}')
    print(f'   Capacity: {loco.capacity_in_tons} tons')
    print(f'   Tractive Effort: {loco.tractive_effort} kN')
    
    # Get assigned wagons
    wagon_assignments = LocomotiveWagonAssignment.objects.filter(locomotive=loco).select_related('wagon')
    total_weight = 0
    wagon_count = 0
    
    for wa in wagon_assignments:
        wagon = wa.wagon
        tare = float(wagon.tare_weight or 0)
        payload = float(wagon.payload_capacity or 0)
        wagon_weight = tare + payload
        total_weight += wagon_weight
        wagon_count += 1
        print(f'   + Wagon {wagon.wagon_number}: {wagon_weight}t (tare: {tare}t, payload: {payload}t)')
    
    if wagon_count > 0:
        print(f'\n   📊 TOTAL LOAD: {total_weight}t ({wagon_count} wagon{"s" if wagon_count > 1 else ""})')
        
        # Extract numeric values
        try:
            loco_capacity = float(loco.capacity_in_tons)
            capacity_percent = (total_weight / loco_capacity * 100)
            print(f'   📈 Capacity Usage: {capacity_percent:.1f}% ({total_weight}t / {loco_capacity}t)')
        except:
            print(f'   ⚠️  Cannot calculate capacity - invalid value')
        
        try:
            tractive_effort_str = loco.tractive_effort or "0"
            numbers = re.findall(r'[-+]?\d*\.?\d+', tractive_effort_str)
            tractive_effort = float(numbers[0]) if numbers else None
            
            if tractive_effort:
                # Power (HP) ≈ Tractive Effort (kN) × Speed (km/h) / 2.65
                loco_power_hp = (tractive_effort * 60 / 2.65)
                power_required_flat = total_weight * 1
                power_required_grade = total_weight * 3.5
                power_to_weight = loco_power_hp / total_weight
                
                print(f'\n   ⚡ POWER ANALYSIS:')
                print(f'      Locomotive Power: {loco_power_hp:,.0f} HP')
                print(f'      Required (Flat): {power_required_flat:,.0f} HP')
                print(f'      Required (Grade): {power_required_grade:,.0f} HP')
                print(f'      Power-to-Weight: {power_to_weight:.2f} HP/ton')
                
                if power_to_weight >= 3:
                    status = '✅ EXCELLENT - Can handle steep grades'
                elif power_to_weight >= 2:
                    status = '✅ GOOD - Can handle moderate grades'
                elif power_to_weight >= 1:
                    status = '⚠️  MARGINAL - Adequate for flat terrain only'
                else:
                    status = '❌ UNDERPOWERED - May struggle'
                
                print(f'      Status: {status}')
        except Exception as e:
            print(f'   ⚠️  Cannot calculate power - error: {e}')
    else:
        print(f'   ℹ️  No wagons assigned')
    
    print('\n' + '='*60 + '\n')

print('✓ Test complete! The page should now show these calculations.')
