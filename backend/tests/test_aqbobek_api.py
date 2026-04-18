"""
Aqbobek ACS Backend API Tests
Tests all API endpoints for the AI-dispatcher dashboard for Kazakh school.
"""
import pytest
import requests
import os
from datetime import date

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
DIRECTOR_EMAIL = "director@aqbobek.kz"
DIRECTOR_PASSWORD = "director123"
TEACHER_EMAIL = "teacher1@aqbobek.kz"
TEACHER_PASSWORD = "teacher123"


class TestAuth:
    """Authentication endpoint tests"""
    
    def test_director_login_success(self):
        """POST /api/auth/login for director returns JWT + user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DIRECTOR_EMAIL,
            "password": DIRECTOR_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "access_token" in data, "Missing access_token"
        assert "user" in data, "Missing user"
        assert data["user"]["email"] == DIRECTOR_EMAIL
        assert data["user"]["user_role"] == "director"
        assert len(data["access_token"]) > 0
    
    def test_teacher_login_success(self):
        """Teacher login (teacher1@aqbobek.kz / teacher123) works and returns user_role=teacher"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEACHER_EMAIL,
            "password": TEACHER_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["user_role"] == "teacher"
    
    def test_login_invalid_credentials(self):
        """Invalid credentials return 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401
    
    def test_auth_me_with_token(self):
        """GET /api/auth/me with Bearer token returns user"""
        # First login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DIRECTOR_EMAIL,
            "password": DIRECTOR_PASSWORD
        })
        token = login_resp.json()["access_token"]
        
        # Then get /me
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == DIRECTOR_EMAIL
        assert data["user_role"] == "director"
    
    def test_auth_me_without_token(self):
        """GET /api/auth/me without token returns 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401


@pytest.fixture
def director_token():
    """Get director authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": DIRECTOR_EMAIL,
        "password": DIRECTOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Director authentication failed")


@pytest.fixture
def teacher_token():
    """Get teacher authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEACHER_EMAIL,
        "password": TEACHER_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Teacher authentication failed")


@pytest.fixture
def director_headers(director_token):
    return {"Authorization": f"Bearer {director_token}"}


@pytest.fixture
def teacher_headers(teacher_token):
    return {"Authorization": f"Bearer {teacher_token}"}


class TestDashboard:
    """Dashboard endpoint tests"""
    
    def test_dashboard_stats_requires_auth(self):
        """GET /api/dashboard/stats requires auth"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 401
    
    def test_dashboard_stats_returns_data(self, director_headers):
        """GET /api/dashboard/stats returns expected fields"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=director_headers)
        assert response.status_code == 200
        data = response.json()
        # Check all required fields
        assert "employees" in data
        assert "incidents_open" in data
        assert "tasks_open" in data
        assert "canteen_today" in data
        assert "substitutions_today" in data
        assert "messages_week" in data
        assert "incidents_recent" in data
        # Validate types
        assert isinstance(data["employees"], int)
        assert isinstance(data["incidents_recent"], list)
    
    def test_dashboard_heatmap(self, director_headers):
        """GET /api/dashboard/heatmap returns {days, rows}"""
        response = requests.get(f"{BASE_URL}/api/dashboard/heatmap", headers=director_headers)
        assert response.status_code == 200
        data = response.json()
        assert "days" in data
        assert "rows" in data
        assert len(data["days"]) == 5  # Mon-Fri
        assert isinstance(data["rows"], list)


class TestEmployees:
    """Employees CRUD tests"""
    
    def test_list_employees(self, director_headers):
        """GET /api/employees returns list with 44 employees"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=director_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 44, f"Expected at least 44 employees, got {len(data)}"
        # Check employee structure
        emp = data[0]
        assert "full_name" in emp
        assert "role" in emp
        assert "email" in emp
    
    def test_create_employee_director_only(self, director_headers, teacher_headers):
        """POST /api/employees (director only) creates new employee; non-director gets 403"""
        # Teacher should get 403
        response = requests.post(f"{BASE_URL}/api/employees", 
            headers=teacher_headers,
            json={"full_name": "TEST_Teacher", "role": "Учитель", "subject": "Тест"})
        assert response.status_code == 403
        
        # Director should succeed
        response = requests.post(f"{BASE_URL}/api/employees",
            headers=director_headers,
            json={"full_name": "TEST_NewEmployee", "role": "Учитель", "subject": "Тестовый предмет"})
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "TEST_NewEmployee"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/employees/{data['id']}", headers=director_headers)


class TestIncidents:
    """Incidents CRUD tests"""
    
    def test_list_incidents(self, director_headers):
        """GET /api/incidents returns kanban list with assignee_name"""
        response = requests.get(f"{BASE_URL}/api/incidents", headers=director_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 13, f"Expected at least 13 incidents, got {len(data)}"
    
    def test_create_incident(self, director_headers):
        """POST /api/incidents creates new incident"""
        response = requests.post(f"{BASE_URL}/api/incidents",
            headers=director_headers,
            json={"title": "TEST_Incident", "description": "Test description", "priority": "high"})
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "TEST_Incident"
        assert data["status"] == "new"
        incident_id = data["id"]
        
        # Test status update
        response = requests.patch(f"{BASE_URL}/api/incidents/{incident_id}/status",
            headers=director_headers,
            json={"status": "in_progress"})
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"
        
        # Test assign
        response = requests.patch(f"{BASE_URL}/api/incidents/{incident_id}/assign",
            headers=director_headers,
            json={"assigned_to": 1})
        assert response.status_code == 200
        assert response.json()["assigned_to"] == 1


class TestTasks:
    """Tasks CRUD tests"""
    
    def test_list_tasks_director(self, director_headers):
        """GET /api/tasks without ?mine=true returns all for director"""
        response = requests.get(f"{BASE_URL}/api/tasks", headers=director_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_list_tasks_mine(self, teacher_headers):
        """GET /api/tasks with ?mine=true filters for logged-in user"""
        response = requests.get(f"{BASE_URL}/api/tasks?mine=true", headers=teacher_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_and_update_task(self, director_headers):
        """POST /api/tasks creates task; PATCH status transitions"""
        # Create
        response = requests.post(f"{BASE_URL}/api/tasks",
            headers=director_headers,
            json={"title": "TEST_Task", "description": "Test task", "priority": "medium", "assigned_to": 1})
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "TEST_Task"
        assert data["status"] == "new"
        task_id = data["id"]
        
        # Update status: new -> in_progress
        response = requests.patch(f"{BASE_URL}/api/tasks/{task_id}/status",
            headers=director_headers,
            json={"status": "in_progress"})
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"
        
        # Update status: in_progress -> done
        response = requests.patch(f"{BASE_URL}/api/tasks/{task_id}/status",
            headers=director_headers,
            json={"status": "done"})
        assert response.status_code == 200
        assert response.json()["status"] == "done"


class TestCanteen:
    """Canteen endpoint tests"""
    
    def test_canteen_list(self, director_headers):
        """GET /api/canteen returns list"""
        response = requests.get(f"{BASE_URL}/api/canteen", headers=director_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_canteen_summary(self, director_headers):
        """GET /api/canteen/summary returns today and by_day"""
        response = requests.get(f"{BASE_URL}/api/canteen/summary", headers=director_headers)
        assert response.status_code == 200
        data = response.json()
        assert "today" in data
        assert "by_day" in data
    
    def test_canteen_create(self, director_headers):
        """POST /api/canteen adds a record"""
        today = date.today().isoformat()
        response = requests.post(f"{BASE_URL}/api/canteen",
            headers=director_headers,
            json={"date": today, "class_name": "TEST_7A", "students_count": 25, "notes": "Test"})
        assert response.status_code == 200
        data = response.json()
        assert data["class_name"] == "TEST_7A"
        assert data["students_count"] == 25


class TestSchedule:
    """Schedule endpoint tests"""
    
    def test_schedule_list(self, director_headers):
        """GET /api/schedule returns schedule entries"""
        response = requests.get(f"{BASE_URL}/api/schedule", headers=director_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 58, f"Expected at least 58 schedule entries, got {len(data)}"
    
    def test_schedule_filter_by_class(self, director_headers):
        """GET /api/schedule filters by class_name - 7A has ~30 lessons"""
        response = requests.get(f"{BASE_URL}/api/schedule?class_name=7A", headers=director_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # 7A should have around 30 lessons
        assert len(data) >= 25, f"Expected ~30 lessons for 7A, got {len(data)}"
    
    def test_schedule_create_conflict_detection(self, director_headers):
        """POST /api/schedule detects conflicts (same teacher or room at same day+time) returns 409"""
        # First create a schedule entry
        response = requests.post(f"{BASE_URL}/api/schedule",
            headers=director_headers,
            json={
                "teacher_id": 1,
                "class_name": "TEST_CLASS",
                "day_of_week": "Суббота",  # Use Saturday to avoid conflicts with existing
                "lesson_time": "14:00",
                "room": "TEST_ROOM"
            })
        assert response.status_code == 200
        first_id = response.json()["id"]
        
        # Try to create conflicting entry (same teacher, same time)
        response = requests.post(f"{BASE_URL}/api/schedule",
            headers=director_headers,
            json={
                "teacher_id": 1,
                "class_name": "TEST_CLASS2",
                "day_of_week": "Суббота",
                "lesson_time": "14:00",
                "room": "TEST_ROOM2"
            })
        assert response.status_code == 409, f"Expected 409 conflict, got {response.status_code}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/schedule/{first_id}", headers=director_headers)
    
    def test_schedule_create_delete_director_only(self, director_headers, teacher_headers):
        """POST /api/schedule DELETE /api/schedule/{id} require director role"""
        # Teacher should get 403 on create
        response = requests.post(f"{BASE_URL}/api/schedule",
            headers=teacher_headers,
            json={
                "teacher_id": 1,
                "class_name": "TEST",
                "day_of_week": "Воскресенье",
                "lesson_time": "15:00",
                "room": "999"
            })
        assert response.status_code == 403
        
        # Director can create
        response = requests.post(f"{BASE_URL}/api/schedule",
            headers=director_headers,
            json={
                "teacher_id": 1,
                "class_name": "TEST_DELETE",
                "day_of_week": "Воскресенье",
                "lesson_time": "15:00",
                "room": "999"
            })
        assert response.status_code == 200
        schedule_id = response.json()["id"]
        
        # Teacher should get 403 on delete
        response = requests.delete(f"{BASE_URL}/api/schedule/{schedule_id}", headers=teacher_headers)
        assert response.status_code == 403
        
        # Director can delete
        response = requests.delete(f"{BASE_URL}/api/schedule/{schedule_id}", headers=director_headers)
        assert response.status_code == 200


class TestAIScheduleGenerator:
    """AI Schedule Generator tests (greedy algorithm, not LLM)"""
    
    def test_generate_schedule(self, director_headers):
        """POST /api/ai/schedule/generate returns {schedule, conflicts}"""
        response = requests.post(f"{BASE_URL}/api/ai/schedule/generate",
            headers=director_headers,
            json={
                "classes": [{"class_name": "TEST", "subjects": [{"subject": "Алгебра", "hours": 2}]}],
                "rooms": ["101", "102"],
                "replace": False
            })
        assert response.status_code == 200
        data = response.json()
        assert "schedule" in data
        assert "conflicts" in data
        assert isinstance(data["schedule"], list)


class TestAISubstitute:
    """AI Substitution tests"""
    
    def test_substitute_teacher(self, director_headers):
        """POST /api/ai/substitute returns {absent_teacher, suggestions}"""
        # Get a teacher with schedule
        schedule_resp = requests.get(f"{BASE_URL}/api/schedule", headers=director_headers)
        schedule = schedule_resp.json()
        if not schedule:
            pytest.skip("No schedule entries to test substitution")
        
        teacher_id = schedule[0]["teacher_id"]
        today = date.today().isoformat()
        
        response = requests.post(f"{BASE_URL}/api/ai/substitute",
            headers=director_headers,
            json={
                "teacher_id": teacher_id,
                "date": today,
                "reason": "Болезнь"
            })
        assert response.status_code == 200
        data = response.json()
        assert "absent_teacher" in data
        assert "suggestions" in data


class TestAIVoiceParse:
    """AI Voice-to-Task tests"""
    
    def test_voice_parse(self, director_headers):
        """POST /api/ai/voice/parse with text returns {parsed, created}"""
        response = requests.post(f"{BASE_URL}/api/ai/voice/parse",
            headers=director_headers,
            json={"text": "Марат, почини парту. Айгерим, подготовь зал."},
            timeout=60)  # AI calls may take time
        # Note: This calls Groq API, may fail with 429 rate limit
        if response.status_code == 500 and "Groq" in response.text:
            pytest.skip("Groq API rate limit or error - AI external dependency")
        assert response.status_code == 200
        data = response.json()
        assert "parsed" in data
        assert "created" in data


class TestAIOrdersSimplify:
    """AI Orders RAG tests"""
    
    def test_orders_simplify(self, director_headers):
        """POST /api/ai/orders/simplify with {text, mode:'simplify'} returns {result}"""
        response = requests.post(f"{BASE_URL}/api/ai/orders/simplify",
            headers=director_headers,
            json={
                "text": "Приказ о проведении влажной уборки в помещениях школы.",
                "mode": "simplify"
            },
            timeout=60)
        # Note: This calls Groq API
        if response.status_code == 500 and "Groq" in response.text:
            pytest.skip("Groq API rate limit or error - AI external dependency")
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert len(data["result"]) > 0


class TestClasses:
    """Classes endpoint tests"""
    
    def test_list_classes(self, director_headers):
        """GET /api/classes returns distinct class names"""
        response = requests.get(f"{BASE_URL}/api/classes", headers=director_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestMessages:
    """Messages feed tests"""
    
    def test_messages_feed(self, director_headers):
        """GET /api/messages returns messages from bot"""
        response = requests.get(f"{BASE_URL}/api/messages", headers=director_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have 54 messages from bot
        assert len(data) >= 50, f"Expected ~54 messages, got {len(data)}"


class TestSubstitutions:
    """Substitutions endpoint tests"""
    
    def test_list_substitutions(self, director_headers):
        """GET /api/substitutions returns list"""
        response = requests.get(f"{BASE_URL}/api/substitutions", headers=director_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
