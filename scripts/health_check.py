import os
import sys
import urllib.error
import urllib.request

# Load .env file if present
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip("'\"")


REQUIRED_ENV = [
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_JWT_SECRET",
    "APP_SECRET_KEY",
    "ENCRYPTION_SECRET_KEY",
]


def ok(name: str, passed: bool, detail: str = "") -> bool:
    label = "PASS" if passed else "FAIL"
    print(f"{label} - {name} {detail}".rstrip())
    return passed


def env_present(key: str) -> bool:
    value = os.getenv(key, "")
    return bool(value.strip()) and value.lower() not in {"your_key_here", "changeme", "test", "none", "null"}


def http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return 200 <= response.status < 500
    except (urllib.error.URLError, TimeoutError):
        return False


def main() -> int:
    print("Running Numeris health checks...\n")
    checks = [ok(key, env_present(key)) for key in REQUIRED_ENV]
    checks.append(ok("Frontend package lock", os.path.exists("frontend/package-lock.json")))
    checks.append(ok("Backend importable files", os.path.exists("backend/main.py")))

    backend_url = os.getenv("NUMERIS_BACKEND_URL", "http://localhost:8000")
    if os.getenv("CHECK_RUNNING_SERVICES") == "1":
        checks.append(ok("Backend /health", http_ok(f"{backend_url}/health"), f"({backend_url})"))

    passed = sum(1 for item in checks if item)
    print(f"\nOverall: {passed}/{len(checks)} checks passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
