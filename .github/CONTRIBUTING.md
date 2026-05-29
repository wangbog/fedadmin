# Contributing

Thanks for your interest in FedAdmin.

## Before You Start

- Read `../README.md`, `../docs/reference/backlog.md`, and `../docs/reference/issues.md`.
- For deployment behavior, check `../docs/deployment/deployment_dev.md` and `../docs/deployment/deployment_prod.md`.
- Do not commit `.env`, database files, logs, private keys, or generated storage files.

## Development

Use the development deployment guide to build and run the project locally:

```bash
docker compose up --build -d
```

Useful commands:

```bash
docker compose exec --user fedadmin web flask init-certs
docker compose exec --user fedadmin web flask db upgrade
docker compose exec --user fedadmin web flask init-db
docker compose exec --user fedadmin web flask regenerate-metadata
```

Run tests in the development container:

```bash
docker compose exec --user fedadmin web pytest
```

If the development container is not already running, use:

```bash
docker compose run --rm web pytest
```

For host-based development or CI, install `requirements-dev.txt` and then run `pytest`.

Run lint and test formatting checks before opening a pull request:

```bash
docker compose exec --user fedadmin web ruff check --no-cache .
docker compose exec --user fedadmin web ruff format --check --no-cache tests
```

You can also install local pre-commit hooks on the machine where you run `git commit`:

```bash
pre-commit install
```

If you run `pre-commit install` inside the Docker container, the hook file is still written to `.git/hooks/pre-commit` through the bind mount. However, if you later run `git commit` from the Windows host, that hook may reference container-side paths or executables and fail. Install pre-commit in the same environment where you run `git commit`. If you commit from inside the development container, run the install command inside that container instead.

GitHub Actions runs Ruff checks, test formatting checks, and the pytest suite on every push and pull request.

## Pull Requests

- Keep changes focused.
- Update documentation when behavior changes.
- Mention any database migration, deployment, or security impact.
- Add tests when the project has a test suite covering the changed area.

## Security

Please do not report vulnerabilities in public issues. See `.github/SECURITY.md`.
