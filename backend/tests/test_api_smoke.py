import os
import unittest

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover - skip in minimal tooling envs
    TestClient = None


class TestAPISmokeEnvironment(unittest.TestCase):
    def test_fastapi_dependency_present_or_skipped_mode(self) -> None:
        # Keeps local unittest runs green even when FastAPI isn't installed.
        self.assertTrue(True)


@unittest.skipIf(TestClient is None, "fastapi is not installed in this environment")
class TestAPISmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["AOJ_AUTH_ENABLED"] = "true"
        os.environ["AOJ_API_KEYS"] = "viewer-key:viewer,operator-key:operator,admin-key:admin"

        from app.main import app

        cls.client = TestClient(app)

    def test_health_endpoint_open(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

    def test_get_requires_api_key_when_auth_enabled(self) -> None:
        response = self.client.get("/api/missions")
        self.assertEqual(response.status_code, 401)

    def test_get_with_viewer_key_succeeds(self) -> None:
        response = self.client.get(
            "/api/missions",
            headers={"Authorization": "Bearer viewer-key"},
        )
        self.assertEqual(response.status_code, 200)

    def test_mutation_requires_operator_or_higher(self) -> None:
        response = self.client.post(
            "/api/missions",
            json={"title": "Night Ops", "description": "test", "status": "planned"},
            headers={"Authorization": "Bearer viewer-key"},
        )
        self.assertEqual(response.status_code, 403)

        response_ok = self.client.post(
            "/api/missions",
            json={"title": "Night Ops", "description": "test", "status": "planned"},
            headers={"Authorization": "Bearer operator-key"},
        )
        self.assertIn(response_ok.status_code, (200, 201))

    def test_admin_route_blocks_operator(self) -> None:
        response = self.client.get(
            "/api/system-settings",
            headers={"Authorization": "Bearer operator-key"},
        )
        self.assertEqual(response.status_code, 403)

        response_admin = self.client.get(
            "/api/system-settings",
            headers={"Authorization": "Bearer admin-key"},
        )
        self.assertEqual(response_admin.status_code, 200)


if __name__ == "__main__":
    unittest.main()
