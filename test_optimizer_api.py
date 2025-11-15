"""
Test script for Optimizer API Integration
Run this script to test the optimizer API endpoints
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_KEY = "your-api-key-here"  # Update with actual API key

# Admin credentials for testing (update with actual credentials)
ADMIN_EMAIL = "admin@transnet.com"
ADMIN_PASSWORD = "admin123"


class OptimizerAPITester:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.csrf_token = None
        
    def login(self, email, password):
        """Login to get session cookie"""
        print("🔐 Logging in...")
        
        # Get CSRF token
        response = self.session.get(f"{self.base_url}/")
        self.csrf_token = response.cookies.get('csrftoken')
        
        # Login
        response = self.session.post(
            f"{self.base_url}/",
            data={
                'username': email,
                'password': password,
                'csrfmiddlewaretoken': self.csrf_token
            },
            headers={'Referer': f"{self.base_url}/"}
        )
        
        if response.status_code == 200:
            print("✅ Login successful!")
            return True
        else:
            print(f"❌ Login failed: {response.status_code}")
            return False
    
    def request_optimization(self, optimization_type="FULL_SYSTEM", parameters=None):
        """Test requesting optimization"""
        print(f"\n📤 Requesting {optimization_type} optimization...")
        
        payload = {
            "optimization_type": optimization_type,
            "parameters": parameters or {}
        }
        
        response = self.session.post(
            f"{self.base_url}/api/optimizer/request/",
            json=payload,
            headers={
                'X-CSRFToken': self.csrf_token,
                'Content-Type': 'application/json'
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Optimization request submitted!")
            print(f"   Request ID: {result.get('request_id')}")
            print(f"   Status: {result.get('status')}")
            return result.get('request_id')
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    
    def send_optimization_results(self, request_id):
        """Simulate external optimizer sending results"""
        print(f"\n📥 Sending optimization results for {request_id}...")
        
        # Sample suggestions
        results = {
            "request_id": request_id,
            "suggestions": [
                {
                    "type": "ROUTE_OPTIMIZATION",
                    "title": "Optimize JHB-CPT Route",
                    "description": "Switch to coastal route to reduce fuel consumption by 15%",
                    "priority": "HIGH",
                    "expected_improvement": {
                        "fuel_savings": "15%",
                        "time_reduction": "2 hours",
                        "cost_savings": "R5000 per trip"
                    },
                    "current_metrics": {
                        "distance_km": 1400,
                        "fuel_consumption_liters": 2000,
                        "estimated_time_hours": 18,
                        "average_cost": 35000
                    },
                    "projected_metrics": {
                        "distance_km": 1350,
                        "fuel_consumption_liters": 1700,
                        "estimated_time_hours": 16,
                        "average_cost": 30000
                    },
                    "implementation_steps": [
                        "Update route preference in system",
                        "Notify affected drivers via email",
                        "Update GPS waypoints",
                        "Monitor fuel consumption for 1 week",
                        "Review and adjust if needed"
                    ]
                },
                {
                    "type": "MAINTENANCE_SCHEDULING",
                    "title": "Optimize Maintenance Schedule",
                    "description": "Reschedule locomotive maintenance to off-peak hours",
                    "priority": "MEDIUM",
                    "expected_improvement": {
                        "downtime_reduction": "20%",
                        "cost_savings": "R3000 per maintenance"
                    },
                    "current_metrics": {
                        "avg_downtime_hours": 8,
                        "maintenance_cost": 15000
                    },
                    "projected_metrics": {
                        "avg_downtime_hours": 6.4,
                        "maintenance_cost": 12000
                    },
                    "implementation_steps": [
                        "Identify off-peak hours",
                        "Reschedule maintenance windows",
                        "Notify maintenance teams"
                    ]
                },
                {
                    "type": "LOAD_BALANCING",
                    "title": "Balance Wagon Loads",
                    "description": "Redistribute cargo across wagons to improve fuel efficiency",
                    "priority": "CRITICAL",
                    "expected_improvement": {
                        "fuel_savings": "10%",
                        "wear_reduction": "15%"
                    },
                    "current_metrics": {
                        "wagon_utilization": 0.65,
                        "fuel_efficiency": 0.75
                    },
                    "projected_metrics": {
                        "wagon_utilization": 0.85,
                        "fuel_efficiency": 0.85
                    },
                    "implementation_steps": [
                        "Analyze current cargo distribution",
                        "Create balanced loading plan",
                        "Implement new loading procedures",
                        "Train staff on new procedures"
                    ]
                }
            ],
            "metrics": {
                "processing_time_seconds": 45,
                "confidence_score": 0.92,
                "analyzed_data_points": 15000
            }
        }
        
        response = requests.post(
            f"{self.base_url}/api/optimizer/results/",
            json=results,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Results submitted successfully!")
            print(f"   Suggestions count: {result.get('suggestions_count')}")
            return True
        else:
            print(f"❌ Failed to submit results: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    def get_suggestions(self, status=None, priority=None):
        """Test retrieving suggestions"""
        print(f"\n📋 Retrieving suggestions...")
        
        params = {}
        if status:
            params['status'] = status
        if priority:
            params['priority'] = priority
        
        response = self.session.get(
            f"{self.base_url}/api/optimizer/suggestions/",
            params=params
        )
        
        if response.status_code == 200:
            result = response.json()
            suggestions = result.get('suggestions', [])
            print(f"✅ Retrieved {len(suggestions)} suggestions")
            
            for i, suggestion in enumerate(suggestions, 1):
                print(f"\n   Suggestion {i}:")
                print(f"   - Title: {suggestion['title']}")
                print(f"   - Priority: {suggestion['priority']}")
                print(f"   - Status: {suggestion['implementation_status']}")
            
            return suggestions
        else:
            print(f"❌ Failed to retrieve suggestions: {response.status_code}")
            return []
    
    def update_suggestion_status(self, suggestion_id, status, notes=""):
        """Test updating suggestion status"""
        print(f"\n✏️  Updating suggestion {suggestion_id} to {status}...")
        
        payload = {
            "status": status,
            "notes": notes
        }
        
        response = self.session.post(
            f"{self.base_url}/api/optimizer/suggestions/{suggestion_id}/update/",
            json=payload,
            headers={
                'X-CSRFToken': self.csrf_token,
                'Content-Type': 'application/json'
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Suggestion status updated!")
            return True
        else:
            print(f"❌ Failed to update status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    def run_full_test(self):
        """Run complete test suite"""
        print("\n" + "="*60)
        print("🚀 Starting Optimizer API Test Suite")
        print("="*60)
        
        # Step 1: Login
        if not self.login(ADMIN_EMAIL, ADMIN_PASSWORD):
            print("\n❌ Test suite failed: Could not login")
            return False
        
        # Step 2: Request optimization
        request_id = self.request_optimization(
            optimization_type="FULL_SYSTEM",
            parameters={"test_mode": True}
        )
        
        if not request_id:
            print("\n❌ Test suite failed: Could not create optimization request")
            return False
        
        # Step 3: Send results (simulating external optimizer)
        if not self.send_optimization_results(request_id):
            print("\n❌ Test suite failed: Could not submit results")
            return False
        
        # Step 4: Retrieve suggestions
        suggestions = self.get_suggestions(status="PENDING_REVIEW")
        
        if not suggestions:
            print("\n⚠️  Warning: No suggestions found")
        else:
            # Step 5: Update first suggestion status
            first_suggestion = suggestions[0]
            self.update_suggestion_status(
                suggestion_id=first_suggestion['id'],
                status="APPROVED",
                notes="Approved for testing purposes"
            )
        
        print("\n" + "="*60)
        print("✅ Test suite completed successfully!")
        print("="*60)
        print("\n📊 Summary:")
        print(f"   - Optimization request created: {request_id}")
        print(f"   - Results submitted: 3 suggestions")
        print(f"   - Suggestions retrieved: {len(suggestions)}")
        
        return True


def main():
    """Main test function"""
    print("\n🧪 Optimizer API Integration Test")
    print("="*60)
    
    # Create tester instance
    tester = OptimizerAPITester(BASE_URL, API_KEY)
    
    # Run full test suite
    success = tester.run_full_test()
    
    if success:
        print("\n🎉 All tests passed!")
        print("\n💡 Next steps:")
        print("   1. Visit http://127.0.0.1:8000/optimization-dashboard/")
        print("   2. Review the suggestions in the dashboard")
        print("   3. Approve/reject suggestions as needed")
        print("   4. Check the admin panel for detailed logs")
    else:
        print("\n❌ Some tests failed. Check the output above.")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
