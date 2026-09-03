# Security policy

## Supported versions

Only the latest release on the `main` branch receives security fixes. Deployments should track tagged releases and update when a new one is published.

## Reporting a vulnerability

Do not open a public issue for a vulnerability. Send a report to s.wacker@tudelft.nl with the affected version, the endpoint or component, and steps to reproduce. You will get an acknowledgement within five working days and a fix or a mitigation plan before any public disclosure.

## Deployment notes

- Set `ADMIN_SECRET_KEY` to a random value. Without it the server generates a key at startup and admin sessions end on every restart. Admin tokens are accepted only for configured admin users or admin email addresses.
- Run the dashboard behind HTTPS. SAML login refuses plain HTTP in production mode.
- Agent API keys are stored hashed and shown once. Rotate a key from the admin panel if it leaks.
- The dashboard endpoints are readable without login when SAML is disabled. Enable SAML or restrict network access for any deployment that holds real usage data.
