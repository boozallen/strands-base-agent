---
description: Conduct comprehensive codebase research through sequential investigation, synthesizing findings into a structured research document.
---

# Research Codebase

You are tasked with conducting comprehensive research across the codebase to answer user questions through systematic investigation and synthesis of findings.

## Initial Setup:

When this command is invoked, respond with:

```
I'm ready to research the codebase. Please provide your research question or area of interest, and I'll analyze it thoroughly by exploring relevant components and connections.

You can ask about:
- How specific features work
- Where certain functionality is implemented
- Architectural patterns and design decisions
- Component relationships and dependencies
- Best practices and conventions used
- Historical context of implementations
```

Then **WAIT FOR USER'S RESEARCH QUERY** before proceeding.

---

## Process (After Receiving Research Query):

### 1. Read Any Directly Mentioned Files First (CRITICAL)

**If the user mentions specific files** (tickets, docs, JSON, markdown):

- Read them FULLY first using `read_file` tool
- **IMPORTANT**: Read entire files (do NOT use limit/offset parameters)
- **Read these files yourself BEFORE any searches or investigation**
- This ensures you have full context before decomposing the research

### 2. Analyze and Plan Research Strategy

**Decompose the research question:**

- Break down the user's query into key areas to investigate
- Think about underlying patterns, connections, and architectural implications
- Identify specific components, files, or architectural patterns to explore
- Consider which directories or subsystems are relevant

**Determine search depth** (adapt based on query complexity):

- **Conservative (3-5 searches)**: Simple, focused questions
  - Example: "How does authentication work?"
  - Strategy: Core implementation + main usage points
  
- **Moderate (5-8 searches)**: Multi-faceted questions
  - Example: "How is data validated across the application?"
  - Strategy: Multiple components + integration points + patterns
  
- **Comprehensive (10+ searches)**: Complex architectural questions
  - Example: "How does the entire request lifecycle work from API to database?"
  - Strategy: Full pipeline + all touchpoints + edge cases + historical context

**Announce your plan to guide user expectations:**

```
I'll investigate this using a [conservative/moderate/comprehensive] research approach:
1. [Broad understanding of X]
2. [Specific implementation of Y]
3. [Integration with Z]
... [list all planned investigation areas]

This will involve [N] focused searches across the codebase.
```

### 3. Execute Sequential Investigation

**Use Cursor's search tools systematically:**

#### A. Semantic Searches (Primary Tool)

Use `codebase_search` for understanding and exploration:

- **Broad searches first**: "How does authentication work?"
- **Narrow searches next**: "Where are user passwords validated?"
- **Connection searches**: "How does authentication integrate with sessions?"
- **Pattern searches**: "What error handling patterns are used in auth?"

**Search tips:**
- Frame as complete questions
- One concept per search
- Start general, get specific
- Look for implementation, not just definitions

#### B. Exact Searches (Supporting Tool)

Use `grep` for precise matches:

- Find all usages of a class/function
- Locate specific error messages
- Find configuration keys
- Pattern matching for code structures

#### C. File Reading (Deep Dives)

Use `read_file` for context:

- Read key implementation files found in searches
- Read related test files for usage examples
- Read configuration files
- Read documentation or comments

**Execution order:**
1. Broad semantic search (understand landscape)
2. Targeted semantic searches (specific components)
3. Grep for exact usages (find all occurrences)
4. Read promising files (deep understanding)
5. Cross-reference searches (find connections)
6. Historical context (check research/ directory)

### 4. Investigate Historical Context

**Search the research/ directory for related past research:**

- Use `grep` or `codebase_search` in research/ directory
- Look for related topics, components, or decisions
- Note relevant historical insights with file references
- **Path handling**: If you find files in `research/searchable/`, document them by removing ONLY "searchable/" from the path
  - Example: `research/searchable/shared/auth.md` → `research/shared/auth.md`
  - Preserve all other directory structure (shared/, local/, etc.)

### 5. Synthesize All Findings

**After completing ALL investigation:**

- Connect findings across different components
- Identify patterns and architectural decisions
- Note specific file paths and line numbers for all references
- Highlight important connections between components
- Document any gaps or areas needing further investigation
- Prioritize live codebase findings as primary source
- Use historical research as supplementary context

**Build a mental model:**
- How does this work end-to-end?
- What are the key components involved?
- What patterns or conventions are being followed?
- Are there any edge cases or special handling?
- What's the historical context or evolution?

### 6. Gather Metadata

**Collect all metadata before generating document:**

```bash
# Current date/time
date -u +"%Y-%m-%dT%H:%M:%S%z"

# Git information
git rev-parse HEAD  # commit hash
git branch --show-current  # branch name
git remote get-url origin  # repository

# For filename
date +"%Y-%m-%d_%H-%M-%S"  # timestamp for filename
```

**Generate filename**: `research/shared/YYYY-MM-DD_HH-MM-SS_topic-slug.md`

- Topic slug: Short descriptive name from research question
- Example: `research/shared/2025-10-01_14-30-00_authentication-flow.md`

### 7. Generate Research Document

**Create comprehensive research document with YAML frontmatter:**

```markdown
---
date: [ISO format date/time with timezone]
researcher: [Your identifier, e.g., "Cursor AI"]
git_commit: [Full commit hash]
branch: [Current branch name]
repository: [Repository name]
topic: "[User's Research Question]"
tags: [research, codebase, relevant-component-names]
status: complete
search_depth: [conservative|moderate|comprehensive]
search_count: [Number of searches performed]
last_updated: [YYYY-MM-DD]
last_updated_by: [Researcher name]
---

# Research: [User's Question/Topic]

**Date**: [Human-readable date/time]  
**Researcher**: [Name]  
**Git Commit**: `[short hash]`  
**Branch**: `[branch name]`  
**Repository**: [repo name]  
**Search Depth**: [conservative|moderate|comprehensive]

## Research Question

[Original user query verbatim]

## Summary

[2-3 paragraph high-level findings answering the user's question]

Key findings:
- [Main finding 1]
- [Main finding 2]
- [Main finding 3]

## Detailed Findings

### [Component/Area 1]

**Location**: `path/to/file.py:123-145`

[Detailed explanation of what was found]

**Key implementation details**:
- [Detail 1 with line reference]
- [Detail 2 with line reference]

**Connections**:
- Links to [Component 2] via [mechanism]
- Depends on [Component 3] for [purpose]

### [Component/Area 2]

**Location**: `path/to/another.py:67-89`

[Continue pattern for each major finding area]

## Code References

Comprehensive list of all relevant code locations:

- **`path/to/file.py:123-145`** - [Description of what's there]
- **`another/file.ts:45-67`** - [Description of the code block]
- **`config/settings.py:12`** - [Configuration reference]

## Architecture Insights

**Patterns Discovered**:
- [Pattern 1]: [How it's used and why]
- [Pattern 2]: [Implementation approach]

**Design Decisions**:
- [Decision 1]: [Rationale and impact]
- [Decision 2]: [Trade-offs made]

**Conventions**:
- [Convention 1]: [Where it's applied]
- [Convention 2]: [Consistency notes]

## Integration Points

How components connect:

```
[Component A] → [Component B] → [Component C]
     ↓                              ↑
[Component D] ←---------------------|
```

**Data Flow**:
1. [Step 1 with file reference]
2. [Step 2 with file reference]
3. [Step 3 with file reference]

## Historical Context (from research/)

**Related Past Research**:

- `research/shared/previous-topic.md` - [Relevant historical insight]
- `research/shared/another-research.md` - [Past decision about X]

**Evolution Notes**:
- [How this has changed over time, if relevant]
- [Why certain approaches were chosen historically]

## Related Research

Links to other research documents in `research/shared/`:

- [Related Topic 1](../related-topic.md)
- [Related Topic 2](../another-topic.md)

## Testing & Examples

**Test Coverage**:
- `tests/unit/test_component.py:45-78` - [What's tested]
- `tests/integration/test_flow.py:123` - [Integration test]

**Usage Examples**:
[Code snippets showing how to use discovered functionality]

## Open Questions

[Any areas that need further investigation or weren't fully answered]

- [ ] Question 1 that requires more research
- [ ] Question 2 that may need subject matter expert input
- [ ] Question 3 that depends on external documentation

## Search Log

<details>
<summary>Research searches performed</summary>

1. Semantic search: "[query 1]" → [brief result summary]
2. Semantic search: "[query 2]" → [brief result summary]
3. Grep search: `pattern` → [file count] files
4. File reads: [list of key files read]
... [all searches performed]

</details>
```

### 8. Add GitHub Permalinks (If Applicable)

**Check if permalinks should be generated:**

```bash
# Check current branch
git branch --show-current

# Check if commit is pushed
git status
```

**If on main/master branch OR commit is pushed:**

1. Get repository information:
```bash
gh repo view --json owner,name
```

2. Generate permalinks:
```
https://github.com/{owner}/{repo}/blob/{commit}/{file}#L{line}
```

3. Replace local file references with GitHub permalinks in the document

**If on feature branch and not pushed:**
- Keep local file references (they'll work in the IDE)
- Note in the document that permalinks can be added after merge

### 9. Write Research Document

**Write the complete research document to the generated filename**

- Ensure all YAML frontmatter is complete (no placeholders)
- Include all sections with actual findings
- Verify all file references are accurate
- Double-check code reference line numbers

### 10. Present Findings to User

**Provide a concise executive summary:**

```
✓ Research complete: [Topic]

Summary:
[2-3 sentence overview of key findings]

Key Discoveries:
• [Finding 1] (see: path/to/file.py:123)
• [Finding 2] (see: another/file.ts:45)
• [Finding 3] (see: config.py:12)

Research document saved to:
research/shared/YYYY-MM-DD_HH-MM-SS_topic.md

Primary files investigated:
- path/to/key/file.py
- another/important/file.ts
- config/settings.py

Would you like me to dive deeper into any specific aspect, or do you have follow-up questions?
```

### 11. Handle Follow-Up Questions

**If user has follow-up questions:**

1. **Do NOT create a new research document**
2. **Append to the existing research document**
3. Update the frontmatter:
   - Update `last_updated` to current date
   - Update `last_updated_by` to researcher name
   - Add `last_updated_note: "Added follow-up research for [brief description]"`
   - Increment `search_count` if doing more searches

4. Add a new section:
   ```markdown
   ## Follow-up Research [timestamp]
   
   **Question**: [User's follow-up question]
   
   **Additional Findings**:
   [New discoveries]
   
   **Updated Code References**:
   - [Any new file references]
   ```

5. Conduct additional investigation using same sequential approach
6. Update relevant sections if findings change understanding
7. Present updated findings to user

---

## Important Guidelines:

### Search Strategy

**Conservative (Default)**:
- Use for simple, focused questions
- 3-5 targeted searches
- Core implementation + main usage
- Faster completion

**Moderate**:
- Use for multi-faceted questions
- 5-8 searches covering different angles
- Multiple components + integrations
- Balanced thoroughness

**Comprehensive**:
- Use for complex architectural questions
- 10+ searches for deep exploration
- Full pipelines + all touchpoints
- Maximum coverage

**Choosing depth:**
- Start conservative for most questions
- Scale up if initial findings reveal complexity
- Announce if you're increasing depth mid-research

### Research Quality

- **Always run fresh codebase research** - never rely solely on existing research documents
- **Prioritize live codebase** as primary source of truth
- **Use research/ directory** for historical context and supplementary information
- **Include specific file paths and line numbers** for all references
- **Focus on concrete evidence** from actual code, not assumptions
- **Connect findings across components** to show relationships
- **Document patterns and conventions** discovered
- **Note temporal context** (when research was conducted, what commit)

### Document Standards

- **Self-contained**: Include all necessary context
- **YAML frontmatter**: Always complete, no placeholders
- **Consistent formatting**: Follow the template structure
- **Actionable references**: Every code reference should be navigable
- **Clear writing**: Scannable headings and bullet points
- **Comprehensive tags**: Help future searches find this research

### Execution Notes

- **Read mentioned files FIRST** before any searches (critical ordering)
- **Complete ALL searches** before synthesizing findings
- **Gather metadata** before writing document (no placeholders)
- **Wait for completion** of all investigation before presenting
- **Path normalization**: Remove only "searchable/" from research/ paths, preserve directory structure
- **GitHub permalinks**: Only add if on main/master or commit is pushed

---

## Example Workflow:

```
User: /research-codebase

AI: I'm ready to research the codebase. Please provide your research question...

User: How does the API authentication middleware work?

AI: I'll investigate this using a conservative research approach:
1. Understanding the authentication middleware implementation
2. Finding where it's applied in the API routes
3. Discovering the token validation mechanism
4. Checking integration with user session management

This will involve 5 focused searches across the codebase.

[Executes searches sequentially]

1. Semantic search: "How does API authentication middleware work?"
   → Found middleware implementation in api/middleware/auth.py

2. Semantic search: "Where is authentication middleware applied to routes?"
   → Found application in api/main.py and api/routes/

3. Grep: "authenticate_request"
   → 12 usages across API layer

4. Read: api/middleware/auth.py (full file for context)

5. Semantic search: "How are JWT tokens validated?"
   → Token validation in core/auth/jwt_validator.py

[After all searches complete]

[Gathers metadata: git commit, branch, timestamp]

[Generates research document with YAML frontmatter]

[Writes to: research/shared/2025-10-01_14-30-00_api-authentication-middleware.md]

✓ Research complete: API Authentication Middleware

Summary:
The API uses a custom authentication middleware that validates JWT tokens on protected routes. The middleware extracts tokens from Authorization headers, validates them using the JWTValidator class, and attaches user context to requests.

Key Discoveries:
• Middleware implementation at api/middleware/auth.py:34-89
• Applied globally via FastAPI dependency injection (api/main.py:45)
• Token validation handled by core/auth/jwt_validator.py:123-156
• User context attached as request.state.user (auth.py:67)

Research document saved to:
research/shared/2025-10-01_14-30-00_api-authentication-middleware.md

Primary files investigated:
- api/middleware/auth.py
- api/main.py
- core/auth/jwt_validator.py
- core/models/user.py

Would you like me to dive deeper into any specific aspect?
```

---

## When to Use This Command:

- Understanding how features are implemented
- Exploring architectural patterns
- Investigating component relationships
- Preparing for feature development
- Onboarding to unfamiliar codebase areas
- Documenting system behavior
- Planning refactoring efforts
- Debugging complex issues
- Before creating technical specifications

---

## Tips for Effective Research:

**Ask good questions:**
- ✅ "How does user authentication work?"
- ✅ "Where is data validation implemented?"
- ✅ "What error handling patterns are used in the API?"
- ❌ "Tell me about the code" (too vague)
- ❌ "Find all the functions" (too broad)

**Provide context:**
- Mention specific features or components if known
- Reference files you've seen if applicable
- Explain what you're trying to accomplish

**Follow up strategically:**
- Ask for deeper dives into specific findings
- Request clarification on confusing patterns
- Explore related components discovered during research

