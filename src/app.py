"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from teacher_auth import hash_password

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(current_dir,
          "static")), name="static")

TEACHER_ACCOUNTS_FILE = Path(__file__).with_name("teacher_accounts.json")
TEACHER_SESSION_COOKIE = "teacher_session"
TEACHER_SESSION_MAX_AGE = 8 * 60 * 60
PASSWORD_HASH_ITERATIONS = 310_000
teacher_sessions: dict[str, tuple[str, float]] = {}

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


class TeacherLogin(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


def load_teacher_accounts() -> list[dict[str, str]]:
    with TEACHER_ACCOUNTS_FILE.open(encoding="utf-8") as accounts_file:
        accounts = json.load(accounts_file)

    if not isinstance(accounts, list):
        raise ValueError("Teacher accounts file must contain a JSON list")

    usernames = set()
    for account in accounts:
        if (
            not isinstance(account, dict)
            or not isinstance(account.get("username"), str)
            or not isinstance(account.get("salt"), str)
            or not isinstance(account.get("password_hash"), str)
        ):
            raise ValueError("Teacher account entries must include username, salt, and password_hash")
        if account["username"] in usernames:
            raise ValueError("Teacher usernames must be unique")
        usernames.add(account["username"])
        try:
            salt = bytes.fromhex(account["salt"])
            int(account["password_hash"], 16)
        except ValueError as error:
            raise ValueError("Teacher account salt and password hash must be hexadecimal") from error
        if len(salt) != 16 or len(account["password_hash"]) != 64:
            raise ValueError("Teacher account salt or password hash has an invalid length")

    return accounts


def require_teacher(request: Request) -> str:
    session_token = request.cookies.get(TEACHER_SESSION_COOKIE)
    session = teacher_sessions.get(session_token or "")
    if session is None or session[1] <= time.time():
        if session_token:
            teacher_sessions.pop(session_token, None)
        raise HTTPException(status_code=401, detail="Teacher sign-in required")
    return session[0]


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/auth/session")
def get_teacher_session(request: Request):
    session_token = request.cookies.get(TEACHER_SESSION_COOKIE)
    session = teacher_sessions.get(session_token or "")
    if session is not None and session[1] <= time.time():
        teacher_sessions.pop(session_token, None)
        session = None
    username = session[0] if session else None
    return {"authenticated": username is not None, "username": username}


@app.post("/auth/login")
def login_teacher(credentials: TeacherLogin, request: Request, response: Response):
    accounts = load_teacher_accounts()
    account = next(
        (entry for entry in accounts if entry["username"] == credentials.username),
        None,
    )
    salt = bytes.fromhex(account["salt"]) if account else bytes(16)
    candidate_hash = hash_password(credentials.password, salt)
    expected_hash = account["password_hash"] if account else "0" * 64

    if not hmac.compare_digest(candidate_hash, expected_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    session_token = secrets.token_urlsafe(32)
    teacher_sessions[session_token] = (
        credentials.username,
        time.time() + TEACHER_SESSION_MAX_AGE,
    )
    response.set_cookie(
        key=TEACHER_SESSION_COOKIE,
        value=session_token,
        max_age=TEACHER_SESSION_MAX_AGE,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
        path="/",
    )
    return {"message": "Signed in successfully", "username": credentials.username}


@app.post("/auth/logout")
def logout_teacher(request: Request, response: Response):
    session_token = request.cookies.get(TEACHER_SESSION_COOKIE)
    if session_token:
        teacher_sessions.pop(session_token, None)
    response.delete_cookie(
        key=TEACHER_SESSION_COOKIE,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
        path="/",
    )
    return {"message": "Signed out successfully"}


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    _teacher: str = Depends(require_teacher),
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    _teacher: str = Depends(require_teacher),
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
