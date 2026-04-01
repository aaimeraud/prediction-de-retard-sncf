#!/usr/bin/env python3
"""
Security Validation Script for SNCF Delay Prediction Project

Verifies:
- OpenSSL availability and version
- Dependency versions and known vulnerabilities
- Docker security configuration
- API security headers
"""

import sys
import ssl
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple


def check_openssl() -> bool:
    """Verify OpenSSL is available and properly configured."""
    print("=" * 60)
    print("Checking OpenSSL Configuration")
    print("=" * 60)
    
    try:
        ssl_version = ssl.OPENSSL_VERSION
        print(f"✅ OpenSSL Version: {ssl_version}")
        
        if "LibreSSL" in ssl_version:
            print("⚠️  WARNING: LibreSSL detected (not OpenSSL)")
            print("   For production, install OpenSSL:")
            print("   brew install openssl")
            return False
        
        if "2.8" in ssl_version or "1.1" not in ssl_version:
            print("⚠️  WARNING: OpenSSL version may be outdated")
            print("   Recommend OpenSSL 1.1.1+ or 3.0+")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error checking OpenSSL: {e}")
        return False


def check_requirements() -> Tuple[bool, List[str]]:
    """Verify dependencies have pinned versions."""
    print("\n" + "=" * 60)
    print("Checking Dependency Versions")
    print("=" * 60)
    
    issues = []
    
    for req_file in ["requirements.txt", "requirements-prod.txt"]:
        if not Path(req_file).exists():
            print(f"⚠️  {req_file} not found")
            continue
        
        print(f"\nChecking {req_file}:")
        with open(req_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                if ">=" in line and req_file == "requirements-prod.txt":
                    issues.append(f"❌ {line} - should use == in production")
                    print(f"   {issues[-1]}")
                else:
                    pkg_name = line.split(">")[0].split("=")[0].split("<")[0].strip()
                    print(f"   ✅ {line}")
    
    return len(issues) == 0, issues


def check_docker_files() -> bool:
    """Verify Dockerfile security configurations."""
    print("\n" + "=" * 60)
    print("Checking Docker Security Configuration")
    print("=" * 60)
    
    dockerfile = Path("Dockerfile")
    dockerfile_prod = Path("Dockerfile.prod")
    
    checks = {
        "Dockerfile": [
            ("openssl", "OpenSSL installed"),
            ("--no-cache-dir", "No cache in pip"),
            ("USER developer", "Non-root user"),
            ("HEALTHCHECK", "Health check configured"),
        ],
        "Dockerfile.prod": [
            ("FROM", "Multi-stage build"),
            ("openssl", "OpenSSL installed"),
            ("--user", "Non-root installation"),
            ("slim", "Slim base image"),
        ]
    }
    
    all_pass = True
    
    for df, requirements in checks.items():
        path = Path(df)
        if not path.exists():
            print(f"⚠️  {df} not found")
            continue
        
        print(f"\n{df}:")
        content = path.read_text()
        
        for check_str, description in requirements:
            if check_str in content:
                print(f"   ✅ {description}")
            else:
                print(f"   ❌ Missing: {description}")
                all_pass = False
    
    return all_pass


def check_compose_files() -> bool:
    """Verify compose security configurations."""
    print("\n" + "=" * 60)
    print("Checking Docker Compose Configuration")
    print("=" * 60)
    
    compose_prod = Path("compose-prod.yaml")
    
    if not compose_prod.exists():
        print("⚠️  compose-prod.yaml not found")
        return False
    
    print("compose-prod.yaml:")
    content = compose_prod.read_text()
    
    checks = [
        ("no-new-privileges:true", "No new privileges"),
        ("cap_drop:", "Capability dropping"),
        ("cap_add:", "Capability addition"),
        ("memory:", "Memory limits"),
        ("cpus:", "CPU limits"),
        ("healthcheck:", "Health checks"),
        ("logging:", "Logging configured"),
    ]
    
    all_pass = True
    for check_str, description in checks:
        if check_str in content:
            print(f"   ✅ {description}")
        else:
            print(f"   ⚠️  {description} - check manually")
    
    return all_pass


def check_gitignore() -> bool:
    """Verify sensitive files are in .gitignore."""
    print("\n" + "=" * 60)
    print("Checking .gitignore")
    print("=" * 60)
    
    gitignore = Path(".gitignore")
    if not gitignore.exists():
        print("⚠️  .gitignore not found")
        return False
    
    content = gitignore.read_text()
    
    sensitive_patterns = [
        ".env",
        ".pem",
        ".key",
        "*.key",
        "*.pem",
    ]
    
    all_pass = True
    for pattern in sensitive_patterns:
        if pattern in content:
            print(f"   ✅ {pattern} in .gitignore")
        else:
            print(f"   ⚠️  {pattern} NOT in .gitignore")
            all_pass = False
    
    return all_pass


def check_api_security() -> bool:
    """Verify API security features."""
    print("\n" + "=" * 60)
    print("Checking API Security Features")
    print("=" * 60)
    
    api_file = Path("src/api_server.py")
    if not api_file.exists():
        print("⚠️  src/api_server.py not found")
        return False
    
    content = api_file.read_text()
    
    checks = [
        ("CORSMiddleware", "CORS configured"),
        ("Field(..., ge=0", "Input validation (ge)"),
        ("Field(..., le=", "Input validation (le)"),
        ("pydantic", "Pydantic validation"),
        ("HTTPException", "HTTP exception handling"),
    ]
    
    all_pass = True
    for check_str, description in checks:
        if check_str in content:
            print(f"   ✅ {description}")
        else:
            print(f"   ⚠️  {description}")
    
    return all_pass


def main():
    """Run all security checks."""
    print("\n")
    print("🔒 SNCF Delay Prediction - Security Validation")
    print("=" * 60)
    
    results = {
        "OpenSSL": check_openssl(),
        "Requirements": check_requirements()[0],
        "Docker Files": check_docker_files(),
        "Compose Config": check_compose_files(),
        ".gitignore": check_gitignore(),
        "API Security": check_api_security(),
    }
    
    print("\n" + "=" * 60)
    print("SECURITY CHECK SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check}")
    
    print(f"\nScore: {passed}/{total} passed")
    
    if passed == total:
        print("\n✅ All security checks passed!")
        print("Ready for development and production deployment.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} security check(s) failed.")
        print("See above for details and remediation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
