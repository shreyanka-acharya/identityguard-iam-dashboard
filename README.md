# IdentityGuard - IAM Dashboard

A local, portfolio-focused Identity & Access Management (IAM) demo using synthetic employee identities.

## Features
- Identity directory and dashboard metrics
- Joiner onboarding, mover role/department changes, leaver deactivation
- Role assignment from a fixed role catalog
- Privileged account review candidates
- Append-only-by-application audit event log
- SQLite persistence

## Quick start

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown in the terminal (typically http://localhost:8501).

Run tests:

```bash
pytest -q
```

## Structure

- `app.py`: Streamlit user interface
- `iam.py`: SQLite schema and JML operations
- `test_iam.py`: workflow tests
- `requirements.txt`: dependencies
- `.gitignore`: excludes database, secrets, and virtual environments

## Security and scope

**Demo only, not production-ready.** There is no login, session authorization, SSO, MFA, SCIM, provisioning to third-party applications, or enforced least privilege. Role assignments are demo data, not permissions enforced against the dashboard operator. Audit events identify a fixed local demo actor, not an authenticated user, and are not tamper-proof. Never enter real employee data or deploy this app publicly without a security redesign.

## Roadmap
1. Separate API service and authenticated sessions
2. Enforce administrator/operator RBAC on all mutations
3. Approval workflow and access certifications
4. SCIM integration with a test identity provider
5. Hardened audit storage and integration tests
