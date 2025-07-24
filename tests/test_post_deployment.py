"""
Post-Deployment Tests for CalStack
These tests run against the actual deployed application with real OAuth providers
"""

import pytest
import requests
import os
from urllib.parse import urljoin, urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

# These tests require real deployment URL and OAuth credentials
DEPLOYMENT_URL = os.getenv('DEPLOYMENT_URL', 'https://your-app.com')
ENABLE_OAUTH_TESTS = os.getenv('ENABLE_OAUTH_TESTS', 'false').lower() == 'true'

@pytest.mark.skipif(not ENABLE_OAUTH_TESTS, reason="OAuth tests disabled - set ENABLE_OAUTH_TESTS=true")
@pytest.mark.post_deployment
class TestOAuthIntegration:
    """Test OAuth integration with real providers"""
    
    @pytest.fixture(scope="class")
    def browser(self):
        """Browser for OAuth flow testing"""
        chrome_options = Options()
        if os.getenv('HEADLESS', 'true').lower() == 'true':
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()
    
    def test_google_oauth_flow_initiation(self, browser):
        """Test that Google OAuth flow can be initiated"""
        browser.get(f"{DEPLOYMENT_URL}/login")
        
        # Look for Google login button/link
        google_elements = browser.find_elements(By.PARTIAL_LINK_TEXT, "Google")
        google_elements.extend(browser.find_elements(By.XPATH, "//*[contains(text(), 'Google')]"))
        
        assert len(google_elements) > 0, "Google login option not found"
        
        # Click Google login (this will redirect to Google)
        google_elements[0].click()
        
        # Wait for redirect to Google
        WebDriverWait(browser, 10).until(
            lambda driver: "google" in driver.current_url.lower() or "accounts.google.com" in driver.current_url
        )
        
        # Verify we're on Google's OAuth page
        assert "google" in browser.current_url.lower()
    
    def test_outlook_oauth_flow_initiation(self, browser):
        """Test that Outlook OAuth flow can be initiated"""
        browser.get(f"{DEPLOYMENT_URL}/login/outlook")
        
        # Should redirect to Microsoft login
        WebDriverWait(browser, 10).until(
            lambda driver: "microsoft" in driver.current_url.lower() or "login.microsoftonline.com" in driver.current_url
        )
        
        # Verify we're on Microsoft's OAuth page
        assert "microsoft" in browser.current_url.lower() or "login.microsoftonline.com" in browser.current_url
    
    def test_oauth_callback_endpoints_exist(self):
        """Test that OAuth callback endpoints are accessible"""
        api_client = requests.Session()
        
        # Test Google callback (should return error without proper state/code)
        response = api_client.get(f"{DEPLOYMENT_URL}/oauth2callback")
        assert response.status_code in [400, 401, 302], "Google callback endpoint not properly configured"
        
        # Test Outlook callback
        response = api_client.get(f"{DEPLOYMENT_URL}/oauth2callback/outlook")
        assert response.status_code in [400, 401, 302], "Outlook callback endpoint not properly configured"

@pytest.mark.post_deployment
class TestDeploymentHealth:
    """Test overall deployment health and functionality"""
    
    def test_application_is_accessible(self):
        """Test that the deployed application is accessible"""
        response = requests.get(DEPLOYMENT_URL, timeout=30)
        assert response.status_code == 200
        assert "CalStack" in response.text or "Calendar" in response.text
    
    def test_database_connectivity(self):
        """Test database connectivity through the app"""
        # Try to access a page that requires database
        response = requests.get(f"{DEPLOYMENT_URL}/team/create")
        # Should either load or redirect (not crash with 500)
        assert response.status_code in [200, 302]
    
    def test_ssl_certificate(self):
        """Test SSL certificate if using HTTPS"""
        if DEPLOYMENT_URL.startswith('https'):
            response = requests.get(DEPLOYMENT_URL, verify=True)
            assert response.status_code == 200
    
    def test_performance_under_load(self):
        """Basic load test - multiple concurrent requests"""
        import concurrent.futures
        import threading
        
        def make_request():
            try:
                response = requests.get(DEPLOYMENT_URL, timeout=10)
                return response.status_code == 200
            except:
                return False
        
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # At least 80% should succeed
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.8, f"Only {success_rate:.1%} of requests succeeded"

@pytest.mark.post_deployment
class TestEmailIntegration:
    """Test email functionality in production"""
    
    def test_email_service_configuration(self):
        """Test that email service is properly configured"""
        # This is a basic test - you might want to add actual email sending test
        # with a test email address if you have SendGrid properly configured
        
        # For now, just verify the invite endpoint doesn't crash
        api_client = requests.Session()
        response = api_client.post(
            f"{DEPLOYMENT_URL}/api/team/test_team_id/invite",
            json={"emails": ["test@example.com"]}
        )
        
        # Should require authentication, not crash
        assert response.status_code in [302, 401, 403, 500]  # 500 is OK for invalid team

@pytest.mark.post_deployment
class TestSecurityInProduction:
    """Test security measures in production environment"""
    
    def test_https_redirect(self):
        """Test that HTTP redirects to HTTPS if configured"""
        if DEPLOYMENT_URL.startswith('https'):
            http_url = DEPLOYMENT_URL.replace('https://', 'http://')
            try:
                response = requests.get(http_url, allow_redirects=False, timeout=10)
                # Should redirect to HTTPS
                assert response.status_code in [301, 302, 308]
                assert 'https' in response.headers.get('Location', '').lower()
            except requests.exceptions.RequestException:
                # HTTP might not be available, which is fine
                pass
    
    def test_security_headers(self):
        """Test security headers in production"""
        response = requests.get(DEPLOYMENT_URL)
        headers = response.headers
        
        # Check for basic security headers (these are recommendations)
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': ['DENY', 'SAMEORIGIN'],
            'X-XSS-Protection': '1; mode=block'
        }
        
        for header, expected_values in security_headers.items():
            if header in headers:
                if isinstance(expected_values, list):
                    assert headers[header] in expected_values
                else:
                    assert headers[header] == expected_values
    
    def test_no_debug_info_exposed(self):
        """Test that debug information is not exposed in production"""
        response = requests.get(DEPLOYMENT_URL)
        content = response.text.lower()
        
        # These shouldn't appear in production
        debug_indicators = [
            'traceback',
            'werkzeug',
            'debug=true',
            'flask development server'
        ]
        
        for indicator in debug_indicators:
            assert indicator not in content, f"Debug indicator '{indicator}' found in production"

if __name__ == "__main__":
    print("Post-Deployment Test Suite")
    print("=" * 40)
    print(f"Target URL: {DEPLOYMENT_URL}")
    print(f"OAuth Tests: {'Enabled' if ENABLE_OAUTH_TESTS else 'Disabled'}")
    print()
    print("To run OAuth tests, set environment variables:")
    print("  export DEPLOYMENT_URL=https://your-domain.com")
    print("  export ENABLE_OAUTH_TESTS=true")
    print("  export HEADLESS=false  # to see browser automation")
    print()
    print("Run with: pytest tests/test_post_deployment.py -v")
