# Contributing to Strands Base Agent

This guide covers the process and conventions for contributing changes to this
repo. For a tour of the codebase — file layout, packages, extension points —
see `AGENTS.md`, which is the single source of truth for repo structure.

## Development Setup

```bash
just setup
```

This installs dependencies via `uv` and registers pre-commit hooks. Then copy
the env template and fill in your AWS Bedrock credentials:

```bash
cp env.template .env
# Edit .env — at minimum set AWS_DEFAULT_REGION and AWS_PROFILE
```

## Code Quality Standards

Tooling enforced locally and in CI:

- **Ruff** — formatting and linting
- **basedpyright** — static type checking
- **pytest** — tests with a 70% coverage gate
- **pre-commit hooks** — run on each commit

```bash
just check        # lint + format + type-check + test
just format       # apply Ruff formatting
just type-check   # basedpyright only
```

## Testing

```bash
just test               # all tests
just test-unit          # unit tests
just test-integration   # integration tests
```

When adding code, write unit tests for new behavior, keep coverage at or above
70%, and prefer the existing pytest fixture patterns. Integration tests live
in `tests/integration/`; unit tests live in `tests/unit/`.

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

1. `just check` and `just test` must pass locally before pushing.
2. Update relevant docs.
3. If the change touches a STIG-relevant area (auth, authz, crypto,
   audit logging, session handling, data handling, input validation),
   update `security/stig_checklist.json` in the same PR. See
   `security/README.md` for the workflow.
4. Open a PR against upstream `develop` and address review feedback.

### CI/CD

GitHub Actions runs CodeQL, the lint/type/test pipeline, and a coverage gate
(70% minimum). All checks must pass before merge.

### Branch Protection

The `develop` branch is protected with the following requirements:

- **2 approving reviews** required before merge
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
- `security/README.md` — STIG checklist and security posture
- GitHub Issues — bugs and feature requests

## License

By contributing, you agree that your contributions will be licensed under the
same license as the project.
