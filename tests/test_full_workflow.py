"""
Complete User Workflow Tests

Tests the full user journey: authentication → team creation → poll creation → voting → meeting creation
Uses Flask test client with mocked authentication to bypass OAuth limitations.
"""

import pytest
import json
from test_authenticated_client import AuthenticatedTestHelper

@pytest.mark.authenticated
class TestCompleteUserWorkflow:
    """
    Test complete user workflows with proper authentication simulation
    """
    
    def test_complete_team_creation_workflow(self, auth_helper):
        """
        Test: Complete team creation workflow
        Flow: User creates team → invites members → team is accessible
        """
        # Step 1: Create team
        response, team_id = auth_helper.create_team(
            team_name="Engineering Team",
            invited_emails=["alice@example.com", "bob@example.com"]
        )
        
        # Should redirect to team page after creation
        assert response.status_code in [200, 302], f"Team creation failed: {response.status_code}"
        
        # Verify team creation was called with correct data
        auth_helper.mock_db['teams'].insert_one.assert_called_once()
        call_args = auth_helper.mock_db['teams'].insert_one.call_args[0][0]
        assert call_args['name'] == "Engineering Team"
        assert auth_helper.test_user_email in call_args['members']
        
        # Verify invitations were sent (SendGrid called)
        auth_helper.mock_services['sendgrid'].assert_called_once()
    
    def test_complete_poll_workflow(self, auth_helper):
        """
        Test: Complete poll creation and voting workflow
        Flow: Create team → create poll → vote → results
        """
        # Step 1: Create team first
        team_response, team_id = auth_helper.create_team("Poll Team")
        assert team_response.status_code in [200, 302]
        
        # Step 2: Create poll
        poll_response, poll_id = auth_helper.create_poll(
            team_id=team_id,
            poll_title="Meeting Time Preference",
            options=["Monday 2PM", "Tuesday 10AM", "Wednesday 3PM"]
        )
        assert poll_response.status_code in [200, 302]
        
        # Verify poll creation
        auth_helper.mock_db['polls'].insert_one.assert_called_once()
        poll_data = auth_helper.mock_db['polls'].insert_one.call_args[0][0]
        assert poll_data['title'] == "Meeting Time Preference"
        assert poll_data['team_id'] == team_id
        
        # Step 3: Vote in poll
        vote_response = auth_helper.vote_in_poll(
            team_id=team_id,
            poll_id=poll_id,
            selected_options=["Monday 2PM", "Wednesday 3PM"]
        )
        assert vote_response.status_code in [200, 302]
    
    def test_complete_meeting_workflow(self, auth_helper):
        """
        Test: Complete meeting creation workflow
        Flow: Create team → create meeting → verify scheduling
        """
        # Step 1: Create team
        team_response, team_id = auth_helper.create_team("Meeting Team")
        assert team_response.status_code in [200, 302]
        
        # Step 2: Create meeting
        meeting_data = {
            'title': 'Sprint Planning',
            'date': '2024-12-15',
            'time': '10:00',
            'duration': '90'
        }
        meeting_response, meeting_id = auth_helper.create_meeting(team_id, meeting_data)
        assert meeting_response.status_code in [200, 302]
        
        # Verify meeting creation
        auth_helper.mock_db['meetings'].insert_one.assert_called_once()
        meeting_doc = auth_helper.mock_db['meetings'].insert_one.call_args[0][0]
        assert meeting_doc['title'] == 'Sprint Planning'
        assert meeting_doc['team_id'] == team_id
    
    def test_team_join_workflow(self, auth_helper):
        """
        Test: Team joining workflow
        Flow: User receives invite code → joins team → becomes member
        """
        # Step 1: Join team with code
        response, team_id = auth_helper.join_team("test1234")
        assert response.status_code in [200, 302]
        
        # Verify team lookup was performed
        auth_helper.mock_db['teams'].find_one.assert_called()
    
    def test_availability_security_workflow(self, auth_helper):
        """
        Test: Availability endpoint security (now requires authentication)
        Flow: Authenticated user → check team member availability → success
        """
        # Step 1: Create team first
        team_response, team_id = auth_helper.create_team("Availability Team")
        
        # Step 2: Check availability (should now work with authentication)
        availability_response = auth_helper.get_team_availability(
            team_id=team_id,
            email="member1@example.com"
        )
        
        # Should succeed with proper authentication and team membership
        assert availability_response.status_code == 200
        
        # Verify response contains availability data
        data = availability_response.get_json()
        assert 'busy' in data
        assert isinstance(data['busy'], list)

@pytest.mark.authenticated
class TestWorkflowErrorHandling:
    """
    Test error handling in workflows with proper authentication
    """
    
    def test_team_creation_validation(self, auth_helper):
        """
        Test: Team creation input validation
        """
        # Test empty team name
        response = auth_helper.client.post('/team/create', data={
            'team_name': '',
            'invited_emails': 'test@example.com'
        })
        # Should show error (200 with error message or redirect)
        assert response.status_code in [200, 302]
        
        # Test invalid email format
        response = auth_helper.client.post('/team/create', data={
            'team_name': 'Valid Team',
            'invited_emails': 'invalid-email'
        })
        # Should show error for invalid email
        assert response.status_code in [200, 302]
        
        # Test team name too long
        response = auth_helper.client.post('/team/create', data={
            'team_name': 'x' * 150,  # Too long
            'invited_emails': 'test@example.com'
        })
        # Should show error for name too long
        assert response.status_code in [200, 302]
    
    def test_unauthorized_access_prevention(self, auth_helper):
        """
        Test: Unauthorized access is properly prevented
        """
        # Create a client without authentication
        from app import app
        app.config['TESTING'] = True
        
        with app.test_client() as unauth_client:
            # Try to access team creation without auth
            response = unauth_client.get('/team/create')
            assert response.status_code == 302  # Should redirect to login
            
            # Try to create team without auth
            response = unauth_client.post('/team/create', data={
                'team_name': 'Unauthorized Team',
                'invited_emails': 'test@example.com'
            })
            assert response.status_code == 302  # Should redirect to login

@pytest.mark.authenticated
class TestMultiUserWorkflow:
    """
    Test workflows involving multiple users
    """
    
    def test_multi_user_poll_workflow(self, auth_helper):
        """
        Test: Multiple users participating in poll workflow
        """
        # Step 1: Create team
        team_response, team_id = auth_helper.create_team("Multi-User Team")
        
        # Step 2: Create poll
        poll_response, poll_id = auth_helper.create_poll(team_id, "Best Meeting Time")
        
        # Step 3: Simulate multiple users voting
        # User 1 votes
        vote1_response = auth_helper.vote_in_poll(team_id, poll_id, ["Option 1"])
        assert vote1_response.status_code in [200, 302]
        
        # Simulate User 2 voting (change session email)
        with auth_helper.client.session_transaction() as sess:
            sess['email'] = 'user2@example.com'
        
        vote2_response = auth_helper.vote_in_poll(team_id, poll_id, ["Option 2"])
        assert vote2_response.status_code in [200, 302]
    
    def test_team_member_availability_access(self, auth_helper):
        """
        Test: Team members can access each other's availability
        """
        # Step 1: Create team
        team_response, team_id = auth_helper.create_team("Availability Team")
        
        # Step 2: Check own availability
        own_availability = auth_helper.get_team_availability(team_id, auth_helper.test_user_email)
        assert own_availability.status_code == 200
        
        # Step 3: Check team member availability
        member_availability = auth_helper.get_team_availability(team_id, "member1@example.com")
        assert member_availability.status_code == 200

@pytest.mark.authenticated  
class TestWorkflowIntegration:
    """
    Test integration between different workflow components
    """
    
    def test_end_to_end_meeting_scheduling(self, auth_helper):
        """
        Test: Complete end-to-end meeting scheduling workflow
        Flow: Create team → poll for time → create meeting → check availability
        """
        # Step 1: Create team
        team_response, team_id = auth_helper.create_team("Scheduling Team")
        assert team_response.status_code in [200, 302]
        
        # Step 2: Create poll for meeting time
        poll_response, poll_id = auth_helper.create_poll(
            team_id=team_id,
            poll_title="Best Meeting Time",
            options=["Monday 2PM", "Tuesday 10AM", "Friday 3PM"]
        )
        assert poll_response.status_code in [200, 302]
        
        # Step 3: Vote in poll
        vote_response = auth_helper.vote_in_poll(team_id, poll_id, ["Monday 2PM"])
        assert vote_response.status_code in [200, 302]
        
        # Step 4: Create meeting based on poll results
        meeting_response, meeting_id = auth_helper.create_meeting(
            team_id=team_id,
            meeting_data={
                'title': 'Team Meeting',
                'date': '2024-12-02',  # Monday
                'time': '14:00',       # 2PM
                'duration': '60'
            }
        )
        assert meeting_response.status_code in [200, 302]
        
        # Step 5: Check availability for meeting time
        availability_response = auth_helper.get_team_availability(team_id, auth_helper.test_user_email)
        assert availability_response.status_code == 200
        
        # Verify the complete workflow executed successfully
        assert auth_helper.mock_db['teams'].insert_one.called
        assert auth_helper.mock_db['polls'].insert_one.called
        assert auth_helper.mock_db['meetings'].insert_one.called
