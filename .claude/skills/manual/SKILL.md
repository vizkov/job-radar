---
name: manual
description: Show the job-radar manual — every capability the user can ask for, generated live from the skills and tools so it is always current. Use when the user types /manual, asks "what can you do?", "help", "what does the system offer?", or seems unaware of a capability that fits their request.
---

# Manual

1. Run `python tools/manual.py` (or `python tools/manual.py skills` for just the "what you can ask for" list).
2. Present it to the user in plain language, grouped by what they'd want to do: find roles, judge fit,
   apply, track, prepare for interviews, improve the CV, keep the system healthy. Don't paste the raw
   tool list unless they ask how things work underneath.
3. If the session brief listed "System updated since last session", point out the new capabilities first.
4. End with 2-3 suggestions that fit their current state (e.g. unscored fresh Tier 1 roles, a
   follow-up due, missing STAR stories).
