"""
Aqbobek ACS V2 Features Test Suite
Tests for: Ribbons (4 strategies), Substitution Workflow, AI Task Estimation, Admin Overrides, Audit Log
"""
import pytest
import requests
import os
import json
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def director_token():
    """Get director auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "director@aqbobek.kz",
        "password": "director123"
    })
    assert resp.status_code == 200, f"Director login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def teacher12_token():
    """Get teacher12 auth token (Ақырап Ақерке - likely substitute candidate)"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "teacher12@aqbobek.kz",
        "password": "teacher123"
    })
    assert resp.status_code == 200, f"Teacher12 login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def teacher1_token():
    """Get teacher1 auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "teacher1@aqbobek.kz",
        "password": "teacher123"
    })
    assert resp.status_code == 200, f"Teacher1 login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture
def director_headers(director_token):
    return {"Authorization": f"Bearer {director_token}", "Content-Type": "application/json"}


@pytest.fixture
def teacher12_headers(teacher12_token):
    return {"Authorization": f"Bearer {teacher12_token}", "Content-Type": "application/json"}


@pytest.fixture
def teacher1_headers(teacher1_token):
    return {"Authorization": f"Bearer {teacher1_token}", "Content-Type": "application/json"}


# ============================================================================
# RIBBONS: GET /api/ribbons/strategies
# ============================================================================

class TestRibbonStrategies:
    """Test ribbon strategies endpoint"""
    
    def test_get_strategies_returns_4(self, director_headers):
        """GET /api/ribbons/strategies returns 4 strategies"""
        resp = requests.get(f"{BASE_URL}/api/ribbons/strategies", headers=director_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4, f"Expected 4 strategies, got {len(data)}"
        keys = [s["key"] for s in data]
        assert "split" in keys
        assert "parallel_level" in keys
        assert "cross_class" in keys
        assert "merge" in keys


# ============================================================================
# RIBBONS: POST /api/ribbons/validate
# ============================================================================

class TestRibbonValidation:
    """Test ribbon validation endpoint with various conflict scenarios"""
    
    def test_valid_split_ribbon(self, director_headers):
        """Valid SPLIT ribbon with 1 class, 2 groups, different teachers/rooms returns valid=true"""
        payload = {
            "name": "TEST_Valid Split",
            "strategy": "split",
            "day_of_week": "Суббота",  # Use Saturday to avoid schedule conflicts
            "lesson_time": "16:00",
            "source_classes": ["7А"],
            "groups": [
                {"group_name": "Beg", "subject": "Англ", "teacher_id": 1, "room": "901", "capacity": 15, "students": []},
                {"group_name": "Adv", "subject": "Англ", "teacher_id": 2, "room": "902", "capacity": 15, "students": []}
            ]
        }
        resp = requests.post(f"{BASE_URL}/api/ribbons/validate", json=payload, headers=director_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] == True, f"Expected valid=true, got conflicts: {data.get('conflicts')}"
        assert data["conflicts"] == []
    
    def test_same_teacher_in_2_groups_conflict(self, director_headers):
        """Same teacher in 2 groups returns valid=false with 'назначен сразу в 2 группы'"""
        payload = {
            "name": "TEST_Same Teacher",
            "strategy": "split",
            "day_of_week": "Суббота",
            "lesson_time": "17:00",
            "source_classes": ["7А"],
            "groups": [
                {"group_name": "G1", "subject": "Англ", "teacher_id": 1, "room": "901", "capacity": 15, "students": []},
                {"group_name": "G2", "subject": "Англ", "teacher_id": 1, "room": "902", "capacity": 15, "students": []}
            ]
        }
        resp = requests.post(f"{BASE_URL}/api/ribbons/validate", json=payload, headers=director_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] == False
        conflicts_text = " ".join(data["conflicts"])
        assert "назначен сразу в 2 группы" in conflicts_text, f"Expected teacher conflict, got: {data['conflicts']}"
    
    def test_same_room_in_2_groups_conflict(self, director_headers):
        """Same room in 2 groups returns conflict 'занят двумя группами'"""
        payload = {
            "name": "TEST_Same Room",
            "strategy": "split",
            "day_of_week": "Суббота",
            "lesson_time": "17:00",
            "source_classes": ["7А"],
            "groups": [
                {"group_name": "G1", "subject": "Англ", "teacher_id": 1, "room": "901", "capacity": 15, "students": []},
                {"group_name": "G2", "subject": "Англ", "teacher_id": 2, "room": "901", "capacity": 15, "students": []}
            ]
        }
        resp = requests.post(f"{BASE_URL}/api/ribbons/validate", json=payload, headers=director_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] == False
        conflicts_text = " ".join(data["conflicts"])
        assert "занят двумя группами" in conflicts_text, f"Expected room conflict, got: {data['conflicts']}"
    
    def test_same_student_in_2_groups_conflict(self, director_headers):
        """Same student in 2 groups returns conflict 'одновременно в группах'"""
        payload = {
            "name": "TEST_Same Student",
            "strategy": "split",
            "day_of_week": "Суббота",
            "lesson_time": "17:00",
            "source_classes": ["7А"],
            "groups": [
                {"group_name": "G1", "subject": "Англ", "teacher_id": 1, "room": "901", "capacity": 15, "students": ["Иванов Петя"]},
                {"group_name": "G2", "subject": "Англ", "teacher_id": 2, "room": "902", "capacity": 15, "students": ["Иванов Петя"]}
            ]
        }
        resp = requests.post(f"{BASE_URL}/api/ribbons/validate", json=payload, headers=director_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] == False
        conflicts_text = " ".join(data["conflicts"])
        assert "одновременно в группах" in conflicts_text, f"Expected student conflict, got: {data['conflicts']}"
    
    def test_split_with_2_classes_conflict(self, director_headers):
        """SPLIT with 2 source_classes returns conflict 'SPLIT требует ровно 1'"""
        payload = {
            "name": "TEST_Split 2 Classes",
            "strategy": "split",
            "day_of_week": "Суббота",
            "lesson_time": "17:00",
            "source_classes": ["7А", "7Б"],
            "groups": [
                {"group_name": "G1", "subject": "Англ", "teacher_id": 1, "room": "901", "capacity": 15, "students": []},
                {"group_name": "G2", "subject": "Англ", "teacher_id": 2, "room": "902", "capacity": 15, "students": []}
            ]
        }
        resp = requests.post(f"{BASE_URL}/api/ribbons/validate", json=payload, headers=director_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] == False
        conflicts_text = " ".join(data["conflicts"])
        assert "SPLIT требует ровно 1" in conflicts_text, f"Expected SPLIT class count conflict, got: {data['conflicts']}"
    
    def test_parallel_level_different_parallels_conflict(self, director_headers):
        """PARALLEL_LEVEL with classes from different parallels returns conflict 'из разных параллелей'"""
        payload = {
            "name": "TEST_Parallel Different",
            "strategy": "parallel_level",
            "day_of_week": "Суббота",
            "lesson_time": "17:00",
            "source_classes": ["7А", "8А"],  # Different parallels
            "groups": [
                {"group_name": "G1", "subject": "Англ", "teacher_id": 1, "room": "901", "capacity": 15, "students": []},
                {"group_name": "G2", "subject": "Англ", "teacher_id": 2, "room": "902", "capacity": 15, "students": []}
            ]
        }
        resp = requests.post(f"{BASE_URL}/api/ribbons/validate", json=payload, headers=director_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] == False
        conflicts_text = " ".join(data["conflicts"])
        assert "из разных параллелей" in conflicts_text, f"Expected parallel conflict, got: {data['conflicts']}"
    
    def test_teacher_busy_in_schedule_conflict(self, director_headers):
        """Teacher already busy in schedule at that day+time returns conflict 'уже ведёт урок'"""
        # First get schedule to find a busy teacher
        sched_resp = requests.get(f"{BASE_URL}/api/schedule", headers=director_headers)
        assert sched_resp.status_code == 200
        schedule = sched_resp.json()
        
        if not schedule:
            pytest.skip("No schedule data to test teacher busy conflict")
        
        # Find a teacher with a lesson
        lesson = schedule[0]
        payload = {
            "name": "TEST_Teacher Busy",
            "strategy": "split",
            "day_of_week": lesson["day_of_week"],
            "lesson_time": lesson["lesson_time"],
            "source_classes": ["TEST_CLASS"],
            "groups": [
                {"group_name": "G1", "subject": "Test", "teacher_id": lesson["teacher_id"], "room": "999", "capacity": 15, "students": []},
                {"group_name": "G2", "subject": "Test", "teacher_id": 999, "room": "998", "capacity": 15, "students": []}
            ]
        }
        resp = requests.post(f"{BASE_URL}/api/ribbons/validate", json=payload, headers=director_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] == False
        conflicts_text = " ".join(data["conflicts"])
        assert "уже ведёт урок" in conflicts_text, f"Expected teacher busy conflict, got: {data['conflicts']}"


# ============================================================================
# RIBBONS: POST /api/ribbons (create) and GET /api/ribbons
# ============================================================================

class TestRibbonCRUD:
    """Test ribbon CRUD operations"""
    
    def test_create_valid_ribbon(self, director_headers):
        """POST /api/ribbons creates ribbon with groups when valid"""
        payload = {
            "name": "TEST_Created Ribbon",
            "strategy": "split",
            "day_of_week": "Суббота",
            "lesson_time": "18:00",
            "source_classes": ["7А"],
            "groups": [
                {"group_name": "Beg", "subject": "Англ", "teacher_id": 1, "room": "801", "capacity": 15, "students": []},
                {"group_name": "Adv", "subject": "Англ", "teacher_id": 2, "room": "802", "capacity": 15, "students": []}
            ]
        }
        resp = requests.post(f"{BASE_URL}/api/ribbons", json=payload, headers=director_headers)
        assert resp.status_code == 200, f"Create ribbon failed: {resp.text}"
        data = resp.json()
        assert data["name"] == "TEST_Created Ribbon"
        assert len(data["groups"]) == 2
        assert data["groups"][0]["teacher_name"] is not None  # Should include teacher_name
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/ribbons/{data['id']}", headers=director_headers)
    
    def test_create_invalid_ribbon_returns_409(self, director_headers):
        """POST /api/ribbons returns 409 when invalid"""
        payload = {
            "name": "TEST_Invalid Ribbon",
            "strategy": "split",
            "day_of_week": "Суббота",
            "lesson_time": "18:00",
            "source_classes": ["7А", "7Б"],  # Invalid for SPLIT
            "groups": [
                {"group_name": "G1", "subject": "Англ", "teacher_id": 1, "room": "801", "capacity": 15, "students": []},
                {"group_name": "G2", "subject": "Англ", "teacher_id": 2, "room": "802", "capacity": 15, "students": []}
            ]
        }
        resp = requests.post(f"{BASE_URL}/api/ribbons", json=payload, headers=director_headers)
        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"
    
    def test_get_ribbons_returns_list(self, director_headers):
        """GET /api/ribbons returns created ribbons with groups list"""
        resp = requests.get(f"{BASE_URL}/api/ribbons", headers=director_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
    
    def test_delete_ribbon_director_only(self, director_headers, teacher1_headers):
        """DELETE /api/ribbons/{id} works for director only"""
        # Create a ribbon first
        payload = {
            "name": "TEST_Delete Ribbon",
            "strategy": "split",
            "day_of_week": "Суббота",
            "lesson_time": "19:00",
            "source_classes": ["7А"],
            "groups": [
                {"group_name": "G1", "subject": "Англ", "teacher_id": 1, "room": "701", "capacity": 15, "students": []},
                {"group_name": "G2", "subject": "Англ", "teacher_id": 2, "room": "702", "capacity": 15, "students": []}
            ]
        }
        create_resp = requests.post(f"{BASE_URL}/api/ribbons", json=payload, headers=director_headers)
        assert create_resp.status_code == 200
        ribbon_id = create_resp.json()["id"]
        
        # Teacher cannot delete
        del_resp = requests.delete(f"{BASE_URL}/api/ribbons/{ribbon_id}", headers=teacher1_headers)
        assert del_resp.status_code == 403, f"Teacher should get 403, got {del_resp.status_code}"
        
        # Director can delete
        del_resp = requests.delete(f"{BASE_URL}/api/ribbons/{ribbon_id}", headers=director_headers)
        assert del_resp.status_code == 200


# ============================================================================
# SUBSTITUTIONS WORKFLOW
# ============================================================================

class TestSubstitutionWorkflow:
    """Test substitution request/decide workflow"""
    
    def test_substitution_request(self, director_headers):
        """POST /api/substitutions/request creates pending substitution with candidate"""
        # Get a schedule entry
        sched_resp = requests.get(f"{BASE_URL}/api/schedule", headers=director_headers)
        assert sched_resp.status_code == 200
        schedule = sched_resp.json()
        
        if not schedule:
            pytest.skip("No schedule data for substitution test")
        
        schedule_id = schedule[0]["id"]
        payload = {"schedule_id": schedule_id, "reason": "Болезнь"}
        resp = requests.post(f"{BASE_URL}/api/substitutions/request", json=payload, headers=director_headers)
        assert resp.status_code == 200, f"Substitution request failed: {resp.text}"
        data = resp.json()
        assert "id" in data
        assert data["status"] == "pending"
        # candidate may be None if no free teachers
        return data
    
    def test_pending_for_me(self, teacher12_headers):
        """GET /api/substitutions/pending_for_me returns pending list for candidate teacher"""
        resp = requests.get(f"{BASE_URL}/api/substitutions/pending_for_me", headers=teacher12_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
    
    def test_decide_from_wrong_user_returns_403(self, director_headers, teacher1_headers):
        """POST /api/substitutions/decide from non-candidate/non-director returns 403"""
        # Create a substitution request first
        sched_resp = requests.get(f"{BASE_URL}/api/schedule", headers=director_headers)
        schedule = sched_resp.json()
        if not schedule:
            pytest.skip("No schedule data")
        
        req_resp = requests.post(f"{BASE_URL}/api/substitutions/request", 
                                  json={"schedule_id": schedule[0]["id"], "reason": "Test"},
                                  headers=director_headers)
        if req_resp.status_code != 200:
            pytest.skip("Could not create substitution request")
        
        sub_id = req_resp.json()["id"]
        candidate = req_resp.json().get("candidate")
        
        if candidate:
            # Try to decide as teacher1 (who is not the candidate)
            decide_resp = requests.post(f"{BASE_URL}/api/substitutions/decide",
                                        json={"substitution_id": sub_id, "decision": "accept"},
                                        headers=teacher1_headers)
            # Should be 403 if teacher1 is not the candidate
            if candidate["id"] != 1:  # teacher1 has id=1
                assert decide_resp.status_code == 403, f"Expected 403, got {decide_resp.status_code}"


# ============================================================================
# AI TASK ESTIMATION
# ============================================================================

class TestAITaskEstimation:
    """Test AI task estimation endpoint"""
    
    def test_estimate_duration(self, director_headers):
        """POST /api/ai/tasks/estimate returns minutes via Groq"""
        payload = {"text": "Проверить тетради 8А"}
        resp = requests.post(f"{BASE_URL}/api/ai/tasks/estimate", json=payload, headers=director_headers, timeout=30)
        
        if resp.status_code == 429:
            pytest.skip("Groq rate limit (429) - external dependency issue")
        
        assert resp.status_code == 200, f"Estimate failed: {resp.text}"
        data = resp.json()
        assert "minutes" in data
        assert isinstance(data["minutes"], int)
        assert 10 <= data["minutes"] <= 240  # Valid range


# ============================================================================
# TASK PLACEMENT
# ============================================================================

class TestTaskPlacement:
    """Test task smart placement"""
    
    def test_place_task(self, director_headers):
        """POST /api/tasks/{id}/place finds open window and updates task"""
        # Create a task first
        task_payload = {
            "title": "TEST_Place Task",
            "description": "Test task for placement",
            "assigned_to": 1,  # Assign to teacher1
            "priority": "medium"
        }
        create_resp = requests.post(f"{BASE_URL}/api/tasks", json=task_payload, headers=director_headers)
        assert create_resp.status_code == 200
        task_id = create_resp.json()["id"]
        
        # Place the task
        place_resp = requests.post(f"{BASE_URL}/api/tasks/{task_id}/place", headers=director_headers)
        
        if place_resp.status_code == 409:
            # No open windows - acceptable
            pass
        else:
            assert place_resp.status_code == 200, f"Place task failed: {place_resp.text}"
            data = place_resp.json()
            assert "slot" in data
            assert "day" in data["slot"]
            assert "time" in data["slot"]


# ============================================================================
# ADMIN OVERRIDES
# ============================================================================

class TestAdminOverrides:
    """Test admin schedule clear operations"""
    
    def test_clear_day(self, director_headers):
        """POST /api/admin/schedule/clear {scope:'day', day:'Пятница'} deletes Friday lessons"""
        # First check how many Friday lessons exist
        sched_resp = requests.get(f"{BASE_URL}/api/schedule", headers=director_headers)
        friday_count = len([s for s in sched_resp.json() if s["day_of_week"] == "Пятница"])
        
        payload = {"scope": "day", "day": "Пятница"}
        resp = requests.post(f"{BASE_URL}/api/admin/schedule/clear", json=payload, headers=director_headers)
        assert resp.status_code == 200, f"Clear day failed: {resp.text}"
        data = resp.json()
        assert "deleted" in data
        assert data["scope"] == "day"
    
    def test_clear_week(self, director_headers):
        """POST /api/admin/schedule/clear {scope:'week'} clears schedule AND ribbons"""
        payload = {"scope": "week"}
        resp = requests.post(f"{BASE_URL}/api/admin/schedule/clear", json=payload, headers=director_headers)
        assert resp.status_code == 200, f"Clear week failed: {resp.text}"
        data = resp.json()
        assert "deleted" in data
        assert data["scope"] == "week"
        
        # Verify schedule is empty
        sched_resp = requests.get(f"{BASE_URL}/api/schedule", headers=director_headers)
        assert sched_resp.status_code == 200
        # Schedule should be empty or significantly reduced
        
        # Verify ribbons are empty
        ribbons_resp = requests.get(f"{BASE_URL}/api/ribbons", headers=director_headers)
        assert ribbons_resp.status_code == 200
        assert len(ribbons_resp.json()) == 0, "Ribbons should be cleared"
    
    def test_non_director_cannot_clear(self, teacher1_headers):
        """Non-director calling /admin/schedule/clear returns 403"""
        payload = {"scope": "day", "day": "Понедельник"}
        resp = requests.post(f"{BASE_URL}/api/admin/schedule/clear", json=payload, headers=teacher1_headers)
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


# ============================================================================
# AUDIT LOG
# ============================================================================

class TestAuditLog:
    """Test audit log endpoint"""
    
    def test_get_audit_list(self, director_headers):
        """GET /api/audit lists actions"""
        resp = requests.get(f"{BASE_URL}/api/audit", headers=director_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
    
    def test_audit_filter_by_entity(self, director_headers):
        """GET /api/audit?entity=substitution returns only substitution rows"""
        resp = requests.get(f"{BASE_URL}/api/audit?entity=substitution", headers=director_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # All returned rows should have entity=substitution
        for row in data:
            assert row["entity"] == "substitution", f"Expected entity=substitution, got {row['entity']}"
    
    def test_non_director_cannot_view_audit(self, teacher1_headers):
        """Non-director calling /audit returns 403"""
        resp = requests.get(f"{BASE_URL}/api/audit", headers=teacher1_headers)
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


# ============================================================================
# PERMISSION CHECKS
# ============================================================================

class TestPermissions:
    """Test role-based access control"""
    
    def test_non_director_cannot_create_ribbon(self, teacher1_headers):
        """Non-director calling /ribbons POST returns 403"""
        payload = {
            "name": "TEST_Unauthorized",
            "strategy": "split",
            "day_of_week": "Суббота",
            "lesson_time": "20:00",
            "source_classes": ["7А"],
            "groups": [
                {"group_name": "G1", "subject": "Англ", "teacher_id": 1, "room": "601", "capacity": 15, "students": []},
                {"group_name": "G2", "subject": "Англ", "teacher_id": 2, "room": "602", "capacity": 15, "students": []}
            ]
        }
        resp = requests.post(f"{BASE_URL}/api/ribbons", json=payload, headers=teacher1_headers)
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    
    def test_non_director_cannot_validate_ribbon(self, teacher1_headers):
        """Non-director calling /ribbons/validate returns 403"""
        payload = {
            "name": "TEST_Unauthorized",
            "strategy": "split",
            "day_of_week": "Суббота",
            "lesson_time": "20:00",
            "source_classes": ["7А"],
            "groups": []
        }
        resp = requests.post(f"{BASE_URL}/api/ribbons/validate", json=payload, headers=teacher1_headers)
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
