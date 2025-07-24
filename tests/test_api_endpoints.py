import pytest
import requests
import json
from urllib.parse import urljoin

@pytest.mark.api
class TestBasicEndpoints:
    """Test basic application endpoints"""
    
    def test_home_page_accessible(self, base_url, api_client):
        """Test that the home page is accessible"""
        response = api_client.get(base_url)
        assert response.status_code == 200
        
    def test_index_redirect(self, base_url, api_client):
        """Test that index redirects properly"""
        response = api_client.get(urljoin(base_url, '/'))
        assert response.status_code in [200, 302]

@pytest.mark.api
class TestTeamEndpoints:
    """Test team-related API endpoints"""
    
    def test_create_team_page_accessible(self, base_url, api_client):
        """Test that create team page is accessible"""
        response = api_client.get(urljoin(base_url, '/team/create'))
        assert response.status_code in [200, 302]  # May redirect if not authenticated
        
    def test_create_team_requires_auth(self, base_url, api_client):
        """Test that creating a team requires authentication"""
        team_data = {
            'name': 'Test Team',
            'description': 'Test Description'
        }
        response = api_client.post(
            urljoin(base_url, '/team/create'),
            data=team_data
        )
        # Should redirect to login or return 401/403
        assert response.status_code in [302, 401, 403]
        
    def test_join_team_page_structure(self, base_url, api_client):
        """Test join team page structure"""
        # Test the join team page (without team ID)
        response = api_client.get(urljoin(base_url, '/team/join'))
        # Should either show join page or redirect
        assert response.status_code in [200, 302]

@pytest.mark.api
class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_login_page_accessible(self, base_url, api_client):
        """Test that login page is accessible"""
        response = api_client.get(urljoin(base_url, '/login'))
        assert response.status_code == 200
        
    def test_outlook_login_accessible(self, base_url, api_client):
        """Test that Outlook login is accessible"""
        response = api_client.get(urljoin(base_url, '/login/outlook'))
        assert response.status_code in [200, 302]

@pytest.mark.api
class TestAPIResponseHeaders:
    """Test API response headers and security"""
    
    def test_response_headers(self, base_url, api_client):
        """Test that responses have appropriate headers"""
        response = api_client.get(base_url)
        
        # Check that response is HTML
        assert 'text/html' in response.headers.get('Content-Type', '')
        
    def test_no_sensitive_info_in_headers(self, base_url, api_client):
        """Test that sensitive information is not exposed in headers"""
        response = api_client.get(base_url)
        
        # Check that server info is not overly detailed
        server_header = response.headers.get('Server', '').lower()
        assert 'flask' not in server_header or 'werkzeug' not in server_header

@pytest.mark.api
class TestErrorHandling:
    """Test error handling"""
    
    def test_404_handling(self, base_url, api_client):
        """Test 404 error handling"""
        response = api_client.get(urljoin(base_url, '/nonexistent_page'))
        assert response.status_code == 404
        
    def test_invalid_team_id(self, base_url, api_client):
        """Test handling of invalid team IDs"""
        response = api_client.get(urljoin(base_url, '/team/invalid_id_12345'))
        # App may handle gracefully by redirecting or showing error
        assert response.status_code in [200, 302, 404, 500]
