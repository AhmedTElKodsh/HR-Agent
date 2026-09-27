# War stories

Write these from real traces while building, not afterwards. Interviewers grade them on five points. Aim for at least 4, from different layers: data, retrieval, generation, agent or operations.

## Template

### Title (one line: what broke)

- **What happened and the impact:**
- **How I found the cause** (trace evidence, not guesses):
- **The fix, and the layer it belongs to** (parsing, chunking, retrieval, ranking, generation, tools, document):
- **How I made a silent regression impossible** (the eval items or alert I added):
- **Measured result** (before and after, from `docs/results.md`):

## Stories the data is set up to produce

You will probably hit these. When you do, record what really happened.

- Outdated policy: the 2025 leave PDF outranks the 2026 one on carry-over questions.
- Jumbled table: the scanned insurance schedule or a PDF table loses its column meaning.
- The follow-up that failed: "And in Paris?" retrieves nothing useful without query rewriting.
- The retry loop: the agent keeps calling a failing HR tool (scenario a09).
- The two-column trap: the privacy notice's columns interleave, and the answers mix sections.
- The hidden instruction: the FAQ page's hidden text reaches the prompt.
