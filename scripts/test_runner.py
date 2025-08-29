#!/usr/bin/env python3
"""
Test runner script with comprehensive testing options.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
import time

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_command(command, description):
    """Run a shell command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'='*60}")
    
    start_time = time.time()
    result = subprocess.run(command, cwd=PROJECT_ROOT)
    duration = time.time() - start_time
    
    status = "✓ PASSED" if result.returncode == 0 else "✗ FAILED"
    print(f"\n{status} ({duration:.2f}s)")
    
    return result.returncode == 0


def run_unit_tests(verbose=False):
    """Run unit tests."""
    command = ["python", "-m", "pytest", "tests/unit", "-m", "unit"]
    if verbose:
        command.append("-v")
    
    return run_command(command, "Unit Tests")


def run_integration_tests(verbose=False):
    """Run integration tests."""
    command = ["python", "-m", "pytest", "tests/integration", "-m", "integration"]
    if verbose:
        command.append("-v")
    
    return run_command(command, "Integration Tests")


def run_e2e_tests(verbose=False):
    """Run end-to-end tests."""
    command = ["python", "-m", "pytest", "tests/e2e", "-m", "e2e"]
    if verbose:
        command.extend(["-v", "--tb=long"])
    
    return run_command(command, "End-to-End Tests")


def run_performance_tests(verbose=False):
    """Run performance tests."""
    command = ["python", "-m", "pytest", "tests/performance", "-m", "performance"]
    if verbose:
        command.append("-v")
    
    return run_command(command, "Performance Tests")


def run_specific_tests(test_path, verbose=False):
    """Run specific test file or directory."""
    command = ["python", "-m", "pytest", test_path]
    if verbose:
        command.append("-v")
    
    return run_command(command, f"Specific Tests: {test_path}")


def run_coverage_report():
    """Generate and display coverage report."""
    command = ["python", "-m", "pytest", "--cov=src", "--cov-report=term-missing", "--cov-report=html"]
    return run_command(command, "Coverage Report")


def run_linting():
    """Run code linting."""
    success = True
    
    # Run flake8 if available
    try:
        command = ["python", "-m", "flake8", "src", "tests"]
        if not run_command(command, "Flake8 Linting"):
            success = False
    except FileNotFoundError:
        print("Flake8 not found, skipping...")
    
    # Run black check if available
    try:
        command = ["python", "-m", "black", "--check", "src", "tests"]
        if not run_command(command, "Black Code Formatting Check"):
            success = False
    except FileNotFoundError:
        print("Black not found, skipping...")
    
    # Run isort check if available
    try:
        command = ["python", "-m", "isort", "--check-only", "src", "tests"]
        if not run_command(command, "Import Sorting Check"):
            success = False
    except FileNotFoundError:
        print("isort not found, skipping...")
    
    return success


def run_type_checking():
    """Run type checking with mypy."""
    try:
        command = ["python", "-m", "mypy", "src"]
        return run_command(command, "Type Checking (MyPy)")
    except FileNotFoundError:
        print("MyPy not found, skipping type checking...")
        return True


def run_security_check():
    """Run security checks with bandit."""
    try:
        command = ["python", "-m", "bandit", "-r", "src", "-f", "json", "-o", "bandit_report.json"]
        return run_command(command, "Security Check (Bandit)")
    except FileNotFoundError:
        print("Bandit not found, skipping security check...")
        return True


def run_dependency_check():
    """Check for dependency vulnerabilities."""
    try:
        command = ["python", "-m", "safety", "check"]
        return run_command(command, "Dependency Security Check (Safety)")
    except FileNotFoundError:
        print("Safety not found, skipping dependency check...")
        return True


def run_comprehensive_tests(include_slow=False, verbose=False):
    """Run comprehensive test suite."""
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST SUITE")
    print("="*80)
    
    results = []
    
    # Code quality checks
    print("\n📋 PHASE 1: CODE QUALITY CHECKS")
    results.append(("Linting", run_linting()))
    results.append(("Type Checking", run_type_checking()))
    results.append(("Security Check", run_security_check()))
    results.append(("Dependency Check", run_dependency_check()))
    
    # Unit tests
    print("\n🧪 PHASE 2: UNIT TESTS")
    results.append(("Unit Tests", run_unit_tests(verbose)))
    
    # Integration tests
    print("\n🔗 PHASE 3: INTEGRATION TESTS")
    results.append(("Integration Tests", run_integration_tests(verbose)))
    
    # Performance tests (if requested)
    if include_slow:
        print("\n⚡ PHASE 4: PERFORMANCE TESTS")
        results.append(("Performance Tests", run_performance_tests(verbose)))
    
    # E2E tests (if requested)
    if include_slow:
        print("\n🌍 PHASE 5: END-TO-END TESTS")
        results.append(("E2E Tests", run_e2e_tests(verbose)))
    
    # Coverage report
    print("\n📊 PHASE 6: COVERAGE REPORT")
    results.append(("Coverage Report", run_coverage_report()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{test_name:25} {status}")
        if success:
            passed += 1
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print(f"❌ {total - passed} test(s) failed")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run LOs Generation Pipeline tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--lint", action="store_true", help="Run linting checks only")
    parser.add_argument("--type-check", action="store_true", help="Run type checking only")
    parser.add_argument("--security", action="store_true", help="Run security checks only")
    parser.add_argument("--all", action="store_true", help="Run all tests (comprehensive)")
    parser.add_argument("--include-slow", action="store_true", help="Include slow tests (performance, e2e)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--test-path", type=str, help="Run specific test file or directory")
    
    args = parser.parse_args()
    
    # Change to project directory
    os.chdir(PROJECT_ROOT)
    
    success = True
    
    if args.test_path:
        success = run_specific_tests(args.test_path, args.verbose)
    elif args.unit:
        success = run_unit_tests(args.verbose)
    elif args.integration:
        success = run_integration_tests(args.verbose)
    elif args.e2e:
        success = run_e2e_tests(args.verbose)
    elif args.performance:
        success = run_performance_tests(args.verbose)
    elif args.coverage:
        success = run_coverage_report()
    elif args.lint:
        success = run_linting()
    elif args.type_check:
        success = run_type_checking()
    elif args.security:
        success = run_security_check()
    elif args.all:
        success = run_comprehensive_tests(args.include_slow, args.verbose)
    else:
        # Default: run unit and integration tests
        print("Running default test suite (unit + integration)...")
        success = (run_unit_tests(args.verbose) and 
                  run_integration_tests(args.verbose))
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
