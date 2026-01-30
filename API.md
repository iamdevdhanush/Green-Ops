# GreenOps API Documentation

## Base URL
```
http://localhost:5000/api/v1
```

## Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

### Get Access Token
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin"
  }
}
```

## Endpoints

### Agent Endpoints

#### Report System Status
```http
POST /api/v1/agent/report
Content-Type: application/json

{
  "pc_id": "PC-001",
  "hostname": "workstation-01",
  "os": "Linux",
  "os_version": "Ubuntu 22.04",
  "idle_minutes": 25.5,
  "action": "SLEEP",
  "reason": "Idle exceeded threshold",
  "threshold": 15,
  "timestamp": "2026-01-29T10:30:00Z"
}
```

**Response:**
```json
{
  "status": "ok",
  "system_id": 123,
  "metrics": {
    "energy_kwh": 0.625,
    "co2_kg": 0.512,
    "cost_saved": 5.0
  }
}
```

#### Get Policy
```http
GET /api/v1/agent/policy
```

**Response:**
```json
{
  "idle_threshold": 15,
  "sleep_threshold": 30,
  "action_type": "sleep",
  "warning_enabled": true,
  "warning_duration": 300,
  "schedule": "Mon-Fri 9:00-18:00"
}
```

### System Management

#### List All Systems
```http
GET /api/v1/systems
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "id": 1,
    "pc_id": "PC-001",
    "hostname": "workstation-01",
    "os": "Linux",
    "department_id": 1,
    "power_watts": 150,
    "status": "active",
    "last_seen": "2026-01-29T10:30:00Z"
  }
]
```

#### Get System Details
```http
GET /api/v1/systems/{system_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "system": {
    "id": 1,
    "pc_id": "PC-001",
    "status": "active"
  },
  "recent_logs": [
    {
      "id": 100,
      "idle_minutes": 25.5,
      "action": "SLEEP",
      "timestamp": "2026-01-29T10:30:00Z"
    }
  ]
}
```

### Metrics & Analytics

#### Get Summary Metrics
```http
GET /api/v1/metrics/summary?period=7d
Authorization: Bearer <token>
```

**Parameters:**
- `period`: `24h`, `7d`, `30d`

**Response:**
```json
{
  "period": "7d",
  "total_energy_kwh": 125.5,
  "total_co2_kg": 102.91,
  "total_cost_saved": 1004.0,
  "total_actions": 45,
  "carbon_budget": 5000,
  "budget_remaining": 4897.09,
  "budget_used_percentage": 2.1
}
```

#### Get Trends
```http
GET /api/v1/metrics/trends?days=7
Authorization: Bearer <token>
```

**Response:**
```json
{
  "trends": [
    {
      "date": "2026-01-23",
      "energy_kwh": 18.5,
      "co2_kg": 15.17,
      "cost_saved": 148.0,
      "actions": 7
    }
  ]
}
```

### Policy Management

#### List Policies
```http
GET /api/v1/policies
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Office Hours Policy",
    "idle_threshold": 15,
    "sleep_threshold": 30,
    "action_type": "sleep",
    "is_active": true
  }
]
```

#### Create Policy
```http
POST /api/v1/policies
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Aggressive Savings",
  "description": "Stricter policy for maximum savings",
  "idle_threshold": 10,
  "sleep_threshold": 20,
  "action_type": "sleep",
  "warning_enabled": true,
  "warning_duration": 180,
  "schedule": "Mon-Fri 9:00-18:00"
}
```

**Response:**
```json
{
  "id": 2,
  "name": "Aggressive Savings",
  "idle_threshold": 10,
  "sleep_threshold": 20,
  "is_active": false
}
```

### Export Data

#### Export CSV
```http
GET /api/v1/export/csv?period=30d
Authorization: Bearer <token>
```

**Parameters:**
- `period`: `7d`, `30d`, `all`

**Response:** CSV file download

### System Health

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "version": "2.0.0",
  "database": "ok",
  "demo_mode": true
}
```

#### Prometheus Metrics
```http
GET /metrics
```

**Response:** Prometheus-format metrics

## Error Responses

All endpoints return errors in this format:
```json
{
  "error": "Description of the error"
}
```

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests
- `500` - Internal Server Error

## Rate Limiting

API endpoints are rate-limited:
- Default: 200 requests per day, 50 per hour
- Agent endpoints: 120 requests per minute
- Login endpoint: 5 requests per minute

## Webhooks (Coming Soon)

GreenOps will support webhooks for real-time notifications:
- System sleep events
- Budget threshold alerts
- Policy violations

## Python SDK Example

```python
import requests

class GreenOpsClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {'Authorization': f'Bearer {api_key}'}
    
    def get_systems(self):
        response = requests.get(
            f'{self.base_url}/api/v1/systems',
            headers=self.headers
        )
        return response.json()
    
    def get_metrics(self, period='7d'):
        response = requests.get(
            f'{self.base_url}/api/v1/metrics/summary',
            params={'period': period},
            headers=self.headers
        )
        return response.json()

# Usage
client = GreenOpsClient('http://localhost:5000', 'your-api-key')
systems = client.get_systems()
metrics = client.get_metrics('30d')
```

## Support

For API support, visit:
- Documentation: https://docs.greenops.io
- GitHub: https://github.com/yourusername/greenops
- Email: api-support@greenops.io
