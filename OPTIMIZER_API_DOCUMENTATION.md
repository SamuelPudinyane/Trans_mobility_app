# Optimizer API Integration Documentation

## Overview
This document describes the API endpoints for integrating with an external optimization system. The system collects data from the Transnet Freight Rail mobility platform, sends it to an external optimizer, and receives optimization suggestions.

## Architecture
```
Transnet Platform → External Optimizer → Transnet Platform
     (Request)            (Process)         (Suggestions)
```

## Configuration

### Environment Variables
Add these to your `.env` file or system environment:

```bash
OPTIMIZER_API_URL=http://external-optimizer-api.com/api/v1
OPTIMIZER_API_KEY=your-api-key-here
```

## API Endpoints

### 1. Request Optimization

**Endpoint:** `POST /api/optimizer/request/`

**Description:** Submit a new optimization request to the external system.

**Authentication:** Required (Admin only)

**Request Body:**
```json
{
  "optimization_type": "ROUTE_OPTIMIZATION",
  "parameters": {
    "custom_param1": "value1",
    "custom_param2": "value2"
  }
}
```

**Optimization Types:**
- `ROUTE_OPTIMIZATION` - Optimize delivery routes
- `LOAD_BALANCING` - Balance cargo across wagons
- `FUEL_EFFICIENCY` - Optimize fuel consumption
- `MAINTENANCE_SCHEDULING` - Optimize maintenance schedules
- `WAGON_ALLOCATION` - Optimize wagon assignments
- `LOCOMOTIVE_ASSIGNMENT` - Optimize locomotive assignments
- `FULL_SYSTEM` - Comprehensive system optimization

**Response:**
```json
{
  "success": true,
  "request_id": "uuid-string",
  "status": "PROCESSING",
  "message": "Optimization request submitted successfully",
  "external_request_id": "external-system-id"
}
```

**Data Sent to External Optimizer:**
The system automatically collects and sends:
- Locomotive specifications and status
- Wagon inventory and assignments
- Cargo data (weight, origin, destination)
- Route information
- Fuel data and prices
- Current assignments
- Maintenance schedules
- Driver requests

---

### 2. Receive Optimization Results (Webhook)

**Endpoint:** `POST /api/optimizer/results/`

**Description:** Webhook endpoint for external optimizer to send results back.

**Authentication:** Bearer token in Authorization header

**Request Headers:**
```
Authorization: Bearer your-api-key-here
Content-Type: application/json
```

**Request Body:**
```json
{
  "request_id": "uuid-string",
  "suggestions": [
    {
      "type": "ROUTE_CHANGE",
      "title": "Optimize Route A-B",
      "description": "Change route from Johannesburg to Cape Town to reduce fuel consumption",
      "priority": "HIGH",
      "expected_improvement": {
        "fuel_savings": "15%",
        "time_reduction": "2 hours",
        "cost_savings": "R5000"
      },
      "current_metrics": {
        "distance_km": 1400,
        "fuel_consumption": 2000,
        "estimated_time": 18
      },
      "projected_metrics": {
        "distance_km": 1350,
        "fuel_consumption": 1700,
        "estimated_time": 16
      },
      "implementation_steps": [
        "Update route preference in system",
        "Notify affected drivers",
        "Update scheduling system"
      ]
    }
  ],
  "metrics": {
    "processing_time_seconds": 45,
    "confidence_score": 0.92
  }
}
```

**Suggestion Fields:**
- `type`: Type of suggestion (string)
- `title`: Short title (string, max 255 chars)
- `description`: Detailed description (text)
- `priority`: LOW | MEDIUM | HIGH | CRITICAL
- `expected_improvement`: JSON object with improvement metrics
- `current_metrics`: JSON object with current state
- `projected_metrics`: JSON object with expected state
- `implementation_steps`: Array of steps to implement

**Response:**
```json
{
  "success": true,
  "message": "Results received and processed",
  "suggestions_count": 5
}
```

---

### 3. Get Optimization Suggestions

**Endpoint:** `GET /api/optimizer/suggestions/`

**Description:** Retrieve optimization suggestions for admin review.

**Authentication:** Required (Admin only)

**Query Parameters:**
- `status`: Filter by implementation status (PENDING_REVIEW, APPROVED, REJECTED, IMPLEMENTED)
- `priority`: Filter by priority (LOW, MEDIUM, HIGH, CRITICAL)
- `type`: Filter by suggestion type

**Example:**
```
GET /api/optimizer/suggestions/?status=PENDING_REVIEW&priority=HIGH
```

**Response:**
```json
{
  "success": true,
  "suggestions": [
    {
      "id": 1,
      "request_id": "uuid-string",
      "optimization_type": "ROUTE_OPTIMIZATION",
      "suggestion_type": "ROUTE_CHANGE",
      "title": "Optimize Route A-B",
      "description": "Change route from Johannesburg to Cape Town...",
      "priority": "HIGH",
      "implementation_status": "PENDING_REVIEW",
      "expected_improvement": {...},
      "current_metrics": {...},
      "projected_metrics": {...},
      "implementation_steps": [...],
      "created_at": "2025-11-15T10:30:00Z",
      "reviewed_by": null,
      "reviewed_at": null,
      "review_notes": null
    }
  ],
  "count": 1
}
```

---

### 4. Update Suggestion Status

**Endpoint:** `POST /api/optimizer/suggestions/<suggestion_id>/update/`

**Description:** Update the implementation status of a suggestion.

**Authentication:** Required (Admin only)

**Request Body:**
```json
{
  "status": "APPROVED",
  "notes": "Approved for implementation next week"
}
```

**Status Values:**
- `PENDING_REVIEW` - Awaiting admin review
- `APPROVED` - Approved for implementation
- `REJECTED` - Rejected by admin
- `IMPLEMENTED` - Successfully implemented
- `PARTIALLY_IMPLEMENTED` - Partially implemented

**Response:**
```json
{
  "success": true,
  "message": "Suggestion status updated",
  "suggestion_id": 1,
  "new_status": "APPROVED"
}
```

---

### 5. Optimization Dashboard

**Endpoint:** `GET /optimization-dashboard/`

**Description:** Web interface for viewing and managing optimization suggestions.

**Authentication:** Required (Admin only)

**Features:**
- View optimization statistics
- Submit new optimization requests
- Review high-priority suggestions
- Approve/reject suggestions
- View implementation history

---

## Database Models

### OptimizerRequest
Tracks optimization requests sent to external system.

**Fields:**
- `request_id` - Unique identifier
- `optimization_type` - Type of optimization
- `requested_by` - Admin user who requested
- `status` - PENDING | PROCESSING | COMPLETED | FAILED
- `request_payload` - Data sent to optimizer
- `external_request_id` - ID from external system
- `optimizer_endpoint` - External API endpoint used
- `created_at` - Request timestamp
- `processed_at` - Processing completion timestamp

### OptimizerResponse
Stores optimization suggestions from external system.

**Fields:**
- `optimizer_request` - FK to OptimizerRequest
- `suggestion_type` - Type of suggestion
- `title` - Short title
- `description` - Detailed description
- `priority` - LOW | MEDIUM | HIGH | CRITICAL
- `expected_improvement` - JSON with improvements
- `current_metrics` - JSON with current state
- `projected_metrics` - JSON with projected state
- `implementation_steps` - JSON array of steps
- `implementation_status` - Review/implementation status
- `reviewed_by` - Admin who reviewed
- `reviewed_at` - Review timestamp
- `review_notes` - Admin review notes

### OptimizationLog
Audit log for all optimizer interactions.

**Fields:**
- `optimizer_request` - FK to OptimizerRequest
- `log_type` - REQUEST | RESPONSE | ERROR | INFO
- `message` - Log message
- `details` - JSON with additional details
- `timestamp` - Log timestamp

---

## External Optimizer Requirements

### Expected Endpoints

The external optimizer should implement:

**1. Process Optimization Request**
```
POST /api/v1/optimize
Authorization: Bearer {API_KEY}
Content-Type: application/json

Body: {
  "request_id": "uuid",
  "data": {...}  // System data from Transnet
}

Response: {
  "external_request_id": "external-id",
  "status": "processing",
  "estimated_completion_seconds": 60
}
```

**2. Send Results Back**
When processing is complete, POST results to:
```
POST {TRANSNET_URL}/api/optimizer/results/
Authorization: Bearer {API_KEY}
Content-Type: application/json

Body: {
  "request_id": "original-uuid",
  "suggestions": [...]
}
```

---

## Usage Examples

### Example 1: Request Route Optimization

```python
import requests

response = requests.post(
    'http://your-domain.com/api/optimizer/request/',
    headers={
        'Authorization': 'Bearer your-token',
        'Content-Type': 'application/json'
    },
    json={
        'optimization_type': 'ROUTE_OPTIMIZATION',
        'parameters': {
            'origin': 'Johannesburg',
            'destination': 'Cape Town',
            'max_stops': 3
        }
    }
)

result = response.json()
print(f"Request ID: {result['request_id']}")
```

### Example 2: External System Sending Results

```python
import requests

results = {
    'request_id': 'abc-123-def-456',
    'suggestions': [
        {
            'type': 'ROUTE_CHANGE',
            'title': 'Use Alternative Route',
            'description': 'Switch to coastal route for better efficiency',
            'priority': 'HIGH',
            'expected_improvement': {
                'fuel_savings': '15%',
                'time_reduction': '2 hours'
            },
            'current_metrics': {
                'distance_km': 1400,
                'fuel_consumption': 2000
            },
            'projected_metrics': {
                'distance_km': 1350,
                'fuel_consumption': 1700
            },
            'implementation_steps': [
                'Update route in system',
                'Notify drivers',
                'Monitor for 1 week'
            ]
        }
    ]
}

response = requests.post(
    'http://transnet-domain.com/api/optimizer/results/',
    headers={
        'Authorization': 'Bearer api-key',
        'Content-Type': 'application/json'
    },
    json=results
)

print(response.json())
```

### Example 3: Retrieve Pending Suggestions

```python
import requests

response = requests.get(
    'http://your-domain.com/api/optimizer/suggestions/',
    headers={'Authorization': 'Bearer your-token'},
    params={
        'status': 'PENDING_REVIEW',
        'priority': 'HIGH'
    }
)

suggestions = response.json()['suggestions']
for suggestion in suggestions:
    print(f"{suggestion['title']} - Priority: {suggestion['priority']}")
```

---

## Testing

### Test Data Generation

Create test optimization requests:

```python
python manage.py shell

from transnet_mobility.models import OptimizerRequest, OptimizerResponse
from django.contrib.auth import get_user_model

User = get_user_model()
admin = User.objects.filter(role='ADMIN').first()

# Create test request
request = OptimizerRequest.objects.create(
    optimization_type='ROUTE_OPTIMIZATION',
    requested_by=admin,
    request_payload={'test': 'data'}
)

# Create test response/suggestion
OptimizerResponse.objects.create(
    optimizer_request=request,
    suggestion_type='ROUTE_CHANGE',
    title='Test Suggestion',
    description='This is a test suggestion',
    priority='HIGH',
    expected_improvement={'fuel_savings': '10%'},
    raw_response={'test': 'data'}
)
```

---

## Security

### API Key Management
- API keys should be stored securely in environment variables
- Never commit API keys to version control
- Rotate API keys regularly
- Use different keys for development and production

### Authentication
- All endpoints require authentication
- Admin role required for optimizer endpoints
- Bearer token authentication for webhooks

### Rate Limiting
Consider implementing rate limiting:
- Max 10 optimization requests per hour per admin
- Max 100 webhook calls per hour from external system

---

## Monitoring and Logging

All optimizer interactions are logged in the `OptimizationLog` model:

```python
from transnet_mobility.models import OptimizationLog

# View recent logs
logs = OptimizationLog.objects.all()[:50]
for log in logs:
    print(f"{log.timestamp} - {log.log_type}: {log.message}")
```

Monitor for:
- Failed requests
- Processing time
- Success rate
- Implementation rate of suggestions

---

## Support

For issues or questions:
1. Check logs in Django admin: `/admin/transnet_mobility/optimizationlog/`
2. Review optimizer requests: `/admin/transnet_mobility/optimizerrequest/`
3. Check suggestion status: `/admin/transnet_mobility/optimizerresponse/`

---

## Future Enhancements

Planned features:
- Automatic implementation of low-risk suggestions
- A/B testing framework for suggestions
- Machine learning for suggestion prioritization
- Real-time optimization triggers
- Batch optimization scheduling
- Cost-benefit analysis dashboard
