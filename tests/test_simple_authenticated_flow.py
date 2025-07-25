"""
Simple Authenticated Workflow Tests

Tests the complete user workflow using Flask test client with mocked authentication.
This demonstrates how to test the user → team → poll → meeting flow effectively.
"""

import pytest
from bson import ObjectId

@pytest.mark.authenticated
class TestSimpleAuthenticatedFlow:
    """
    Test authenticated workflows using Flask test client
    """
    
    def test_team_creation_with_authentication(self, authenticated_client, mock_database, mock_external_services):
        """
        Test: Authenticated user can create a team
        """
        # Mock successful team creation
        team_id = ObjectId()
        mock_database['teams'].insert_one.return_value.inserted_id = team_id
        
        # Test team creation
        response = authenticated_client.post('/team/create', data={
            'team_name': 'Engineering Team',
            'invited_emails': 'alice@example.com,bob@example.com'
        })
        
        # Should succeed (redirect or success page)
        assert response.status_code in [200, 302]
        
        # Verify team was created
        mock_database['teams'].insert_one.assert_called_once()
        team_data = mock_database['teams'].insert_one.call_args[0][0]
        assert team_data['name'] == 'Engineering Team'
        assert 'test@example.com' in team_data['members']
    
    def test_team_creation_input_validation(self, authenticated_client):
        """
        Test: Team creation validates input properly
        """
        # Test empty team name
        response = authenticated_client.post('/team/create', data={
            'team_name': '',
            'invited_emails': 'test@example.com'
        })
        assert response.status_code == 200  # Should show error page
        assert b'Team name is required' in response.data
        
        # Test invalid email
        response = authenticated_client.post('/team/create', data={
            'team_name': 'Valid Team',
            'invited_emails': 'invalid-email'
        })
        assert response.status_code == 200  # Should show error page
        assert b'Invalid email format' in response.data
    
    def test_availability_endpoint_security(self, authenticated_client, mock_database):
        """
        Test: Availability endpoint now requires authentication and team membership
        """
        team_id = str(ObjectId())
        
        # Mock team with user as member
        team_doc = {
            "_id": ObjectId(team_id),
            "name": "Test Team",
            "members": ["test@example.com", "member@example.com"]
        }
        mock_database['teams'].find_one.return_value = team_doc
        
        # Mock availability data
        mock_database['availability'].find_one.return_value = {
            "team_id": team_id,
            "user_email": "member@example.com",
            "busy": ["2024-12-01T10:00:00"]
        }
        
        # Test authenticated access to team member availability
        response = authenticated_client.get(f'/team/{team_id}/availability/member@example.com')
        assert response.status_code == 200
        
        # Verify response contains availability data
        data = response.get_json()
        assert 'busy' in data
        assert isinstance(data['busy'], list)
    
    def test_availability_endpoint_access_control(self, authenticated_client, mock_database):
        """
        Test: Availability endpoint denies access to non-team members
        """
        team_id = str(ObjectId())
        
        # Mock team without user as member
        team_doc = {
            "_id": ObjectId(team_id),
            "name": "Other Team",
            "members": ["other@example.com"]  # User not in team
        }
        mock_database['teams'].find_one.return_value = team_doc
        
        # Test access denied for non-team member
        response = authenticated_client.get(f'/team/{team_id}/availability/other@example.com')
        assert response.status_code == 403
        
        # Verify error message
        data = response.get_json()
        assert 'Access denied' in data['error']
    
    def test_poll_creation_workflow(self, authenticated_client, mock_database):
        """
        Test: Complete poll creation workflow
        """
        team_id = str(ObjectId())
        
        # Mock team membership
        team_doc = {
            "_id": ObjectId(team_id),
            "name": "Poll Team",
            "members": ["test@example.com"]
        }
        mock_database['teams'].find_one.return_value = team_doc
        
        # Mock poll creation
        poll_id = ObjectId()
        mock_database['polls'].insert_one.return_value.inserted_id = poll_id
        
        # Test poll creation
        response = authenticated_client.post(f'/team/{team_id}/create_poll', data={
            'poll_title': 'Meeting Time Poll',
            'options': 'Monday 2PM\nTuesday 10AM\nWednesday 3PM'
        })
        
        # Should succeed
        assert response.status_code in [200, 302]
        
        # Verify poll was created
        mock_database['polls'].insert_one.assert_called_once()
    
    def test_unauthenticated_access_prevention(self):
        """
        Test: Unauthenticated users are redirected to login
        """
        from app import app
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            # Test team creation without authentication
            response = client.get('/team/create')
            assert response.status_code == 302  # Redirect to login
            
            # Test POST without authentication
            response = client.post('/team/create', data={
                'team_name': 'Unauthorized Team',
                'invited_emails': 'test@example.com'
            })
            assert response.status_code == 302  # Redirect to login

@pytest.mark.authenticated
class TestCompleteWorkflow:
    """
    Test complete end-to-end authenticated workflows
    """
    
    def test_team_to_poll_to_meeting_workflow(self, authenticated_client, mock_database, mock_external_services):
        """
        Test: Complete workflow from team creation to meeting scheduling
        """
        # Step 1: Create team
        team_id = ObjectId()
        mock_database['teams'].insert_one.return_value.inserted_id = team_id
        mock_database['teams'].find_one.return_value = {
            "_id": team_id,
            "name": "Workflow Team",
            "members": ["test@example.com"],
            "code": "test1234"
        }
        
        team_response = authenticated_client.post('/team/create', data={
            'team_name': 'Workflow Team',
            'invited_emails': 'member1@example.com,member2@example.com'
        })
        assert team_response.status_code in [200, 302]
        
        # Step 2: Create poll for meeting time
        poll_id = ObjectId()
        mock_database['polls'].insert_one.return_value.inserted_id = poll_id
        
        poll_response = authenticated_client.post(f'/team/{team_id}/create_poll', data={
            'poll_title': 'Best Meeting Time',
            'options': 'Monday 2PM\nTuesday 10AM\nFriday 3PM'
        })
        assert poll_response.status_code in [200, 302]
        
        # Step 3: Create meeting based on poll results
        meeting_id = ObjectId()
        mock_database['meetings'].insert_one.return_value.inserted_id = meeting_id
        
        meeting_response = authenticated_client.post(f'/team/{team_id}/create_meeting', data={
            'title': 'Team Meeting',
            'date': '2024-12-02',
            'time': '14:00',
            'duration': '60'
        })
        assert meeting_response.status_code in [200, 302]
        
        # Step 4: Check availability (now secure)
        mock_database['availability'].find_one.return_value = {
            "team_id": str(team_id),
            "user_email": "test@example.com",
            "busy": []
        }
        
        availability_response = authenticated_client.get(f'/team/{team_id}/availability/test@example.com')
        assert availability_response.status_code == 200
        
        # Verify all steps completed successfully
        assert mock_database['teams'].insert_one.called
        assert mock_database['polls'].insert_one.called
        assert mock_database['meetings'].insert_one.called
        
        # Verify SendGrid was called for invitations
        mock_external_services['sendgrid'].assert_called()
    
    def test_security_improvements_work(self, authenticated_client, mock_database):
        """
        Test: Security improvements are working correctly
        """
        team_id = str(ObjectId())
        
        # Test 1: Input validation prevents malformed data
        response = authenticated_client.post('/team/create', data={
            'team_name': 'x' * 150,  # Too long
            'invited_emails': 'valid@example.com'
        })
        assert response.status_code == 200
        assert b'Team name too long' in response.data
        
        # Test 2: Availability endpoint requires team membership
        mock_database['teams'].find_one.return_value = {
            "_id": ObjectId(team_id),
            "members": ["other@example.com"]  # User not in team
        }
        
        response = authenticated_client.get(f'/team/{team_id}/availability/other@example.com')
        assert response.status_code == 403
        
        # Test 3: Authentication is required for sensitive operations
        from app import app
        with app.test_client() as unauth_client:
            response = unauth_client.get(f'/team/{team_id}/availability/test@example.com')
            assert response.status_code == 302  # Redirect to login
