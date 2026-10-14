import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import app
from teacher_auth import create_password_hash


class TeacherAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.original_activities = deepcopy(app.activities)
        app.teacher_sessions.clear()
        self.temp_dir = tempfile.TemporaryDirectory()
        accounts_file = Path(self.temp_dir.name) / "teacher_accounts.json"
        salt, password_hash = create_password_hash("correct horse battery staple")
        accounts_file.write_text(
            json.dumps(
                [
                    {
                        "username": "teacher",
                        "salt": salt,
                        "password_hash": password_hash,
                    }
                ]
            ),
            encoding="utf-8",
        )
        self.accounts_file_patch = patch.object(app, "TEACHER_ACCOUNTS_FILE", accounts_file)
        self.accounts_file_patch.start()
        self.client = TestClient(app.app)

    def tearDown(self):
        self.client.close()
        self.accounts_file_patch.stop()
        self.temp_dir.cleanup()
        app.teacher_sessions.clear()
        app.activities.clear()
        app.activities.update(self.original_activities)

    def test_activity_list_and_participants_are_public(self):
        response = self.client.get("/activities")

        self.assertEqual(response.status_code, 200)
        self.assertIn("michael@mergington.edu", response.json()["Chess Club"]["participants"])

    def test_signup_and_unregister_require_teacher_session(self):
        signup = self.client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "new.student@mergington.edu"},
        )
        unregister = self.client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": "michael@mergington.edu"},
        )

        self.assertEqual(signup.status_code, 401)
        self.assertEqual(unregister.status_code, 401)
        self.assertNotIn(
            "new.student@mergington.edu",
            app.activities["Chess Club"]["participants"],
        )

    def test_teacher_can_sign_in_and_manage_registrations(self):
        login = self.client.post(
            "/auth/login",
            json={
                "username": "teacher",
                "password": "correct horse battery staple",
            },
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("httponly", login.headers["set-cookie"].lower())
        self.assertIn("samesite=strict", login.headers["set-cookie"].lower())

        signup = self.client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "new.student@mergington.edu"},
        )
        unregister = self.client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": "new.student@mergington.edu"},
        )

        self.assertEqual(signup.status_code, 200)
        self.assertEqual(unregister.status_code, 200)

    def test_invalid_credentials_do_not_create_session(self):
        response = self.client.post(
            "/auth/login",
            json={"username": "teacher", "password": "wrong password"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertFalse(self.client.get("/auth/session").json()["authenticated"])

    def test_logout_revokes_teacher_session(self):
        self.client.post(
            "/auth/login",
            json={
                "username": "teacher",
                "password": "correct horse battery staple",
            },
        )
        logout = self.client.post("/auth/logout")
        signup = self.client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "new.student@mergington.edu"},
        )

        self.assertEqual(logout.status_code, 200)
        self.assertEqual(signup.status_code, 401)

    def test_teacher_session_expires_after_eight_hours(self):
        with patch("app.time.time", return_value=1000):
            self.client.post(
                "/auth/login",
                json={
                    "username": "teacher",
                    "password": "correct horse battery staple",
                },
            )

        expired_time = 1000 + app.TEACHER_SESSION_MAX_AGE + 1
        with patch("app.time.time", return_value=expired_time):
            session = self.client.get("/auth/session")
            signup = self.client.post(
                "/activities/Chess%20Club/signup",
                params={"email": "new.student@mergington.edu"},
            )

        self.assertFalse(session.json()["authenticated"])
        self.assertEqual(signup.status_code, 401)


if __name__ == "__main__":
    unittest.main()
