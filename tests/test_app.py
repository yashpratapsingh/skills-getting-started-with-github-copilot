"""
FastAPI Backend Tests for Mergington High School Activities API

Tests cover all endpoints with happy paths and edge cases using pytest and the AAA (Arrange-Act-Assert) pattern.
Uses FastAPI's TestClient for integration testing.
"""

import copy
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Fixture: Returns a TestClient instance for making requests."""
    return TestClient(app)


@pytest.fixture
def fresh_activities():
    """
    Fixture: Returns a deep copy of activities for test isolation.
    
    Each test gets its own copy to prevent mutations from affecting other tests.
    This ensures tests are independent and repeatable.
    """
    return copy.deepcopy(activities)


@pytest.fixture
def mock_app_activities(fresh_activities, monkeypatch):
    """
    Fixture: Replaces the app's global activities with a fresh copy.
    
    Ensures each test starts with clean data. Uses monkeypatch to safely
    replace the app's activities dictionary without affecting the real one.
    """
    monkeypatch.setattr("src.app.activities", fresh_activities)
    return fresh_activities


# ============================================================================
# Tests for GET / (Root Redirect)
# ============================================================================

class TestRootRedirect:
    """Tests for GET / endpoint - should redirect to /static/index.html"""

    def test_root_redirects_to_index_html(self, client):
        """
        Arrange: Make a GET request to root endpoint
        Act: Verify the response
        Assert: Should redirect (status 307) to /static/index.html
        """
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


# ============================================================================
# Tests for GET /activities (List All Activities)
# ============================================================================

class TestGetActivities:
    """Tests for GET /activities endpoint - retrieves all activities"""

    def test_get_activities_returns_all_activities(self, client, mock_app_activities):
        """
        Arrange: Prepare fresh activities data
        Act: GET /activities
        Assert: Should return 200 with all activities
        """
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9  # 9 activities in the seed data
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Science Club" in data

    def test_get_activities_returns_activity_structure(self, client, mock_app_activities):
        """
        Arrange: Expected activity keys
        Act: GET /activities and inspect one activity
        Assert: Activity should have description, schedule, max_participants, participants
        """
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)

    def test_get_activities_shows_current_participants(self, client, mock_app_activities):
        """
        Arrange: Activities with existing participants
        Act: GET /activities
        Assert: Participants list should match seed data
        """
        response = client.get("/activities")
        data = response.json()
        
        # Chess Club has 2 seed participants
        assert len(data["Chess Club"]["participants"]) == 2
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]


# ============================================================================
# Tests for POST /activities/{activity_name}/signup (Register for Activity)
# ============================================================================

class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_successful(self, client, mock_app_activities):
        """
        Arrange: Valid activity name and new email
        Act: POST signup request
        Assert: Should return 200 and add participant to activity
        """
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        assert "Signed up newstudent@mergington.edu" in response.json()["message"]
        
        # Verify participant was actually added
        activities_check = client.get("/activities").json()
        assert "newstudent@mergington.edu" in activities_check["Chess Club"]["participants"]

    def test_signup_duplicate_email_returns_400(self, client, mock_app_activities):
        """
        Arrange: Email already signed up for this activity (michael@mergington.edu for Chess Club)
        Act: Try to sign up with same email again
        Assert: Should return 400 with error message
        """
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_invalid_activity_returns_404(self, client, mock_app_activities):
        """
        Arrange: Activity name that doesn't exist
        Act: POST signup for non-existent activity
        Assert: Should return 404 with "Activity not found"
        """
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_multiple_different_activities(self, client, mock_app_activities):
        """
        Arrange: Same email, different activities
        Act: Sign up for multiple activities
        Assert: Email should appear in all activity participant lists
        """
        email = "versatile@mergington.edu"
        
        # Sign up for Chess Club
        response1 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Sign up for Programming Class
        response2 = client.post(f"/activities/Programming Class/signup?email={email}")
        assert response2.status_code == 200
        
        # Verify in both
        activities_check = client.get("/activities").json()
        assert email in activities_check["Chess Club"]["participants"]
        assert email in activities_check["Programming Class"]["participants"]

    def test_signup_email_case_sensitive(self, client, mock_app_activities):
        """
        Arrange: Same email with different case (Michael@mergington.edu vs michael@mergington.edu)
        Act: Try to sign up with different case of already-registered email
        Assert: Should treat as different email and allow signup (case-sensitive)
        """
        # michael@mergington.edu is already in Chess Club
        response = client.post(
            "/activities/Chess Club/signup?email=Michael@mergington.edu"
        )
        # Will succeed because email comparison is case-sensitive
        assert response.status_code == 200
        
        activities_check = client.get("/activities").json()
        assert "michael@mergington.edu" in activities_check["Chess Club"]["participants"]
        assert "Michael@mergington.edu" in activities_check["Chess Club"]["participants"]


# ============================================================================
# Tests for DELETE /activities/{activity_name}/signup (Unregister from Activity)
# ============================================================================

class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/signup endpoint"""

    def test_unregister_successful(self, client, mock_app_activities):
        """
        Arrange: Existing participant (michael@mergington.edu in Chess Club)
        Act: DELETE signup request
        Assert: Should return 200 and remove participant
        """
        response = client.delete(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        assert "Unregistered michael@mergington.edu" in response.json()["message"]
        
        # Verify participant was actually removed
        activities_check = client.get("/activities").json()
        assert "michael@mergington.edu" not in activities_check["Chess Club"]["participants"]

    def test_unregister_nonexistent_participant_returns_400(self, client, mock_app_activities):
        """
        Arrange: Email that's not signed up for this activity
        Act: Try to unregister non-existent participant
        Assert: Should return 400 with error message
        """
        response = client.delete(
            "/activities/Chess Club/signup?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_unregister_invalid_activity_returns_404(self, client, mock_app_activities):
        """
        Arrange: Activity name that doesn't exist
        Act: DELETE signup from non-existent activity
        Assert: Should return 404 with error message
        """
        response = client.delete(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_then_can_signup_again(self, client, mock_app_activities):
        """
        Arrange: Registered participant
        Act: Unregister then re-register
        Assert: Should be able to sign up again after unregistering
        """
        email = "michael@mergington.edu"
        activity = "Chess Club"
        
        # Unregister
        response1 = client.delete(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200
        
        # Sign up again
        response2 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response2.status_code == 200
        
        # Verify in activity
        activities_check = client.get("/activities").json()
        assert email in activities_check[activity]["participants"]

    def test_unregister_multiple_participants(self, client, mock_app_activities):
        """
        Arrange: Activity with multiple participants
        Act: Unregister one participant
        Assert: Other participants should remain
        """
        activity = "Chess Club"
        email_to_remove = "michael@mergington.edu"
        email_to_keep = "daniel@mergington.edu"
        
        # Unregister one
        response = client.delete(
            f"/activities/{activity}/signup?email={email_to_remove}"
        )
        assert response.status_code == 200
        
        # Check that removed one is gone, other remains
        activities_check = client.get("/activities").json()
        assert email_to_remove not in activities_check[activity]["participants"]
        assert email_to_keep in activities_check[activity]["participants"]


# ============================================================================
# Integration Tests (Multi-step Workflows)
# ============================================================================

class TestSignupUnregisterWorkflow:
    """Integration tests for signup and unregister workflows"""

    def test_signup_unregister_signup_workflow(self, client, mock_app_activities):
        """
        Arrange: Fresh activities
        Act: Sign up → Unregister → Sign up again
        Assert: Each step should work correctly
        """
        email = "workflow@mergington.edu"
        activity = "Debate Team"
        
        # Step 1: Sign up
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200
        
        check1 = client.get("/activities").json()
        assert email in check1[activity]["participants"]
        initial_count = len(check1[activity]["participants"])
        
        # Step 2: Unregister
        response2 = client.delete(f"/activities/{activity}/signup?email={email}")
        assert response2.status_code == 200
        
        check2 = client.get("/activities").json()
        assert email not in check2[activity]["participants"]
        assert len(check2[activity]["participants"]) == initial_count - 1
        
        # Step 3: Sign up again
        response3 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response3.status_code == 200
        
        check3 = client.get("/activities").json()
        assert email in check3[activity]["participants"]
        assert len(check3[activity]["participants"]) == initial_count
