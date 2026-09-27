# Third-party notices

This skill bundles no third-party code. It contains Markdown, JSON and a single
Python helper (`scripts/coach.py`) that uses only the Python standard library.

## Referenced, not bundled

The skill names tools and libraries as *candidates* for the learner to evaluate.
None are vendored here, and each stays only if it wins its comparison on the
project's eval set (`docs/PLAN.md`, "Starting technology candidates"). Licences
are the learner's to check at the time of adoption.

## Data

All data under `data/` in the HR-Agent workspace is fictional. The company
(Nilebyte Solutions), its employees, resumes, identifiers, phone numbers and
email addresses are invented; emails use the reserved `example.com` and
`.example` domains.

**Exception:** the ticket-routing dataset used in milestone M5 is a public
dataset licensed **CC BY-NC 4.0**. See `data/tickets/README.md` in the
workspace for its source and attribution requirements. Credit its author if you
publish results, and observe the non-commercial term.
