---
paths:
  - "tests/**/*.py"
---

# Test conventions

- Use the `client` fixture pattern: a fresh `Repository()` injected via
  `app.dependency_overrides`, cleared after the test. No shared mutable state.
- One behaviour per test; name it `test_<behaviour>`.
- For every new error path, assert the status code **and** the problem `type` slug.
- Use the shared reports (R1, R2, R3) and real catalog ids (e.g. `physical-08`); don't invent fixtures.
- No network, no sleeps, no real user data.
