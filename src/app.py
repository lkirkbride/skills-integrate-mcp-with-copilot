"""
High School Management System API

A FastAPI application that allows authenticated students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import os
import re
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

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

users = {}
sessions = {}

SESSION_COOKIE = "mergington_session"
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


class AccountCredentials(BaseModel):
    email: str
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class PasswordReset(BaseModel):
    email: str
    recovery_code: str
    new_password: str


def normalize_email(email: str) -> str:
    normalized = email.strip().casefold()
    if not EMAIL_PATTERN.fullmatch(normalized):
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    return normalized


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )


def hash_secret(secret: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        secret.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
    )


def verify_secret(secret: str, salt: bytes, expected_hash: bytes) -> bool:
    return hmac.compare_digest(hash_secret(secret, salt), expected_hash)


def create_session(email: str, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    sessions[token] = email
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=False,
        samesite="strict",
        max_age=60 * 60 * 8,
    )


def revoke_sessions(email: str) -> None:
    for token, session_email in list(sessions.items()):
        if session_email == email:
            del sessions[token]


def get_current_student(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE)
    email = sessions.get(token) if token else None
    if email is None:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    return email


def public_activity(activity: dict) -> dict:
    return {
        "description": activity["description"],
        "schedule": activity["schedule"],
        "max_participants": activity["max_participants"],
        "participant_count": len(activity["participants"]),
    }


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return {
        name: public_activity(activity)
        for name, activity in activities.items()
    }


@app.post("/accounts", status_code=201)
def create_account(credentials: AccountCredentials):
    email = normalize_email(credentials.email)
    validate_password(credentials.password)
    if email in users:
        raise HTTPException(status_code=409, detail="An account already exists for this email")

    password_salt = secrets.token_bytes(16)
    recovery_salt = secrets.token_bytes(16)
    recovery_code = secrets.token_urlsafe(18)
    users[email] = {
        "password_salt": password_salt,
        "password_hash": hash_secret(credentials.password, password_salt),
        "recovery_salt": recovery_salt,
        "recovery_hash": hash_secret(recovery_code, recovery_salt),
    }
    return {
        "message": "Account created. Save your recovery code, then sign in.",
        "recovery_code": recovery_code,
    }


@app.post("/sessions")
def login(credentials: AccountCredentials, response: Response):
    email = normalize_email(credentials.email)
    user = users.get(email)
    if user is None or not verify_secret(
        credentials.password,
        user["password_salt"],
        user["password_hash"],
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    revoke_sessions(email)
    create_session(email, response)
    return {"message": "Signed in", "email": email}


@app.get("/session")
def get_session(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    token = request.cookies.get(SESSION_COOKIE)
    email = sessions.get(token) if token else None
    return {"authenticated": email is not None, "email": email}


@app.delete("/sessions/current")
def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        sessions.pop(token, None)
    response.delete_cookie(SESSION_COOKIE, samesite="strict")
    return {"message": "Signed out"}


@app.put("/accounts/password")
def change_password(
    password_change: PasswordChange,
    response: Response,
    email: str = Depends(get_current_student),
):
    validate_password(password_change.new_password)
    user = users[email]
    if not verify_secret(
        password_change.current_password,
        user["password_salt"],
        user["password_hash"],
    ):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    password_salt = secrets.token_bytes(16)
    user["password_salt"] = password_salt
    user["password_hash"] = hash_secret(password_change.new_password, password_salt)
    revoke_sessions(email)
    response.delete_cookie(SESSION_COOKIE, samesite="strict")
    return {"message": "Password changed. Sign in again."}


@app.post("/accounts/password-reset")
def reset_password(password_reset: PasswordReset):
    email = normalize_email(password_reset.email)
    validate_password(password_reset.new_password)
    user = users.get(email)
    if user is None or not verify_secret(
        password_reset.recovery_code,
        user["recovery_salt"],
        user["recovery_hash"],
    ):
        raise HTTPException(status_code=400, detail="Invalid email or recovery code")

    password_salt = secrets.token_bytes(16)
    recovery_salt = secrets.token_bytes(16)
    recovery_code = secrets.token_urlsafe(18)
    user["password_salt"] = password_salt
    user["password_hash"] = hash_secret(password_reset.new_password, password_salt)
    user["recovery_salt"] = recovery_salt
    user["recovery_hash"] = hash_secret(recovery_code, recovery_salt)
    revoke_sessions(email)
    return {
        "message": "Password reset. Save your new recovery code, then sign in.",
        "recovery_code": recovery_code,
    }


@app.get("/me")
def get_dashboard(
    response: Response,
    email: str = Depends(get_current_student),
):
    response.headers["Cache-Control"] = "no-store"
    registrations = [
        {
            "name": name,
            "description": activity["description"],
            "schedule": activity["schedule"],
        }
        for name, activity in activities.items()
        if email in activity["participants"]
    ]
    return {"email": email, "registrations": registrations}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str = Depends(get_current_student),
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
    email: str = Depends(get_current_student),
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
