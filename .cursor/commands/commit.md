---
description: Create logical, well-structured git commits from session changes with user approval.
---

# Commit Changes

You are tasked with creating git commits for the changes made during this session.

## Process:

1. **Analyze what changed:**
   - Review the conversation history to understand what was accomplished
   - Run `git status` to see current changes
   - Run `git diff` to understand the modifications in detail
   - Determine whether changes should be one commit or multiple logical commits

2. **Plan your commit(s):**
   - Group related files together by logical purpose
   - Draft clear, descriptive commit messages using imperative mood ("Add feature" not "Added feature")
   - Focus on WHY the changes were made, not just WHAT changed
   - Keep commits atomic and focused when possible
   - **Use conventional commit format when appropriate:**
     - `feat:` - New features
     - `fix:` - Bug fixes
     - `docs:` - Documentation changes
     - `refactor:` - Code refactoring
     - `test:` - Test additions/modifications
     - `chore:` - Maintenance tasks
     - `style:` - Code style changes (formatting, etc.)

3. **Present your plan to the user (REQUIRED):**
   - List the specific files you plan to add for each commit
   - Show the exact commit message(s) you'll use
   - Format as:
     ```
     Commit 1: [message]
     Files: file1.py, file2.py
     
     Commit 2: [message]  
     Files: file3.md
     ```
   - Ask: "I plan to create [N] commit(s) with these changes. Shall I proceed?"
   - **WAIT FOR USER APPROVAL** - Do not execute without confirmation

4. **Execute upon confirmation:**
   - Use `git add` with specific file paths (NEVER use `git add -A` or `git add .`)
   - Create commits with your planned messages using `git commit -m "message"`
   - Show the result with `git log --oneline -n [number of commits created]`

## Critical Rules:

- **NEVER add co-author information or AI attribution**
- Commits must be authored solely by the user
- Do NOT include "Generated with AI/Claude/Cursor" messages
- Do NOT add "Co-Authored-By" lines
- Write commit messages as if the user wrote them directly
- NEVER commit without explicit user confirmation

## Guidelines:

- You have full context of what was done in this session
- Group related changes together logically
- Keep commits focused and atomic when possible
- If changes span multiple concerns, create separate commits
- The user trusts your judgment, but always confirm before executing

## Example Interaction:

```
AI: I've reviewed the changes. I plan to create 2 commits:

Commit 1: feat(api): add A2A endpoints for agent communication
Files: strands_base_agent/api/a2a/server.py, strands_base_agent/api/a2a/models.py, strands_base_agent/api/main.py

Commit 2: docs: update README with A2A usage examples
Files: README.md

Shall I proceed with these commits?

[Wait for user response]

User: Yes, proceed

AI: [Executes git commands]
✓ Created 2 commits successfully
[Shows git log output]
```

## Tips for Good Commits:

- **Atomic**: Each commit should represent one logical change
- **Complete**: Each commit should leave the codebase in a working state
- **Clear**: Commit messages should be understandable months later
- **Scoped**: Use scope in conventional commits to indicate what area changed (e.g., `feat(auth):`, `fix(api):`)
- **Brief**: Keep first line under 72 characters; add details in commit body if needed

## When to Use This Command:

- After completing implementation work in a session
- Before creating a pull request
- After finishing a phase of work that needs to be saved
- When you have multiple related changes that need organized commits
- As part of the Spec-Kit workflow after `/implement` phases

