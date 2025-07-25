#!/usr/bin/env python3
"""
Test runner script for CalStack application
Runs tests against the deployed application
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def check_app_running(url="http://localhost:5000"):
    """Check if the application is running"""
    import requests
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def install_test_dependencies():
    """Install test dependencies"""
    print("Installing test dependencies...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-r", "test_requirements.txt"
    ], check=True)

def run_tests(test_type="all", verbose=False, coverage=False):
    """Run the specified tests"""
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=.", "--cov-report=html:test_reports/coverage"])
    
    # Add HTML report
    cmd.extend(["--html=test_reports/report.html", "--self-contained-html"])
    
    # Select test type
    if test_type == "api":
        cmd.extend(["-m", "api"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "workflow":
        # Run workflow integration tests
        test_files = ['tests/test_workflow_integration.py']
        markers = ['-m', 'workflow']
        cmd.extend(markers)
        cmd.extend(test_files)
    elif test_type == "authenticated":
        # Run authenticated workflow tests
        test_files = ['tests/test_full_workflow.py', 'tests/test_authenticated_workflows.py']
        markers = ['-m', 'authenticated']
        cmd.extend(markers)
        cmd.extend(test_files)
    elif test_type == "e2e":
        cmd.extend(["-m", "e2e"])
    elif test_type == "fast":
        cmd.extend(["-m", "not slow and not e2e"])  # Exclude slow E2E tests
    elif test_type == "all":
        cmd.append("tests/")
    
    print(f"Running command: {' '.join(cmd)}")
    return subprocess.run(cmd)

def main():
    parser = argparse.ArgumentParser(description="Run CalStack tests")
    parser.add_argument(
        "--type", 
        choices=["all", "api", "integration", "workflow", "authenticated", "e2e", "fast"],
        default="fast",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--install-deps", 
        action="store_true",
        help="Install test dependencies before running"
    )
    parser.add_argument(
        "--check-app", 
        action="store_true",
        help="Check if app is running before tests"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:5000",
        help="Base URL for the application"
    )
    
    args = parser.parse_args()
    
    # Set environment variable for tests
    os.environ["TEST_BASE_URL"] = args.url
    
    try:
        # Install dependencies if requested
        if args.install_deps:
            install_test_dependencies()
        
        # Check if app is running
        if args.check_app:
            print(f"Checking if app is running at {args.url}...")
            if not check_app_running(args.url):
                print(f"❌ Application is not running at {args.url}")
                print("Please start your application first:")
                print("  python app.py")
                return 1
            else:
                print(f"✅ Application is running at {args.url}")
        
        # Create test reports directory
        Path("test_reports").mkdir(exist_ok=True)
        
        # Run tests
        print(f"\n🧪 Running {args.type} tests...")
        result = run_tests(args.type, args.verbose, args.coverage)
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
            print(f"📊 Test report: test_reports/report.html")
            if args.coverage:
                print(f"📈 Coverage report: test_reports/coverage/index.html")
        else:
            print("\n❌ Some tests failed!")
            print(f"📊 Test report: test_reports/report.html")
        
        return result.returncode
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running tests: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        return 1

if __name__ == "__main__":
    sys.exit(main())
