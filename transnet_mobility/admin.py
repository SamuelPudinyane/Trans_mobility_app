from django.contrib import admin
from .models import (
    CustomUser, UserLocation, LocomotiveSpec, CargoSpec, WheelsetSpec, WagonSpec,
    RoutePreferenceSpec, LocomotiveAssignment, LocomotiveWagonAssignment, FuelSpec, DriverRequest,
    DispatchLog, DispatchNotification, DriverAssignmentNotification,
    MaintenanceSchedule, MaintenanceStatusUpdate, PrivateMessage, MessageRecipient,
    OptimizerRequest, OptimizerResponse, OptimizationLog
)

# Register your models here.
admin.site.register(CustomUser)
admin.site.register(UserLocation)
admin.site.register(LocomotiveSpec)
admin.site.register(CargoSpec)
admin.site.register(WheelsetSpec)
admin.site.register(WagonSpec)
admin.site.register(RoutePreferenceSpec)
admin.site.register(LocomotiveAssignment)
admin.site.register(LocomotiveWagonAssignment)
admin.site.register(FuelSpec)
admin.site.register(DriverRequest)
admin.site.register(DispatchLog)
admin.site.register(DispatchNotification)
admin.site.register(DriverAssignmentNotification)
admin.site.register(MaintenanceSchedule)
admin.site.register(MaintenanceStatusUpdate)
admin.site.register(PrivateMessage)
admin.site.register(MessageRecipient)
admin.site.register(OptimizerRequest)
admin.site.register(OptimizerResponse)
admin.site.register(OptimizationLog)
