---
name: referrals
description: Find a referral route for a role the user wants to apply to, in their order (people they know first, then recruiters and hiring managers), draft messages to strangers only (recruiters, HR, hiring and team managers) from their own CV lines, and track every ask and answer on the board. Use when a role is shortlisted or recommended "apply", when the user says "who do I know at …", "I asked X", "X referred me", or when the session brief lists an unanswered referral ask.
---

# Referrals (the user asks people they know; Claude drafts only for strangers)

The user wants a referral for each application, asked **before** applying (many companies only
credit a referral made before the application), but only briefly: if nothing comes back within
`referrals.wait_days` (config.json, default 4), suggest applying directly.

Hard lines: never send, email or message anyone; never look people up on LinkedIn, Indeed or
Glassdoor (the user does any searching and tells you); never invent anything about the user in a
message. `profile/network.csv` holds only names and the companies each person can help with: it is
private and never leaves their repo. Don't record how people are related, what they do or how to reach
them: the user doesn't want that captured.

## 0. Will they sponsor?
If the card's Sponsor is Licensed, Unclear or Unlikely (not yet checked), run `sponsorship-check` first:
don't spend a referral on a role that can't sponsor the user.

## 1. Who can help there?
- Role: find its ref in `data/matches.csv` (or the card's Role ID) and the company.
- `python tools/referrals.py contacts "<company>"` lists people the user has named for that company.
- If there's nobody, **ask the user**: "Does anyone you know help with <company>?" Add each name to
  `profile/network.csv` as `name,company,added` (one row per company), nothing else.
- Several people for one company: suggest **one person per role**; companies record one referral per
  application, and duplicate referrals look disorganised.
- Nobody the user knows: look in the JD packet (`work/jd/<ref>/jd.txt`) for a named recruiter or
  hiring manager, or ask the user whether they've found one; that's a stranger route (step 2).
- No route at all: `python tools/referrals.py route <ref> --status none --note "…"`, tell the user,
  and suggest applying directly. If the user doesn't want a referral: `route <ref> --status not_needed`.
- Still looking: `route <ref> --status finding`.

## 2. What to give the user
- **People they know: no draft.** The user writes to family, friends and their network in their own
  words. Give them only what the person needs to act on it: each role's title, link and the company's
  job ID (for internal referral tools), best role first, and offer the tailored CV to attach.
- **Strangers (recruiters, HR, hiring managers, team managers): draft it.** Save in
  `profile/applications/<folder>/outreach.md` (folder named as in tailor-application): a short cold
  note with the role and link, 2–3 of the user's strongest matching lines (from the score's "Matches",
  lightly rephrased; cite IDs in an HTML comment for your own checking), the visa sponsorship need
  stated plainly (the user is in India), and a request for a short call or for the CV to be considered.
  Only facts from `profile/career/` and the score. The user edits and sends it.

## 3. Track it
- When the user says they asked someone: `python tools/referrals.py ask <ref> --person "<name>"`
  (add `--relation recruiter|hiring_manager` for a stranger). This logs it, sets the card's
  **Referral** field to *Asked* and adds a comment on the card.
- When they hear back: `python tools/referrals.py result <ref> --person "<name>" --status
  referred|declined|no_reply [--note "…"]`. *Referred* sets the field; after a decline or no reply,
  try the next person, or `route <ref> --status none` if nobody is left.
- The session brief lists asks unanswered after `wait_days`: suggest one nudge (the user writes it to
  people they know; draft it only for a stranger), or applying directly. Don't chase twice.

## 4. Then apply
Once referred (or the route is exhausted), continue with `tailor-application` / `apply-assist`. If the
referral went through an internal portal, the user may not need to apply separately: ask.
