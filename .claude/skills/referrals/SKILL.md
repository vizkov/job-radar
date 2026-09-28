---
name: referrals
description: Find a referral route for a role the user wants to apply to, in their order (friends and family, then their network, then recruiters and hiring managers), draft each message from their own CV lines, and track every ask and answer on the board. Use when a role is shortlisted or recommended "apply", when the user says "who do I know at …", "I asked X", "X referred me", or when the session brief lists an unanswered referral ask.
---

# Referrals (Claude drafts, the user sends)

The user wants a referral for each application, asked **before** applying (many companies only
credit a referral made before the application), but only briefly: if nothing comes back within
`referrals.wait_days` (config.json, default 4), suggest applying directly.

Hard lines: never send, email or message anyone; never look people up on LinkedIn, Indeed or
Glassdoor (the user does any searching and tells you); never invent anything about the user in a
message. `profile/network.csv` holds names of the user's friends and colleagues: it is private
and never leaves their repo.

## 0. Will they sponsor?
If the card's Sponsor is Licensed, Unclear or Unlikely (not yet checked), run `sponsorship-check` first:
don't spend a referral on a role that can't sponsor the user.

## 1. Who do they know there?
- Role: find its ref in `data/matches.csv` (or the card's Role ID) and the company.
- `python tools/referrals.py contacts "<company>"` lists people already in `profile/network.csv`,
  in the user's order: friend_family, connection, recruiter, hiring_manager.
- Then **ask the user**, in that order: "Do you know anyone at <company>: family or friends? Anyone in
  your network? Is a recruiter or hiring manager named in the ad or known to you?" Add every person
  they mention to `profile/network.csv` (`name,relation,company,role,how_to_reach,notes,added`;
  `how_to_reach` is what the user says, e.g. "WhatsApp", "LinkedIn message", "email"; never
  guess contact details). Also look in the JD packet (`work/jd/<ref>/jd.txt`) for a named recruiter.
- Nobody at all: `python tools/referrals.py route <ref> --status none --note "…"`, tell the user,
  and suggest applying directly. If the user doesn't want a referral for this one:
  `route <ref> --status not_needed`.
- Still looking (the user will check with someone): `route <ref> --status finding`.

## 2. Draft the message (one per person, best route first)
Save drafts in `profile/applications/<folder>/outreach.md` (create the folder name as in
tailor-application). Keep each short, in the user's voice, and specific:
- **Friend/family:** warm and plain: which role (title + link), why it fits in one line, what you're
  asking (a referral through their internal system, or passing the CV to the hiring manager), and
  an easy out ("no worries if it's awkward").
- **Connection:** a brief reminder of how they know each other if the user told you, the role and
  link, 2–3 of the user's strongest matching lines (from the score's "Matches", rephrased only
  lightly, citing IDs in a comment for your own checking), and the ask.
- **Recruiter / hiring manager:** a cold note: role and link, 2–3 matching lines, the visa
  sponsorship need stated plainly (the user is in India), and a request for a short call or for the
  CV to be considered. No referral ask here; this route is a direct introduction.
Only facts from `profile/career/` and the score; no new numbers, employers or claims. Show the
drafts to the user; they edit and send.

## 3. Track it
- When the user says they sent it: `python tools/referrals.py ask <ref> --person "<name>"
  --relation <relation> --channel "<how>"`. This logs it, sets the card's **Referral** field to
  *Asked* and adds a comment on the card.
- When they hear back: `python tools/referrals.py result <ref> --person "<name>" --status
  referred|declined|no_reply [--note "…"]`. *Referred* sets the field; after a decline or no reply,
  move to the next person in the order, or `route <ref> --status none` if nobody is left.
- The session brief lists asks unanswered after `wait_days`: offer **one** polite follow-up draft,
  or suggest applying directly. Don't chase twice.

## 4. Then apply
Once referred (or the route is exhausted), continue with `tailor-application` / `apply-assist`. If the
referral went through an internal portal, the user may not need to apply separately: ask.
