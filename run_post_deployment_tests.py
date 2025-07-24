#!/usr/bin/env python3
"""
Post-Deployment Test Runner for CalStack
Run this against your live deployment to test OAuth and production features
"""

import os
import sys
import subprocess
import argparse
from urllib.parse import urlparse

def validate_url(url):
    """Validate that the URL is properly formatted"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def check_url_accessible(url):
    """Check if the URL is accessible"""
    import requests
    try:
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def main():
    parser = argparse.ArgumentParser(description="Run post-deployment tests for CalStack")
    parser.add_argument(
        "--url", 
        required=True,
        help="Deployment URL (e.g., https://your-app.com)"
    )
    parser.add_argument(
        "--enable-oauth", 
        action="store_true",
        help="Enable OAuth flow testing (requires real OAuth credentials)"
    )
    parser.add_argument(
        "--headless", 
        action="store_true",
        default=True,
        help="Run browser tests in headless mode"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--test-type",
        choices=["all", "health", "oauth", "security"],
        default="all",
        help="Type of tests to run"
    )
    
    args = parser.parse_args()
    
    # Validate URL
    if not validate_url(args.url):
        print(f"❌ Invalid URL: {args.url}")
        print("Please provide a valid URL like: https://your-app.com")
        return 1
    
    print(f"🌐 Post-Deployment Testing for CalStack")
    print(f"Target URL: {args.url}")
    print(f"OAuth Tests: {'Enabled' if args.enable_oauth else 'Disabled'}")
    print("=" * 50)
    
    # Check if URL is accessible
    print("🔍 Checking if deployment is accessible...")
    if not check_url_accessible(args.url):
        print(f"❌ Cannot access {args.url}")
        print("Please ensure your deployment is running and accessible.")
        return 1
    
    print(f"✅ Deployment is accessible at {args.url}")
    
    # Set environment variables
    os.environ["DEPLOYMENT_URL"] = args.url
    os.environ["ENABLE_OAUTH_TESTS"] = "true" if args.enable_oauth else "false"
    os.environ["HEADLESS"] = "true" if args.headless else "false"
    
    # Build pytest command
    cmd = ["python", "-m", "pytest", "tests/test_post_deployment.py"]
    
    if args.verbose:
        cmd.append("-v")
    
    # Add test markers based on type
    if args.test_type == "health":
        cmd.extend(["-m", "post_deployment and not oauth"])
    elif args.test_type == "oauth":
        cmd.extend(["-m", "oauth"])
        if not args.enable_oauth:
            print("⚠️  OAuth tests requested but --enable-oauth not set. Enabling OAuth tests.")
            os.environ["ENABLE_OAUTH_TESTS"] = "true"
    elif args.test_type == "security":
        cmd.extend(["-k", "security"])
    
    # Add HTML report
    cmd.extend([
        "--html=test_reports/post_deployment_report.html",
        "--self-contained-html"
    ])
    
    try:
        print(f"\n🧪 Running {args.test_type} tests...")
        print(f"Command: {' '.join(cmd)}")
        print()
        
        # Ensure test reports directory exists
        os.makedirs("test_reports", exist_ok=True)
        
        # Run tests
        result = subprocess.run(cmd)
        
        print("\n" + "=" * 50)
        if result.returncode == 0:
            print("✅ All post-deployment tests passed!")
        else:
            print("❌ Some post-deployment tests failed!")
        
        print(f"📊 Detailed report: test_reports/post_deployment_report.html")
        
        if args.enable_oauth:
            print("\n🔐 OAuth Testing Notes:")
            print("- OAuth tests verify redirect flows to Google/Microsoft")
            print("- Actual login testing requires manual verification")
            print("- Ensure your OAuth apps are configured with correct redirect URIs")
        
        return result.returncode
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running tests: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        return 1

if __name__ == "__main__":
    sys.exit(main())
