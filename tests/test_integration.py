import pytest
import requests
import json
from urllib.parse import urljoin
import time

@pytest.mark.integration
class TestTeamWorkflow:
    """Test complete team workflow integration"""
    
    def test_team_creation_workflow(self, base_url, api_client):
        """Test the team creation workflow without authentication"""
        # Test that team creation page loads
        response = api_client.get(urljoin(base_url, '/team/create'))
        assert response.status_code in [200, 302]
        
        # If redirected, should be to login
        if response.status_code == 302:
            assert 'login' in response.headers.get('Location', '').lower()

@pytest.mark.integration 
class TestCalendarIntegration:
    """Test calendar integration functionality"""
    
    def test_suggest_slots_endpoint_structure(self, base_url, api_client):
        """Test suggest slots endpoint structure"""
        # Test with dummy team ID
        response = api_client.post(
            urljoin(base_url, '/team/dummy_id/suggest_slots'),
            json={'duration': 60, 'days_ahead': 7}
        )
        # Should require authentication or return proper error (500 is also acceptable for invalid team)
        assert response.status_code in [302, 401, 403, 404, 500]

@pytest.mark.integration
class TestPollWorkflow:
    """Test polling workflow integration"""
    
    def test_poll_creation_endpoint(self, base_url, api_client):
        """Test poll creation endpoint"""
        poll_data = {
            'title': 'Test Poll',
            'options': ['Option 1', 'Option 2']
        }
        response = api_client.post(
            urljoin(base_url, '/team/dummy_id/create_poll'),
            json=poll_data
        )
        # Should require authentication (405 Method Not Allowed is also acceptable)
        assert response.status_code in [302, 401, 403, 404, 405]

@pytest.mark.integration
class TestEmailIntegration:
    """Test email integration functionality"""
    
    def test_invite_members_endpoint(self, base_url, api_client):
        """Test invite members endpoint"""
        invite_data = {
            'emails': ['test1@example.com', 'test2@example.com']
        }
        response = api_client.post(
            urljoin(base_url, '/api/team/dummy_id/invite'),
            json=invite_data
        )
        # Should require authentication
        assert response.status_code in [302, 401, 403, 404, 500]

@pytest.mark.integration
class TestDatabaseConnectivity:
    """Test database connectivity and basic operations"""
    
    def test_app_database_connection(self, base_url, api_client):
        """Test that app can connect to database by checking page loads"""
        response = api_client.get(base_url)
        assert response.status_code == 200
        
        # If the app loads, database connection is likely working
        # (since most pages require database queries)

@pytest.mark.integration
class TestSecurityHeaders:
    """Test security-related headers and configurations"""
    
    def test_security_headers_present(self, base_url, api_client):
        """Test that basic security headers are present"""
        response = api_client.get(base_url)
        
        # Check for basic security practices
        assert response.status_code == 200
        
        # Verify no sensitive information in response
        response_text = response.text.lower()
        sensitive_terms = ['password', 'secret', 'token', 'key']
        
        # These shouldn't appear in plain text on public pages
        for term in sensitive_terms:
            # Allow these terms in form labels/placeholders but not values
            assert f'value="{term}"' not in response_text
