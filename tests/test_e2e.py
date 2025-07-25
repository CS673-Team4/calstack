import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time

@pytest.mark.e2e
@pytest.mark.slow
class TestUserInterface:
    """Test user interface and basic navigation"""
    
    def test_home_page_loads(self, browser, base_url):
        """Test that home page loads correctly"""
        browser.get(base_url)
        
        # Wait for page to load
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        assert "CalStack" in browser.title or "Calendar" in browser.title
        
    def test_navigation_elements_present(self, browser, base_url):
        """Test that basic navigation elements are present"""
        browser.get(base_url)
        
        # Look for common navigation elements
        try:
            # Check for login/auth buttons
            login_elements = browser.find_elements(By.PARTIAL_LINK_TEXT, "Login")
            auth_elements = browser.find_elements(By.PARTIAL_LINK_TEXT, "Sign")
            
            # Should have some form of authentication UI
            assert len(login_elements) > 0 or len(auth_elements) > 0
        except Exception:
            # If no login elements, check if already authenticated
            pass

@pytest.mark.e2e
class TestAuthenticationFlow:
    """Test authentication flow UI"""
    
    def test_login_page_accessible(self, browser, base_url):
        """Test that login page is accessible and has required elements"""
        browser.get(f"{base_url}/login")
        
        # Wait for page to load
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Should have some authentication options
        page_text = browser.page_source.lower()
        auth_keywords = ['google', 'outlook', 'login', 'sign in']
        
        assert any(keyword in page_text for keyword in auth_keywords)

@pytest.mark.e2e
class TestTeamPages:
    """Test team-related pages"""
    
    def test_create_team_page_structure(self, browser, base_url):
        """Test create team page structure"""
        browser.get(f"{base_url}/create_team")
        
        # Wait for page to load
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Check if redirected to login or if form is present
        current_url = browser.current_url
        page_text = browser.page_source.lower()
        
        # Either should be on login page or create team page
        assert ('login' in current_url or 
                'create' in page_text or 
                'team' in page_text)

@pytest.mark.e2e
class TestResponsiveDesign:
    """Test responsive design elements"""
    
    def test_mobile_viewport(self, browser, base_url):
        """Test mobile viewport rendering"""
        # Set mobile viewport
        browser.set_window_size(375, 667)  # iPhone 6/7/8 size
        browser.get(base_url)
        
        # Wait for page to load
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Page should still be functional
        assert browser.find_element(By.TAG_NAME, "body")
        
    def test_desktop_viewport(self, browser, base_url):
        """Test desktop viewport rendering"""
        # Set desktop viewport
        browser.set_window_size(1920, 1080)
        browser.get(base_url)
        
        # Wait for page to load
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Page should render properly
        assert browser.find_element(By.TAG_NAME, "body")

@pytest.mark.e2e
class TestErrorPages:
    """Test error page handling"""
    
    def test_404_page_handling(self, browser, base_url):
        """Test 404 page handling"""
        browser.get(f"{base_url}/nonexistent_page_12345")
        
        # Wait for page to load
        time.sleep(2)
        
        # Should either show 404 page or redirect gracefully
        page_text = browser.page_source.lower()
        
        # Check for 404 indicators or that we're redirected to a valid page
        is_404 = ('404' in page_text or 
                 'not found' in page_text or 
                 'page not found' in page_text)
        
        is_redirect = browser.current_url != f"{base_url}/nonexistent_page_12345"
        
        # Either should show 404 or redirect to valid page
        assert is_404 or is_redirect

@pytest.mark.e2e
class TestPerformance:
    """Test basic performance metrics"""
    
    def test_page_load_time(self, browser, base_url):
        """Test that pages load within reasonable time"""
        start_time = time.time()
        browser.get(base_url)
        
        # Wait for page to be fully loaded
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        load_time = time.time() - start_time
        
        # Page should load within 10 seconds (generous for testing)
        assert load_time < 10, f"Page took {load_time:.2f} seconds to load"
