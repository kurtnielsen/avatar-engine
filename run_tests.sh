#!/bin/bash

# Avatar Engine Test Runner
# Run tests with various options

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="all"
COVERAGE=true
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            TEST_TYPE="unit"
            shift
            ;;
        --integration)
            TEST_TYPE="integration"
            shift
            ;;
        --performance)
            TEST_TYPE="performance"
            shift
            ;;
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            echo "Avatar Engine Test Runner"
            echo ""
            echo "Usage: ./run_tests.sh [options]"
            echo ""
            echo "Options:"
            echo "  --unit          Run only unit tests"
            echo "  --integration   Run only integration tests"
            echo "  --performance   Run only performance tests"
            echo "  --no-coverage   Skip coverage report"
            echo "  --verbose       Show verbose output"
            echo "  --help          Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./run_tests.sh                    # Run all tests with coverage"
            echo "  ./run_tests.sh --unit            # Run only unit tests"
            echo "  ./run_tests.sh --no-coverage     # Run all tests without coverage"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Ensure we're in the right directory
cd "$(dirname "$0")"

echo -e "${GREEN}🧪 Avatar Engine Test Suite${NC}"
echo "=========================="

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}⚠️  Warning: No virtual environment detected${NC}"
    echo "Consider activating a virtual environment before running tests"
    echo ""
fi

# Build pytest command
PYTEST_CMD="python -m pytest"

# Add test selection
case $TEST_TYPE in
    unit)
        echo -e "${GREEN}Running unit tests...${NC}"
        PYTEST_CMD="$PYTEST_CMD tests/unit"
        ;;
    integration)
        echo -e "${GREEN}Running integration tests...${NC}"
        PYTEST_CMD="$PYTEST_CMD tests/integration"
        ;;
    performance)
        echo -e "${GREEN}Running performance tests...${NC}"
        PYTEST_CMD="$PYTEST_CMD tests/performance"
        ;;
    all)
        echo -e "${GREEN}Running all tests...${NC}"
        ;;
esac

# Add coverage if enabled
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=backend --cov-report=term-missing --cov-report=html:htmlcov"
else
    PYTEST_CMD="$PYTEST_CMD --no-cov"
fi

# Add verbose flag if requested
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -vv"
fi

# Run the tests
echo "Command: $PYTEST_CMD"
echo ""

if $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}✅ All tests passed!${NC}"
    
    if [ "$COVERAGE" = true ]; then
        echo ""
        echo -e "${GREEN}📊 Coverage Report:${NC}"
        echo "HTML coverage report generated in: htmlcov/index.html"
        
        # Try to get coverage percentage
        if command -v coverage &> /dev/null; then
            COVERAGE_PCT=$(coverage report --format=total)
            echo "Total coverage: ${COVERAGE_PCT}%"
        fi
    fi
else
    echo ""
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi

# Performance test results summary
if [ "$TEST_TYPE" = "performance" ] || [ "$TEST_TYPE" = "all" ]; then
    echo ""
    echo -e "${GREEN}📈 Performance Summary:${NC}"
    echo "Check the test output above for detailed performance metrics"
fi