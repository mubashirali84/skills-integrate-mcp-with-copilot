# Mergington High School Activities

A small FastAPI application for viewing extracurricular activities. Students can
browse activities and participant lists; teachers must sign in before changing
registrations.

## Features

- View all available extracurricular activities
- View participant lists without signing in
- Teacher-only student sign-up and unregistration
- Teacher sign-in with salted PBKDF2 password hashes and an HTTP-only session cookie

## Getting Started

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. From the `src` directory, run the application:

   ```
   uvicorn app:app --reload
   ```

3. Open your browser and go to:
   - Activities page: http://localhost:8000/
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## Set up teacher accounts

The checked-in `teacher_accounts.json` starts empty. Create an account by
running this command from the repository root:

```bash
python src/manage_teachers.py <username>
```

The command prompts for the teacher's password twice and writes only a
random-salt PBKDF2 hash to `teacher_accounts.json`; plaintext passwords are
never stored. Review and commit the updated JSON file so the account is
available to the application. Do not put teacher passwords in source control.

Teacher sessions are held in server memory and expire after eight hours. They
are cleared when the server restarts, so this demo should run as a single
server process.

## Run tests

```bash
python -m unittest discover -s src -p 'test_*.py' -v
```

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                        | Get all activities, details, participant lists, and capacity       |
| GET    | `/auth/session`                                                       | Check whether the current browser has a teacher session              |
| POST   | `/auth/login`                                                         | Sign in using a JSON `username` and `password`                       |
| POST   | `/auth/logout`                                                        | Sign out and revoke the current session                              |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu`    | Teacher-only student sign-up                                        |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu`| Teacher-only unregistration                                          |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity and registration data is stored in memory, so it resets when the
server restarts. Teacher account hashes are stored in `teacher_accounts.json`.
