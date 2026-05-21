import json
import os
import sys
import urllib.error
import urllib.request


BASE_URL = os.getenv("NUMERIS_BACKEND_URL", "http://localhost:8000")


def request(path: str) -> tuple[int, object]:
    url = f"{BASE_URL}{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body) if body else {}


def check(name: str, passed: bool) -> bool:
    print(f"{'PASS' if passed else 'FAIL'} - {name}")
    return passed


def main() -> int:
    tests = []
    status, health = request("/health")
    tests.append(check("health endpoint", status == 200 and health.get("platform") == "Numeris"))

    status, dashboard = request("/api/numeris")
    tests.append(check("dashboard endpoint is gated (unauthorized returns 401/403)", status in (401, 403)))

    status, news = request("/api/geopolitical-news")
    tests.append(check("geopolitical news endpoint is gated (unauthorized returns 401/403)", status in (401, 403)))

    status, search = request("/api/market/search?query=AAPL")
    tests.append(check("market search endpoint is gated (unauthorized returns 401/403)", status in (401, 403)))

    status, candles = request("/api/market/candles?symbol=AAPL")
    tests.append(check("market candles endpoint is gated (unauthorized returns 401/403)", status in (401, 403)))

    passed = sum(1 for item in tests if item)
    print(f"\nOverall: {passed}/{len(tests)} integration tests passed")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
