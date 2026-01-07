# models.py
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser,BaseUserManager
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, Enum, DateTime, LargeBinary, func, Text
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from django.conf import settings  # important for custom user reference
import os
import uuid
import bcrypt


DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mobility_transnet")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "malvapudding78*")


connection_string = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(connection_string, echo=True)
Session = sessionmaker(bind=engine)
db_session = Session()

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

# --- Custom User Manager ---
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "ADMIN")   # ✅ force role as ADMIN for superusers
        extra_fields.setdefault("account_type", "ADMIN")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)
# --- Custom User ---
class CustomUser(AbstractUser):
    # Date when user should return from leave (auto-reset to available)
    on_leave_until = models.DateField(blank=True, null=True, help_text="Date when user should return from leave (auto-reset to available)")
    User_id = models.CharField(max_length=255, primary_key=True, default=generate_uuid)
    username = None  # ✅ disable username
    email = models.EmailField(unique=True, blank=False, null=False)  # ✅ email required & unique

    phone_number = models.CharField(max_length=15, blank=True, null=True)
    staff_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    profession = models.CharField(max_length=100, blank=True, null=True)
    id_number = models.CharField(max_length=50, blank=True, null=True)
    employee_number = models.CharField(max_length=50, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)

    account_type = models.CharField(
        max_length=55,
        choices=[
            ('ADMIN', 'Admin'),
            ('STAFF', 'Staff'),
            ('DRIVER', 'Driver'),
            ('ELECTRICAL_MAINTENANCE_TEAM','Electrical_Maintenance_Team'),
            ('MECHANICAL_MAINTENANCE_TEAM','Mechanical_Maintenance_Team'),
            ('EMERGENCY_RESPONSE_TEAM','Emergency_Response_Team'),
            ('SECURITY_TEAM','Security_Team'),
            ('MEDICAL_TEAM','Medical_Team'),
            ('TOWING_SERVICE','Towing_Service'),
            ('OTHER', 'Other')
        ],
        default='OTHER'
    )

    # Scheduling/availability fields for drivers
    driver_status = models.CharField(
        max_length=20,
        choices=[
            ('available', 'Available'),
            ('on_leave', 'On Leave'),
            ('emergency', 'Emergency'),
        ],
        default='available',
        blank=True,
        null=True
    )
    last_location = models.CharField(max_length=100, blank=True, null=True)
    current_location = models.CharField(max_length=100, blank=True, null=True)

    role = models.CharField(
        max_length=50,
        choices=[
            ('ADMIN', 'Admin'),
            ('STAFF', 'Staff'),
            ('DRIVER', 'Driver'),
            ('ELECTRICAL_MAINTENANCE_TEAM','Electrical_Maintenance_Team'),
            ('MECHANICAL_MAINTENANCE_TEAM','Mechanical_Maintenance_Team'),
            ('EMERGENCY_RESPONSE_TEAM','Emergency_Response_Team'),
            ('SECURITY_TEAM','Security_Team'),
            ('MEDICAL_TEAM','Medical_Team'),
            ('TOWING_SERVICE','Towing_Service'),
            ('OTHER', 'Other')
        ],
        default='OTHER'
    )

    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)

    # ✅ Tell Django to use email as username
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []   # we don’t need extra required fields since email is unique

    objects = CustomUserManager()

    def __str__(self):
        return self.email



class UserLocation(models.Model):
        # Optionally, add a helper to update CustomUser.current_location on save
    def save(self, *args, **kwargs):
            super().save(*args, **kwargs)
            # Update user's current_location field
            self.user.current_location = f"{self.latitude},{self.longitude}"
            self.user.save(update_fields=["current_location"])
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field='User_id',  # Use the UUID primary key
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.email} @ {self.latitude}, {self.longitude}"


class LocomotiveSpec(models.Model):
    area = models.CharField(max_length=100, blank=True, null=True)
    """Store locomotive specification fields and the raw survey data.
    survey_raw will contain the questions and answers concatenated using commas
    as requested (question, type, answers joined with commas, ...)
    """
    id = models.AutoField(primary_key=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        to_field='User_id'
    )
    locomotive = models.CharField(max_length=200, blank=True, null=True)
    loc_type = models.CharField(max_length=200, blank=True, null=True)
    loc_class = models.CharField(max_length=200, blank=True, null=True)
    engine_supply = models.CharField(max_length=200, blank=True, null=True)
    length = models.CharField(max_length=100, blank=True, null=True)
    capacity_in_tons = models.CharField(max_length=100, blank=True, null=True)
    distributed_power = models.CharField(max_length=200, blank=True, null=True)
    tractive_effort = models.CharField(max_length=200, blank=True, null=True)
    truck_circuit_spec = models.CharField(max_length=200, blank=True, null=True)
    
    # Enhanced status tracking
    status = models.CharField(
        max_length=50,
        choices=[
            ('AVAILABLE', 'Available'),
            ('ON_DUTY', 'On Duty'),
            ('IN_MAINTENANCE', 'In Maintenance'),
            ('READY_FOR_ACTIVATION', 'Ready for Activation'),
            ('WRITTEN_OFF', 'Written Off'),
        ],
        default='AVAILABLE'
    )
    
    # Activation control - admin must activate after maintenance
    is_active = models.BooleanField(default=True)
    
    # Maintenance status field (kept for backward compatibility)
    maintenance_status = models.CharField(
        max_length=50,
        choices=[
            ('OPERATIONAL', 'Operational'),
            ('UNDER_MAINTENANCE', 'Under Maintenance'),
            ('WRITTEN_OFF', 'Written Off'),
        ],
        default='OPERATIONAL'
    )

    # Store questions and answers as a single text column (user asked for text and comma-joining)
    survey_raw = models.TextField(blank=True, null=True)
    
    # Store additional specifications as list of dictionaries [{'label': 'Field Name', 'value': 'Field Value'}, ...]
    additional_specs = models.JSONField(blank=True, null=True, default=list)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.locomotive:
            return f"{self.locomotive} (ID {self.id})"
        return f"LocomotiveSpec {self.id} by {getattr(self.created_by, 'email', 'unknown')}"


class CargoSpec(models.Model):
    id = models.AutoField(primary_key=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        to_field='User_id'
    )
    wagon = models.ForeignKey(
        'WagonSpec',
        on_delete=models.CASCADE,
        related_name='cargo_entries',
        null=True,
        blank=True
    )
    cargo_type = models.CharField(max_length=200, blank=True, null=True)
    cargo_volume = models.CharField(max_length=100, blank=True, null=True)
    cargo_weight_tons = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text="Cargo weight in tonnes")
    special_handling = models.CharField(max_length=400, blank=True, null=True)
    
    # Enhanced status tracking
    status = models.CharField(
        max_length=50,
        choices=[
            ('AVAILABLE', 'Available'),
            ('IN_USE', 'In Use'),
            ('IN_MAINTENANCE', 'In Maintenance'),
            ('READY_FOR_ACTIVATION', 'Ready for Activation'),
        ],
        default='AVAILABLE'
    )
    
    # Activation control - admin must activate after maintenance
    is_active = models.BooleanField(default=True)
    
    # Maintenance status field (kept for backward compatibility)
    maintenance_status = models.CharField(
        max_length=50,
        choices=[
            ('OPERATIONAL', 'Operational'),
            ('UNDER_MAINTENANCE', 'Under Maintenance'),
        ],
        default='OPERATIONAL'
    )
    
    # survey_raw stores builder questions/answers as text (comma-joined per earlier approach)
    survey_raw = models.TextField(blank=True, null=True)
    
    # Store additional specifications as list of dictionaries [{'label': 'Field Name', 'value': 'Field Value'}, ...]
    additional_specs = models.JSONField(blank=True, null=True, default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CargoSpec {self.id} ({self.cargo_type}) by {getattr(self.created_by, 'email', 'unknown')} - Wagon {getattr(self.wagon, 'wagon_number', 'None')}"


class WheelsetSpec(models.Model):
    id = models.AutoField(primary_key=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        to_field='User_id'
    )
    locomotive = models.ForeignKey(
        LocomotiveSpec,
        on_delete=models.CASCADE,
        related_name='wheelset_entries',
        null=True,
        blank=True
    )
    wheel_profile = models.CharField(max_length=200, blank=True, null=True)
    diameter_differentials = models.CharField(max_length=200, blank=True, null=True)
    symmetry = models.CharField(max_length=200, blank=True, null=True)
    radial_run_out = models.CharField(max_length=200, blank=True, null=True)
    axial_run_out = models.CharField(max_length=200, blank=True, null=True)
    witness_marks = models.CharField(max_length=200, blank=True, null=True)
    surface_roughness = models.CharField(max_length=200, blank=True, null=True)
    stenciling = models.CharField(max_length=200, blank=True, null=True)
    main_machine_diameter = models.CharField(max_length=200, blank=True, null=True)
    survey_raw = models.TextField(blank=True, null=True)
    
    # Store additional specifications as list of dictionaries [{'label': 'Field Name', 'value': 'Field Value'}, ...]
    additional_specs = models.JSONField(blank=True, null=True, default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"WheelsetSpec {self.id} ({self.wheel_profile}) by {getattr(self.created_by, 'email', 'unknown')}"



# Wagon-related constants (move outside class for correct indentation)
WAGON_TYPES = [
    ('BOX', 'Box Wagon'),
    ('FLAT', 'Flat Wagon'),
    ('HOPPER', 'Hopper Wagon'),
    ('TANK', 'Tank Wagon'),
    ('REFRIGERATED', 'Refrigerated Wagon'),
    ('AUTO_CARRIER', 'Auto Carrier'),
    ('TIPPLER', 'Tippler Wagon'),
]

BRAKING_SYSTEMS = [
    ('UIC', 'UIC Standard Air Brake'),
    ('AAR', 'AAR Standard Air Brake'),
]

COUPLING_TYPES = [
    ('AAR', 'AAR Knuckle Coupler'),
    ('SA3', 'SA3 Automatic Coupler'),
]

TRACK_GAUGES = [
    ('1435', '1,435 mm (Standard Gauge)'),
    ('1067', '1,067 mm (Cape Gauge)'),
]

SUSPENSION_TYPES = [
    ('COIL', 'Coil Spring Bogies'),
    ('LEAF', 'Leaf Spring Bogies'),
]

BOGIE_TYPES = [
    ('TWO_AXLE', 'Two-Axle Bogies'),
    ('FOUR_AXLE', 'Four-Axle Bogies'),
]

class WagonSpec(models.Model):
    def get_assigned_locomotives(self):
        """Return all LocomotiveSpec objects assigned to this wagon."""
        return LocomotiveSpec.objects.filter(wagon_assignments__wagon=self)

    def get_total_locomotive_power(self):
        """Sum the power of all assigned locomotives for this wagon."""
        locomotives = self.get_assigned_locomotives()
        total_power = 0
        for loco in locomotives:
            # Assuming 'tractive_effort' or 'power' field exists and is numeric
            try:
                if hasattr(loco, 'tractive_effort') and loco.tractive_effort:
                    total_power += float(loco.tractive_effort)
                elif hasattr(loco, 'power') and loco.power:
                    total_power += float(loco.power)
            except Exception:
                continue
        return total_power

    id = models.AutoField(primary_key=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        to_field='User_id'
    )

    # General Identification
    wagon_number = models.CharField(max_length=100, unique=True, help_text="Unique wagon identifier")
    wagon_type = models.CharField(max_length=50, choices=WAGON_TYPES, default='BOX')

    # General Dimensions
    length_over_buffers = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Length in meters (10-25m)")
    width = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True, help_text="Width in meters (2.8-3.2m)")
    height = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True, help_text="Height in meters (3.8-4.2m)")
    track_gauge = models.CharField(max_length=10, choices=TRACK_GAUGES, default='1067', help_text="Track gauge in mm")
    
    # Weight and Load Capacity
    tare_weight = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text="Empty weight in tonnes (15-30t)")
    payload_capacity = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text="Maximum cargo weight in tonnes (40-80t)")
    gross_laden_weight = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text="Tare + payload in tonnes (60-100t)")
    axle_load = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Load per axle in tonnes (16-25t)")
    
    # Performance and Operation
    maximum_speed = models.IntegerField(blank=True, null=True, help_text="Maximum speed in km/h (80-120 km/h)")
    braking_system = models.CharField(max_length=50, choices=BRAKING_SYSTEMS, default='UIC')
    coupling_type = models.CharField(max_length=50, choices=COUPLING_TYPES, default='SA3')
    buffer_drawgear_capacity = models.IntegerField(blank=True, null=True, help_text="Load capacity in kN (850-1000 kN)")
    
    # Material and Build
    body_material = models.CharField(max_length=200, blank=True, null=True, help_text="e.g., High-strength steel (Corten)")
    frame_construction = models.CharField(max_length=200, blank=True, null=True, help_text="e.g., Welded steel underframe")
    suspension_system = models.CharField(max_length=50, choices=SUSPENSION_TYPES, default='COIL')
    bogie_type = models.CharField(max_length=50, choices=BOGIE_TYPES, default='TWO_AXLE')
    floor_type = models.CharField(max_length=200, blank=True, null=True, help_text="e.g., Steel plate, wooden deck")
    
    # Type-Specific Features
    special_features = models.TextField(blank=True, null=True, help_text="Type-specific features (e.g., discharge gates, cooling unit)")
    
    # Enhanced status tracking
    status = models.CharField(
        max_length=50,
        choices=[
            ('AVAILABLE', 'Available'),
            ('IN_USE', 'In Use'),
            ('IN_MAINTENANCE', 'In Maintenance'),
            ('READY_FOR_ACTIVATION', 'Ready for Activation'),
            ('WRITTEN_OFF', 'Written Off'),
        ],
        default='AVAILABLE'
    )
    
    is_active = models.BooleanField(default=True)
    
    # Track if wagon is currently assigned to a locomotive
    is_assigned = models.BooleanField(default=False, help_text="True if wagon is currently assigned to a locomotive")
    
    # Track current cargo assignment (one cargo per wagon)
    current_cargo = models.OneToOneField(
        'CargoSpec',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_wagon',
        help_text="Current cargo assigned to this wagon"
    )
    
    # Compatible cargo types for validation
    compatible_cargo_types = models.JSONField(
        blank=True,
        null=True,
        default=list,
        help_text="List of cargo types compatible with this wagon type"
    )
    
    # Survey for additional specs
    survey_raw = models.TextField(blank=True, null=True)
    
    # Store additional specifications as list of dictionaries [{'label': 'Field Name', 'value': 'Field Value'}, ...]
    additional_specs = models.JSONField(blank=True, null=True, default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_total_weight(self):
        """Calculate total weight including tare and cargo if assigned"""
        tare = float(self.tare_weight or 0)
        
        # Get cargo weight if cargo is assigned
        if self.current_cargo:
            cargo_weight = float(self.current_cargo.cargo_weight_tons or 0)
            return tare + cargo_weight
        
        # If no cargo, return tare + max payload capacity
        payload = float(self.payload_capacity or 0)
        return tare + payload
    
    def get_cargo_weight(self):
        """Get weight of cargo currently assigned to this wagon"""
        if self.current_cargo:
            return float(self.current_cargo.cargo_weight_tons or 0)
        return 0

    def __str__(self):
        return f"{self.wagon_number} - {self.get_wagon_type_display()}"
    
    class Meta:
        ordering = ['-created_at']


class RoutePreferenceSpec(models.Model):
    id = models.AutoField(primary_key=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        to_field='User_id'
    )
    locomotive = models.ForeignKey(
        LocomotiveSpec,
        on_delete=models.CASCADE,
        related_name='route_preference_entries',
        null=True,
        blank=True
    )
    preferred_route_corridor = models.CharField(max_length=300, blank=True, null=True)
    transshipment_required = models.CharField(max_length=20, blank=True, null=True)  # Yes/No
    delivery_node = models.CharField(max_length=300, blank=True, null=True)
    receiving_facility = models.CharField(max_length=300, blank=True, null=True)
    survey_raw = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RoutePreferenceSpec {self.id} ({self.preferred_route_corridor}) by {getattr(self.created_by, 'email', 'unknown')}"


class FuelSpec(models.Model):
    id = models.AutoField(primary_key=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        to_field='User_id'
    )
    locomotive = models.ForeignKey(
        LocomotiveSpec,
        on_delete=models.CASCADE,
        related_name='fuel_entries',
        null=True,
        blank=True
    )
    daily_fuel_consumption = models.CharField(max_length=100, blank=True, null=True)
    fuel_cost_per_litre = models.CharField(max_length=100, blank=True, null=True)
    average_load_per_trip = models.CharField(max_length=100, blank=True, null=True)
    fuel_type = models.CharField(max_length=100, blank=True, null=True)
    survey_raw = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FuelSpec {self.id} (type={self.fuel_type}) by {getattr(self.created_by, 'email', 'unknown')}"

class LocomotiveAssignment(models.Model):
    # Optionally, add assistant driver
    assistant = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            to_field='User_id',
            related_name='assistant_assignments'
        )
    """Represents assignment of a driver to a locomotive. One row per (locomotive, driver).
    We enforce uniqueness at the DB level to avoid duplicate assignments. The application
    logic will ensure a locomotive does not end up with more than two assigned drivers.
    """
    id = models.AutoField(primary_key=True)
    locomotive = models.ForeignKey(
        LocomotiveSpec,
        on_delete=models.CASCADE,
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field='User_id'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    # Track assignment status for scheduling
    status = models.CharField(
        max_length=20,
        choices=[
            ('assigned', 'Assigned'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='assigned',
    )

    class Meta:
        unique_together = ('locomotive', 'driver')

class Schedule(models.Model):
    """Driver scheduling for day/week/month with color-coded status and area/location validation."""
    id = models.AutoField(primary_key=True)
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field='User_id',
        related_name='driver_schedules'
    )
    assistant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        to_field='User_id',
        related_name='assistant_schedules'
    )
    locomotives = models.ManyToManyField(
        LocomotiveSpec,
        related_name='schedule_locomotives',
        blank=True
    )
    date = models.DateField()
    shift_type = models.CharField(
        max_length=10,
        choices=[('day', 'Day'), ('week', 'Week'), ('month', 'Month')],
        default='day',
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('available', 'Available'),
            ('on_leave', 'On Leave'),
            ('emergency', 'Emergency'),
            ('assigned', 'Assigned'),
            ('completed', 'Completed'),
        ],
        default='available',
    )
    area = models.CharField(max_length=100, blank=True, null=True)
    last_location = models.CharField(max_length=100, blank=True, null=True)
    current_location = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "driver"]
        unique_together = ("driver", "date", "shift_type")

    def __str__(self):
        locomotives_str = ", ".join([str(loco) for loco in self.locomotives.all()])
        parts = [
            f"Driver: {getattr(self.driver, 'email', '?')}",
            f"Assistant: {getattr(self.assistant, 'email', 'None')}",
            f"Locomotives: {locomotives_str if locomotives_str else 'None'}",
            f"Date: {self.date}",
            f"Shift: {self.shift_type}",
            f"Status: {self.status}"
        ]
        return " | ".join(parts)


class LocomotiveWagonAssignment(models.Model):
    """Represents assignment of wagons to a locomotive.
    A locomotive can have multiple wagons assigned to it.
    """
    id = models.AutoField(primary_key=True)
    locomotive = models.ForeignKey(
        LocomotiveSpec,
        on_delete=models.CASCADE,
        related_name='wagon_assignments'
    )
    wagon = models.ForeignKey(
        WagonSpec,
        on_delete=models.CASCADE,
        related_name='locomotive_assignments'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        to_field='User_id'
    )

    class Meta:
        unique_together = ('locomotive', 'wagon')

    def __str__(self):
        return f"Wagon {getattr(self.wagon,'wagon_number','?')} assigned to {getattr(self.locomotive,'locomotive','?')}"


class DriverRequest(models.Model):
    """Store driver assistance requests with captured image and location"""
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field='User_id'
    )
    locomotive = models.ForeignKey(
        'LocomotiveSpec',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='driver_requests'
    )
    issue_description = models.TextField(blank=True, null=True)
    captured_image = models.ImageField(upload_to='driver_requests/', blank=True, null=True)  # Store image file
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    incident_category = models.CharField(
        max_length=20,
        choices=[
            ('CRIME', 'Crime Related'),
            ('SAFETY', 'Safety Issue'),
            ('MECHANICAL', 'Mechanical'),
            ('OTHER', 'Other'),
        ],
        default='OTHER'
    )
    priority = models.CharField(
        max_length=20,
        choices=[
            ('NORMAL', 'Normal'),
            ('CRITICAL', 'Critical - Duplicate Request'),
        ],
        default='NORMAL'
    )
    status = models.CharField(
        max_length=50,
        choices=[
            ('PENDING', 'Pending'),
            ('IN_PROGRESS', 'In Progress'),
            ('RESOLVED', 'Resolved'),
            ('CANCELLED', 'Cancelled'),
        ],
        default='PENDING'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Request {self.id} by {getattr(self.user, 'email', 'unknown')} - {self.status}"


class DispatchLog(models.Model):
    """Track dispatch actions for emergency requests"""
    id = models.AutoField(primary_key=True)
    driver_request = models.ForeignKey(
        DriverRequest,
        on_delete=models.CASCADE,
        related_name='dispatch_logs'
    )
    dispatched_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        to_field='User_id',
        related_name='dispatches_made'
    )
    response_team = models.CharField(max_length=100)
    assigned_personnel = models.TextField(blank=True, null=True)
    estimated_arrival = models.DateTimeField(blank=True, null=True)
    response_notes = models.TextField(blank=True, null=True)
    dispatched_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Dispatch {self.id} for Request #{self.driver_request.id} - {self.response_team}"


class DispatchNotification(models.Model):
    """Store notifications for response team members"""
    id = models.AutoField(primary_key=True)
    dispatch_log = models.ForeignKey(
        DispatchLog,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field='User_id',
        related_name='dispatch_notifications'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)
    
    # Distance from recipient to emergency location (in km)
    distance_km = models.FloatField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {getattr(self.recipient, 'email', 'unknown')} - Request #{self.dispatch_log.driver_request.id}"


class DriverAssignmentNotification(models.Model):
    """Store notifications for driver assignments"""
    id = models.AutoField(primary_key=True)
    assignment = models.ForeignKey(
        LocomotiveAssignment,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field='User_id',
        related_name='assignment_notifications'
    )
    notification_type = models.CharField(
        max_length=20,
        choices=[
            ('ASSIGNED', 'Assigned'),
            ('REASSIGNED', 'Reassigned'),
            ('UNASSIGNED', 'Unassigned'),
        ],
        default='ASSIGNED'
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Assignment notification for {getattr(self.driver, 'email', 'unknown')} - {self.notification_type}"


class MaintenanceSchedule(models.Model):
    """Track maintenance schedules for locomotives, cargo, and wagons"""
    id = models.AutoField(primary_key=True)
    
    # What is being maintained
    item_type = models.CharField(
        max_length=20,
        choices=[
            ('LOCOMOTIVE', 'Locomotive'),
            ('CARGO', 'Cargo'),
            ('WAGON', 'Wagon'),
        ]
    )
    locomotive = models.ForeignKey(
        LocomotiveSpec,
        on_delete=models.CASCADE,
        related_name='maintenance_schedules',
        null=True,
        blank=True
    )
    cargo = models.ForeignKey(
        CargoSpec,
        on_delete=models.CASCADE,
        related_name='maintenance_schedules',
        null=True,
        blank=True
    )
    wagon = models.ForeignKey(
        WagonSpec,
        on_delete=models.CASCADE,
        related_name='maintenance_schedules',
        null=True,
        blank=True
    )
    
    # Maintenance details
    reason = models.TextField(help_text="Reason for maintenance")
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        to_field='User_id',
        related_name='scheduled_maintenance'
    )
    
    # Time tracking
    scheduled_date = models.DateTimeField(help_text="When maintenance was scheduled")
    expected_completion_date = models.DateTimeField(help_text="Expected completion date")
    actual_completion_date = models.DateTimeField(null=True, blank=True)
    
    # Status tracking
    status = models.CharField(
        max_length=30,
        choices=[
            ('SCHEDULED', 'Scheduled'),
            ('IN_PROGRESS', 'In Progress'),
            ('COMPLETED', 'Completed'),
            ('READY_FOR_ACTIVATION', 'Ready for Activation'),
            ('ACTIVATED', 'Activated'),
        ],
        default='SCHEDULED'
    )
    
    # Notes and updates
    maintenance_notes = models.TextField(blank=True, null=True)
    completion_notes = models.TextField(blank=True, null=True)

    # Urgency level for maintenance
    urgency_level = models.CharField(
        max_length=20,
        choices=[
            ("LOW", "Low"),
            ("MEDIUM", "Medium"),
            ("HIGH", "High"),
            ("CRITICAL", "Critical"),
        ],
        default="MEDIUM"
    )
    
    # Admin activation
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        to_field='User_id',
        related_name='activated_maintenance'
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        item_name = ""
        if self.item_type == 'LOCOMOTIVE' and self.locomotive:
            item_name = self.locomotive.locomotive or f"Locomotive #{self.locomotive.id}"
        elif self.item_type == 'CARGO' and self.cargo:
            item_name = self.cargo.cargo_type or f"Cargo #{self.cargo.id}"
        elif self.item_type == 'WAGON' and self.wagon:
            item_name = self.wagon.wagon_number or f"Wagon #{self.wagon.id}"
        return f"Maintenance: {item_name} - {self.status}"
    
    def get_duration_in_maintenance(self):
        """Calculate how long the item has been in maintenance"""
        from django.utils import timezone
        from datetime import timedelta
        
        if self.status in ['SCHEDULED']:
            return None
        
        # Use completion date if completed, otherwise use current time
        end_date = self.actual_completion_date if self.actual_completion_date else timezone.now()
        delta = end_date - self.scheduled_date
        
        days = delta.days
        years = days // 365
        remaining_days = days % 365
        months = remaining_days // 30
        remaining_days = remaining_days % 30
        weeks = remaining_days // 7
        remaining_days = remaining_days % 7
        
        parts = []
        if years > 0:
            parts.append(f"{years} year{'s' if years != 1 else ''}")
        if months > 0:
            parts.append(f"{months} month{'s' if months != 1 else ''}")
        if weeks > 0:
            parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")
        if remaining_days > 0:
            parts.append(f"{remaining_days} day{'s' if remaining_days != 1 else ''}")
        
        return ", ".join(parts) if parts else "Less than a day"


class MaintenanceStatusUpdate(models.Model):
    """Track status changes and updates during maintenance"""
    id = models.AutoField(primary_key=True)
    maintenance_schedule = models.ForeignKey(
        MaintenanceSchedule,
        on_delete=models.CASCADE,
        related_name='status_updates'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        to_field='User_id'
    )
    previous_status = models.CharField(max_length=30)
    new_status = models.CharField(max_length=30)
    update_notes = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Status update: {self.previous_status} → {self.new_status}"


class PrivateMessage(models.Model):
    """Store private messages between users"""
    id = models.AutoField(primary_key=True)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field='User_id',
        related_name='sent_messages'
    )
    subject = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField()
    
    # Group messaging support
    is_group_message = models.BooleanField(default=False)
    target_role = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('ALL', 'All Users'),
            ('ADMIN', 'Admin'),
            ('STAFF', 'Staff'),
            ('DRIVER', 'Driver'),
            ('ELECTRICAL_MAINTENANCE_TEAM', 'Electrical Maintenance Team'),
            ('MECHANICAL_MAINTENANCE_TEAM', 'Mechanical Maintenance Team'),
            ('EMERGENCY_RESPONSE_TEAM', 'Emergency Response Team'),
            ('SECURITY_TEAM', 'Security Team'),
            ('MEDICAL_TEAM', 'Medical Team'),
            ('TOWING_SERVICE', 'Towing Service'),
        ],
        help_text="If group message, specify target role"
    )
    
    # Thread support for replies
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        if self.is_group_message:
            return f"Group message from {self.sender.email} to {self.target_role}"
        return f"Message from {self.sender.email}"


class MessageRecipient(models.Model):
    """Track individual recipients of messages and their read status"""
    id = models.AutoField(primary_key=True)
    message = models.ForeignKey(
        PrivateMessage,
        on_delete=models.CASCADE,
        related_name='recipients'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field='User_id',
        related_name='received_messages'
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_deleted_by_recipient = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-message__created_at']
        unique_together = ('message', 'recipient')
    
    def __str__(self):
        status = "Read" if self.is_read else "Unread"
        return f"{status} message to {self.recipient.email}"


# ========== OPTIMIZER INTEGRATION MODELS ==========

class OptimizerRequest(models.Model):
    """Track requests sent to external optimizer system"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    OPTIMIZATION_TYPE_CHOICES = [
        ('ROUTE_OPTIMIZATION', 'Route Optimization'),
        ('LOAD_BALANCING', 'Load Balancing'),
        ('FUEL_EFFICIENCY', 'Fuel Efficiency'),
        ('MAINTENANCE_SCHEDULING', 'Maintenance Scheduling'),
        ('WAGON_ALLOCATION', 'Wagon Allocation'),
        ('LOCOMOTIVE_ASSIGNMENT', 'Locomotive Assignment'),
        ('FULL_SYSTEM', 'Full System Optimization'),
    ]
    
    id = models.AutoField(primary_key=True)
    request_id = models.CharField(max_length=100, unique=True, default=generate_uuid)
    optimization_type = models.CharField(max_length=50, choices=OPTIMIZATION_TYPE_CHOICES)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        to_field='User_id',
        related_name='optimizer_requests'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Request payload sent to optimizer
    request_payload = models.JSONField(help_text="Data sent to optimizer")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # External optimizer details
    external_request_id = models.CharField(max_length=255, null=True, blank=True)
    optimizer_endpoint = models.URLField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['request_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.optimization_type} - {self.status} ({self.request_id})"


class OptimizerResponse(models.Model):
    """Store optimization suggestions received from external system"""
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    IMPLEMENTATION_STATUS_CHOICES = [
        ('PENDING_REVIEW', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('IMPLEMENTED', 'Implemented'),
        ('PARTIALLY_IMPLEMENTED', 'Partially Implemented'),
    ]
    
    id = models.AutoField(primary_key=True)
    optimizer_request = models.ForeignKey(
        OptimizerRequest,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    
    # Suggestion details
    suggestion_type = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    
    # Metrics and impacts
    expected_improvement = models.JSONField(
        null=True,
        blank=True,
        help_text="Expected improvements (e.g., fuel savings, time reduction)"
    )
    current_metrics = models.JSONField(
        null=True,
        blank=True,
        help_text="Current performance metrics"
    )
    projected_metrics = models.JSONField(
        null=True,
        blank=True,
        help_text="Projected performance after optimization"
    )
    
    # Implementation details
    implementation_steps = models.JSONField(
        null=True,
        blank=True,
        help_text="Steps to implement the suggestion"
    )
    implementation_status = models.CharField(
        max_length=30,
        choices=IMPLEMENTATION_STATUS_CHOICES,
        default='PENDING_REVIEW'
    )
    
    # Review information
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        to_field='User_id',
        related_name='reviewed_optimizations'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(null=True, blank=True)
    
    # Full response data from optimizer
    raw_response = models.JSONField(help_text="Complete response from optimizer")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['implementation_status']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.priority} priority"


class OptimizationLog(models.Model):
    """Log all optimizer API interactions for audit and debugging"""
    LOG_TYPE_CHOICES = [
        ('REQUEST', 'Request Sent'),
        ('RESPONSE', 'Response Received'),
        ('ERROR', 'Error'),
        ('INFO', 'Information'),
    ]
    
    id = models.AutoField(primary_key=True)
    optimizer_request = models.ForeignKey(
        OptimizerRequest,
        on_delete=models.CASCADE,
        related_name='logs',
        null=True,
        blank=True
    )
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES)
    message = models.TextField()
    details = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.log_type} - {self.timestamp}"

