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


## Synthetic enterprise demo dataset

Use the **🌱 Load 500 demo employees** button in the sidebar, or run:

```bash
python seed_data.py
streamlit run app.py
```

The deterministic generator adds 500 synthetic identities, 12 application catalog entries, application access assignments, and example access requests. It uses the reserved `identityguard.example` domain; no real employees or live SaaS accounts are involved. Seeding is idempotent: clicking again does not duplicate the generated identities. Existing local data is preserved.

Explore **Applications** for entitlement assignments, **Access Requests** for a read-only request queue, and **Access Review** for stale grants and access retained by disabled identities.

The seeded entitlement data intentionally includes governance issues for analysis. Counts reflect generated demo records, not real organizational security findings. JML operations in this MVP change the local identity record only; they do not revoke application entitlements. A production system would need lifecycle-driven entitlement reconciliation, authenticated operator authorization, and protected audit logs.
