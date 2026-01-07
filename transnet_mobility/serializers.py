from rest_framework import serializers
from .models import CustomUser, LocomotiveSpec, LocomotiveAssignment, Schedule, WagonSpec, MaintenanceSchedule

class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'User_id', 'first_name', 'last_name', 'email', 'phone_number', 'staff_number', 'profession', 'id_number',
            'employee_number', 'mobile_number', 'account_type', 'role', 'profile_picture',
            'driver_status', 'last_location', 'current_location'
        ]

class LocomotiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocomotiveSpec
        fields = '__all__'

class LocomotiveAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocomotiveAssignment
        fields = '__all__'

class ScheduleSerializer(serializers.ModelSerializer):
    def get_auto_assistant(self, driver, date, shift_type, area):
        # Find an available driver (not the main driver) in the same area, not on leave/emergency, not already assigned
        from .models import Schedule, CustomUser
        assigned_ids = set(Schedule.objects.filter(date=date, shift_type=shift_type).values_list('driver', flat=True))
        assigned_ids.add(driver.User_id)
        candidates = CustomUser.objects.filter(
            account_type='DRIVER',
            driver_status='available',
            current_location=area
        ).exclude(User_id__in=assigned_ids)
        return candidates.first() if candidates.exists() else None

    def create(self, validated_data):
        assistant = validated_data.get('assistant', None)
        driver = validated_data['driver']
        date = validated_data['date']
        shift_type = validated_data['shift_type']
        area = validated_data.get('area', None)
        locomotives_data = validated_data.pop('locomotives', [])
        if not assistant:
            auto_assistant = self.get_auto_assistant(driver, date, shift_type, area)
            if auto_assistant:
                validated_data['assistant'] = auto_assistant
        instance = super().create(validated_data)
        if locomotives_data:
            instance.locomotives.set(locomotives_data)
        return instance

    def update(self, instance, validated_data):
        assistant = validated_data.get('assistant', None)
        driver = validated_data.get('driver', instance.driver)
        date = validated_data.get('date', instance.date)
        shift_type = validated_data.get('shift_type', instance.shift_type)
        area = validated_data.get('area', instance.area)
        locomotives_data = validated_data.pop('locomotives', None)
        if not assistant:
            auto_assistant = self.get_auto_assistant(driver, date, shift_type, area)
            if auto_assistant:
                validated_data['assistant'] = auto_assistant
        instance = super().update(instance, validated_data)
        if locomotives_data is not None:
            instance.locomotives.set(locomotives_data)
        return instance

    # Accept PKs for writes, provide nested details for reads
    driver = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.filter(account_type='DRIVER'))
    assistant = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.filter(account_type='DRIVER'), allow_null=True, required=False)
    locomotives = serializers.PrimaryKeyRelatedField(queryset=LocomotiveSpec.objects.all(), many=True, required=False)
    status = serializers.CharField(required=False, default='available')
    driver_detail = DriverSerializer(source='driver', read_only=True)
    assistant_detail = DriverSerializer(source='assistant', read_only=True)

    class Meta:
        model = Schedule
        fields = [
            'id', 'driver', 'assistant', 'locomotives', 'date', 'shift_type', 'status',
            'area', 'last_location', 'current_location', 'created_at', 'updated_at',
            'driver_detail', 'assistant_detail'
        ]

    def validate(self, data):
        # Unique together error customization
        driver = data.get('driver')
        date = data.get('date')
        shift_type = data.get('shift_type')
        instance = getattr(self, 'instance', None)
        qs = Schedule.objects.filter(driver=driver, date=date, shift_type=shift_type)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError({
                'non_field_errors': [
                    'This driver is already scheduled for this date and shift. Please choose a different driver, date, or shift.'
                ]
            })
        return data

class WagonSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = WagonSpec
        fields = '__all__'

class MaintenanceScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceSchedule
        fields = '__all__'
