# Security policy

Thank you for helping keep Dokbot and its users safe.

## Supported versions

| Version | Supported |
|---------|-----------|
| `main`  | ✅ Yes     |

We recommend deploying from the latest `main` branch and pinning dependencies in production.

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Instead, report responsibly using one of these options:

1. **GitHub:** open a [Private security advisory](https://github.com/Azizmkadmini/Dokbot/security/advisories/new) on this repository (if enabled for your role).
2. **Email:** contact the maintainer privately (add your preferred email here if you publish one publicly).

Include:

- A short description of the issue and its impact  
- Steps to reproduce or a minimal proof of concept  
- Affected version / commit / deployment context (self-hosted vs cloud)  

We will acknowledge receipt when possible and work with you on a coordinated disclosure timeline.

## Security practices for self-hosting

- **Never commit secrets.** Use `.env` locally and secret managers in production. The repository intentionally ignores `.env` and Chroma data paths.
- **Rotate `ADMIN_API_KEY`** from the default value before any public deployment. All ingest and analytics routes require this header.
- **Restrict CORS** in production: set `CORS_ORIGINS` to your real front-end origins instead of `*`.
- **TLS:** expose the API only behind HTTPS (reverse proxy, load balancer, or PaaS default).
- **Dependencies:** run `pip install` from pinned `requirements.txt` and monitor advisories (e.g. GitHub Dependabot).
- **Data:** ChromaDB stores embeddings and document text on disk; protect the host filesystem and backups.

## Out of scope (examples)

- Social engineering against maintainers or users  
- Spam or denial-of-service requiring massive resources unless reproducible at small scale  

We reserve the right to define scope; we still appreciate good-faith reports.
