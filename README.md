# KidEarn

KidEarn is a parent-child finance learning application. Parents can link a
child's account, assign chores with reward amounts and due dates, and review
the child's submissions. Children can see chores assigned to them and, after
approval, see the resulting reward in their wallet history.

## Core feature

The chore workflow is:

1. A parent links an existing Kid account by username.
2. The parent creates, reads, updates, or deletes their chores and sets the
   assigned child, due date, and reward amount.
3. The child sees only chores assigned through their parent link, then submits
   completed work.
4. The parent reviews the submission. An approved chore creates a reward entry
   for that child; rejected work can be corrected and resubmitted.

Only authenticated parents can manage chores or review work. Children can only
see and submit their own assignments. Rewards are virtual records; KidEarn
does not process real-money transfers.

## Setup

Requirements: Python 3.12 or later and PostgreSQL.

1. Create and activate a virtual environment, then install dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

2. Copy the example environment file and edit the local copy. Generate a
   unique Django key with
   `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`.
   Set your PostgreSQL database name, role, password, host, and port in `.env`.
   Never commit `.env` or send its secrets in messages.

   ```powershell
   Copy-Item .env.example .env
   ```

3. Create the PostgreSQL database and role if they do not already exist. Ensure
   the role in `.env` has permission to use the database.

4. Apply migrations, create an administrator, and run Django:

   ```powershell
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```

5. Visit `http://127.0.0.1:8000/`. Register a Parent and a Kid account. From
   the parent dashboard, link the Kid account by username, assign chores, and
   use the kid dashboard to submit work and review rewards.

## Tests

The test suite can run with PostgreSQL credentials from `.env`. For an isolated
SQLite test run in PowerShell:

```powershell
$env:DJANGO_SECRET_KEY = "local-test-key"
$env:DJANGO_DEBUG = "True"
$env:DB_ENGINE = "django.db.backends.sqlite3"
$env:DB_NAME = ":memory:"
python manage.py test
```

## Branch workflow

`main` is the stable branch. Feature work starts from `develop` in
`feature/<feature-name>` branches and is merged to `develop` through pull
requests. Completed increments are promoted from `develop` to `main` through a
pull request.
