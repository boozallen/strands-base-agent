# Security posture

This directory tracks the security posture and production-readiness
artifacts for `strands-base-agent`. The intent is to give adopters
pursuing ATO-style requirements a head start: controls inherited from
the baseline are pre-recorded here, and what remains is whatever the
adopter adds on top.

## Contents

| File | Purpose |
|------|---------|
| `stig_checklist.json` | Machine-readable assessment of the baseline against the DISA Application Security and Development (ASD) STIG. One entry per STIG control with `status`, `responsibility`, `finding_details`, and `comments`. **Evidence lives inside this file** — there are no companion `.md` evidence notes. |

This is intentional. Evidence collected in the baseline's environment
(line numbers, scan dates, test names, file paths) is rarely useful to
adopters once they fork — they need to regenerate it against their own
code anyway. Keeping everything in the JSON means adopters refresh one
file, not a directory.

## How to use this as an adopter

The checklist is a **recommended template, not a hard requirement**.

- If you're pursuing ATO or a regulated deployment, fork the JSON and
  keep it current as your code diverges from the baseline. The
  `responsibility` field marks which controls the baseline already
  satisfies versus which ones you need to address in your overlay.
- If you have no compliance obligation, you can tailor or remove this
  directory entirely.

## Schema (per finding)

| Field | Values | Notes |
|-------|--------|-------|
| `vuln_id` | e.g. `V-222387` | DISA vulnerability ID. |
| `rule_id` | e.g. `SV-222387r960735_rule` | DISA rule identifier. |
| `stig_id` | e.g. `SRG-APP-000001` | Security Requirements Guide ID. |
| `severity` | `low`, `medium`, `high` | DISA-assigned severity. |
| `status` | `meets_requirement`, `non_compliant`, `not_applicable`, `needs_human_review` | Current assessment. |
| `responsibility` | `baseline`, `delivery`, `shared` | Who owns satisfying the control. `baseline` = this repo / its packages. `delivery` = the adopter's overlay. `shared` = both. |
| `responsibility_rationale` | Free text | One-line justification for the responsibility tag. |
| `finding_details` | Free text — short | One-to-two-sentence summary of the current state: what was checked, what was found. |
| `comments` | Free text — long | Longer attestation: policy statement, enforcement mechanism, scope, links to relevant code or specs. This is where multi-paragraph evidence belongs when the control needs it. |
| `domains_assessed` | `audit`, `auth`, `authz`, `crypto`, `data`, `session`, `validation` | Which domain assessment(s) produced this finding. |
| `ecs_findings`, `glasswing_findings` | Optional | Cross-references to scanner output, when applicable. |

## Refreshing the checklist

Two patterns work; pick whichever matches your team's level of AI
adoption.

### Skill-driven (what the Foundry team uses internally)

Coding agents drive the assessment via `foundry-stigkit`-backed skills.
The checklist's `assessment.assessed_by` field reflects this. These
skills are internal Booz Allen tooling and are **not available to
adopters outside the Foundry team**, but the workflow they encode is:

1. Run a per-domain assessment (auth, authz, crypto, etc.).
2. Triage the resulting findings into the four `status` buckets.
3. Update each affected finding's `finding_details` and `comments` in
   `stig_checklist.json`.

Any coding agent given the schema above and the existing JSON can
reproduce this loop.

### Manual / traditional

When code lands that affects a STIG-relevant area, edit
`stig_checklist.json` directly:

- Update the affected finding's `status`, `finding_details`, and
  `comments`.
- Adjust `responsibility` if the control moves between baseline and
  delivery ownership in your fork.
- Update `assessment.assessment_date` and the `status_summary` /
  `severity_summary` aggregates.

## When to update

In the same PR as any change that touches:

- Authentication or authorization
- Cryptography (at-rest, in-transit, key handling)
- Audit logging or telemetry
- Session handling
- Data handling (storage, retention, sanitization)
- Input validation
- Command execution or process invocation

The `CONTRIBUTING.md` PR checklist mirrors this list.

## Adopter notes

If your deployment requires a written prose security policy (for ATO or
similar), add it directly to the relevant control's `comments` field in
your fork's `stig_checklist.json`. The baseline does not ship policy
documents alongside the JSON — for code-level controls like
command-injection prevention (`V-222604`), the baseline relies on the
enforced ruff/bandit rules in `pyproject.toml` and CI as the policy.

## Related

- `../AGENTS.md` — repo orientation, including the "Security posture &
  STIG tracking" section.
- `../openspec/config.yaml` — instructs coding agents to update this
  checklist alongside spec-driven changes that affect STIG-relevant
  areas.
- `../pyproject.toml` — `ruff` / `bandit` rules that enforce the
  command-injection prohibition tracked under `V-222604`.
