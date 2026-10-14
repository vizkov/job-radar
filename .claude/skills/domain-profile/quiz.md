# Question banks

Ask in plain words. Each answer: yes / no / unsure + note + role + "five minutes in an interview?".

## Payments and fintech (first run 2026-10-20)

1. Did you test systems that handle card or bank payments that were inside PCI DSS scope? Which activities (pen test, code review, design review)? Did you decide the scope, or test inside it?
2. Did you see card numbers swapped for tokens, or secrets and keys kept in a vault or hardware module?
3. Did you test the extra confirmation step on card payments (one-time code, app approval)? Or only login MFA?
4. Did you test APIs a bank or processor exposes to outside companies or apps?
5. Did you test file or batch flows (settlement files, merchant payouts, reconciliation)?
6. Did you test for fraud or abuse (stolen accounts, fake sign-ups, promo or limit abuse)?
7. Did you test customer onboarding, identity checks, or moving customers between systems?
8. Did you review or build threat models for payment flows? Which flows? Built or reviewed?
9. Did reports or client briefs name a regulation (PSD2, DORA, EBA, NIS2, SWIFT, ISO 20022)?
10. Did the findings get fixed before go-live?

Add banks for other domains (aviation, healthcare, crypto, cloud platform) here when the user targets them.
