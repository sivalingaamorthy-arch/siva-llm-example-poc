# Safety content (always loaded: no `paths`, applies everywhere)

The shared R2 rules from `Sample-Data-Health-Content/` are enforced in
`routes/recommendations.py` via `sample_data.safety_violations()`:

- Never recommend an article with `approved: false`.
- Never recommend an article whose `contraindications` overlap the report's markers.
- Never recommend `intensity: "high"` content when the report has `hypertension`.

Rules for working in this repo:
- Markers come from the report (`sample_data.markers()`), never from request input.
  Do not add a request field that lets callers declare their own conditions.
- Do not remove, weaken or bypass the guard, even in tests or "temporary" code.
  Any change to it needs tests proving R2 + `physical-08` is still rejected.
- Never edit `Sample-Data-Health-Content/` from this project. It is shared by every POC.
- Never write medical advice, dosages or diagnostic statements into code, comments,
  fixtures or commit messages. If a task seems to need that, stop and ask.
