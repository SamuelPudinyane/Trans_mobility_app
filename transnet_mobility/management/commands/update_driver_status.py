from django.core.management.base import BaseCommand
from django.utils import timezone
from transnet_mobility.models import CustomUser

class Command(BaseCommand):
    help = 'Auto-update driver status to available if leave/emergency has ended.'

    def handle(self, *args, **options):
        today = timezone.now().date()
        # Find drivers whose leave/emergency has ended
        drivers = CustomUser.objects.filter(
            driver_status__in=['on_leave', 'emergency'],
            on_leave_until__isnull=False,
            on_leave_until__lte=today
        )
        updated = 0
        for driver in drivers:
            driver.driver_status = 'available'
            driver.on_leave_until = None
            driver.save(update_fields=['driver_status', 'on_leave_until'])
            updated += 1
        self.stdout.write(self.style.SUCCESS(f'Updated {updated} driver(s) to available.'))