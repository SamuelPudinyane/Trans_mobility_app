from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from transnet_mobility.models import Schedule, LocomotiveAssignment, WagonSpec, MaintenanceSchedule
from transnet_mobility.serializers import (
    ScheduleSerializer, LocomotiveAssignmentSerializer, WagonSpecSerializer, MaintenanceScheduleSerializer
)
import requests

# Send data to BI endpoint
class SendToBIView(APIView):
    def post(self, request):
        # Example: send all schedules
        schedules = Schedule.objects.all()
        serializer = ScheduleSerializer(schedules, many=True)
        bi_url = 'https://bi.example.com/api/receive-data/'  # Replace with real BI endpoint
        response = requests.post(bi_url, json=serializer.data)
        return Response({'status': 'sent', 'bi_response': response.json()}, status=status.HTTP_200_OK)

# Send data to Optimizer and get suggestions
class SendToOptimizerView(APIView):
    def post(self, request):
        # Example: send current assignments
        data = request.data  # Should include type: schedule, maintenance, etc.
        optimizer_url = 'https://optimizer.example.com/api/optimize/'  # Replace with real Optimizer endpoint
        response = requests.post(optimizer_url, json=data)
        return Response({'status': 'sent', 'optimizer_response': response.json()}, status=status.HTTP_200_OK)

# Accept Optimizer suggestions (overwrite admin changes)
class AcceptOptimizerSuggestionView(APIView):
    def post(self, request):
        # Example: Overwrite assignments with optimizer's suggestion
        suggestion = request.data.get('suggestion')
        # Apply suggestion logic here (update DB)
        # ...
        return Response({'status': 'applied', 'applied_data': suggestion}, status=status.HTTP_200_OK)
