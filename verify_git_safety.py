#!/usr/bin/env python3
"""
Git Safety Verification Script

Run this before your first git push to verify no sensitive data will be committed.

Usage:
    python verify_git_safety.py
"""

import os
import sys
from pathlib import Path

# ANSI colors for terminal output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")

def check_file_exists(filepath, should_exist=True):
    """Check if a file exists (or doesn't exist)"""
    exists = Path(filepath).exists()

    if should_exist:
        if exists:
            print_success(f"{filepath} exists")
            return True
        else:
            print_error(f"{filepath} NOT found")
            return False
    else:
        if not exists:
            print_success(f"{filepath} properly excluded")
            return True
        else:
            print_error(f"{filepath} exists but should NOT be committed")
            return False

def check_gitignore():
    """Verify .gitignore has critical exclusions"""
    print_header("Checking .gitignore")

    if not Path('.gitignore').exists():
        print_error(".gitignore file not found!")
        return False

    with open('.gitignore', 'r') as f:
        gitignore_content = f.read()

    critical_patterns = [
        '.env',
        '.cache/',
        '*.db',
        '.venv/',
        'node_modules/',
        'logs/',
        '*.bak',
    ]

    all_good = True
    for pattern in critical_patterns:
        if pattern in gitignore_content:
            print_success(f"'{pattern}' is in .gitignore")
        else:
            print_error(f"'{pattern}' is MISSING from .gitignore")
            all_good = False

    return all_good

def check_env_file():
    """Check .env vs .env.example"""
    print_header("Checking Environment Files")

    all_good = True

    # .env should exist locally but not in git
    if Path('.env').exists():
        print_success(".env exists locally (good for development)")

        # Check if it has real values
        with open('.env', 'r') as f:
            env_content = f.read()

        if 'your_email@example.com' in env_content or 'your_password_here' in env_content:
            print_warning(".env appears to have placeholder values - update with real credentials")
        else:
            print_success(".env has real values (make sure it's in .gitignore!)")
    else:
        print_warning(".env not found - you'll need to create it from .env.example")

    # .env.example should exist
    if Path('.env.example').exists():
        print_success(".env.example exists (safe template)")

        # Verify it has NO real credentials
        with open('.env.example', 'r') as f:
            example_content = f.read()

        # Check for common credential patterns
        if 'AIzaSy' in example_content or '@gmail.com' in example_content:
            print_error(".env.example contains REAL credentials! Replace with placeholders!")
            all_good = False
        else:
            print_success(".env.example has safe placeholder values")
    else:
        print_error(".env.example not found")
        all_good = False

    return all_good

def check_sensitive_files():
    """Check for sensitive files that should not be committed"""
    print_header("Checking for Sensitive Files")

    all_good = True

    # Files that should NOT exist or should be ignored
    sensitive_paths = {
        '.env': 'Environment variables with secrets',
        '.cache/': 'Portfolio data and screening results',
        'portfolio.db': 'SQLite database',
        '.venv/': 'Python virtual environment',
        'frontend/node_modules/': 'Node.js dependencies',
    }

    for path, description in sensitive_paths.items():
        if Path(path).exists():
            # Check if it's in .gitignore
            with open('.gitignore', 'r') as f:
                gitignore = f.read()

            # Simple check - just see if the pattern is in gitignore
            base_pattern = path.rstrip('/')
            if base_pattern in gitignore or f"{base_pattern}/" in gitignore:
                print_success(f"{path} exists but is properly ignored ({description})")
            else:
                print_error(f"{path} exists and may NOT be ignored! ({description})")
                all_good = False
        else:
            print_success(f"{path} not found (won't be committed)")

    return all_good

def check_required_files():
    """Check that important files exist"""
    print_header("Checking Required Files")

    required_files = [
        'README.md',
        'requirements.txt',
        'config.ini',
        '.gitignore',
        '.env.example',
    ]

    all_good = True
    for filepath in required_files:
        if not check_file_exists(filepath, should_exist=True):
            all_good = False

    return all_good

def scan_for_secrets():
    """Scan Python files for hardcoded secrets"""
    print_header("Scanning for Hardcoded Secrets")

    suspicious_patterns = [
        'password',
        'api_key',
        'secret',
        'token',
        'credential',
    ]

    found_issues = []

    # Scan .py files
    for py_file in Path('.').rglob('*.py'):
        # Skip .venv and .cache directories
        if '.venv' in str(py_file) or '.cache' in str(py_file):
            continue

        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower()

            for pattern in suspicious_patterns:
                if f'{pattern} =' in content or f'{pattern}=' in content:
                    # Check if it's loading from environment
                    if 'os.getenv' in content or 'os.environ' in content or 'config.get' in content:
                        continue  # It's loading from env, which is good

                    # Potential hardcoded value
                    found_issues.append((py_file, pattern))

    if found_issues:
        print_warning(f"Found {len(found_issues)} potential hardcoded secrets:")
        for filepath, pattern in found_issues:
            print(f"  {filepath}: '{pattern}'")
        print_warning("Review these files to ensure secrets are loaded from environment variables")
        return False
    else:
        print_success("No hardcoded secrets detected")
        return True

def main():
    print(f"\n{BLUE}╔{'═'*68}╗{RESET}")
    print(f"{BLUE}║{' '*20}GIT SAFETY VERIFICATION{' '*25}║{RESET}")
    print(f"{BLUE}╚{'═'*68}╝{RESET}")

    checks = [
        ("GitIgnore Configuration", check_gitignore),
        ("Environment Files", check_env_file),
        ("Sensitive Files", check_sensitive_files),
        ("Required Files", check_required_files),
        ("Hardcoded Secrets", scan_for_secrets),
    ]

    results = []

    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Error in {name}: {e}")
            results.append((name, False))

    # Summary
    print_header("VERIFICATION SUMMARY")

    all_passed = all(result for _, result in results)

    for name, result in results:
        if result:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")

    print()

    if all_passed:
        print(f"{GREEN}{'='*70}{RESET}")
        print(f"{GREEN}✓ ALL CHECKS PASSED - Safe to push to Git!{RESET}")
        print(f"{GREEN}{'='*70}{RESET}")
        print(f"\n{BLUE}Next steps:{RESET}")
        print("  1. git init")
        print("  2. git add .")
        print("  3. git commit -m 'Initial commit'")
        print("  4. git remote add origin <your-repo-url>")
        print("  5. git push -u origin main")
        print(f"\n{BLUE}See GIT_SETUP_GUIDE.md for detailed instructions{RESET}\n")
        return 0
    else:
        print(f"{RED}{'='*70}{RESET}")
        print(f"{RED}✗ SOME CHECKS FAILED - DO NOT PUSH YET!{RESET}")
        print(f"{RED}{'='*70}{RESET}")
        print(f"\n{YELLOW}Fix the issues above before pushing to Git{RESET}")
        print(f"{YELLOW}Review GIT_SETUP_GUIDE.md for help{RESET}\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
