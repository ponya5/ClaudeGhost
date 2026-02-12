#!/usr/bin/env python3
"""
ClaudeGhost Master Test Runner

Runs all test suites and provides a summary report.

Usage:
    python tests/run_all_tests.py           # Run all tests
    python tests/run_all_tests.py --quick   # Skip slow tests
    python tests/run_all_tests.py --verbose # Show all output
"""
import os
import sys
import time
import argparse

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")


def print_section(text: str):
    print(f"\n{Colors.BOLD}--- {text} ---{Colors.END}")


def run_test_module(module_name: str, verbose: bool = False):
    """Run a test module and return (passed, failed, duration)."""
    start = time.time()
    
    try:
        if verbose:
            print(f"\nRunning {module_name}...")
        
        # Import and run the module's run_all function
        module = __import__(f"tests.{module_name}", fromlist=["run_all"])
        passed, failed = module.run_all()
        
        duration = time.time() - start
        return passed, failed, duration
        
    except Exception as e:
        duration = time.time() - start
        print(f"{Colors.RED}[ERROR] Failed to run {module_name}: {e}{Colors.END}")
        return 0, 1, duration


def run_syntax_check():
    """Run Python syntax check on all source files."""
    print_section("Syntax Check")
    
    src_dir = os.path.join(PROJECT_ROOT, "src")
    errors = 0
    checked = 0
    
    for filename in os.listdir(src_dir):
        if filename.endswith(".py"):
            filepath = os.path.join(src_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    source = f.read()
                compile(source, filepath, 'exec')
                checked += 1
            except SyntaxError as e:
                print(f"{Colors.RED}[SYNTAX ERROR] {filename}: {e}{Colors.END}")
                errors += 1
    
    if errors == 0:
        print(f"{Colors.GREEN}[PASS] All {checked} source files have valid syntax{Colors.END}")
    
    return 0 if errors == 0 else 1


def run_import_check():
    """Verify all modules can be imported."""
    print_section("Import Check")
    
    modules = [
        "src.config",
        "src.utils",
        "src.guardian",
        "src.waha",
        "src.bridge",
        "src.main",
        "src.launcher",
        "src.cli",
    ]
    
    errors = 0
    for mod in modules:
        try:
            __import__(mod)
            print(f"{Colors.GREEN}[OK]{Colors.END} {mod}")
        except Exception as e:
            print(f"{Colors.RED}[FAIL]{Colors.END} {mod}: {e}")
            errors += 1
    
    return 0 if errors == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="ClaudeGhost Test Runner")
    parser.add_argument("--quick", action="store_true", help="Skip slow tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    print_header("ClaudeGhost Test Suite")
    
    total_passed = 0
    total_failed = 0
    total_time = 0.0
    
    # Run syntax check
    start = time.time()
    if run_syntax_check() != 0:
        total_failed += 1
    else:
        total_passed += 1
    total_time += time.time() - start
    
    # Run import check
    start = time.time()
    if run_import_check() != 0:
        total_failed += 1
    else:
        total_passed += 1
    total_time += time.time() - start
    
    # Test modules to run
    test_modules = [
        "test_config",
        "test_guardian",
        "test_waha",
        "test_bridge",
        "test_utils",
        "test_integration",
    ]
    
    results = []
    
    for module in test_modules:
        print_section(f"Running {module}")
        passed, failed, duration = run_test_module(module, args.verbose)
        results.append((module, passed, failed, duration))
        total_passed += passed
        total_failed += failed
        total_time += duration
    
    # Print summary
    print_header("Test Results Summary")
    
    print(f"{'Module':<25} {'Passed':>8} {'Failed':>8} {'Time':>10}")
    print("-" * 55)
    
    for module, passed, failed, duration in results:
        status_color = Colors.GREEN if failed == 0 else Colors.RED
        print(f"{module:<25} {Colors.GREEN}{passed:>8}{Colors.END} {status_color}{failed:>8}{Colors.END} {duration:>9.2f}s")
    
    print("-" * 55)
    print(f"{'TOTAL':<25} {Colors.GREEN}{total_passed:>8}{Colors.END} ", end="")
    
    if total_failed == 0:
        print(f"{Colors.GREEN}{total_failed:>8}{Colors.END} {total_time:>9.2f}s")
    else:
        print(f"{Colors.RED}{total_failed:>8}{Colors.END} {total_time:>9.2f}s")
    
    print()
    
    if total_failed == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}All tests passed!{Colors.END}")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}{total_failed} test(s) failed{Colors.END}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
