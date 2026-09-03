# Local Development Setup

This guide covers setting up a local development environment with SAML authentication for the SLURM Usage History Dashboard.

## Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend development)
- Git

## Development Environment

The development setup includes:

- **Backend**: FastAPI server with hot reload
- **Frontend**: Vite dev server with HMR at `localhost:5173`
- **SAML IdP**: SimpleSAMLphp test identity provider at `localhost:8080`

## Quick Start

1. Clone the repository:
```bash
git clone <repository-url>
cd slurm-usage-history
```

2. Start the development environment:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

3. Access the application:
   - Frontend (Vite dev server): http://localhost:5173
   - Backend API: http://localhost:8100
   - SAML IdP: http://localhost:8080

## Test Users

The development SAML IdP includes these test users:

| Username | Password | Role | Attributes |
|----------|----------|------|------------|
| `admin` | `admin` | Superadmin | netid: admin, email: admin@example.com |
| `user` | `user` | Regular user | netid: user, email: user@example.com |
| `testuser` | `testuser` | Student | netid: testuser, email: testuser@example.com |

## Development Configuration

### Environment Variables

The development environment is configured in `docker-compose.dev.yml`:

```yaml
environment:
  - ENVIRONMENT=development  # Enables permissive settings
  - ENABLE_SAML=true
  - CORS_ORIGINS=http://localhost:5173,http://localhost:3100,http://localhost:8100
  - DEBUG=true
  - RELOAD=true
```

### Development vs Production

The `ENVIRONMENT` variable controls security settings:

#### Development Mode (`ENVIRONMENT=development`)
- ✅ Allows HTTP connections
- ✅ Sets `SameSite=None` cookies for cross-origin requests
- ✅ Enables CORS from Vite dev server
- ✅ Hot reload enabled
- ✅ Debug logging

#### Production Mode (`ENVIRONMENT=production`)
- ⛔ Requires HTTPS (rejects HTTP)
- 🔒 Sets `SameSite=Lax` cookies for security
- 🔒 Strict CORS policy
- 📊 Production logging

## Frontend Development

### Using Vite Dev Server

The recommended way to develop the frontend:

```bash
cd frontend
npm install
npm run dev
```

Access at http://localhost:5173 with:
- Hot Module Replacement (HMR)
- Fast refresh
- Full TypeScript support

### SAML Authentication Flow

1. Visit http://localhost:5173
2. Redirected to http://localhost:8080 (SAML IdP)
3. Login with test credentials
4. Redirected back to dashboard
5. Session cookie allows API requests

### Cookie Configuration

In development, the backend uses special cookie settings:

```typescript
// Session cookie settings
samesite: "none"  // Allows cross-origin from localhost:5173 to localhost:8100
secure: false     // Works over HTTP
httponly: true    // Prevents XSS
max_age: 86400    // 24 hours
```

!!! warning "Development Only"
    `SameSite=None` without `Secure` is **only allowed in development**. Production mode enforces HTTPS and uses `SameSite=Lax`.

## Backend Development

### Hot Reload

The backend automatically reloads when Python files change:

```bash
# Watch logs
docker-compose -f docker-compose.dev.yml logs -f backend

# Example output
WARNING:  WatchFiles detected changes in 'backend/app/api/saml.py'. Reloading...
```

### Code Structure

```
backend/
├── app/
│   ├── api/          # API endpoints
│   │   ├── saml.py   # SAML authentication
│   │   └── dashboard.py
│   ├── core/         # Configuration and utilities
│   │   ├── config.py # Settings and environment
│   │   └── saml_auth.py
│   └── main.py       # FastAPI application
```

### Adding API Endpoints

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/example")
async def example_endpoint():
    return {"message": "Hello"}
```

## SAML IdP Configuration

### Test IdP Settings

The SimpleSAMLphp test IdP is configured in:

- `Dockerfile.saml-idp`: IdP container setup
- `docker/saml-idp/authsources.php`: Test users
- `docker/saml-idp/saml20-sp-remote.php`: Service Provider registration

### Modifying Test Users

Edit `docker/saml-idp/authsources.php`:

```php
'example-userpass' => [
    'exampleauth:UserPass',
    'newuser:password' => [
        'uid' => ['newuser'],
        'email' => ['newuser@example.com'],
        'netid' => ['newuser'],
    ],
],
```

Restart the IdP:
```bash
docker-compose -f docker-compose.dev.yml restart saml-idp
```

## Testing

### Automated Tests

Run the test suite using pytest:

```bash
# Install with dev dependencies
uv pip install -e ".[all,dev]"

# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=slurm_usage_history

# Run specific test file
uv run pytest tests/test_chart_generation.py

# Run with verbose output
uv run pytest -v

# Run tests in parallel (faster)
uv run pytest -n auto
```

The test suite includes:
- **Chart generation tests** - validates all chart output formats (pie, bar, stacked, trends)
- **Data processing tests** - ensures correct data transformations
- **API endpoint tests** - verifies REST API functionality

Tests are configured in `pyproject.toml` with:
- Warnings treated as errors for strict validation
- Coverage reporting enabled
- Automatic test discovery

### Manual Testing

1. Login flow: Visit http://localhost:5173 → should redirect to SAML IdP
2. API access: Check browser console for successful API requests
3. Session persistence: Refresh page → should stay logged in
4. Logout: Click logout button → should clear session

### Backend Logs

```bash
# Watch all logs
docker-compose -f docker-compose.dev.yml logs -f

# Only backend
docker-compose -f docker-compose.dev.yml logs -f backend

# Only SAML IdP
docker-compose -f docker-compose.dev.yml logs -f saml-idp
```

### Browser DevTools

Check in browser developer tools:

1. **Network tab**: Verify `/saml/me` returns 200 OK
2. **Application/Storage tab**: Check for `session_token` cookie
3. **Console**: Look for any errors

## Common Issues

### "401 Unauthorized" after login

**Cause**: Session cookie not being sent from Vite dev server

**Check**:
1. `ENVIRONMENT=development` is set
2. Backend logs show "Reloading" after changes
3. Cookie exists in browser (DevTools → Application → Cookies)

**Solution**: Clear cookies and re-login

### SAML redirect loop

**Cause**: SAML configuration mismatch

**Check**:
1. Backend logs for SAML errors
2. IdP certificate matches in `docker/saml-config/settings.json`

**Solution**: Rebuild containers:
```bash
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d --build
```

### Frontend not connecting to backend

**Cause**: CORS or API URL misconfiguration

**Check**:
1. `VITE_API_URL` in frontend (should be `http://localhost:8100`)
2. `CORS_ORIGINS` in backend includes `http://localhost:5173`

### Port already in use

**Cause**: Another service using the port

**Solution**:
```bash
# Find process
lsof -i :5173  # or :8100, :8080

# Kill process
kill -9 <PID>

# Or change ports in docker-compose.dev.yml
```

## Rebuilding Containers

When changing Dockerfiles or dependencies:

```bash
# Rebuild all
docker-compose -f docker-compose.dev.yml up -d --build

# Rebuild specific service
docker-compose -f docker-compose.dev.yml up -d --build backend

# Force recreate without cache
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up -d
```

## Clean Up

Stop and remove everything:

```bash
docker-compose -f docker-compose.dev.yml down

# Also remove volumes
docker-compose -f docker-compose.dev.yml down -v
```

## Next Steps

- [Production Deployment](../deployment/saml-setup.md)
- [Configuration Guide](../user-guide/configuration.md)
- [API Documentation](http://localhost:8100/docs) - Interactive API docs when running locally

## Quality Gates

Every rule in this project has an enforcement mechanism; prose-only rules are not accepted.

- `uv run ruff check` and `uv run ruff format --check .` must pass with zero findings. Accepted rules (for example `G004`, `PLC0415`) are listed with a one-line reason in `pyproject.toml`; anything not listed there fails the build.
- `uvx vulture --min-confidence 80 src/slurm_usage_history backend/app scripts` must report nothing: dead code is removed, not documented.
- `uv run mypy src/slurm_usage_history backend/app scripts` must pass. The gate runs at mypy's default strictness (configured in `pyproject.toml` under `[tool.mypy]`); `--strict` is the target and its remaining errors are tracked work.
- `uv run pytest` runs the full backend suite; `npm test` (vitest) and `npx eslint src` cover the frontend.

Install the pre-commit hooks once per clone:

```bash
uv run pre-commit install
```

The hooks run ruff (lint + format), vulture, and mypy on every commit. CI runs the same checks in the `lint:python` job plus the full test suites; no test job is allowed to fail.

## Frontend styling

Colors, radii, shadows, fonts, and spacing come from the custom properties declared in `frontend/src/App.css` (`--bg-*`, `--text-*`, `--border`, `--radius-*`, `--shadow-*`, `--font-*`, `--space-*`). The printable report page is always light and uses its own `--report-*` properties, declared on `.report-page` in the same file. A `var(--name)` whose name is not declared in any stylesheet is invalid CSS and silently drops the declaration. Gate: `frontend/src/theme/cssTokens.test.ts` fails on any undeclared name. Color literals live only in `App.css`; the same test fails on a hex or `rgb()` literal in any other stylesheet.

Admin pages (login, clusters, users, cluster detail) render inside `frontend/src/components/AdminLayout.tsx`, which provides the header, navigation, theme toggle, and logout, and they use the `cp-*` classes from `frontend/src/pages/admin.css`. A new admin page adds no stylesheet of its own.

## Untrusted input

Request values never become SQL text or filesystem paths. Each rule has a test that fails when it is broken.

- DuckDB queries bind request values (dates, partitions, accounts, users, QOS, states) as prepared-statement parameters. The `hostname` is looked up in the datastore's known hosts before it is used in a `read_parquet` path; an unknown hostname returns an empty result instead of touching the filesystem. Gate: `tests/test_duckdb_injection.py`.
- Admin tokens are signed with `ADMIN_SECRET_KEY`, which has no default in code; an unset or placeholder value is replaced by a random key at startup. A token is accepted only when its subject is a configured admin. Gate: `tests/test_admin_auth.py`.
- Agent uploads are written under the cluster directory of the API key only. The client filename must be a single path component (no separators, no `..`) and the content must parse as parquet; anything else is rejected with `400`. Gate: `tests/test_agent_upload.py`.
- `POST /api/data/ingest` writes to the directory of the cluster that owns the API key. A body `hostname` that names a different cluster is rejected with `403`; a legacy key from `API_KEYS` (not bound to a cluster) may name any cluster, but the name must be a single path component. Gate: `tests/test_ingest_hostname.py`.
