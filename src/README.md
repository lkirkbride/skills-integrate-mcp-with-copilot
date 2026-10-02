# Mergington High School Activities API

A FastAPI application that allows students to securely manage their own
extracurricular activity registrations.

## Features

- View all available extracurricular activities
- Create an account, sign in, sign out, and recover or change a password
- Sign up for activities while authenticated
- View and cancel only your own registrations
- Keep participant email addresses private

## Getting Started

1. Install the dependencies:

   ```
   pip install -r ../requirements.txt
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                               | Get public activity details and participant counts |
| POST   | `/accounts`                                 | Create a student account and recovery code         |
| POST   | `/sessions`                                 | Sign in and start a secure session                  |
| DELETE | `/sessions/current`                        | Sign out                                            |
| GET    | `/me`                                       | Get the signed-in student's registrations           |
| POST   | `/activities/{activity_name}/signup`        | Sign the current student up for an activity         |
| DELETE | `/activities/{activity_name}/unregister`    | Cancel the current student's registration           |
| PUT    | `/accounts/password`                       | Change the current student's password               |
| POST   | `/accounts/password-reset`                 | Reset a password using a recovery code              |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses a normalized email address as the identifier and stores
   salted password and recovery-code hashes.

All data, including accounts and sessions, is stored in memory, which means it
will be reset when the server restarts.

## Tests

Install the development dependencies and run the focused API tests:

```
pip install -r ../requirements-dev.txt
pytest ../tests
```
