# OcéEns

Teaching evaluation platform for EPF: surveys (*sondages*) are created per program, students answer them, and the answers are exported, visualized, and summarized (*synthèses*) via an LLM.

## Language

This document, the README, the ADRs and other prose documentation are written in English. The product's own domain vocabulary stays in French where the application itself is French: *sondage* (survey), *synthèse* (summary/verbatim summary), and terms derived from them (e.g. *filière* for program). Use the French term when it names something the application shows to its French-speaking users; use English for everything else, including this glossary's own definitions.

### Authentication

**Development login** (`AUTH_MODE=dev`):
Login without an identity provider: you pick a user's email address and are logged in as them, with no proof of identity. It only exists when `AUTH_MODE=dev` and must never be used in production.
_Avoid_: impersonation, usurpation, fake login
