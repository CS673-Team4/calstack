#!/bin/bash

# CalStack Test Automation Script
# Run this script to execute comprehensive testing

set -e  # Exit on any error

echo "🧪 CalStack Test Automation"
echo "=========================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_warning "Virtual environment not detected. Activating..."
    source ~/venv/bin/activate
fi

# Check if app is running
echo "🔍 Checking if CalStack is running..."
if curl -s http://localhost:5000 > /dev/null; then
    print_status "CalStack is running on localhost:5000"
else
    print_error "CalStack is not running. Please start it first:"
    echo "   python app.py"
    exit 1
fi

# Install test dependencies if needed
echo "📦 Checking test dependencies..."
python -c "import pytest" 2>/dev/null || {
    print_warning "Installing test dependencies..."
    pip install -r test_requirements.txt
}

# Create test reports directory
mkdir -p test_reports

# Run different test suites
echo ""
echo "🚀 Running Test Suites"
echo "====================="

# 1. Fast API tests
echo "1️⃣  Running API Tests..."
if python -m pytest tests/test_api_endpoints.py -v --tb=short; then
    print_status "API tests completed"
else
    print_warning "Some API tests failed (check details above)"
fi

echo ""

# 2. Integration tests
echo "2️⃣  Running Integration Tests..."
if python -m pytest tests/test_integration.py -v --tb=short; then
    print_status "Integration tests completed"
else
    print_warning "Some integration tests failed (check details above)"
fi

echo ""

# 3. Simple E2E tests (server-friendly)
echo "3️⃣  Running E2E Tests..."
if python -m pytest tests/test_e2e_simple.py -v --tb=short; then
    print_status "E2E tests completed"
else
    print_warning "Some E2E tests failed (check details above)"
fi

echo ""

# 4. Full test suite with coverage
echo "4️⃣  Running Full Test Suite with Coverage..."
python run_tests.py --type fast --coverage --verbose

# Generate summary
echo ""
echo "📊 Test Summary"
echo "==============="

# Count test results
TOTAL_TESTS=$(python -m pytest --collect-only -q tests/test_api_endpoints.py tests/test_integration.py tests/test_e2e_simple.py 2>/dev/null | grep "test session starts" -A 20 | grep -o "[0-9]\+ item" | cut -d' ' -f1 || echo "27")

echo "📈 Test Reports Generated:"
echo "   - HTML Report: test_reports/report.html"
echo "   - Coverage Report: test_reports/coverage/index.html"
echo ""
echo "🎯 Quick Commands:"
echo "   - Run all tests: python run_tests.py --type all"
echo "   - Run API only:  python run_tests.py --type api"
echo "   - Run fast tests: python run_tests.py --type fast"
echo ""

print_status "Test automation completed!"
echo "Open test_reports/report.html in your browser to view detailed results."
