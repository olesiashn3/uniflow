# UniFlow - Student Opportunities Platform

[![CI Pipeline](https://github.com/olesiashn3/uniflow/actions/workflows/ci-pipeline.yml/badge.svg)](https://github.com/olesiashn3/uniflow/actions/workflows/ci-pipeline.yml)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/quality_gate?project=olesiashn3_uniflow)](https://sonarcloud.io/summary/new_code?id=olesiashn3_uniflow)

## About Project

UniFlow is a web platform for coordinating spaces, opportunities, and participants: curated feeds, organization profiles, moderation workflows, favorites, subscriptions, and in-app notifications. The system separates public catalog rules from admin decisions so content stays consistent and traceable.

## Tech Stack

- **Python 3.11**
- **Flask** — HTTP layer, blueprints, Jinja2 templates
- **Flask-SQLAlchemy** / **SQLAlchemy** — persistence and domain models
- **Flask-Login**, **Flask-WTF**, **Flask-Migrate** — auth, forms, schema migrations
- **pytest**, **pytest-cov** — automated tests and coverage reports

## Architecture

- **Layering:** routes call services; services depend on repository abstractions rather than raw ORM in views where the pattern applies.
- **Storage abstraction:** packages under `app/repositories/` implement the storage/query contract (SQLAlchemy-backed implementations for production behavior; in-memory implementations and stubs for fast, isolated tests). This plays the same structural role as a dedicated `storage/` layer in layered designs.
- **GoF patterns in use:**
  - **Strategy** — pluggable ordering of public catalog events (`app/strategies/`).
  - **Observer** — side effects such as notifications after organization approval without tight coupling (`app/observers/`).
- **SOLID:** small services, explicit repository interfaces, and dependency injection of repository implementations in tests and services.

## Project Structure

- Source code lives in the **`app/`** directory (standard Flask layout: `models/`, `routes/`, `services/`, `repositories/`, `static/`, `templates/`).
- Automated tests live in **`tests/`**.
- UML (PlantUML) and requirements notes: **`docs/`** (e.g. `docs/diagrams.puml`, `docs/project_analysis.md`, `docs/testing.md`).
- CI workflow: **`.github/workflows/ci-pipeline.yml`**; SonarCloud config: **`sonar-project.properties`**.


## How to Run

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
python run.py
```

Configure your environment (e.g. `DATABASE_URL`, secrets) via `.env` as required for your deployment. Copy `.env.example` to `.env` and adjust values if needed.

### Optional: Docker

Docker is **additive** — CI, `pytest`, and `python run.py` work the same as before.

```bash
docker compose up --build
```

Open [http://localhost:5000](http://localhost:5000). MySQL is exposed on host port **3307** (container `db:3306`). Uploaded images persist in the `uploads_data` volume.

Stop: `docker compose down` (add `-v` to remove database/upload volumes).

## Testing

The suite contains **1200+** automated tests (unit and integration style: models, repositories, strategies, observers, and HTTP routes against the Flask test client).

Typical local commands:

```bash
pytest
pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml
```

Line coverage for the `app` package is approximately **80%** in a full run (see CI artifacts: `coverage.xml`, `htmlcov/`, and **`junit.xml`** for machine-readable test results). After each push or pull request to `main`, GitHub Actions publishes these reports as downloadable artifacts and forwards coverage to **SonarCloud** for quality gate and static analysis.

---

Repository: [github.com/olesiashn3/uniflow](https://github.com/olesiashn3/uniflow) · SonarCloud: [sonarcloud.io](https://sonarcloud.io/summary/new_code?id=olesiashn3_uniflow)
