"""Small regression test suite using Python's built-in unittest module."""

import unittest

import app as task_app
from app import app, TASKS


class StudentTaskManagerTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        TASKS.clear()
        task_app._next_task_id = 1
        with self.client.session_transaction() as session:
            session["_csrf_token"] = "test-csrf-token"

    def post_form(self, path, data=None):
        form_data = {"csrf_token": "test-csrf-token"}
        if data:
            form_data.update(data)
        return self.client.post(path, data=form_data, follow_redirects=False)

    def valid_task_data(self):
        return {"title": "Finish Flask assignment", "deadline": "2030-05-20", "priority": "High"}

    def test_dashboard_and_about_pages_load(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/about").status_code, 200)
        self.assertEqual(self.client.get("/tasks").status_code, 200)

    def test_valid_task_is_created(self):
        response = self.post_form("/tasks", self.valid_task_data())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(TASKS), 1)
        self.assertEqual(TASKS[0]["title"], "Finish Flask assignment")
        self.assertFalse(TASKS[0]["completed"])

    def test_blank_title_is_rejected(self):
        data = self.valid_task_data()
        data["title"] = "   "
        response = self.post_form("/tasks", data)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Task title is required", response.data)
        self.assertEqual(TASKS, [])

    def test_invalid_priority_is_rejected(self):
        data = self.valid_task_data()
        data["priority"] = "Urgent"
        response = self.post_form("/tasks", data)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Choose a valid priority", response.data)
        self.assertEqual(TASKS, [])

    def test_task_can_be_completed_and_deleted(self):
        self.post_form("/tasks", self.valid_task_data())
        complete_response = self.post_form("/tasks/1/complete")
        self.assertEqual(complete_response.status_code, 302)
        self.assertTrue(TASKS[0]["completed"])
        delete_response = self.post_form("/tasks/1/delete")
        self.assertEqual(delete_response.status_code, 302)
        self.assertEqual(TASKS, [])

    def test_post_without_csrf_token_is_rejected(self):
        response = self.client.post("/tasks", data=self.valid_task_data())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(TASKS, [])


if __name__ == "__main__":
    unittest.main()
