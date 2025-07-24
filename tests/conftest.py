import pytest
import os
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test configuration
BASE_URL = os.getenv('TEST_BASE_URL', 'http://localhost:5000')
TEST_EMAIL = os.getenv('TEST_EMAIL', 'test@example.com')
TEST_PASSWORD = os.getenv('TEST_PASSWORD', 'testpassword123')

@pytest.fixture(scope="session")
def base_url():
    """Base URL for the application"""
    return BASE_URL

@pytest.fixture(scope="session")
def api_client():
    """HTTP client for API testing"""
    session = requests.Session()
    session.headers.update({'Content-Type': 'application/json'})
    return session

@pytest.fixture(scope="function")
def browser():
    """Selenium WebDriver for end-to-end tests"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)
    
    yield driver
    driver.quit()

@pytest.fixture
def test_user_data():
    """Sample test user data"""
    return {
        'email': TEST_EMAIL,
        'name': 'Test User',
        'provider': 'test'
    }

@pytest.fixture
def test_team_data():
    """Sample test team data"""
    return {
        'name': 'Test Team',
        'description': 'A team for testing purposes',
        'timezone': 'UTC'
    }

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "auth: Authentication tests")
    config.addinivalue_line("markers", "slow: Slow running tests")

def is_app_running(url):
    """Check if the application is running"""
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

@pytest.fixture(scope="session", autouse=True)
def check_app_running(base_url):
    """Ensure the application is running before tests"""
    if not is_app_running(base_url):
        pytest.exit(f"Application is not running at {base_url}. Please start the application first.")
