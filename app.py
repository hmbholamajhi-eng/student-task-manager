"""Student Task Manager — a small, beginner-friendly Flask application.

Tasks are kept in memory in TASKS. They disappear when the server restarts.
This is intentional for the initial minor-project version (no database).
"""

import os
import secrets
from datetime import date, datetime

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
# For local use, generate a random key at startup. Set FLASK_SECRET_KEY in the
# environment if you need sessions to remain valid across process restarts.
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

PRIORITIES = ("Low", "Medium", "High")
MAX_TITLE_LENGTH = 100

# In-memory storage: deliberately simple for this beginner project.
TASKS = []
_next_task_id = 1


@app.context_processor
def inject_template_values():
    """Make today's date and a CSRF token available to every template."""
    token = session.get("_csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return {"today": date.today(), "csrf_token": token}


@app.before_request
def protect_post_requests():
    """Reject cross-site or malformed POST requests with no valid form token."""
    if request.method != "POST":
        return None

    expected = session.get("_csrf_token", "")
    submitted = request.form.get("csrf_token", "")
    if not expected or not submitted or not secrets.compare_digest(expected, submitted):
        return render_template(
            "error.html",
            page_title="Request could not be verified",
            error_code=400,
            message="This form could not be verified. Refresh the page and try again.",
        ), 400
    return None


def sorted_tasks():
    """Return pending tasks first, sorted by deadline and then creation order."""
    return sorted(TASKS, key=lambda task: (task["completed"], task["deadline"], task["id"]))


def dashboard_context(form_data=None, form_errors=None):
    """Build the values displayed on the home page."""
    ordered = sorted_tasks()
    pending = [task for task in ordered if not task["completed"]]
    overdue = [task for task in pending if task["deadline"] < date.today()]
    return {
        "total_count": len(TASKS),
        "pending_count": len(pending),
        "completed_count": len(TASKS) - len(pending),
        "overdue_count": len(overdue),
        "upcoming_tasks": pending[:3],
        "priorities": PRIORITIES,
        "form_data": form_data or {},
        "form_errors": form_errors or [],
    }


def find_task_or_404(task_id):
    """Find a task by its integer ID, or show a friendly 404 page."""
    for task in TASKS:
        if task["id"] == task_id:
            return task
    abort(404)


@app.get("/")
def home():
    """Show the dashboard and task-creation form."""
    return render_template("index.html", **dashboard_context())


@app.route("/tasks", methods=["GET", "POST"])
def tasks():
    """List tasks (GET) or create a task (POST)."""
    if request.method == "GET":
        return render_template("tasks.html", tasks=sorted_tasks())

    global _next_task_id

    form_data = {
        "title": request.form.get("title", "").strip(),
        "deadline": request.form.get("deadline", "").strip(),
        "priority": request.form.get("priority", "").strip(),
    }
    errors = []

    if not form_data["title"]:
        errors.append("Task title is required.")
    elif len(form_data["title"]) > MAX_TITLE_LENGTH:
        errors.append(f"Task title must be {MAX_TITLE_LENGTH} characters or fewer.")

    parsed_deadline = None
    if not form_data["deadline"]:
        errors.append("Please choose a deadline.")
    else:
        try:
            parsed_deadline = datetime.strptime(form_data["deadline"], "%Y-%m-%d").date()
        except ValueError:
            errors.append("Enter a valid deadline date.")

    if not form_data["priority"]:
        errors.append("Please select a priority.")
    elif form_data["priority"] not in PRIORITIES:
        errors.append("Choose a valid priority: Low, Medium, or High.")

    if errors:
        return render_template(
            "index.html",
            **dashboard_context(form_data=form_data, form_errors=errors),
        ), 400

    TASKS.append(
        {
            "id": _next_task_id,
            "title": form_data["title"],
            "deadline": parsed_deadline,
            "priority": form_data["priority"],
            "completed": False,
        }
    )
    _next_task_id += 1

    flash(f'“{form_data["title"]}” was added to your tasks.', "success")
    return redirect(url_for("tasks"))


@app.post("/tasks/<int:task_id>/complete")
def toggle_task_complete(task_id):
    """Mark a task complete, or move it back to pending."""
    task = find_task_or_404(task_id)
    task["completed"] = not task["completed"]
    if task["completed"]:
        flash(f'“{task["title"]}” marked as complete.', "success")
    else:
        flash(f'“{task["title"]}” moved back to pending.', "info")
    return redirect(url_for("tasks"))


@app.post("/tasks/<int:task_id>/delete")
def delete_task(task_id):
    """Delete a task using its ID."""
    task = find_task_or_404(task_id)
    TASKS.remove(task)
    flash(f'“{task["title"]}” was deleted.', "success")
    return redirect(url_for("tasks"))


@app.get("/about")
def about():
    """Explain the app's purpose and its route structure."""
    return render_template("about.html")


@app.errorhandler(404)
def not_found(_error):
    return render_template(
        "error.html",
        page_title="Page not found",
        error_code=404,
        message="We couldn't find that page or task. It may have been removed.",
    ), 404


if __name__ == "__main__":
    # Debug mode is off by default. Enable it locally with FLASK_DEBUG=1 if needed.
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
