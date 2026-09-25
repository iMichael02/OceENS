# OcéEns II

Teaching evaluation platform built for the EPF engineering school.

## Overview

The **OcéEns II** application lets program managers, facilitators, campus management and admins create and manage evaluation surveys (*sondages*) for EPF's different programs, and lets students answer them. Answers can be exported, visualized, and summarized (*synthèses*) via an LLM. The interface follows EPF's official design system.

### Tech stack

| Component | Technology |
|-----------|-------------|
| **Framework** | FastAPI (Python 3.12) |
| **Authentication** | Microsoft Entra ID (Azure AD) via OAuth 2.0 / MSAL, Microsoft Graph |
| **Database** | SQLite (via SQLAlchemy + SQLModel) |
| **Templating** | Jinja2 (server-side rendering) |
| **Frontend** | HTML / CSS / JavaScript, no framework |
| **Server** | Uvicorn |
| **Logging** | Python's standard `logging` module, via the Uvicorn handlers |
| **Exports** | Pandas (CSV) |
| **Verbatim summaries** | Separate daemon, calls an LLM (`requests-cache`, `markdown-it-py`) |

---

## Roles

- `student`: answers the surveys they're enrolled in.
- `program_manager:<code>`: manages the surveys of their program(s).
- `facilitator:<code>`: runs the surveys of their program(s).
- `campus_manager:<campus>`: campus-wide scope.
- `admin`: general administration.

A user can hold several roles, each with its own scope (program codes or campuses separated by `;`).

---

## Main pages and routes

| Route | Description |
|-------|-------------|
| `/` | Home, authentication hub. |
| `/login`, `/auth/callback`, `/logout` | Microsoft Entra ID authentication flow. |
| `/dev/login` | Development login: user-picker page on `GET`, login on `POST` (only with `AUTH_MODE=dev`, see [Development-mode authentication](#development-mode-authentication)). |
| `/dashboard/student` | Student dashboard. |
| `/dashboard/program-manager` | Program manager dashboard. |
| `/dashboard/facilitator` | Facilitator dashboard. |
| `/dashboard/campus-manager` | Campus management dashboard. |
| `/dashboard/teachers/analytics` | Satisfaction score per teacher, filterable by year / semester / program. Available to the `campus_manager` and `program_manager` roles, scoped to each one's own perimeter. |
| `/dashboard/admin` | Admin dashboard. |
| `/dashboard/survey-create` | Survey creation / setup. |
| `/api/surveys/{survey_id}` | Questionnaire (answering the survey). |
| `/api/surveys/{survey_id}/status` | Change a survey's status. |
| `/api/surveys/{survey_id}/students` | Manage the students enrolled in a survey. |
| `/api/surveys/{survey_id}/export` | CSV export of the answers. |
| `/api/surveys/{survey_id}/visualisation` | Visualization of the answers. Accepts `?teacher=<name>` to land already filtered on a teacher. |
| `/api/surveys/{survey_id}/generate-summaries` | Trigger LLM summary generation. |
| `/api/surveys/{survey_id}/destroy-summaries` | Delete generated summaries. |
| `/api/users/{user_id}/role` | Change a user's role. |
| `/backend/prompts` | List of LLM prompts (admin only). |
| `/backend/prompts/new` | Prompt creation form. |
| `/backend/prompts/{id}/edit` | Prompt edit form. |
| `/api/prompts` | Create a prompt (POST, form). |
| `/api/prompts/{id}` | Edit a prompt (PUT, fetch). Blocked if the prompt is referenced by any `summaries`. |
| `/api/prompts/{id}/delete` | Delete a prompt (POST, form). Blocked if the prompt is referenced by any `summaries`. |

---

## Installation and startup

### Prerequisites

- Python 3.12
- A configured `.env` file (see [Configuration](#configuration))

### Quickstart (fresh clone, no credentials)

`AUTH_MODE=dev` (the default in `.env.example`) needs no Entra credentials, and the app runs with no LLM key too — summaries are simply unavailable until one is set (see [Configuration](#configuration)).

```bash
git clone <repo-url>
cd OceENS
cp .env.example .env
```

Then either run it with Docker Compose:

```bash
docker compose up --build
```

or without Docker, see [Manual installation](#manual-installation-no-docker) below. Either way, open **http://localhost:8000**.

`docker compose up` fails with `env file .env not found` if you skip the `cp .env.example .env` step — that's intended.

### With Docker Compose (recommended)

```bash
docker compose up --build
```

The SQLite database is persisted to a local directory. By default `./database/`; to point elsewhere, set `LOCAL_DATABASE_DIR` in `.env` or in the environment:

```env
LOCAL_DATABASE_DIR=/path/to/database
```

**Development** — source mounted as a volume, for iterating without rebuilding the image:

```bash
docker run -p 8000:8000 --env-file .env -v oceens_db:/app/database -v ./import:/app/import -v .:/app oceens:1.0 \
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> The `Dockerfile`'s `CMD` does **not** include `--reload`. Bind-mounting the source with `-v .:/app` only enables live reload if you also override the container's command to add `--reload`, as above. For a production-style run of the same image, drop both the bind mount and `--reload`.

> The SQLite database is persisted in the `oceens_db` Docker volume (`/app/database`).
> The `.env` file is never copied into the image: it's passed via `--env-file` at launch.

### Manual installation (no Docker)

1. **Clone the project**

   ```bash
   git clone <repo-url>
   cd OceENS
   ```

2. **Create and activate a virtual environment**

   ```bash
   python3 -m venv .venv
   .venv\Scripts\activate       # Windows
   source .venv/bin/activate    # Linux / macOS
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the database**
   Create a `database/` folder and place `db_oceens.db` in it, or let `seed_all_if_necessary()` initialize an empty database on first startup.

5. **Run the application**:

   ```bash
   fastapi dev
   ```

   Or directly with Uvicorn:

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

   In production, `launch.sh` runs the application and the summaries daemon in separate `screen` sessions.

6. **(Optional) Run the LLM summaries daemon**:

   ```bash
   python summaries_generator_daemon.py
   ```

   This process loops, writes to the database, and contacts an external LLM service: only run it when needed.

   > Setting `RUN_SUMMARIES_DAEMON=1` in `.env` makes Uvicorn launch the
   > daemon automatically as a separate process at startup (and stop it on
   > shutdown). Use this in a Docker production deployment.
   > Note: `launch.sh` (no Docker) already manages the daemon in its own `screen` session.

7. Open your browser at **http://localhost:8000**.

---

## Logging

Application logs use Python's standard `logging` module and the `uvicorn`
logger. This lets messages from the application, from `auth.py` and from
`seed.py` inherit the format, colors and handlers already configured by the
server.

Levels are used by severity:

| Level | Usage |
|--------|-------------|
| `DEBUG` | Detailed information useful during development and seeding. |
| `INFO` | Startup, shutdown, and normal application operations. |
| `WARNING` | An expected resource is missing, or a non-blocking situation. |
| `ERROR` / `EXCEPTION` | An operation failed; `logger.exception()` keeps the traceback. |
| `CRITICAL` | A required piece of configuration is missing, preventing startup. |

Example:

```python
import logging

logger = logging.getLogger("uvicorn")

logger.info("Operation complete")

try:
    risky_operation()
except Exception:
    logger.exception("Operation failed")
```

New diagnostics should use the appropriate logger rather than `print()`.
The application log level is currently set to `DEBUG` in
`core/dependencies.py`. Application logs go through the Uvicorn handler,
usually written to `stderr`; with a separate redirect, use e.g. `2>
error.log` to capture them.

---

## Configuration

Copy `.env.example` to `.env` and fill in what you need:

```bash
cp .env.example .env
```

`.env.example` is the authoritative reference — every environment variable
the application reads is listed there with inline comments. Summary:

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `AUTH_MODE` | No | `entra` | `entra` or `dev` (case/whitespace-insensitive); any other value stops the app at startup. See [Development-mode authentication](#development-mode-authentication). |
| `DEV_LOGIN_KEY` | No | unset (open login) | `dev` mode only; ignored (with a warning) in `entra` mode. |
| `ALLOWED_DOMAINS` | No | `epf.fr,epfedu.fr` in `dev`, empty in `entra` | Comma-separated allowed email domains. |
| `SECRET_KEY` | See [SECRET_KEY](#secret_key) | unset | Session cookie signing key. |
| `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`, `ENTRA_TENANT_ID` | Yes, in `entra` mode | unset | Azure Entra ID app registration; missing any of them exits the app with code 1 in `entra` mode. |
| `REDIRECT_URI` | No | `https://localhost/auth/callback` | Entra OAuth callback URL. |
| `LOCAL_DATABASE_DIR` | No | `./database` | Directory holding the SQLite file. With Docker Compose, also the host directory mounted into the container. |
| `LLM_API_KEY` | No | unset | Default LLM provider's key. Empty: the app starts, but requested summaries are marked as a configuration error. |
| `RUN_SUMMARIES_DAEMON` | No | unset | `1`/`true`/`yes`/`on` launches the summaries daemon alongside Uvicorn as a separate process. Leave unset in production with `launch.sh`, which already manages the daemon. |

### `SECRET_KEY`

`SECRET_KEY` signs the session cookies: whoever knows it can forge an admin
session. It is **required outside `AUTH_MODE=dev`**: if it's missing or
empty, the application logs a critical error and exits at startup (exit
code 1). Generate one with
`python -c "import secrets; print(secrets.token_urlsafe(32))"`.

In `AUTH_MODE=dev` it's optional: if it's missing, a random key is drawn on
every startup (with a warning) and sessions are lost on restart. If a known
`SECRET_KEY` is set in `dev` mode (shared, copied from an example, …),
anyone who knows it can forge a session cookie and bypass `DEV_LOGIN_KEY` —
`dev` mode accepts this because it's only meant for local use.

> [!CAUTION]
> Never commit the `.env` file. It's already listed in `.gitignore`, along with the `*.db` files (`database/db_oceens.db`, `cache_llm.db`).

---

## LLM providers (verbatim summaries)

Verbatim summaries are generated by an LLM. The provider is **configurable
from the UI** (`/backend/providers`, admin only), with no code changes. The
default provider is **Ollama EPF**
(`https://locallm.mde.epf.fr/ollama`), created automatically on first
startup.

### Supported API types

| `api_type` | Covers |
|------------|--------|
| `ollama`    | Ollama servers (local, EPF, third-party) |
| `openai`    | OpenAI **and any OpenAI-compatible endpoint**: vLLM, Groq, Mistral, LM Studio… |
| `anthropic` | Anthropic's Claude API |

### Security principle: no key in the database

The SQLite database is not encrypted and ends up in backups. **No API key
is therefore stored in it.** The `llm_providers` table only holds the
*name* of the environment variable (`api_key_env`, e.g. `OPENAI_API_KEY`);
the value stays in `.env` and is only resolved at call time. This name is
validated against a whitelist (`LLM_*` or `*_API_KEY`) to prevent pointing
at a system secret (`SECRET_KEY`, `ENTRA_CLIENT_SECRET`…).

### Adding a new provider

1. **Add the key to `.env`** with a compliant name (`LLM_*` or `*_API_KEY`):

   ```env
   OPENAI_API_KEY=sk-...
   ```

2. **Restart the summaries daemon** (`.env` variables are only read at
   startup):

   ```bash
   python summaries_generator_daemon.py
   ```

3. **Create the provider** in `/backend/providers` → *+ New provider*:
   fill in the name, API type, base URL, env variable name
   (`OPENAI_API_KEY`), and a default model. The **"key present /
   missing"** indicator confirms the variable is loaded. The **Test**
   button checks that the URL and key respond, then sends a one-token
   generation to confirm the account can actually generate (see below).

4. **Link a prompt** to the provider: in `/backend/prompts`, a `<select>`
   lets you choose a prompt's provider. A prompt with no provider
   (`provider_id` NULL) falls back to Ollama EPF automatically.

> [!NOTE]
> A provider referenced by at least one prompt cannot be deleted (so as
> not to break that prompt's configuration).

### Exhausted credit and other provider errors

Each provider reports failures in a different format: exhausted credit is
a `429 insufficient_quota` at OpenAI, but a `400 "Your credit balance is
too low"` at Anthropic. `services/llm_client.py` normalizes these
responses into categories (`quota`, `rate_limit`, `auth`, `model`,
`server`) and derives a readable message:

> ⚠️ Provider credit or quota exhausted: the key is valid but the account
> can no longer generate. Top up the account or choose another provider.
> (provider OpenAI, model gpt-4o-mini, HTTP 429)

This message is written to `Summary.metadata_text` in place of the raw
JSON — so it's visible directly from the UI when a summary fails. The
provider's raw response stays in the daemon logs for diagnosis.

> [!IMPORTANT]
> The **Test** button doesn't just list models: at both OpenAI and
> Anthropic, `GET /v1/models` still responds perfectly fine with a
> zero balance. A one-token generation ping (negligible cost) is
> therefore sent next — it's the only way to catch exhausted credit
> **before** launching a summary run.

---

## Summary cost

Each summary's cost is **measured, not estimated**. At generation time, the
daemon records the token counters returned by the provider
(`Summary.input_tokens`, `output_tokens`, `model_used`): that's the only
chance to capture them, no API lets you request them again afterwards. The
amount is then obtained by matching these counters against the pricing
table.

> [!NOTE]
> This section replaces the former `llm-utils/token-counting/` scripts,
> which counted tokens in the **repository's source code** and multiplied
> them by a hardcoded rate. That measurement said nothing about the
> application's actual spend. Tracking now covers calls that are actually
> billed.

### Pricing table — `/backend/llm/prices`

Prices live in the database (`llm_model_prices` table), in **dollars per
million tokens**, as providers publish them. They're editable from the
admin UI: no need to ship a release to track a price change, or to cover a
provider added locally.

Pre-filled at startup (`seed_model_prices`, idempotent — a manually
corrected price is never overwritten):

| Model | Input $/M | Output $/M |
| --- | ---: | ---: |
| `claude-opus-5` | 5.00 | 25.00 |
| `claude-sonnet-5` | 3.00 | 15.00 |
| `claude-haiku-4-5` | 1.00 | 5.00 |
| `gemma4:26b` (Ollama EPF, self-hosted) | 0.00 | 0.00 |

Prices for other providers (OpenAI, Mistral, Groq…) are **left to fill
in**: they aren't guessed. A provider-specific price takes precedence over
a generic price with the same model name.

### Viewing costs

| Where | What |
| --- | --- |
| `/backend/llm/costs` | Overall cost, broken down by survey and by model (admin) |
| 💰 button on a survey row | Cost of that survey's summaries |

### What isn't priced

A summary can't be priced when its counters are missing (generated before
this feature, or a provider that doesn't expose them) or when its model has
no registered price. It's then **counted separately**, never estimated nor
rounded to zero: a made-up amount would be more harmful than a missing one,
since it would display with the authority of a real amount. The screens
explicitly flag when a total is partial.

This is distinct from a cost of **zero**: self-hosted models genuinely cost
$0.00, which is not the same information as "unknown".

> [!IMPORTANT]
> Tracking starts when the feature went live: summaries generated before
> that have no counters in the database and cannot be priced
> retroactively.

---

## Project structure

```
OceENS/
├── main.py                       # FastAPI app factory, middlewares and router assembly
├── sondage_loader.py             # Load a full survey for export
├── survey_loader_from_xlsx.py    # Import surveys from an Excel file
├── summaries_generator_daemon.py # Asynchronous processing of LLM summaries (separate process)
├── launch.sh                     # Launch script (production, no Docker)
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Application Docker image
├── .dockerignore                 # Files excluded from the Docker build
├── .env                          # Environment variables (⚠️ not committed)
├── .gitignore                    # Files and folders ignored by Git
│
├── core/                         # Low-level access and security
│   ├── auth.py                   #   Microsoft Entra ID authentication (login, logout, callback) and development login
│   ├── database.py               #   SQLite engine and the SessionDep dependency
│   ├── security.py               #   Roles, scopes, access control
│   ├── dependencies.py           #   Shared Jinja templates and logger
│   └── seed.py                   #   Initial data and program synchronization
│
├── models/                       # SQLModel schema, one file per table
│   ├── __init__.py               #   Re-exports all classes (see its docstring)
│   └── User.py, Survey.py, ...
│
├── routers/                      # Routes split by business domain
│   ├── pages.py                  #   Home and per-role dashboards
│   ├── surveys.py                #   Surveys: CRUD, status, export, visualization
│   ├── students.py                #   Enrolling students in a survey
│   ├── users.py                   #   User role management
│   ├── summaries.py               #   Triggering LLM summaries
│   ├── prompts.py                #   Prompt administration
│   ├── survey_templates.py       #   Survey template administration
│   ├── sections_questions.py     #   Section and question administration
│   └── llm/                      #   LLM administration (unchanged URLs)
│       ├── _access.py            #     Shared access control for the LLM screens
│       ├── providers.py          #     LLM providers (CRUD + connection test)
│       ├── prices.py             #     Per-model pricing table
│       └── costs.py              #     Overall cost and per-survey cost
│
├── database/                     # Folder holding the database (ignored by Git)
│   └── db_oceens.db
│
├── services/                     # Business logic
│   ├── helpers.py                # Navigation, stats, filters, sorting
│   ├── visualisation_data.py     # Aggregations and visualization context
│   ├── llm_client.py             # Multi-provider LLM client (ollama/openai/anthropic)
│   ├── llm_costs.py              # Summary cost (measured tokens × pricing table)
│   └── export_csv.py             # CSV export of the answers
│
├── llm-utils/                    # LLM tools outside the application
│   └── README.md                 # (cost tracking moved into the app, see above)
│
├── templates/                    # HTML templates (Jinja2)
│   ├── index.html                     # Home / login page
│   ├── dashboard/
│   │   ├── admin.html
│   │   ├── student.html
│   │   ├── program_manager.html
│   │   ├── facilitator.html
│   │   ├── campus_manager.html
│   │   ├── teachers-analytics.html       # Teacher satisfaction (campus_manager, program_manager)
│   │   ├── survey.html                   # Answering a survey
│   │   ├── survey_create.html            # Survey creation
│   │   └── visualisation.html            # Answer visualization
│   ├── backend/                       # Admin pages (admin only)
│   │   ├── prompts.html               # LLM prompt list
│   │   ├── prompt_form.html           # Shared create/edit form
│   │   └── llm/                       # LLM screens (providers, prices, costs)
│   │       ├── providers.html
│   │       ├── provider_form.html
│   │       ├── prices.html            # Editable pricing table
│   │       └── costs.html             # Overall and per-survey cost
│   └── template_parts/                # Fragments shared across dashboards
│       ├── part_site_header.html
│       ├── part_dashboard_navigation.html
│       ├── part_theme_switcher.html
│       └── ...
│
├── static/
│   ├── css/                      # admin.css, student.css, program_manager.css, survey.css,
│   │                              # survey_create.css, visualisation.css, prompt_form.css,
│   │                              # llm_backend.css (LLM screens), theme.css, site_header.css,
│   │                              # dashboard_navigation.css, responsive.css
│   ├── js/
│   │   └── survey.js
│   └── img/
│
└── .venv/                         # Python virtual environment (not committed)
```

---

## Authentication (OAuth 2.0)

The authentication flow relies on **Microsoft Entra ID** via the MSAL library:

```
1. User clicks "Sign in"
   → FastAPI generates a random state (UUID, CSRF protection)
   → Redirect to the Microsoft login page

2. The user authenticates with Microsoft
   → Microsoft redirects to /auth/callback with a code + state

3. The server exchanges the code for an access token
   → Fetches user info via Microsoft Graph
   → Looks up the database for the role(s) and their scope
   → Creates the session {name, email, roles}
   → Redirects to the matching dashboard

4. On logout (/logout)
   → Session and cookies are cleared
   → Signed out on Microsoft's side too
   → Back to the home page
```

Authentication alone authorizes no business action: every route then
checks the role and scope (program or campus) via `require_roles()` and
its associated helpers.

---

## Development-mode authentication

To work on a fork without an Azure application, the **development login**
lets you log in as any user, with no proof of identity. It must **never**
be used in production.

| Variable | Role |
|----------|------|
| `AUTH_MODE` | `entra` (default) or `dev`, case/whitespace-insensitive. Any other value stops the application at startup. In `dev`, the `ENTRA_*` variables aren't needed. |
| `DEV_LOGIN_KEY` | Optional, `dev` mode only. If set, every login must supply it (`key` field), otherwise `401`. If unset, login is open. Ignored (with a warning) in `entra` mode. |
| `SECRET_KEY` | Optional in `dev`, required in `entra`. See [`SECRET_KEY`](#secret_key) for the full rule. |
| `ALLOWED_DOMAINS` | Also applies in `dev` (`403` for another domain); defaults to `epf.fr,epfedu.fr` in this mode. |

In `dev` mode, the session cookie is no longer HTTPS-only (`http://localhost` works), `/login` redirects to `/dev/login`, `/auth/callback` doesn't exist, and `/logout` clears the session then redirects to `/`. A warning is logged at startup. A red, non-dismissible banner shows at the top of every page that includes the shared header: it displays the logged-in address, offers "Switch user" (`/dev/login`), and shows "open to everyone" when `DEV_LOGIN_KEY` isn't set.

`POST /dev/login` expects a form with `email`, `name` (optional) and `key`
(if `DEV_LOGIN_KEY` is set). The user is fetched or created just like on
return from Entra: an unknown email becomes a new student. Without `name`,
the displayed name is built from the email
(`bob.leponge@epfedu.fr` → "Bob Leponge"). A new login replaces the
session: that's how you switch users.

In a browser, `GET /dev/login` shows the list of users in the database,
grouped by role name without scope (a user with no role appears under
`student`, a user with several roles appears under each of them). Clicking
a user logs in as them; a free-text field lets you use another address,
with an optional name. If `DEV_LOGIN_KEY` is set, a single key field shows
up and is used for every login on the page; the key is never stored in the
session. You come back to this page to switch users.

```bash
AUTH_MODE=dev DEV_LOGIN_KEY=my-key uvicorn main:app

# Log in as the seed admin; -c saves the session cookie
curl -i -c cookies.txt \
  -d email=antoine.gademer@epf.fr -d key=my-key \
  http://localhost:8000/dev/login

# Reuse the cookie (-b) for subsequent requests
curl -b cookies.txt -c cookies.txt -L http://localhost:8000/
```

---

## Notable features

### Teacher analytics

The `/dashboard/teachers/analytics` route (`campus_manager`,
`program_manager`) aggregates the satisfaction score per
`(teacher, survey)` from `QCU_Satisfaction` answers that have an
`Answer.teacher` set (ME sections). The teacher list is sorted with
`teacher_sort_key()`, case- and accent-insensitive, and stays filterable
by school year, semester, program and teacher.

### Teacher filter in visualization

A client-side selector filters the visualization without a page reload:
only the chosen teacher's modules stay displayed, and the Campus and
Program sections are hidden. The page reads `?teacher=<name>` on load to
pre-filter itself; links from the analytics page pass this parameter
along, so clicking a teacher's score opens their view directly.

### Surveys imported from Excel

Surveys loaded by `survey_loader_from_xlsx.py` have no `QCU_Attendance`
question: `services/visualisation_data.py` then falls back to
`satisfaction_responses_count` as the denominator for the teacher score.
Teacher names are normalized with `.title()` both at import and at
aggregation, to merge case variants (`"GADEMER Antoine"` and
`"Gademer Antoine"` become a single entry). Questions are sorted by
`question_id` in the template, which guarantees charts come before
verbatims regardless of insertion order.

### Campus management scope

The `campus_manager` dashboard only shows closed surveys with at least one
respondent. The link to the questionnaire and the QR code are hidden there
(`can_view_survey_link=False`): this role reviews results without
distributing surveys. The `{% if can_view_survey_link | default(true) %}`
guard leaves the other dashboards unchanged.

### Orphan student cleanup

When a survey is deleted, students no longer attached to **any other**
survey are deleted too, to avoid accumulating unused accounts
(`services/helpers.py`, `_delete_orphan_students`). A safeguard protects
users with a privileged role (`admin`, `program_manager`, `facilitator`,
`campus_manager`): a teacher or manager who answered a survey is never
deleted.

### Adding a user by email

The "Users" tab of the admin dashboard has a **"+ Add a user"** button: an
email address is enough to create the account, with the `student` role by
default (`POST /api/users`, admin only). The email is validated (format +
allowed domain) and duplicates are rejected.

---

## Deployment checklist

- [ ] `.env` created with real Azure credentials and a dedicated `SECRET_KEY` (required outside `AUTH_MODE=dev`, otherwise the application refuses to start — see [`SECRET_KEY`](#secret_key))
- [ ] `AUTH_MODE` unset or `entra`
- [ ] Valid SSL certificate (Let's Encrypt or equivalent)
- [ ] `https_only=True` on the `SessionMiddleware` (automatic outside `AUTH_MODE=dev`)
- [ ] Database present (`database/db_oceens.db`) or a Docker volume mounted
- [ ] Environment variables secured, including `LLM_API_KEY`
- [ ] **Docker Compose**: `.env` loaded via `env_file`, never copied into the image; `LOCAL_DATABASE_DIR` pointing at the right database directory
- [ ] `summaries_generator_daemon.py` running, if LLM summaries are used

---

## Before you contribute

The repository ships no automated test suite or CI. Before proposing a
change, run the manual procedure in
[`docs/smoke-test.md`](docs/smoke-test.md), then manually test the routes
affected by your change on a disposable SQLite database (never a copy of
production), with the relevant roles and survey statuses.

---

## Resources

- [FastAPI](https://fastapi.tiangolo.com/)
- [FastAPI and Uvicorn logging guide](https://apitally.io/blog/fastapi-logging-guide)
- [MSAL Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [Microsoft Graph](https://learn.microsoft.com/en-us/graph/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [Pandas](https://pandas.pydata.org/)

---

**OcéEns Team** — EPF
