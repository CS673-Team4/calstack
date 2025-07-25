"""
Authenticated Test Client for Full Workflow Testing

This module provides a Flask test client that can simulate authenticated sessions
to test the complete user → team → poll → meeting workflow without OAuth.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from bson import ObjectId
import json
import re

# Add the parent directory to sys.path to import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def authenticated_client():
    """
    Create a Flask test client with mocked authentication
    """
    # Import app after adding to path
    from app import app, teams_col, polls_col, meetings_col, availability_col
    
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    
    with app.test_client() as client:
        with app.app_context():
            # Mock session to simulate authenticated user
            with client.session_transaction() as sess:
                sess['email'] = 'test@example.com'
                sess['name'] = 'Test User'
            
            yield client

@pytest.fixture
def mock_database():
    """
    Mock database collections for isolated testing
    """
    with patch('app.teams_col') as mock_teams, \
         patch('app.polls_col') as mock_polls, \
         patch('app.meetings_col') as mock_meetings, \
         patch('app.availability_col') as mock_availability:
        
        # Configure mock collections
        mock_teams.find_one.return_value = None
        mock_teams.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        
        mock_polls.find_one.return_value = None
        mock_polls.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        
        mock_meetings.find_one.return_value = None
        mock_meetings.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        
        mock_availability.find_one.return_value = None
        
        yield {
            'teams': mock_teams,
            'polls': mock_polls,
            'meetings': mock_meetings,
            'availability': mock_availability
        }

@pytest.fixture
def mock_external_services():
    """
    Mock external services (SendGrid, Google Calendar, etc.)
    """
    with patch('app.SendGridAPIClient') as mock_sendgrid, \
         patch('os.environ.get') as mock_env:
        
        # Mock environment variables
        def mock_get_env(key, default=None):
            env_vars = {
                'SENDGRID_API_KEY': 'test_sendgrid_key',
                'GOOGLE_CLIENT_ID': 'test_google_client_id',
                'OUTLOOK_CLIENT_ID': 'test_outlook_client_id'
            }
            return env_vars.get(key, default)
        
        mock_env.side_effect = mock_get_env
        
        # Mock SendGrid
        mock_sg_instance = MagicMock()
        mock_sendgrid.return_value = mock_sg_instance
        mock_sg_instance.send.return_value = MagicMock(status_code=202)
        
        yield {
            'sendgrid': mock_sendgrid,
            'env': mock_env
        }

class AuthenticatedTestHelper:
    """
    Helper class for authenticated workflow testing
    """
    
    def __init__(self, client, mock_db, mock_services):
        self.client = client
        self.mock_db = mock_db
        self.mock_services = mock_services
        self.test_user_email = 'test@example.com'
    
    def create_team(self, team_name="Test Team", invited_emails=None):
        """
        Create a team using the authenticated client
        """
        if invited_emails is None:
            invited_emails = ["member1@example.com", "member2@example.com"]
        
        # Mock successful team creation
        team_id = ObjectId()
        team_doc = {
            "_id": team_id,
            "name": team_name,
            "members": [self.test_user_email],
            "code": "test1234"
        }
        self.mock_db['teams'].insert_one.return_value.inserted_id = team_id
        self.mock_db['teams'].find_one.return_value = team_doc
        
        response = self.client.post('/team/create', data={
            'team_name': team_name,
            'invited_emails': ','.join(invited_emails)
        })
        
        return response, str(team_id)
    
    def join_team(self, team_code):
        """
        Join a team using invite code
        """
        team_id = ObjectId()
        team_doc = {
            "_id": team_id,
            "name": "Test Team",
            "members": ["creator@example.com"],
            "code": team_code
        }
        self.mock_db['teams'].find_one.return_value = team_doc
        
        response = self.client.post('/team/join', data={
            'team_code': team_code
        })
        
        return response, str(team_id)
    
    def create_poll(self, team_id, poll_title="Test Poll", options=None):
        """
        Create a poll for a team
        """
        if options is None:
            options = ["Option 1", "Option 2", "Option 3"]
        
        # Mock team membership check
        team_doc = {
            "_id": ObjectId(team_id),
            "name": "Test Team",
            "members": [self.test_user_email],
            "code": "test1234"
        }
        self.mock_db['teams'].find_one.return_value = team_doc
        
        # Mock poll creation
        poll_id = ObjectId()
        self.mock_db['polls'].insert_one.return_value.inserted_id = poll_id
        
        response = self.client.post(f'/team/{team_id}/create_poll', data={
            'poll_title': poll_title,
            'options': '\n'.join(options)
        })
        
        return response, str(poll_id)
    
    def vote_in_poll(self, team_id, poll_id, selected_options):
        """
        Vote in a poll
        """
        # Mock poll existence and team membership
        poll_doc = {
            "_id": ObjectId(poll_id),
            "team_id": team_id,
            "title": "Test Poll",
            "options": ["Option 1", "Option 2", "Option 3"],
            "votes": {}
        }
        self.mock_db['polls'].find_one.return_value = poll_doc
        
        team_doc = {
            "_id": ObjectId(team_id),
            "members": [self.test_user_email]
        }
        self.mock_db['teams'].find_one.return_value = team_doc
        
        response = self.client.post(f'/team/{team_id}/poll/{poll_id}/vote', 
                                  json={'selected_options': selected_options})
        
        return response
    
    def create_meeting(self, team_id, meeting_data=None):
        """
        Create a meeting for a team
        """
        if meeting_data is None:
            meeting_data = {
                'title': 'Test Meeting',
                'date': '2024-12-01',
                'time': '14:00',
                'duration': '60'
            }
        
        # Mock team membership
        team_doc = {
            "_id": ObjectId(team_id),
            "members": [self.test_user_email]
        }
        self.mock_db['teams'].find_one.return_value = team_doc
        
        # Mock meeting creation
        meeting_id = ObjectId()
        self.mock_db['meetings'].insert_one.return_value.inserted_id = meeting_id
        
        response = self.client.post(f'/team/{team_id}/create_meeting', data=meeting_data)
        
        return response, str(meeting_id)
    
    def get_team_availability(self, team_id, email):
        """
        Get availability for a team member (now requires auth)
        """
        # Mock team membership for both requester and target
        team_doc = {
            "_id": ObjectId(team_id),
            "members": [self.test_user_email, email]
        }
        self.mock_db['teams'].find_one.return_value = team_doc
        
        # Mock availability data
        self.mock_db['availability'].find_one.return_value = {
            "team_id": team_id,
            "user_email": email,
            "busy": ["2024-12-01T10:00:00", "2024-12-01T15:00:00"]
        }
        
        response = self.client.get(f'/team/{team_id}/availability/{email}')
        return response

@pytest.fixture
def auth_helper(authenticated_client, mock_database, mock_external_services):
    """
    Provide the authenticated test helper
    """
    return AuthenticatedTestHelper(authenticated_client, mock_database, mock_external_services)
