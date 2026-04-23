---
name: test-suite
description: Clone test suite repo (if needed), run full test suite, and report results. Use before pushing to ensure nothing is broken.
disable-model-invocation: true
allowed-tools: Bash(python3 -m pytest *) Bash(npx vitest *) Bash(npx tsc *) Bash(python3 -c *) Bash(git clone *) Bash(git -C * pull *) Bash(ls *) Bash(find * -name *) Bash(cp *) Bash(mkdir *) Bash(rm *) Bash(cd *)
---

# Test Suite Runner

Run the full test suite before pushing. This skill ensures the judgement-tests repo is available locally and runs all tests against the current code.

## Step 1: Ensure test suite repo exists

Check if `judgement-tests` is cloned as a sibling directory:

```bash
ls ../judgement-tests/backend 2>/dev/null && echo "FOUND" || echo "NOT_FOUND"
```

- If **NOT_FOUND**, clone it:
  ```bash
  git clone https://github.com/jvalin17/judgement-tests.git ../judgement-tests
  ```
- If **FOUND**, pull latest:
  ```bash
  git -C ../judgement-tests pull --ff-only
  ```

## Step 2: Pydantic sanity check

```bash
python3 -c "from pydantic import BaseModel; print('pydantic OK')"
```

If this fails, stop and tell the user to run: `python3 -m pip install --force-reinstall pydantic pydantic-core`

## Step 3: Run backend smoke tests (main repo)

```bash
python3 -m pytest backend/tests/ -v
```

All must pass. If any fail, stop and report failures. Do NOT continue to the suite.

## Step 4: Run frontend smoke tests (main repo)

```bash
cd frontend && npx vitest run
```

All must pass. If any fail, stop and report failures. Do NOT continue to the suite.

## Step 5: TypeScript check

```bash
cd frontend && npx tsc -b
```

Must produce zero errors. If any fail, stop and report.

## Step 6: Run backend suite tests

```bash
JUDGEMENT_REPO=$(pwd) python3 -m pytest ../judgement-tests/backend/ -v --rootdir=../judgement-tests
```

All must pass. Report any failures.

## Step 7: Run frontend suite tests

Copy suite test files into main repo, run, then clean up:

```bash
# Copy test files
find ../judgement-tests/frontend/src -name "*.test.*" -type f | while IFS= read -r src_file; do
    rel="${src_file#../judgement-tests/frontend/src/}"
    dest="frontend/src/$rel"
    mkdir -p "$(dirname "$dest")"
    cp "$src_file" "$dest"
    echo "$rel" >> frontend/src/.suite-tests-copied
done
```

```bash
cd frontend && npx vitest run
```

Then clean up the copied files:

```bash
if [ -f frontend/src/.suite-tests-copied ]; then
    while IFS= read -r file; do
        rm -f "frontend/src/$file"
    done < frontend/src/.suite-tests-copied
    rm -f frontend/src/.suite-tests-copied
fi
```

## Step 8: Report

Print a summary:

```
=== Test Suite Results ===
Backend smoke:    ✓ (X passed)
Frontend smoke:   ✓ (X passed)
TypeScript:       ✓ (no errors)
Backend suite:    ✓ (X passed)
Frontend suite:   ✓ (X passed)
=========================
All tests passed — safe to push.
```

If ANY step failed, end with:

```
=== BLOCKED ===
Do NOT push. Fix the failures above first.
```
