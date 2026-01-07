from .models import Schedule, CustomUser

def create_or_update_schedule(driver_uuid, date, **kwargs):
    """
    Always assign the CustomUser instance to the driver field when creating/updating Schedule.
    Usage: create_or_update_schedule(driver_uuid, date, status='available', ...)
    """
    try:
        user = CustomUser.objects.get(User_id=driver_uuid)
    except CustomUser.DoesNotExist:
        raise ValueError(f"No CustomUser with User_id={driver_uuid}")
    # If updating, get or create
    schedule, created = Schedule.objects.get_or_create(date=date, defaults={'driver': user, **kwargs})
    if not created:
        schedule.driver = user
        for k, v in kwargs.items():
            setattr(schedule, k, v)
        schedule.save()
    return schedule
