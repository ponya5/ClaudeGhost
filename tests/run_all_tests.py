#!/usr/bin/env python3
"""ClaudeGhost Master Test Runner."""
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

G = "\033[92m"
R = "\033[91m"
C = "\033[96m"
B = "\033[1m"
E = "\033[0m"


def run_test_module(module_name: str):
    start = time.time()
    try:
        module = __import__(f"tests.{module_name}", fromlist=["run_all"])
        passed, failed = module.run_all()
        return passed, failed, time.time() - start
    except Exception as e:
        print(f"{R}[ERROR] {module_name}: {e}{E}")
        return 0, 1, time.time() - start


def run_syntax_check():
    src_dir = os.path.join(PROJECT_ROOT, "src")
    errors = checked = 0
    for fn in os.listdir(src_dir):
        if fn.endswith(".py"):
            fp = os.path.join(src_dir, fn)
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    compile(f.read(), fp, "exec")
                checked += 1
            except SyntaxError as e:
                print(f"{R}[SYNTAX] {fn}: {e}{E}")
                errors += 1
    if errors == 0:
        print(f"{G}[PASS] All {checked} source files valid syntax{E}")
    return errors


def main():
    print(f"\n{B}{C}{'=' * 50}{E}")
    print(f"{B}{C}{'ClaudeGhost Test Suite':^50}{E}")
    print(f"{B}{C}{'=' * 50}{E}\n")

    total_passed = total_failed = 0

    if run_syntax_check() == 0:
        total_passed += 1
    else:
        total_failed += 1

    modules = [
        "test_config",
        "test_guardian",
        "test_bridge",
        "test_utils",
        "test_integration",
    ]

    results = []
    for mod in modules:
        print(f"\n{B}--- {mod} ---{E}")
        p, f, d = run_test_module(mod)
        results.append((mod, p, f, d))
        total_passed += p
        total_failed += f

    print(f"\n{B}{C}{'=' * 50}{E}")
    print(f"{'Module':<25} {'Pass':>6} {'Fail':>6} {'Time':>8}")
    print("-" * 50)
    for mod, p, f, d in results:
        sc = G if f == 0 else R
        print(f"{mod:<25} {G}{p:>6}{E} {sc}{f:>6}{E} {d:>7.2f}s")
    print("-" * 50)
    print(f"{'TOTAL':<25} {G}{total_passed:>6}{E} ", end="")
    fc = G if total_failed == 0 else R
    print(f"{fc}{total_failed:>6}{E}")

    if total_failed == 0:
        print(f"\n{G}{B}All tests passed!{E}")
        return 0
    print(f"\n{R}{B}{total_failed} test(s) failed{E}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
