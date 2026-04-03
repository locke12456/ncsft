# 🔍 Code Implementation Checker

Check whether the specified phases are fully implemented based on the uploaded source code, then update the Work List status and all mention-page references in the spec doc.

**Inputs:**

- `phase[n]` — which phase(s) to verify (e.g. phase 1, phase 2)
- Architecture / spec doc page — the design spec to cross-reference
- *(optional)* `addition: api alignment page` — an additional API alignment page to include in the verification scope

**Steps:**

1. Read each source code file mentioned in the Work List for the target phase(s) from the source code page: [source code](https://www.notion.so/source-code-26a88e4ac48d80739fb5ce8213b619a5?pvs=21). All uploaded code lives there — do not look elsewhere.
2. Cross-reference against the spec doc to determine if every checklist item is implemented.
    - **Stop immediately** if any source file page shows as `<unknown>`. Report which file blocked progress.
3. Update every checklist item in the Work List page:
    - `[x]` if fully implemented and matches the spec.
    - `[ ]` if missing or diverges from the spec (add a short note).
4. **[MANDATORY]** Update all `mention-page` links in the spec doc so they point to the correct current pages (fix any broken or stale references). This step is **required** and must not be skipped — every deleted or outdated page reference must be replaced with the latest active page URL before the task is considered complete.
5. Output a concise summary:
    - Phase status (complete / partial / missing)
    - Any divergences found between source and spec
    - Any `<unknown>` pages that caused an early stop

**Rules:**

- Do not modify source code pages.
- Do not mark a phase complete unless **all** checklist items in that phase pass.
- If `addition: api alignment page` is provided, treat its API definitions as authoritative — flag any mismatch with the spec as a divergence.