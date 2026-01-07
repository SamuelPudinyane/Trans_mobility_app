import random
import uuid
from django.core.management.base import BaseCommand
from django.utils import timezone
from transnet_mobility.models import CustomUser
from django.contrib.auth.hashers import make_password


# Use roles as defined in the CustomUser model
ROLES = [
    ('ADMIN', 'Admin'),
    ('STAFF', 'Staff'),
    ('DRIVER', 'Driver'),
    ('ELECTRICAL_MAINTENANCE_TEAM', 'Electrical_Maintenance_Team'),
    ('MECHANICAL_MAINTENANCE_TEAM', 'Mechanical_Maintenance_Team'),
    ('EMERGENCY_RESPONSE_TEAM', 'Emergency_Response_Team'),
    ('SECURITY_TEAM', 'Security_Team'),
    ('MEDICAL_TEAM', 'Medical_Team'),
    ('TOWING_SERVICE', 'Towing_Service'),
    ('OTHER', 'Other'),
]

FIRST_NAMES = [
    'Alex', 'Sam', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Jamie', 'Riley', 'Drew', 'Cameron',
    'Robin', 'Avery', 'Skyler', 'Quinn', 'Peyton', 'Reese', 'Rowan', 'Sawyer', 'Emerson', 'Finley'
]
LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Martinez', 'Lopez',
    'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson'
]

AREAS = ['Johannesburg', 'Pretoria', 'Durban', 'Cape Town', 'Polokwane', 'Bloemfontein']

PROFILE_IMAGES = [
    'profiles/default1.png', 'profiles/default2.png', 'profiles/default3.png', 'profiles/default4.png',
    'profiles/default5.png', 'profiles/default6.png', 'profiles/default7.png', 'profiles/default8.png',
]

class Command(BaseCommand):
    help = 'Create fake users for each role.'

    def add_arguments(self, parser):
        parser.add_argument('--per_role', type=int, default=10, help='Number of users per role')

    def handle(self, *args, **options):
        per_role = options['per_role']
        for role, display in ROLES:
            for i in range(per_role):
                first_name = random.choice(FIRST_NAMES)
                last_name = random.choice(LAST_NAMES)
                email = f"{first_name.lower()}.{last_name.lower()}{i}@example.com"
                password = email  # Default: password is email
                user, created = CustomUser.objects.get_or_create(
                    email=email,
                    defaults={
                        'password': make_password(password),
                        'is_superuser': role == 'ADMIN',
                        'first_name': first_name,
                        'last_name': last_name,
                        'is_staff': role == 'ADMIN',
                        'is_active': True,
                        'date_joined': timezone.now(),
                        'employee_number': str(random.randint(10000000, 99999999)),
                        'id_number': str(random.randint(1000000000000, 9999999999999)),
                        'phone_number': f"07{random.randint(100000000, 999999999)}",
                        'role': role,
                        'account_type': role,
                        'profile_picture': random.choice(PROFILE_IMAGES),
                        'last_location': f"{random.uniform(-34, -25):.6f},{random.uniform(18, 32):.6f}",
                        'driver_status': random.choice(['available', 'on_leave', 'emergency']),
                        'current_location': random.choice(AREAS),
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Created {role} user: {email} (password: {password})"))
                else:
                    self.stdout.write(self.style.WARNING(f"User already exists: {email}"))
        self.stdout.write(self.style.SUCCESS('Fake users creation complete.'))
