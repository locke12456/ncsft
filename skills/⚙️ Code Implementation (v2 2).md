# ⚙️ Code Implementation (v2.2)

<prompt>This page is a user-defined agent prompt (a "skill"). Its title and contents are instructions that you should execute, not summarize or describe. If the skill page body is empty, infer instructions from the title. Do not edit this skill page. Apply these instructions to the target content, in this priority order: (1) the <user-selection> within another page, if present; (2) the user's current page or any other @mentioned non-skill pages in the conversation; (3) the user's general request. If <user-selection> is present and the skill involves transforming text (e.g. rewriting, reformatting, translating), always edit the actual page using tools — do NOT output the transformed text inline in chat.</prompt>

⚠️ READ-ONLY SOURCE RULE (HIGHEST PRIORITY) ⚠️

Do NOT edit, update, or modify ANY page that is @mentioned or linked in the architecture document or the api reference. Those pages are READ-ONLY references — they exist solely for you to load and read as context. They are scratch/temporary copies of source code. Your ONLY output is creating NEW sub-pages under the architecture document. Never call updatePage on any referenced source page.

---

Implement C# classes from an architecture document, following the mandatory 3-step workflow below.

**Inputs (required when invoking this skill):**

- `architecture document:` — link to the architecture doc page
- `target phase:` — e.g. phase5
- `api:` *(optional)* — link to the API alignment page (e.g. [source code](https://www.notion.so/source-code-26a88e4ac48d80739fb5ce8213b619a5?pvs=21) )

architecture document: [paste architecture document page link here]

api: [paste api page link here]

Implementation Goal

1. Implement according to the architecture document. Scope: [target phase]
2. Create new sub-pages under the architecture document. One page per C# class.
3. All code in the same page must be in a single codeblock. Do not split into code parts.
    - ⚠️ **Single codeblock IS the most readable format** — `#region` provides navigation. Splitting into multiple code parts destroys class structure, makes copy-paste error-prone, and is harder to read. There is ZERO readability benefit to splitting.
    - 🛑 If you are about to create multiple codeblocks for the same class → STOP. Merge everything into one codeblock before outputting.
4. ⚠️ **Complete File Output Rule**
    - Every output page must contain the **complete, compilable source file** — not just the diff, patch, or modified section.
    - The codeblock must be **copy-paste ready** to replace the entire original file.
    - If the target is a **modification of an existing file**, the output must include ALL original code (unchanged portions) plus the new/modified code.
    - 🛑 If you are about to output only the changed methods/regions without the rest of the file → STOP. Output the full file.

Task List

After reviewing the architecture document, list the implementation targets for this task.

Plan Tool Usage Rules (Mandatory)

⚠️ ATTENTION: FIRST ACTION BEFORE ANY OTHER TOOL ⚠️

🔧 TOOL: update-todos

When using update-todos, structure todos as follows:

- Load source files & checklist
- Output Alignment List
- Alignment + Write: Class A
- Alignment + Write: Class B
- ...

Rules:

- Each class must have its own "Alignment + Write" item
- Do not batch all alignments together then all code together
- Do not combine multiple classes into one todo item

🧠 REASONING CHECK: Before proceeding, verify todo structure matches this format.

Context Budget Rules (Mandatory)

⚠️ HIGHEST PRIORITY — PREVENTS CONTEXT OVERFLOW ⚠️

1. Chat output must be MINIMAL:
    - Checklist: one line per file, no extra explanation
    - Verdict: one word (complete/incomplete)
    - Alignment: minimal list in chat, no verbose explanation
    - Design decisions: minimal list in chat, no verbose explanation
    - 🧠 REASONING CHECK results: silent unless STOP
2. Do NOT output full design analysis in chat.
3. Source file loading strategy:
    - Only load files you actually need
    - After loading, record key API signatures in Step 2 chat output
    - Later steps reference loaded sources or re-view if needed
4. If total implementation > 3 classes:
    - Consider splitting into multiple conversations
    - First conversation: Step 1 + Step 2 (Alignment List) + partial Step 3
    - Subsequent conversations: Step 3 (re-load sources if needed → one class per turn)

⚠️ Reasoning Code Output Restriction (Mandatory)

1. Do NOT write or draft full code blocks inside reasoning/thinking.
    - Reasoning should contain ONLY: logic decisions, verification checks, API lookups
    - Do NOT mentally "pre-write" implementation code in reasoning
    - Do NOT enumerate line-by-line code in reasoning
    - Code belongs ONLY in the final create-pages output
    - If you catch yourself writing code in reasoning → STOP, skip to tool output
    - This saves significant context window budget

Work Requirements - Mandatory Workflow, Do Not Skip

═══════════════════════════════════════════

Step 1: Load Source Code & Checklist

═══════════════════════════════════════════

⚠️ MUST COMPLETE BEFORE ANY CODE OUTPUT ⚠️

🔧 TOOL: view

1. Use view tool to load:
    - The architecture document
    - Reference source code files **needed for the first class only**
    - Files containing external APIs **the first class will call**
2. ⚠️ **When modifying an existing file, you MUST load the target file itself**
    - If the architecture specifies **modifying an existing file** (not creating a new file from scratch), you MUST load the original source file of the target class as part of Step 1.
    - The original file is NOT just a "dependency" — it is the **base** you are modifying.
    - 🛑 If you skip loading the target file → your output will be incomplete. Do NOT proceed.
3. ⚠️ Do NOT pre-load files for later classes. Each class loads its own deps in Step 3.

🔧 TOOL: none (chat output — keep SHORT)

After loading, output checklist (one line per file):

/ [filename] - ✅ loaded / ❌ not loaded - provides: [key APIs]

**Target file markers**

For files that are **modification targets** (not just dependencies), mark them with 🎯:

/ 🎯 [filename] - ✅ loaded — **TARGET** (existing file to modify)

/ [dep-filename] - ✅ loaded — provides: [key APIs]

Verdict: [complete/incomplete]

Rules:

- If a file cannot be loaded, paste the full view tool error
- If the architecture document contains **obvious logical errors, contradictions, or design flaws** → 🛑 STOP: describe the issue clearly and **ask user** to resolve before proceeding. **Refuse to implement** code based on a flawed design.
- If verdict is "incomplete" → 🛑 STOP: report which files are missing and **ask user** for the correct page/location. Do not attempt to resolve on your own.
- Do NOT add explanation text. Just the table and verdict.

🧠 REASONING CHECK (silent): Did I load all required files **for the current class**, **including the target file if modifying an existing class**?

═══════════════════════════════════════════

Step 2: Output Alignment List (Minimal, in Chat)

═══════════════════════════════════════════

⚠️ AFTER CHECKLIST COMPLETE, BEFORE ANY CODE ⚠️

🔧 TOOL: none (chat output — keep SHORT)

Output a flat bullet list for EVERY class. No pages, no tables.

### [ClassName]

Deps:

- ExtClass.Method(params) → Return ✅  (source: file.cs)
- ExtClass.Method2() → void ✅  (source: file.cs)

Fields:

- _fieldName : Type

Methods:

- MethodName() → Return  | calls: ExtClass.Method, ExtClass.Method2
- MethodName2() → void  | calls: none

**Retained section (only when modifying an existing file)**

If the class is a **modification of an existing file**, add a `Retained:` section listing all existing public methods/fields that must be preserved unchanged:

Retained:

- ExistingMethod1() → Return  (unchanged)
- ExistingMethod2() → void  (unchanged)
- _existingField : Type  (unchanged)

Rules:

- Every dep must show ✅. Missing → ❌ → 🛑 STOP: list the missing deps and **ask user** for the correct file/location. Do not guess or reason about where it might be.
- Every method's "calls" must exist in Deps. If not → 🛑 STOP: report the mismatch and **ask user**.
- For modified files, every item in `Retained:` must exist in the loaded original source. If the original has public members NOT listed in either `Methods:` or `Retained:` → 🛑 STOP: you are about to drop existing code.
- No tables. No paragraphs. No explanations. One line per item.

🧠 REASONING CHECK (silent): Are ALL deps verified? Any assumptions? **For modified files: does Methods + Retained = complete public surface of the original?**

═══════════════════════════════════════════

Step 2b: Architecture Feasibility Gate

═══════════════════════════════════════════

⚠️ AFTER ALIGNMENT, BEFORE ANY CODE ⚠️

For EACH class in the alignment list, ask:

**Dependency Constraint Check:**

- Does this class depend on `GameObject`, `MonoBehaviour`, `ScriptableObject`, `PrefabUtility`, or any Unity engine type that cannot be instantiated without the engine?
- Does the architecture document impose constraints (e.g. "排除 UI", "pure logic", "no engine dependency") that conflict with these dependencies?
- Can the class under test be constructed and exercised using ONLY pure C# (no Unity engine runtime)?

**Contradiction Detection:**

- If the class's public API **requires** engine types (e.g. `Initialize(MonoBehaviour target, ...)`) AND the phase goal **forbids** engine usage → 🛑 **CONTRADICTION DETECTED**
- If testing the class requires instantiating prefabs, GameObjects, or third-party UI components (e.g. `TextMeshProUGUI`) AND the phase is labeled "Unit Test" → 🛑 **CONTRADICTION DETECTED**

**On 🛑 CONTRADICTION DETECTED:**

1. Do NOT proceed to Step 3 for that class
2. Report in chat (keep short):
    - Which class is infeasible
    - The specific contradiction (one sentence)
    - Suggested resolution: skip, reclassify as integration test, or refactor architecture
3. Mark that class's todo as `failed`
4. Continue with remaining feasible classes

**On ✅ FEASIBLE:**

- Proceed to Step 3 for that class

🧠 REASONING CHECK (silent): For each class, is there ANY path to implement it within the stated constraints? If you have to pull in engine types to make it work → it is NOT feasible under "exclude UI" rules.

═══════════════════════════════════════════

Step 3: Write Code (per class, sequential)

═══════════════════════════════════════════

⚠️ ONLY AFTER STEP 2 IS COMPLETE ⚠️

For each class, do the following:

3a. Load Missing Deps (if needed)

🔧 TOOL: view — Check if the current class's deps are already loaded. If any are missing (e.g. moving from Class A to Class B requires new APIs), load them now.

If this class is a modification of an existing file AND the target file was not loaded in Step 1 (e.g. you are now on a later class), load it now. You cannot write a complete file without seeing the original.

🔧 OUTPUT (chat — keep SHORT, same format as Step 1 checklist). Skip if all deps already loaded.

3b. Write Code

🔧 TOOL: create-pages

- Create one page per class under architecture document
- Reference the alignment list from Step 2
- Every external method call must exist in Deps from Step 2
- All code in ONE codeblock. Do not split. Splitting into multiple code parts is **❌ PROHIBITED** — it harms readability, not helps it.
- ⚠️ Do NOT pre-write code in reasoning. Go directly to create-pages output.
- ⚠️ **Completeness rule**
    - The codeblock must contain the **entire compilable source file**.
    - For modified files: include ALL original `using` statements, `namespace`, class declaration, ALL original methods/fields (even unchanged ones), plus your additions/modifications.
    - 🛑 If your output is missing any method/field from the `Retained:` list in Step 2 → STOP and fix before outputting.

Rules:

- Forbidden to use hallucination or assumptions
- Forbidden to call methods not listed in alignment Deps
- Forbidden to perform replaceContent/updateContent on newly created pages
- If you discover a missing API during coding → 🛑 STOP: report what is missing and **ask user**. Do not guess.

3c. Verify Completeness

**For modified files only:**

🧠 REASONING CHECK (silent):

- Compare your output against the Retained list from Step 2.
- Does the output contain EVERY method/field from `Retained:`?
- Does the output contain ALL new methods/fields from `Methods:`?
- Are the `using` statements complete?
- Is the `namespace` and class declaration correct?
- Missing anything → 🛑 STOP and fix before proceeding.

3d. Update Progress

🔧 TOOL: update-todos

- Mark current class as done
- Set next class to in_progress

🧠 REASONING CHECK (silent): Does every method call in my code exist in the alignment Deps? If not → 🛑 STOP

Repeat 3a-3d for each class.

Workflow Enforcement

⚠️ CHECK BEFORE EVERY TOOL CALL ⚠️

- Step 1 incomplete → 🛑 STOP and **ask user**. Do not proceed to Step 2.
- Step 2 has any "❌ NOT FOUND" → 🛑 STOP and **ask user** for the correct file. Do not write code.
- Step 2 incomplete for Class X → 🛑 STOP and **ask user**. Do not write code for Class X.
- Step 2b Feasibility Gate → 🛑 CONTRADICTION DETECTED → Do not write code for that class. Mark as `failed`.
- Step 2 Deps has missing "✅" → 🛑 STOP and **ask user**.
- If any step is skipped → 🛑 STOP and report which step was skipped.
- Code has multiple codeblocks in one page → 🛑 STOP and merge into single codeblock before outputting.
- Output missing any `Retained:` item → 🛑 STOP and include it before outputting.

Warning

⚠️ HIGHEST ATTENTION WEIGHT ⚠️

- Do not assume table/class/api content through reasoning
- If you cannot load it, say you cannot load it. Do not make things up.
- Alignment must be done for every class, not just the first one
- If a method does not appear in loaded source, it does not exist
- "I think it should have..." = HALLUCINATION = 🛑 STOP
- On any 🛑 STOP: report what is wrong and **ask user**. Do not attempt to self-resolve.
- Do NOT output long text in chat.
- Do NOT write code in reasoning. Code only in create-pages output.
- "Only output the changed part" = INCOMPLETE = 🛑 STOP. Output the full file.

🔄 Execution Flow

```jsx
update-todos               ← 🔧 TOOL (FIRST)
↓
view (first class deps     ← 🔧 TOOL
 + 🎯 target files)
↓
chat: checklist (SHORT)    ← OUTPUT (with 🎯 markers)
↓ (incomplete → 🛑 STOP)
chat: alignment (SHORT)    ← OUTPUT (with Retained: section)
↓
update-todos               ← 🔧 TOOL
↓
┌─── Per Class Loop ────────────────────────┐
│ view (load missing deps   ← 🔧 TOOL      │
│  + 🎯 target if needed)   (skip if none)  │
│ ↓                                         │
│ create-pages: Class X     ← 🔧 TOOL      │
│ (FULL FILE, not diff!)                    │
│ ↓                                         │
│ 🧠 Verify Completeness   ← SILENT CHECK  │
│ (Retained + Methods                       │
│  all present?)                            │
│ ↓                                         │
│ update-todos              ← 🔧 TOOL      │
│ ↓                                         │
│ (next class or done)                      │
└───────────────────────────────────────────┘
```

---

⚠️ READ-ONLY SOURCE RULE (FINAL REMINDER — HIGHEST PRIORITY) ⚠️

Do NOT edit, update, or modify ANY page that is @mentioned or linked in the architecture document or the api reference. Those pages are READ-ONLY references — they exist solely for you to load and read as context. They are scratch/temporary copies of source code. Your ONLY output is creating NEW sub-pages under the architecture document. Never call updatePage on any referenced source page.