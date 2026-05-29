# Contributing

Thanks for your interest in FedAdmin.

## Before You Start

- Read `README.md`, `docs/reference/backlog.md`, and `docs/reference/issues.md`.
- For deployment behavior, check `docs/deployment/deployment_dev.md` and `docs/deployment/deployment_prod.md`.
- Do not commit `.env`, database files, logs, private keys, or generated storage files.

## Development

Use the development deployment guide to build and run the project locally:

```bash
docker compose up --build
```

Useful commands:

```bash
docker compose exec --user fedadmin web flask init-certs
docker compose exec --user fedadmin web flask db upgrade
docker compose exec --user fedadmin web flask init-db
docker compose exec --user fedadmin web flask regenerate-metadata
```

## Pull Requests

- Keep changes focused.
- Update documentation when behavior changes.
- Mention any database migration, deployment, or security impact.
- Add tests when the project has a test suite covering the changed area.

## Security

Please do not report vulnerabilities in public issues. See `SECURITY.md`.
