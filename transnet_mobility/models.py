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
            ('ELECTICAL_MAINTENANCE_TEAM','Electrical_Maintenance_Team'),
            ('MECHANICAL_MAINTENANCE_TEAM','Mechanical_Maintenance_Team'),
            ('EMERGENCY_RESPONSE_TEAM','Emergency_Response_Team'),
            ('OTHER', 'Other')
        ],
        default='OTHER'
    )

    role = models.CharField(
        max_length=50,
        choices=[
            ('ADMIN', 'Admin'),
            ('STAFF', 'Staff'),
            ('DRIVER', 'Driver'),
            ('ELECTICAL_MAINTENANCE_TEAM','Electrical_Maintenance_Team'),
            ('MECHANICAL_MAINTENANCE_TEAM','Mechanical_Maintenance_Team'),
            ('EMERGENCY_RESPONSE_TEAM','Emergency_Response_Team'),
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