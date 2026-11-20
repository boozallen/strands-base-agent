---
description: Generate comprehensive PR descriptions by analyzing changes, running verifications, and updating the PR after user review.
---

# Generate PR Description

You are tasked with generating a comprehensive pull request description following the repository's standard template.

## Prerequisites:

- GitHub CLI (`gh`) must be installed and authenticated
- Repository must have `gh` default set (run `gh repo set-default` if needed)
- User must have write access to the PR

## Process:

### 1. Read the PR Description Template

**Template Resolution (mimics GitHub UI behavior)**:

1. **Repository-level template** (first priority):
   - Check if `.github/pull_request_template.md` exists in the repository
   - If found, use this template

2. **Organization-level template** (fallback):
   - If no repo-level template, check for org-level template:
     ```bash
     # Get the organization name
     gh repo view --json owner --jq '.owner.login'
     
     # Check if org has a .github repository with PR template
     gh repo view {org}/.github --json nameWithOwner 2>/dev/null
     
     # If exists, get the template (try both filename variations)
     gh api /repos/{org}/.github/contents/PULL_REQUEST_TEMPLATE.md --jq '.content' 2>/dev/null | base64 -d || \
     gh api /repos/{org}/.github/contents/pull_request_template.md --jq '.content' 2>/dev/null | base64 -d
     ```
   - If found, use this org-level template

3. **Standard format** (if no templates found):
   - If neither repo nor org templates exist, use standard format with:
     - **What**: Description of changes
     - **Why**: Problem being solved
     - **How**: Implementation approach
     - **Testing**: Verification steps
     - **Breaking Changes**: Any breaking changes
     - **Checklist**: Standard PR checklist

**Note**: This org-level fallback ensures consistency whether PRs are created via this command or through GitHub's UI.

### 2. Identify the PR to Describe

- First, check if current branch has an associated PR:
  ```bash
  gh pr view --json url,number,title,state 2>/dev/null
  ```

- If no PR exists for current branch, or if on main/master, list open PRs:
  ```bash
  gh pr list --limit 10 --json number,title,headRefName,author
  ```

- If multiple PRs exist, present them to the user and ask which to describe:
  ```
  I found the following open PRs:
  1. PR #123: feat(api): Add new endpoint
  2. PR #124: fix(auth): Resolve login issue
  
  Which PR would you like me to generate a description for?
  ```

- **WAIT FOR USER SELECTION** before proceeding

### 3. Detect and Confirm Related Issues

**Automatically detect issue numbers from multiple sources:**

```bash
# 1. Check branch name for issue numbers
git branch --show-current | grep -oE '[0-9]+' | head -1

# 2. Check commit messages for issue references
gh pr view {number} --json commits --jq '.commits[].commit.message' | grep -oE '#[0-9]+' | sort -u

# 3. Check GitHub's linked issues (if any)
gh pr view {number} --json closingIssuesReferences --jq '.closingIssuesReferences[].number'
```

**Present findings to user:**

If issue numbers detected:
```
I found potential issue references:
- From branch name: #100
- From commits: #100, #102
- GitHub linked: #100

Suggested issues: #100, #102

Use these issue numbers? (y/n)
- If no: "Enter correct issue number(s) (e.g., '100' or '100, 101, 102') or 'skip' for none:"
```

If no issue numbers detected:
```
No issue references detected.

Is this PR related to any GitHub issues? (y/n)
- If yes: "Enter issue number(s) (e.g., '100' or '100, 101, 102'):"
- If no: Continue without issue references
```

**WAIT FOR USER RESPONSE** before proceeding.

**Handle user input**:
- If user confirms detected issues (y): Use detected issues
- If user declines detected issues (n): Prompt for correct issue numbers or 'skip'
- If user provides numbers: Use those
- If "skip": Continue without issue references
- Format in description as: `Fixes #100` or `Related to #100, #101`

**Important**: NEVER use "press Enter to skip" - Cursor cannot detect empty Enter presses. Always use explicit y/n prompts.

### 4. Gather Comprehensive PR Information

Once PR is identified and issues are confirmed, gather all information:

```bash
# Get the full PR diff
gh pr diff {number}

# Get commit history
gh pr view {number} --json commits

# Get base branch
gh pr view {number} --json baseRefName

# Get PR metadata
gh pr view {number} --json url,title,number,state,author
```

**Error Handling**:
- If you get "no default remote repository" error, instruct user:
  ```
  Please run: gh repo set-default
  Then select the appropriate repository and run /create-pr again.
  ```

### 5. Analyze the Changes Thoroughly

**Deep Analysis Required** - Take time to understand the changes:

- Read through the entire diff carefully
- For context, read any files that are referenced but not fully shown in the diff
- Understand the purpose and impact of each change
- Identify:
  - User-facing changes vs internal implementation details
  - New features added
  - Bugs fixed
  - Refactoring or improvements
  - Breaking changes or migration requirements
  - Dependencies added or removed
  - Configuration changes

**Ask yourself**:
- What problem does this solve?
- How does it solve it?
- What's the impact on users?
- What's the impact on developers?
- Are there any risks or breaking changes?

### 6. Handle Verification Requirements

Look for checklist items in the template's verification section.

**Execute ALL verification commands found in the template:**

1. **For runnable commands** (e.g., `just test`, `just lint`, `npm test`, `uv run pytest`):
   - Execute each command
   - If **passes**: Mark checkbox as checked `- [x]`
   - If **fails**: Mark checkbox as unchecked `- [ ]` and add explanation of what failed
   - Include command output summary if helpful

2. **For manual testing requirements** (e.g., "Test in browser", "Verify UI changes"):
   - Mark checkbox as unchecked `- [ ]`
   - Add note: "(Requires manual verification)"

3. **Document all verification results**:
   ```
   Verification Results:
   ✓ just test - All tests passed (318 passed)
   ✓ just lint - No linting errors
   ✓ just type-check - Type checking passed
   ✗ just integration-test - 1 integration test failed (see details below)
   ⚠ UI verification - Requires manual testing in browser
   ```

**Common verification commands to try**:
- `just test` / `npm test` / `uv run pytest`
- `just lint` / `npm run lint` / `ruff check`
- `just type-check` / `npm run type-check` / `mypy`
- `just format` / `npm run format` / `black --check`
- `just check` (if exists - often runs all quality checks)

**Run all commands found** - don't skip any automated verification steps.

### 7. Generate the Description

Fill out each section from the template thoroughly:

**General Guidelines**:
- Be specific about problems solved and changes made
- Focus on user impact where relevant
- Include technical details in appropriate sections
- Write clear, scannable content
- Use bullet points for lists
- Include code snippets where helpful
- Write a concise changelog entry (if template has one)

**Template Section Mapping**:
- **What/Summary**: High-level description of changes
  - If user provided issue numbers, add `Fixes #100` (for bug fixes) or `Related to #100` (for features/enhancements)
  - For multiple issues: `Fixes #100, #101` or `Related to #100, #101`
- **Why/Motivation**: Problem being solved, user needs addressed
- **How/Implementation**: Technical approach, architectural decisions
- **Testing/Verification**: How it was tested, verification steps (with checkboxes)
- **Breaking Changes**: Any breaking changes (highlight prominently)
- **Migration**: Migration steps if needed
- **Screenshots**: Note if UI changes (user should add screenshots)
- **Related Issues**: Link to related issues/PRs (if template has separate section for this)
- **Checklist**: Standard items (tests, docs, etc.) with checkboxes

**Tone**:
- Professional and clear
- Thorough but concise
- Scannable (use headings, bullets, formatting)
- Focus on "why" as much as "what"

### 8. Present Description to User for Review (REQUIRED)

**ALWAYS show the generated description to the user before updating the PR:**

```
I've generated the following PR description for PR #{number}:

────────────────────────────────────────
[Show complete generated description]
────────────────────────────────────────

Verification Results:
✓ just test - All 318 tests passed
✓ just lint - No errors
✓ just type-check - Passed
⚠ UI testing - Requires manual verification

Shall I update PR #{number} with this description?
```

**WAIT FOR USER APPROVAL** - Do not update the PR without explicit confirmation.

### 9. Update the PR (After Confirmation)

Once user approves, update the PR description:

```bash
gh pr edit {number} --body "<generated_description>"
```

**After successful update**:
- Confirm the update was successful
- Provide the PR URL for review
- If any verification steps remain unchecked, remind the user:
  ```
  ✓ PR description updated successfully
  URL: https://github.com/org/repo/pull/{number}
  
  The following items still need verification:
  - [ ] UI testing in browser
  - [ ] Performance testing with large datasets
  
  Please complete these before merging.
  ```

## Important Notes:

- **Smart issue detection**: Automatically detects issue numbers from branch names, commits, and GitHub links - always confirms with user
- **Template hierarchy**: Mimics GitHub's behavior - checks repo template first, then org-level fallback, then standard format
- **Org-level consistency**: Using org templates ensures all repos follow the same PR standards when no repo-specific template exists
- **Multi-repository support**: Always read the local template - each repo may differ
- **Be thorough but concise**: Descriptions should be scannable
- **Focus on the "why"**: Explain motivation and impact, not just what changed
- **Highlight breaking changes**: Make them prominent and easy to spot
- **Multi-component PRs**: Organize description by component/area if PR touches multiple parts
- **Always run verifications**: Execute ALL automated verification commands found in the template
- **Clear communication**: Clearly state which verification steps need manual testing
- **Repository-specific commands**: Adapt to the project's build tool (just, npm, uv, etc.)
- **Always get approval**: Never update PR description without user review and confirmation

## Example Interaction:

```
User: /create-pr

AI: I'll generate a PR description for the current branch.

[Runs: gh pr view --json url,number,title]
Found PR #156: feat(api): Add A2A endpoints

Detecting related issues...
[Checks: git branch --show-current → feature/100-add-a2a-endpoints]
[Checks: commit messages for #100]
[Checks: gh pr view 156 --json closingIssuesReferences]

I found potential issue references:
- From branch name: #100
- From commits: #100

Suggested issues: #100

Use these issue numbers? (y/n)

User: y

[Runs: gh pr diff 156]

Checking for PR template...
[Checks: .github/pull_request_template.md - not found]
[Checks: org-level template from {org}/.github - found!]
Using org-level PR template from {org}/.github repository

Analyzing changes... (reading diff, understanding impact)

Running verification checks:
[Runs: just test]
✓ All tests passed (318 passed)

[Runs: just lint]  
✓ No linting errors

[Runs: just type-check]
✓ Type checking passed

[Runs: just check]
✓ Full quality pipeline passed

Generating description based on template...

────────────────────────────────────────
## What

This PR adds Agent-to-Agent (A2A) communication endpoints to the FastAPI server using the Strands SDK's built-in A2A functionality.

Fixes #100

## Why

External AI agents need a standardized way to communicate with the Strands Base Agent without understanding our custom HTTP API. The A2A protocol provides this standardization.

## How

- Created new `api/a2a/` module with:
  - `server.py`: A2A server factory wrapping existing agent
  - `models.py`: Pydantic models for A2A protocol (A2ARequest, A2AResponse, A2AError)
- Mounted A2A server at `/a2a` path on main FastAPI application
- Implemented stateless request handling with minimal logging
- Added comprehensive test coverage (contract, unit, integration tests)

## Testing

- [x] `just test` - All 318 tests pass
- [x] `just lint` - No linting errors
- [x] `just type-check` - Type checking passed
- [x] `just check` - Full quality pipeline passed
- [x] Contract tests validate OpenAPI schema compliance
- [x] Integration tests verify A2A request/response cycle
- [x] Integration tests verify existing endpoints unaffected

## Breaking Changes

None - this is a purely additive change.

## Checklist

- [x] Tests added/updated
- [x] Documentation updated (README.md)
- [x] No breaking changes
- [x] All quality checks passing

────────────────────────────────────────

Verification Results:
✓ just test - All 318 tests passed
✓ just lint - No errors
✓ just type-check - Passed
✓ just check - Full pipeline passed

Shall I update PR #156 with this description?

User: Yes

AI: [Runs: gh pr edit 156 --body "..."]

✓ PR #156 description updated successfully
URL: https://github.com/org/repo/pull/156

All automated verification checks passed. The PR is ready for review.
```

## When to Use This Command:

- After pushing commits to a PR branch
- Before requesting code review
- When PR description is outdated after new commits
- As part of the workflow after `/commit` command
- Integration with Spec-Kit: After completing implementation phases and committing changes

## Troubleshooting:

**"no default remote repository"**:
- Run: `gh repo set-default` and select the repository

**"GraphQL: Could not resolve to a PullRequest"**:
- Check PR number is correct
- Ensure you have access to the repository

**Verification commands fail**:
- Document failures in description
- Mark checkboxes as unchecked with explanation
- Show failures to user in review
- User can fix issues before approving PR description update

**No PR template found**:
- Command automatically tries repo-level → org-level → standard format
- If both repo and org templates are missing, standard format is used
- Adapt to repository conventions based on commit history

**Org template lookup fails**:
- This is normal for personal repos (not in an organization)
- Command will gracefully fall back to standard format
- No action needed from user
