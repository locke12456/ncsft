# ⚙️ Code Implementation (v2.4-python-only)

<aside>
🐍

**v2.4-python-only** — Pure Python patch output only. No sed, no bash.

Based on v2.3-python with sed/bash sections removed.

</aside>

Implement classes from an architecture document, following the mandatory 3-step workflow below.

**Inputs (required when invoking this skill):**

- `architecture document:` — link to the architecture doc page
- `target phase:` — e.g. phase5
- `api:` *(optional)* — link to the API alignment page

architecture document: [paste architecture document page link here]

api: [paste api page link here]

## Implementation Goal

1. Implement according to the architecture document. Scope: [target phase]
2. Create new sub-pages under the architecture document. One page per class/file.
3. **Output format depends on whether the file is new or modified:**
    - 🆕 **New file** → Create full source code page (single codeblock, complete compilable source)
    - ✏️ **Modified existing file** → Create **Python patch page** (pure Python script, no bash, no sed)
4. All code in a new-file page must be in a single codeblock. Do not split into code parts.
    - ⚠️ Single codeblock IS the most readable format — `#region` provides navigation. Splitting destroys class structure.
    - 🛑 If you are about to create multiple codeblocks for the same class → STOP. Merge into one first.
5. ⚠️ **Complete File Output Rule (New files only):** every output page for a new file must contain the complete, compilable source file. The codeblock must be copy-paste ready to replace the entire original file.

---

## ⚠️ English-Only Comments Rule (ALL patches)

<aside>
⚠️

**All comments inside Python scripts MUST be written in English only.**

Non-ASCII characters inside scripts cause encoding errors on many CI/terminal environments.

This applies to: `#` comments in Python.

Page prose and section headings (outside code blocks) may use any language.

</aside>

---

## Output Rules for Modified Files

### ✅ Python Patch (only option)

Use Python for **all modifications**.

- Create one page per modified file under the architecture document.
- Page title: `filename.py` or `ClassName.cs (python patch)`
- Page heading: `## filename — Python Patch`
- Include: 📁 Target file path, a Changes bullet list, then the patch script.

**Python patch script template (use this structure exactly):**

```python
import sys
import os

TARGET = r"/path/to/TargetFile"

with open(TARGET, 'r', encoding='utf-8') as f:
    content = f.read()

# --- Change 1: [English description] ---
content = content.replace('old text', 'new text')

# --- Change 2: [English description] ---
content = content.replace(
    'exact old text',
    'new text'
)

with open(TARGET, 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched:', TARGET)
```

**Python patch rules:**

- Always use `encoding='utf-8'` on open.
- Use `str.replace('exact old text', 'new text')` — verify the exact string exists in the loaded source first.
- For larger blocks, use multi-line strings with `"""..."""`.
- Each change block must have an English `#` comment describing what it does.
- ⚠️ Before writing any `replace()` call, verify the exact original text exists in the loaded source. If unsure → 🛑 STOP.
- 🛑 If uniqueness of the replaced string cannot be guaranteed, add surrounding context lines to make it unique.
- **Multiple files: combine into one Python script.** One `open/replace/write` block per file.

---

## ⚠️ Reasoning Code Output Restriction (Mandatory)

1. Do NOT write or draft full code blocks inside reasoning/thinking.
2. Reasoning: logic decisions, verification checks, API lookups only.
3. Code belongs ONLY in the final create-pages output.
4. If you catch yourself writing code in reasoning → STOP, skip to tool output.

---

## Work Requirements — Mandatory Workflow

### ═══ Step 1: Load Source Code & Checklist ═══

⚠️ MUST COMPLETE BEFORE ANY CODE OUTPUT ⚠️

🔧 TOOL: view

1. Load the architecture document + reference source files needed for the first class only.
2. ⚠️ When modifying an existing file, you MUST load the target file itself — it is the base you are patching. 🛑 If you skip loading the target file → your patch will be wrong. Do NOT proceed.
3. ⚠️ Do NOT pre-load files for later classes.

After loading, output checklist in chat (one line per file):

- `/ 🎯 [filename] - ✅ loaded — TARGET (existing file to modify → python patch)`
- `/ [dep-filename] - ✅ loaded — provides: [key APIs]`
- `Verdict: [complete/incomplete]`

Rules:

- If verdict is "incomplete" → 🛑 STOP: report missing files and ask user.
- If architecture has obvious design flaws → 🛑 STOP and ask user.

### ═══ Step 2: Output Alignment List (in Chat) ═══

⚠️ AFTER CHECKLIST, BEFORE ANY CODE ⚠️

Output a flat bullet list for every class:

- `### [ClassName]`
- `Output type: 🆕 New file / ✏️ Python patch`
- `Deps:` — one line each, e.g. `- ExtClass.Method(params) → Return ✅  (source: file.cs)`
- `Fields:` — one line each
- `Methods:` — one line each
- `Retained:` *(modified files only)*
- `Changes:` *(modified files only)*

Rules:

- Every dep must show ✅. Missing → ❌ → 🛑 STOP.
- For modified files: Methods + Retained must equal complete public surface of original.
- No tables. No paragraphs. One line per item.

### ═══ Step 2b: Architecture Feasibility Gate ═══

For each class: check for engine dependency contradictions.

- On contradiction: report, mark todo failed, continue with other classes.

### ═══ Step 3: Write Code / Patch (per class, sequential) ═══

⚠️ ONLY AFTER STEP 2 IS COMPLETE ⚠️

**3a. Load Missing Deps** (if needed) — same format as Step 1 checklist.

**3b. Write Output** 🔧 TOOL: create-pages

- 🆕 New file: full source in one codeblock.
- ✏️ Python patch: pure Python script (see template above). No bash wrapper, no heredoc.
- ⚠️ All script comments (`#`) must be **English only**.

**3c. Verify Completeness** (silent check)

- New file: all methods present? Using statements complete?
- Python patch: does every `replace()` old string exist in loaded source? All comments English?

**3d. Update Progress** — 🔧 TOOL: update-todos

---

## Plan Tool Usage Rules (Mandatory)

⚠️ FIRST ACTION BEFORE ANY OTHER TOOL ⚠️

🔧 TOOL: update-todos — structure todos as:

- Load source files & checklist
- Output Alignment List
- Alignment + Write: Class A
- Alignment + Write: Class B

Rules: each class has its own item. Do not batch.

---

## Context Budget Rules (Mandatory)

⚠️ HIGHEST PRIORITY — PREVENTS CONTEXT OVERFLOW ⚠️

1. Chat output must be MINIMAL: checklist one line per file, verdict one word.
2. Do NOT output full design analysis in chat.
3. Load only files needed for the current class.
4. If total implementation > 3 classes: split into multiple conversations.

---

## Workflow Enforcement

⚠️ CHECK BEFORE EVERY TOOL CALL ⚠️

- Step 1 incomplete → 🛑 STOP.
- Step 2 has ❌ → 🛑 STOP and ask user.
- Feasibility contradiction → 🛑 mark failed, continue others.
- New file has multiple codeblocks → 🛑 STOP and merge.
- Python patch `replace()` string not found in source → 🛑 STOP and verify.
- Script has non-English comments → 🛑 STOP and fix.
- **Attempting to output sed or bash → 🛑 STOP. Use Python instead.**

---

## Warning

⚠️ HIGHEST ATTENTION WEIGHT ⚠️

- Do not assume API content through reasoning. If you cannot load it, say so.
- Alignment must be done for every class.
- "I think it should have..." = HALLUCINATION = 🛑 STOP.
- Do NOT write code in reasoning.
- **All comments in Python scripts = English only. No exceptions.**
- **No sed. No bash. Python patch only.**

---

## 🔄 Execution Flow

1. update-todos *(FIRST)*
2. view — load first class deps + 🎯 target files
3. Chat: checklist (SHORT)
4. Chat: alignment (SHORT)
5. update-todos
6. Per Class Loop:
    - view — load missing deps if needed
    - create-pages: 🆕 full source / ✏️ Python patch
    - verify (silent)
    - update-todos
    - repeat