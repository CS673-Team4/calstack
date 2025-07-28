import pytest
import requests
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from dotenv import load_dotenv
from unittest.mock import patch, MagicMock
from bson import ObjectId
import sys

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
    """Test user data for authenticated workflows"""
    return {
        'email': 'test@example.com',
        'name': 'Test User'
    }

@pytest.fixture
def test_team_data():
    """Test team data for workflows"""
    return {
        'name': 'Test Team',
        'members': ['test@example.com'],
        'code': 'test1234'
    }

@pytest.fixture
def authenticated_client():
    """Flask test client with mocked authentication"""
    # Add the parent directory to sys.path to import app
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from app import app
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            # Mock session to simulate authenticated user
            with client.session_transaction() as sess:
                sess['email'] = 'test@example.com'
                sess['name'] = 'Test User'
            yield client

@pytest.fixture
def mock_database():
    """Mock database collections for isolated testing"""
    with patch('app.users_col') as mock_users, \
         patch('app.teams_col') as mock_teams, \
         patch('app.polls_col') as mock_polls, \
         patch('app.availability_col') as mock_availability:
        
        # Configure mock collections
        mock_users.find_one.return_value = None
        mock_users.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        
        mock_teams.find_one.return_value = None
        mock_teams.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        
        mock_polls.find_one.return_value = None
        mock_polls.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        
        mock_availability.find_one.return_value = None
        
        yield {
            'users': mock_users,
            'teams': mock_teams,
            'polls': mock_polls,
            'availability': mock_availability
        }

@pytest.fixture
def mock_external_services():
    """Mock external services (SendGrid, Google Calendar, etc.)"""
    with patch('app.SendGridAPIClient') as mock_sendgrid, \
         patch('os.environ.get') as mock_env:
        
        # Mock environment variables
        def mock_get_env(key, default=None):
            env_vars = {
                'SENDGRID_API_KEY': 'test_sendgrid_key',
                'MS_CLIENT_ID': 'test_ms_client_id',
                'MS_CLIENT_SECRET': 'test_ms_client_secret',
                'AZURE_APPLICATION_ID': 'test_azure_app_id',
                'AZURE_DIRECTORY_ID': 'test_azure_dir_id',
                'FLASK_SECRET_KEY': 'test_flask_secret_key'
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
