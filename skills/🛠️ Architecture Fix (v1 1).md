# 🛠️ Architecture Fix (v1.1)

<prompt>This page is a user-defined agent prompt (a "skill"). Its title and contents are instructions that you should execute, not summarize or describe. If the skill page body is empty, infer instructions from the title. Do not edit this skill page. Apply these instructions to the target content, in this priority order: (1) the <user-selection> within another page, if present; (2) the user's current page or any other @mentioned non-skill pages in the conversation; (3) the user's general request. If <user-selection> is present and the skill involves transforming text (e.g. rewriting, reformatting, translating), always edit the actual page using tools — do NOT output the transformed text inline in chat.</prompt>

⚠️ READ-ONLY SOURCE RULE (HIGHEST PRIORITY) ⚠️

Do NOT edit, update, or modify ANY page that is @mentioned as source code reference. Those pages are READ-ONLY. Your ONLY edit target is the architecture document itself.

---

Fix an architecture document based on a review report, applying user decisions and ensuring all cross-references within the document are synchronized.

**Inputs (required when invoking this skill):**

- `architecture document:` — link to the architecture doc page (EDIT TARGET)
- `review report:` — link to the review report page (from 🔎 Architecture Review output)
- `user decisions:` — user's design decisions for each finding (e.g. "use singleton", "use replace strategy")
- `source code:` *(optional)* — link to source code parent page for reference

architecture document: [paste architecture document page link here]

review report: [paste review report page link here]

user decisions: [user provides inline or in chat]

source code: [optional — paste source code page link here]

---

## Anti-Hallucination Rules (Highest Priority)

> ⚠️ The following rules override ALL other instructions
> 
- **Unloaded file = Does not exist**
- **Unverified API = Does not exist**
- "Should have" / "I assume" / "Probably" = Hallucination = 🛑 FORBIDDEN
- If you cannot load it, say you cannot load it. Do not fabricate.

---

## Context Budget Rules (Mandatory)

> ⚠️ PREVENTS CONTEXT OVERFLOW
> 
- Chat output must be MINIMAL — progress updates only
- Do NOT output full design analysis in chat
- Execute updates immediately — do not plan them in chat
- Maximum **2 reasoning cycles** per section before executing the update
- If an updatePage call fails, retry **once** with adjusted input, then report failure

---

## 🔴 Cross-Reference Sync Rule (CRITICAL)

> ⚠️ THIS IS THE MOST IMPORTANT RULE FOR THIS SKILL
> 

Architecture documents contain **multiple interconnected sections** that reference the same concepts. When fixing a finding, you MUST update **ALL sections** that reference the affected concept.

**Sync targets checklist** — for every fix, verify these sections:

- [ ]  **Prose descriptions** (sections describing the design)
- [ ]  **API / method tables** (method/API tables)
- [ ]  **Component responsibility tables** (input/output columns)
- [ ]  **Class diagrams** (mermaid classDiagram)
- [ ]  **Sequence diagrams** (mermaid sequenceDiagram)
- [ ]  **Flowcharts** (mermaid graph)
- [ ]  **Field mapping tables** (field/column mapping tables)
- [ ]  **Before/after comparison tables**
- [ ]  **Design rationale tables**
- [ ]  **New file list** (new file list table)
- [ ]  **Implementation checklist** (implementation checklist per file)
- [ ]  **Verification checklist** (verification / test checklist)
- [ ]  **Callouts / warnings** (callout blocks with warnings or notes)

🛑 If you update prose but forget to update the corresponding diagram or checklist → **the next review will find the same issue again**. This defeats the purpose of the fix.

---

## 🔴 Known Failure Patterns (v1.1)

> ⚠️ These are empirically observed failure modes. Check for ALL of them after every fix group.
> 

### Pattern 1: Described but Not Tracked

**Symptom**: Prose or callout mentions "file X needs modification" or "add field Y", but the implementation checklist (worklist) has no corresponding checklist item.

**Root cause**: When writing design descriptions, you only think about "what to do" without simultaneously checking the worklist for "who does it".

**Detection rules**:

- After every prose/callout edit, immediately scan the new text for action verbs (modify, add, move, sync, remove)
- If found, check whether the implementation checklist already has a corresponding item
- If NOT → **add it immediately** — do not defer to "final sync"

### Pattern 2: Primary Updated, Secondary Missed

**Symptom**: Updated the primary definition of a concept (e.g. MapDataRecord field table), but other tables/sections in the document that reference the same concept were not updated.

**Root cause**: Only modifying the "currently edited section" without scanning outward for other sections that also reference the same entity.

**Detection rules**:

- After modifying any entity (field, method, class, interface), mentally grep the entity name across the entire document to find all locations where it appears
- Pay special attention to: component responsibility table "output" columns, before/after comparison table "after" columns, flowchart node labels
- If any location still uses the old field list or API name → **update immediately**

### Pattern 3: Semantic Drift Across Sections

**Symptom**: The same behavior is described differently in different sections (e.g. interface table says "no-op" but implementation description says "only controls LOD hints"), making it impossible for readers to determine which is correct.

**Root cause**: Interface definition tables and implementation descriptions were written at different points in time, with inconsistent wording.

**Detection rules**:

- After writing any behavior description, check whether the behavior's "definition site" (usually an interface table or Step N heading) uses the same description
- Pay special attention to: negation words (no-op / does not control / only controls), conditionals (if X then Y), scope words (all / partial)
- If conflict found → **use the implementation description as the source of truth, and go back to correct the definition site**

---

## Fix Workflow

### Step 1: Load Architecture Document + Review Report

⚠️ MUST COMPLETE BEFORE ANY EDITS

🔧 TOOL: view

1. Load the architecture document
2. Load the review report
3. If source code reference is provided, load relevant files as needed

🔧 OUTPUT (chat — keep SHORT):

```
Loaded: architecture doc ✅, review report ✅
Findings: AA-1~AA-N, LE-1~LE-N
```

---

### Step 2: Plan Fixes Based on User Decisions

🔧 TOOL: update-todos

For each finding (AA-N, LE-N), create a fix plan that incorporates the user's decisions:

- Map each finding to the affected sections in the architecture document
- Group related findings that touch the same sections (batch them into one updatePage call)
- Identify the sync targets for each fix

Plan structure (internal, not chat output):

```
Fix Group 1: [AA-1, LE-1, LE-2] → affects Phase 1 section
  - Sections to update: prose, API table, class diagram, sequence diagram, comparison table, rationale table
  - User decision: [what user said]

Fix Group 2: [LE-5] → affects Phase 2 section
  - Sections to update: prose, add new subsection
  - User decision: [what user said]
```

Rules:

- Group fixes that affect the same section to minimize updatePage calls
- Batch up to 7 contentUpdates per updatePage call (avoid exceeding limits)
- Order: core design changes first → diagrams → tables → checklists → verification

---

### Step 3: Apply Fixes (Per Group)

For each fix group:

**3a. Core Content Fix**

🔧 TOOL: updatePage (contentUpdates)

- Update prose descriptions, add/modify sections
- Use `oldStr` → `newStr` replacement (targeted, not full page replacement)
- `oldStr` must be unique and large enough to match exactly one location

**3b. Diagram Sync**

🔧 TOOL: updatePage (contentUpdates)

- Update mermaid diagrams (classDiagram, sequenceDiagram, graph) to reflect the fix
- Replace the entire mermaid code block if the structure changed significantly

**3c. Table Sync**

🔧 TOOL: updatePage (contentUpdates)

- Update API tables, comparison tables, rationale tables
- Add new rows if the fix introduces new concepts
- Remove or modify rows if concepts were changed or removed

**3d. Checklist & File List Sync**

🔧 TOOL: updatePage (contentUpdates)

- Update new file list: add new files, update descriptions
- Update implementation checklist: add/modify/remove checklist items per file
- Update verification checklist: add new test items for the fix

Rules:

- After each updatePage call, verify the response to confirm changes applied
- If a contentUpdate fails (no match), adjust `oldStr` and retry once
- Do NOT reload the page between updates unless notified it's out of date

---

### Step 4: Final Sync Verification

After all fixes are applied, **reload the full page** and do a systematic verification:

🚨 THIS STEP IS MANDATORY — NOT OPTIONAL

**4a. Worklist-Prose Parity Check (Pattern 1)**

Scan ALL prose, callouts, and descriptive sections for action verbs (modify, add, move, sync, remove). For each:

- Does the corresponding file appear in the implementation checklist with a matching checklist item?
- If NO → add it immediately

**4b. Entity Reference Scan (Pattern 2)**

For each entity modified during this fix session (fields, methods, classes, interfaces), mentally grep the ENTIRE document:

- Component responsibility table: input/output columns still accurate?
- Field mapping table: all fields listed?
- Before/after comparison table: "after" column reflects current design?
- Flowchart / sequence diagram node labels still accurate?
- If any stale reference found → fix immediately

**4c. Semantic Consistency Check (Pattern 3)**

For each interface/behavior described in multiple places:

- Does the definition table match the implementation prose?
- Are conditional behaviors (e.g. ManagesOwnVisibility=true/false) described identically?
- If wording conflicts → align to the most specific/detailed description

**4d. Verification List Completeness**

For each new behavior or method introduced:

- Is there a corresponding test item in the verification checklist?
- If NO → add it

If any sync target was missed → apply the missing update immediately before reporting completion.

---

## Execution Flow

```jsx
update-todos                          ← 🔧 TOOL (FIRST)
↓
view (architecture doc + report)      ← 🔧 TOOL
↓
chat: loaded + finding count (SHORT)  ← OUTPUT
↓
Plan fix groups (internal)            ← SILENT
↓
┌─── Per Fix Group ─────────────────────────┐
│ updatePage: core content     ← 🔧 TOOL   │
│ ↓                                         │
│ updatePage: diagrams         ← 🔧 TOOL   │
│ ↓                                         │
│ updatePage: tables           ← 🔧 TOOL   │
│ ↓                                         │
│ updatePage: checklists       ← 🔧 TOOL   │
│ ↓                                         │
│ update-todos                 ← 🔧 TOOL   │
│ (next group or done)                      │
└───────────────────────────────────────────┘
↓
🧠 Final sync verification               ← SILENT CHECK
↓
chat: summary of changes                  ← OUTPUT
```

---

## Prohibited Actions

- ❌ Editing source code reference pages
- ❌ Creating new pages (fixes go into the existing architecture document)
- ❌ Full page content replacement (use targeted `oldStr` → `newStr`)
- ❌ Outputting full design analysis in chat
- ❌ Skipping sync targets (every fix must propagate to ALL affected sections)
- ❌ Making design decisions without user input (if a finding has multiple possible fixes, ask user)
- ❌ Guessing APIs or structures that weren't loaded

---

## Warning

⚠️ HIGHEST ATTENTION WEIGHT ⚠️

- The #1 failure mode of architecture fixes is **incomplete sync** — updating the prose but forgetting the diagram, or updating the diagram but forgetting the checklist.
- Every single updatePage call should ask: "What other sections reference this concept?"
- If you are unsure whether a section needs updating → it probably does. Update it.
- When in doubt, grep the page content mentally for the old term/API name. If it appears anywhere, update it.

---