---
name: write-tests
description: Analyze code changes, generate unit and integration tests, add them to the judgement-tests repo. Run after every feature, fix, or refactor — no matter how small.
---

# Write Tests

Generate comprehensive tests for any code change and add them to the [judgement-tests](https://github.com/jvalin17/judgement-tests) repo.

**This skill MUST be run after every code change — no exceptions.** Even a one-line fix needs a test proving it works.

## Step 1: Ensure test suite repo exists

Check if `judgement-tests` is cloned as a sibling:

```bash
ls ../judgement-tests/backend 2>/dev/null && echo "FOUND" || echo "NOT_FOUND"
```

If NOT_FOUND, clone it:
```bash
git clone https://github.com/jvalin17/judgement-tests.git ../judgement-tests
```

## Step 2: Identify what changed

Run `git diff HEAD` and `git diff --cached` and `git status` in the main repo to find all modified, added, or new files. Also check recent commits with `git log --oneline -5` for context on what was just built.

Categorize changes:
- **Backend model/logic** → needs unit tests in `../judgement-tests/backend/`
- **Backend API endpoint** → needs integration tests in `../judgement-tests/backend/`
- **Backend AI strategy** → needs unit tests in `../judgement-tests/backend/`
- **Backend ML** → needs unit tests in `../judgement-tests/backend/`
- **Frontend component** → needs component tests in `../judgement-tests/frontend/src/components/`
- **Frontend hook/context** → needs hook tests in `../judgement-tests/frontend/src/`
- **Frontend service** → needs service tests in `../judgement-tests/frontend/src/services/`
- **Frontend type** → needs type tests in `../judgement-tests/frontend/src/types/`

## Step 3: Read the changed code

Read every changed file thoroughly. Understand:
- What the code does (all branches, edge cases, error paths)
- What inputs it accepts (valid and invalid)
- What outputs it produces
- What side effects it has
- How it integrates with other modules

## Step 4: Read existing tests

Before writing new tests, read the existing test files in `../judgement-tests/` that cover the same area. This ensures:
- No duplicate tests
- Consistent test style and patterns
- Tests are added to the right file (or a new file is created if appropriate)

### Backend test conventions

```python
# File: ../judgement-tests/backend/test_<area>.py
# Import from backend.app.* (main repo is on sys.path via conftest.py)
import pytest
from backend.app.models.card import Card, Suit, Rank
from backend.app.game.engine import GameEngine

# Use descriptive test names
def test_<what>_<scenario>_<expected>():
    """One-line description of what this verifies."""
    # Arrange
    ...
    # Act
    ...
    # Assert
    ...
```

- Use `pytest` (no unittest classes)
- Descriptive function names: `test_bid_dealer_cannot_make_total_equal_cards`
- One assertion per concept (multiple asserts OK if testing one logical thing)
- Use fixtures for repeated setup
- Import from `backend.app.*` — the conftest.py handles sys.path

### Frontend test conventions

```typescript
// File: ../judgement-tests/frontend/src/<path>/<Component>.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

describe('ComponentName', () => {
  it('does something specific', () => {
    // Arrange
    render(<Component {...props} />);
    // Assert
    expect(screen.getByText('...')).toBeInTheDocument();
  });
});
```

- Use `vitest` + `@testing-library/react`
- Use `vi.fn()` for mocks, `vi.stubGlobal()` for globals like `fetch`
- Mirror the source file path: `components/game/BidSelector.tsx` → `components/game/BidSelector.test.tsx`
- Test rendering, user interactions, edge states, error states
- Mock API calls and WebSocket — never hit real servers

## Step 5: Generate tests

Write tests covering ALL of the following for each change:

### Unit tests (required for every change)
- **Happy path** — normal usage with valid inputs
- **Edge cases** — empty inputs, boundary values, zero, max values
- **Error cases** — invalid inputs, missing data, wrong types
- **State transitions** — before/after for anything stateful

### Integration tests (required when multiple modules interact)
- **End-to-end flow** — e.g., create game → bid → play → score
- **API request/response** — correct status codes, response shapes
- **WebSocket message flow** — connect → action → event received
- **Component with context** — component renders correctly within providers

### Regression tests (required for bug fixes)
- **Reproduce the bug** — test that would have failed before the fix
- **Verify the fix** — test that passes with the fix

### Coverage targets
- Every public function/method must have at least one test
- Every conditional branch must be exercised
- Every error path must be tested
- Every prop/parameter combination that matters must be covered

## Step 6: Run the new tests

### Backend
```bash
JUDGEMENT_REPO=$(pwd) python3 -m pytest ../judgement-tests/backend/<test_file>.py -v
```

### Frontend
Copy the test file into the main repo temporarily, run it, then remove:
```bash
# Copy
cp ../judgement-tests/frontend/src/<path>/<test_file> frontend/src/<path>/

# Run
cd frontend && npx vitest run src/<path>/<test_file>

# Clean up
rm frontend/src/<path>/<test_file>
```

ALL tests must pass. If any fail, fix the test (not the code — the code is already working). If tests reveal an actual bug in the code, flag it to the user.

## Step 7: Run full suite to ensure no regressions

Run `/test-suite` to verify the new tests don't break anything existing.

## Step 8: Report

Print a summary:

```
=== Tests Written ===
<filename>: X new tests
  - test_name_1: <what it covers>
  - test_name_2: <what it covers>
  ...

Total: X new tests added
All passing ✓
```

Remind the user to commit and push the test suite repo:
```
Tests are in ../judgement-tests/ — commit and push when ready.
```
