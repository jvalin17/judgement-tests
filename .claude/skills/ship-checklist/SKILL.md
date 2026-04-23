---
name: ship-checklist
description: Pre-push checklist — write tests for changes, run full suite, verify docs, push. Use before every git push.
disable-model-invocation: true
allowed-tools: Bash(npx vitest *) Bash(npx tsc *) Bash(python3 -m pytest *) Bash(python3 -c *) Bash(gh release view *) Bash(git *)
---

# Ship Checklist

Run through every item below before pushing. Do NOT push until all steps pass.

## 1. Write tests for changes

Run `/write-tests` to analyze all code changes and generate tests in the `judgement-tests` repo. Every change — feature, fix, refactor, even a one-liner — must have tests. Do NOT skip this step.

## 2. Run full test suite

Run `/test-suite` to run all smoke tests + suite tests + TypeScript checks. Do NOT proceed until it reports "All tests passed — safe to push."

## 3. README

Check if the change affects any of:
- Feature list or descriptions
- Test counts (currently backend + frontend totals)
- Download links (verify actual artifact names with `gh release view --json assets`)
- Variant count
- Documented behavior or commands

If yes, update README.md accordingly. Read it and verify links are correct.

## 4. RELEASE_NOTES.md

Add an entry under the **Unreleased** section (or the current version section if tagging a release). Categorize as Added / Changed / Fixed / Security.

## 5. LEARNINGS.md

If anything was missed, caught late, or required a fix after the fact during this session, add an entry to LEARNINGS.md under the **Mistakes & Fixes** section. Format:

```
### Short title
What went wrong and the fix so we don't repeat it.
```

## 6. Commit and push

Only after all above steps pass:
- Stage relevant files (not `git add -A`)
- Write a concise commit message
- Push

Report the final test counts and any doc updates made.
