"""
Core Functionality Tests

Simple, focused tests for the essential CalStack functionality:
- Team creation and management
- Authentication and security
- Basic workflows

This replaces the overly complex authenticated workflow tests with clear, purposeful tests.
"""

import pytest

@pytest.mark.core
class TestTeamManagement:
    """Test core team management functionality"""
    
    def test_team_creation(self, authenticated_client, mock_database):
        """Test authenticated user can create a team"""
        response = authenticated_client.post('/team/create', data={
            'team_name': 'Engineering Team',
            'invited_emails': 'alice@example.com, bob@example.com'
        })
        
        # Should succeed (redirect or success page)
        assert response.status_code in [200, 302]
        
        # Verify team creation was attempted
        mock_database['teams'].insert_one.assert_called_once()
    
    def test_team_join(self, authenticated_client, mock_database):
        """Test user can join a team with valid code"""
        # Mock team exists
        from bson import ObjectId
        team_id = ObjectId()
        mock_database['teams'].find_one.return_value = {
            "_id": team_id,
            "name": "Test Team",
            "members": ["creator@example.com"],
            "code": "test1234"
        }
        
        response = authenticated_client.post('/team/join', data={
            'team_code': 'test1234'
        })
        
        assert response.status_code in [200, 302]

@pytest.mark.core
class TestAuthentication:
    """Test authentication and security"""
    
    def test_unauthenticated_redirect(self):
        """Test unauthenticated users are redirected"""
        from app import app
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            response = client.get('/team/create')
            assert response.status_code == 302  # Redirect to login
    
    def test_authenticated_access(self, authenticated_client):
        """Test authenticated users can access protected pages"""
        response = authenticated_client.get('/team/create')
        assert response.status_code == 200
        assert b'Create a New Team' in response.data

@pytest.mark.core
class TestInputValidation:
    """Test input validation and security"""
    
    def test_empty_team_name_rejected(self, authenticated_client):
        """Test empty team name is rejected"""
        response = authenticated_client.post('/team/create', data={
            'team_name': '',
            'invited_emails': 'test@example.com'
        })
        
        assert response.status_code == 200  # Shows form with error
        assert b'Create a New Team' in response.data  # Form redisplayed
    
    def test_invalid_email_rejected(self, authenticated_client):
        """Test invalid email format is rejected"""
        response = authenticated_client.post('/team/create', data={
            'team_name': 'Valid Team',
            'invited_emails': 'invalid-email'
        })
        
        assert response.status_code == 200  # Shows form with error
        assert b'Create a New Team' in response.data  # Form redisplayed
    
    def test_long_team_name_rejected(self, authenticated_client):
        """Test overly long team name is rejected"""
        response = authenticated_client.post('/team/create', data={
            'team_name': 'x' * 150,  # Too long
            'invited_emails': 'test@example.com'
        })
        
        assert response.status_code == 200  # Shows form with error
        assert b'Create a New Team' in response.data  # Form redisplayed

@pytest.mark.core
class TestBasicWorkflows:
    """Test basic user workflows"""
    
    # Availability security test removed - covered by comprehensive auth test
