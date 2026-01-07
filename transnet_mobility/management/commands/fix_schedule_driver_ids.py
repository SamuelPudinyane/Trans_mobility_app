from django.core.management.base import BaseCommand
from transnet_mobility.models import Schedule, CustomUser

class Command(BaseCommand):
    help = 'Fix Schedule entries so driver_id matches a valid User_id from CustomUser.'

    def handle(self, *args, **options):
        fixed = 0
        invalid = 0
        for schedule in Schedule.objects.all():
            # If driver_id is not a valid User_id, try to fix it
            if not CustomUser.objects.filter(User_id=schedule.driver_id).exists():
                # Try to find a user with a matching email or name (customize as needed)
                user = None
                if hasattr(schedule, 'driver_email') and schedule.driver_email:
                    user = CustomUser.objects.filter(email=schedule.driver_email).first()
                if not user and hasattr(schedule, 'driver_name') and schedule.driver_name:
                    first, *last = schedule.driver_name.split()
                    user = CustomUser.objects.filter(first_name=first).first()
                if user:
                    old_id = schedule.driver_id
                    schedule.driver_id = user.User_id
                    schedule.save()
                    fixed += 1
                    self.stdout.write(f"Fixed Schedule id={schedule.id}: {old_id} -> {user.User_id}")
                else:
                    invalid += 1
                    self.stdout.write(f"Could not fix Schedule id={schedule.id}: {schedule.driver_id}")
        self.stdout.write(self.style.SUCCESS(f"Fixed {fixed} schedule entries. {invalid} could not be fixed."))
