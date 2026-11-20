# Contributing to Strands Base Agent

This guide covers the process and conventions for contributing changes to this
repo. For a tour of the codebase — file layout, packages, extension points —
see `AGENTS.md`, which is the single source of truth for repo structure.

## Development Setup

```bash
just setup
```

This syncs dependencies via `uv` (`just sync` on its own does the dependency
sync only) and registers pre-commit hooks. Then copy
the env template and fill in your AWS Bedrock credentials:

```bash
cp env.template .env
# Edit .env — at minimum set AWS_DEFAULT_REGION and AWS_PROFILE
```

## Code Quality Standards

Tooling enforced locally:

- **Ruff** — formatting and linting
- **bandit** — command-injection sink set (`B602`/`B603`/`B605`/`B607`), run by
  `just lint` alongside ruff; enforces STIG V-222604
- **basedpyright** — static type checking
- **pytest** — tests with a coverage gate, run in strict marker and strict
  config mode: an undeclared `@pytest.mark` name or an unrecognized key in
  `[tool.pytest.ini_options]` fails the run instead of being ignored. Declare new
  markers in `pyproject.toml`'s `markers` list
- **pre-commit hooks** — run on each commit

```bash
just check        # full gate: lint + format + type-check + test
just lint         # Ruff + bandit (use `just lint-fix` to auto-fix ruff findings)
just format       # Ruff format check (use `just format-fix` to apply)
just type-check   # basedpyright only
```

`just check` prints `All quality checks passed` when every gate succeeds. Ruff
and basedpyright are always given explicit path arguments in the justfile rather
than relying on config-driven discovery.

## Testing

Tiering is by **directory**, not by marker: a test's tier is decided by where
the file lives, so it cannot be forgotten. Unit tests live in `tests/unit/`;
integration tests live in `tests/integration/`.

```bash
just test               # whole tree: tests/ (unit + integration)
just test-unit          # tests/unit/ only
just test-integration   # tests/integration/ only (no coverage gate)
```

`just test-integration` treats "no tests collected" (pytest exit code 5) as
success and prints `No integration tests collected - not a failure.`, so the
recipe stays portable across repos with no integration suite yet; this repo does
have one.

Coverage reporting is always on via `[tool.pytest.ini_options]` addopts -
terminal and HTML (`htmlcov/`) — so there is no separate coverage recipe. The
`integration` marker is still declared as a trait tag, but nothing selects on
it.

When adding code, write unit tests for new behavior, keep coverage at or above
the configured gate, and prefer the existing pytest fixture patterns.

## Recipe conventions shared across Foundry Python repos

- `just sync` installs dependencies only; `just setup` runs `sync` plus
  repo-specific environment preparation (here: installing pre-commit hooks)
- `just check` does not call `sync` — `uv run` auto-syncs on every invocation,
  so a cold clone can run `just check` directly
- Every recipe invokes its tool as plain `uv run <tool> ...`, with no `--group`
  flag and no `python -m` wrapper
- `just clean` removes `build/`, `dist/`, `htmlcov/`, `*.egg-info/`,
  `.pytest_cache/`, `.ruff_cache/`, `.coverage`, `__pycache__/`, and `*.pyc`,
  then prints `Cleaned build artifacts`. It skips `.venv/` so a clean does not
  invalidate the environment. A stale `.coverage` can make a later coverage run
  fail spuriously, so it is always removed
- Container recipes use one naming set across repos: `up`/`down` with
  `start`/`stop` as aliases, `logs [service]`, `status`, `build`, `reset`
  (down + clean + setup), and `clean-all` (clean + `docker compose down -v
  --remove-orphans`). `clean-all` is scoped to this project's compose file: it
  removes the containers and volumes this repo declares and does not prune the
  Docker host, so it cannot disturb unrelated services
- The local, non-Docker run recipe is `just dev` in every repo, with `just run`
  as an alias

## Project Structure

This repo is a **composition root** that wires shared agent framework packages
together. See `AGENTS.md` for the file layout, package responsibilities,
extension points, and architectural conventions.

## Contribution Workflow

This project uses a **fork-based workflow**:

1. **Fork** the repository to your own GitHub account
2. **Clone** your fork locally
3. **Create a branch** from `develop` using the naming convention below
4. **Make your changes** with tests
5. **Push** to your fork
6. **Open a pull request** against the upstream `develop` branch

Only designated maintainers can merge pull requests. Contributors cannot
self-merge — all changes require review and approval through the process
described in [Branch Protection](#branch-protection) below.

## Branch Naming

Use a prefix that matches the change kind:

- `feature/<slug>` — new functionality
- `fix/<slug>` — bug fix
- `chore/<slug>` — maintenance
- `docs/<slug>` — documentation
- `refactor/<slug>` — restructuring without behavior change

## Commit Messages

Conventional commits, one logical change per commit, each commit green on its
own:

```
<type>: <short description>

<optional body explaining why, not what>
```

Types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`.

## Pull Requests

1. `just check` must pass locally before pushing (it runs lint, format,
   type-check, and the full test suite).
2. Update relevant docs.
3. Open a PR against upstream `develop` and address review feedback.

### CI/CD

GitHub runs CodeQL code scanning on this repository. Lint, type checks, tests and the coverage gate run locally: `just check` must pass before you open a PR.

### Branch Protection

The `develop` branch is protected with the following requirements:

- **1 approving review** required before merge
- **Stale reviews dismissed** — new pushes invalidate previous approvals
- **Code Owners review required** — files covered by `.github/CODEOWNERS` must
  be approved by designated owners
- **Push access restricted** to maintainers only
- **No bypass** — these rules apply to everyone, including administrators

These settings enforce a maintainer-controlled merge model: contributors submit
pull requests, but only designated maintainers with the appropriate role can
approve and merge changes.

## Reporting Security Issues

If you discover a security vulnerability, **do not open a public issue.** See
[SECURITY.md](SECURITY.md) for our responsible disclosure process via GitHub's
private security advisory feature.

## Additional Resources

- `AGENTS.md` — codebase orientation for humans and AI assistants
- `docs/foundry/quickstart.md` — get the agent running locally with Python and `uv`
- `docs/foundry/quickstart-docker.md` — get the agent running in Docker Compose
- `docs/foundry/configuration/index.md` — YAML config reference
- GitHub Issues — bugs and feature requests

## License

By contributing, you agree that your contributions will be licensed under the
same license as the project.
