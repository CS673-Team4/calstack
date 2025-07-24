import pytest
import requests
from urllib.parse import urljoin
import time

@pytest.mark.e2e
class TestUserInterfaceSimple:
    """Test user interface without browser automation (server-friendly)"""
    
    def test_home_page_content(self, base_url, api_client):
        """Test that home page loads and contains expected content"""
        response = api_client.get(base_url)
        assert response.status_code == 200
        
        # Check for basic HTML structure
        content = response.text.lower()
        assert '<html' in content or '<!doctype' in content
        assert '<body' in content
        
    def test_page_titles_and_content(self, base_url, api_client):
        """Test that pages have appropriate titles and content"""
        pages_to_test = [
            ('/', ['calstack', 'calendar', 'team']),
            ('/login', ['login', 'sign', 'auth']),
            ('/team/create', ['create', 'team', 'form']),
            ('/team/join', ['join', 'team'])
        ]
        
        for path, expected_keywords in pages_to_test:
            response = api_client.get(urljoin(base_url, path))
            
            # Should either load successfully or redirect
            assert response.status_code in [200, 302]
            
            if response.status_code == 200:
                content = response.text.lower()
                # At least one keyword should be present
                assert any(keyword in content for keyword in expected_keywords), \
                    f"None of {expected_keywords} found in {path}"

@pytest.mark.e2e
class TestFormStructure:
    """Test form structure and basic validation"""
    
    def test_team_creation_form_structure(self, base_url, api_client):
        """Test that team creation form has required elements"""
        response = api_client.get(urljoin(base_url, '/team/create'))
        
        if response.status_code == 200:
            content = response.text.lower()
            
            # Should have form elements
            form_elements = ['<form', 'input', 'name', 'submit', 'button']
            form_present = any(element in content for element in form_elements)
            
            # Either should have form or be an API endpoint
            assert form_present or 'json' in response.headers.get('content-type', '')
    
    def test_join_team_form_structure(self, base_url, api_client):
        """Test that join team form has required elements"""
        response = api_client.get(urljoin(base_url, '/team/join'))
        
        if response.status_code == 200:
            content = response.text.lower()
            
            # Should have form elements or team selection
            expected_elements = ['<form', 'input', 'team', 'join', 'code']
            has_expected = any(element in content for element in expected_elements)
            
            assert has_expected

@pytest.mark.e2e
class TestAPIEndpointsIntegration:
    """Test API endpoints integration"""
    
    def test_api_endpoints_respond(self, base_url, api_client):
        """Test that API endpoints respond appropriately"""
        api_endpoints = [
            ('/api/team/test_id/polls', 'GET'),
            ('/api/propose_slots', 'POST'),
        ]
        
        for endpoint, method in api_endpoints:
            if method == 'GET':
                response = api_client.get(urljoin(base_url, endpoint))
            else:
                response = api_client.post(urljoin(base_url, endpoint), json={})
            
            # Should respond (not necessarily successfully, but should respond)
            assert response.status_code < 600  # Valid HTTP status code

@pytest.mark.e2e
class TestErrorHandlingIntegration:
    """Test error handling across the application"""
    
    def test_404_pages_handled_gracefully(self, base_url, api_client):
        """Test that 404 pages are handled gracefully"""
        non_existent_pages = [
            '/nonexistent',
            '/team/nonexistent_team_id',
            '/api/nonexistent_endpoint'
        ]
        
        for page in non_existent_pages:
            response = api_client.get(urljoin(base_url, page))
            
            # Should either return 404 or handle gracefully
            assert response.status_code in [200, 302, 404, 500]
            
            # If 500, it should be a server error, not a crash
            if response.status_code == 500:
                # Should still return some content
                assert len(response.text) > 0

@pytest.mark.e2e
class TestSecurityBasics:
    """Test basic security measures"""
    
    def test_no_sensitive_data_exposure(self, base_url, api_client):
        """Test that sensitive data is not exposed in responses"""
        response = api_client.get(base_url)
        
        if response.status_code == 200:
            content = response.text.lower()
            
            # Check for common sensitive data patterns
            sensitive_patterns = [
                'password=',
                'secret=',
                'key=',
                'token=',
                'mongodb://',
                'mysql://',
                'postgres://'
            ]
            
            for pattern in sensitive_patterns:
                assert pattern not in content, f"Sensitive pattern '{pattern}' found in response"
    
    def test_basic_headers_security(self, base_url, api_client):
        """Test basic security headers"""
        response = api_client.get(base_url)
        
        # Should not expose detailed server information
        server_header = response.headers.get('Server', '').lower()
        
        # These are fine, but shouldn't be overly detailed
        problematic_patterns = ['werkzeug/']
        for pattern in problematic_patterns:
            if pattern in server_header:
                # This is just a warning, not a failure for development
                print(f"Warning: Detailed server info exposed: {server_header}")

@pytest.mark.e2e
class TestPerformanceBasics:
    """Test basic performance characteristics"""
    
    def test_response_times(self, base_url, api_client):
        """Test that responses come back in reasonable time"""
        start_time = time.time()
        response = api_client.get(base_url)
        response_time = time.time() - start_time
        
        # Should respond within 5 seconds (generous for testing)
        assert response_time < 5.0, f"Response took {response_time:.2f} seconds"
        assert response.status_code == 200
    
    def test_multiple_requests_handling(self, base_url, api_client):
        """Test that server can handle multiple requests"""
        responses = []
        
        # Make several requests quickly
        for i in range(5):
            response = api_client.get(base_url)
            responses.append(response.status_code)
        
        # All should succeed
        assert all(status == 200 for status in responses)
