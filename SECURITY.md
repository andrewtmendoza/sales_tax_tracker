# Security Policy

## Scope

This is a personal-use self-hosted application for storing receipt images and extracted metadata. It is not designed as a hardened multi-tenant SaaS platform.

## Supported Versions

Security fixes are applied to the current `main` branch.

## Reporting A Vulnerability

If you discover a security issue, please open a private GitHub security advisory if possible. If that is not practical, open a normal issue only after confirming the report does not disclose sensitive exploit details or personal data.

## Deployment Expectations

- Keep the app behind HTTPS.
- Use Django login and a strong password for the application.
- Keep `WEB_BIND_ADDRESS=127.0.0.1` unless a trusted reverse proxy fronts the app.
- Do not expose the app directly to the public internet without understanding the risks.
- Treat receipt images and raw LLM responses as sensitive personal data.

## Third-Party Services

When LLM extraction is enabled, receipt image data is sent to your configured OpenAI-compatible Responses API endpoint. Review that provider's retention and privacy policies before using it with real receipts.
