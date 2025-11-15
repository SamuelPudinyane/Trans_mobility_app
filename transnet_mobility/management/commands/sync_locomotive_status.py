from django.core.management.base import BaseCommand
from transnet_mobility.models import LocomotiveSpec, LocomotiveAssignment


class Command(BaseCommand):
    help = 'Sync locomotive status based on current driver assignments'

    def handle(self, *args, **options):
        self.stdout.write('Starting locomotive status sync...\n')
        
        # Get all locomotives
        all_locomotives = LocomotiveSpec.objects.all()
        updated_count = 0
        
        for loco in all_locomotives:
            # Skip locomotives that are in maintenance or ready for activation
            if loco.status in ['IN_MAINTENANCE', 'READY_FOR_ACTIVATION']:
                self.stdout.write(f'  Skipping {loco.locomotive or f"Locomotive #{loco.id}"} - status is {loco.status}')
                continue
            
            # Check if locomotive has any assigned drivers
            assignment_count = LocomotiveAssignment.objects.filter(locomotive=loco).count()
            
            if assignment_count > 0:
                # Has drivers - should be ON_DUTY
                if loco.status != 'ON_DUTY':
                    old_status = loco.status
                    loco.status = 'ON_DUTY'
                    loco.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Updated {loco.locomotive or f"Locomotive #{loco.id}"}: {old_status} → ON_DUTY ({assignment_count} driver(s))'
                        )
                    )
                    updated_count += 1
                else:
                    self.stdout.write(f'  ✓ {loco.locomotive or f"Locomotive #{loco.id}"} already ON_DUTY')
            else:
                # No drivers - should be AVAILABLE
                if loco.status != 'AVAILABLE':
                    old_status = loco.status
                    loco.status = 'AVAILABLE'
                    loco.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Updated {loco.locomotive or f"Locomotive #{loco.id}"}: {old_status} → AVAILABLE (no drivers)'
                        )
                    )
                    updated_count += 1
                else:
                    self.stdout.write(f'  ✓ {loco.locomotive or f"Locomotive #{loco.id}"} already AVAILABLE')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Sync complete! Updated {updated_count} locomotive(s).'
            )
        )
