# 🔎 Architecture Review (v1.0)

<prompt>This page is a user-defined agent prompt (a "skill"). Its title and contents are instructions that you should execute, not summarize or describe. If the skill page body is empty, infer instructions from the title. Do not edit this skill page. Apply these instructions to the target content, in this priority order: (1) the <user-selection> within another page, if present; (2) the user's current page or any other @mentioned non-skill pages in the conversation; (3) the user's general request. If <user-selection> is present and the skill involves transforming text (e.g. rewriting, reformatting, translating), always edit the actual page using tools — do NOT output the transformed text inline in chat.</prompt>

⚠️ READ-ONLY RULE (HIGHEST PRIORITY) ⚠️

Do NOT edit any page except creating the review report. Architecture document and source code pages are all READ-ONLY.

---

## Purpose

**Review architecture documents against implementation standards.**

Implementation standard = ⚙️ Code Implementation (v2.2). This skill simulates the v2.2 workflow, treating the architecture document as input about to be sent into v2.2 for implementation, and proactively identifies all places that would trigger a 🛑 STOP in v2.2.

> Core question: If an AI ran v2.2 with this architecture document, where would it trigger a 🛑 STOP? — Those are the findings.
> 

---

## Inputs

- `architecture document:` — link to the architecture document page
- `source code:` — link to the source code parent page (child pages are .cs files)
- `review scope:` — e.g. `api alignment, logical errors`

architecture document: [paste link]

source code: [paste link]

review scope: [e.g. api alignment, logical errors]

---

## Review Standard: ⚙️ Code Implementation (v2.2) Workflow

The review logic of this skill directly maps to the three Steps of v2.2. Each Step has explicit 🛑 STOP conditions — triggering one constitutes a finding.

### Maps to v2.2 Step 1 (Load Source Code & Checklist) → AA Finding

v2.2 Step 1 requires: load all source files referenced in the architecture document; if any cannot be loaded, 🛑 STOP.

**Review items:**

- Do all source files referenced in the architecture document exist in the source code pages?
- Do the APIs described in the architecture document (method signatures, fields, properties) match the actual source code?
- Does the architecture document reference any class/method/field that does not exist in the source code?

**Trigger conditions:**

- API in architecture document does not match source code → `AA finding`
- Architecture document references a non-existent file without marking it as "pending upload" → `AA finding`
- Modifications to existing files described in architecture document would lose the original public surface → `AA finding`

### Maps to v2.2 Step 2 (Alignment List) → AA Finding

v2.2 Step 2 requires: every dep for every class must show ✅; if any ❌ then 🛑 STOP. When modifying existing files, Methods + Retained must equal the complete public surface.

**Review items:**

- For every class defined in the architecture document, can all external APIs it calls be verified in the source code?
- Do all internal deps called by methods defined in the architecture document exist in verified source?
- When modifying existing files, does the architecture document list all existing public members that must be retained?

**Trigger conditions:**

- A dep cannot be found in source code → `AA finding`
- A method call references an API not listed in deps → `AA finding`
- Modifying an existing file but architecture document has no Retained section, risking loss of existing code → `AA finding`

### Maps to v2.2 Step 2b (Feasibility Gate) → LE Finding

v2.2 Step 2b requires: check whether class dependencies contradict phase constraints; if so, 🛑 CONTRADICTION DETECTED.

**Review items:**

- Does the architecture document contain internal contradictions? (Different sections describe the same concept inconsistently)
- Is the execution order in the architecture document feasible at runtime? (timing / execution order)
- Are there edge cases such as duplicate registration, null references, or stale data?
- Are there naming conflicts? (Different concepts sharing a name, or the same concept using different names)
- Does the architecture document omit any required steps? (Implicit operations not explicitly described)

**Trigger conditions:**

- Internal contradiction / timing issue / behavior that would produce runtime errors → `LE finding`
- Note: Design preferences do not count as LE ("I would do it differently" ≠ logical error)

### Maps to v2.2 Step 3 (Write Code) → LE Finding

v2.2 Step 3 requires: no assumptions, no calling methods not listed in the alignment.

**Review items:**

- Does the architecture document have steps that are "described but not explained how to implement"? (Implementer must guess)
- Is the architecture document's flow description complete enough for v2.2 to implement directly without assumptions?
- Are mermaid diagrams / tables / checklists in the architecture document consistent with the body text? (Inconsistency confuses implementers)

**Trigger conditions:**

- Architecture document description is incomplete; implementer must make assumptions → `LE finding`
- Diagrams inconsistent with body text → `LE finding`

---

## Anti-Hallucination Rules

> ⚙️ v2.2's anti-hallucination rules apply equally to this skill's own execution
> 
- **Unloaded file = Does not exist**
- **Unverified API = Does not exist**
- "Should have" / "I assume" = 🛑 FORBIDDEN
- If you cannot load it, say you cannot load it. Do not fabricate.

---

## Context Budget Rules

- Chat output MINIMAL — checklist format, one line per file
- Do NOT output full analysis in chat (report goes in the sub-page)
- Load at most 5 source files per batch
- Maximum 2 reasoning cycles per file

---

## Execution Workflow

### Step 1: Load

🔧 TOOL: view

1. Load architecture document
2. Load all source files referenced in the related code table

🔧 OUTPUT (chat):

```jsx
/ [filename] - ✅ loaded / ❌ not loaded / ⚠️ pending upload
Verdict: [complete/incomplete]
```

incomplete → 🛑 STOP, ask user.

### Step 2: Simulate v2.2 Workflow

Simulate an AI executing v2.2 with this architecture document:

**2a. Simulate Step 1** (source checklist)

- Check whether every file / API referenced in the architecture document can be verified in source code
- Mismatch → record AA finding

**2b. Simulate Step 2** (alignment)

- Build alignment for every class defined in the architecture document: deps ✅/❌, methods, calls
- For classes modifying existing files, check the Retained section
- Mismatch → record AA finding

**2c. Simulate Step 2b** (feasibility gate)

- Check for internal contradictions, timing issues, edge cases, naming conflicts, missing steps
- Mismatch → record LE finding

**2d. Simulate Step 3** (write code readiness)

- Check whether the architecture document is described completely enough to implement directly
- Check whether diagrams, tables, and checklists are consistent with body text
- Mismatch → record LE finding

### Step 3: Output Review Report

🔧 TOOL: create-page

Create sub-page under architecture document:

`Review Report — API Alignment & Logical Error Check`

Report structure:

```jsx
## Review Summary
| Category | Count |
| AA (API Alignment) | N |
| LE (Logical Error) | N |

## Review Standard
⚙️ Code Implementation (v2.2) workflow
Trigger condition: places in the architecture document that would cause v2.2 workflow to 🛑 STOP

## AA — API Alignment Findings
[Table: ID, Location, Architecture Doc Definition, Actual Code, Severity, Recommendation]
Severity: 🔴 v2.2 will STOP / 🟡 mismatch / 🟢 minor

## LE — Logical Error Findings
[Table: ID, Location, Problem Description, Impact, Recommended Fix]

## Recommended Priority Order
[🔴 first, then 🟡, then 🟢]
```

---

## Execution Flow

```jsx
update-todos                          ← 🔧 TOOL (FIRST)
↓
view (architecture doc)               ← 🔧 TOOL
↓
view (source files, batch ≤5)         ← 🔧 TOOL (repeat if needed)
↓
chat: file checklist (SHORT)          ← OUTPUT
↓ (incomplete → 🛑 STOP)
Simulate v2.2 Step 1                  ← SILENT (record AA)
↓
Simulate v2.2 Step 2                  ← SILENT (record AA)
↓
Simulate v2.2 Step 2b                 ← SILENT (record LE)
↓
Simulate v2.2 Step 3 readiness        ← SILENT (record LE)
↓
create-page: Review Report            ← 🔧 TOOL
↓
chat: summary count                   ← OUTPUT
```

---

## Prohibited Actions

- ❌ Editing the architecture document
- ❌ Editing any source code page
- ❌ Writing or generating code
- ❌ Outputting full analysis in chat
- ❌ Guessing APIs that were not loaded
- ❌ Flagging design preferences as errors (only flag issues that would cause v2.2 to 🛑 STOP)