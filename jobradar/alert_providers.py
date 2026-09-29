"""Job-alert email providers. STANDARD LIBRARY ONLY.

tools/fetch_alert_emails.py imports this module in the workflow step that holds
the Gmail app password, before any third-party package is installed. Keep it
free of non-stdlib imports so that step never runs third-party code.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from email.message import Message


@dataclass(frozen=True)
class Provider:
    name: str               # also the Posting.source: "<name>_email"
    senders: tuple[str, ...]
    dkim_domain: str
    job_id: re.Pattern      # group(1) = job ID, searched in (URL-decoded) hrefs and text
    url: str                # canonical job URL template with {id}
    # Some alerts carry no job ID, only opaque tracking redirects (Indeed since 2026). Then the job is
    # keyed by title/company/location and this pattern, pinned to the provider's own https redirect host,
    # is the only link accepted, so a spoofed email still can't smuggle in a link elsewhere.
    redirect: re.Pattern | None = None


PROVIDERS = {
    "linkedin": Provider(
        "linkedin", ("jobalerts-noreply@linkedin.com", "jobs-listings@linkedin.com", "jobs-noreply@linkedin.com"),
        "linkedin.com",
        re.compile(r"linkedin\.com/(?:comm/)?jobs/view/(?:[^/?\s\"']*?-)?(\d{6,})", re.I),
        "https://www.linkedin.com/jobs/view/{id}/"),
    "indeed": Provider(
        "indeed", ("alert@indeed.com", "donotreply@jobalert.indeed.com", "noreply@indeed.com", "@indeed.com"),
        "indeed.com",
        re.compile(r"indeed\.[a-z.]+/[^\s\"']*?[?&](?:amp;)?jk=([0-9a-f]{16})", re.I),
        "https://www.indeed.com/viewjob?jk={id}",
        re.compile(r"https://engage\.indeed\.com/f/a/[\w~-]+/[\w~-]+/[\w~-]+")),
    "glassdoor": Provider(
        "glassdoor", ("noreply@glassdoor.com", "@glassdoor.com"),
        "glassdoor.com",
        re.compile(r"glassdoor\.[a-z.]+/[^\s\"']*?[?&](?:amp;)?(?:jobListingId|jl)=(\d{6,})", re.I),
        "https://www.glassdoor.com/partner/jobListing.htm?jobListingId={id}"),
}


def provider_for(msg: Message) -> Provider | None:
    sender = (msg.get("From") or "").lower()
    return next((p for p in PROVIDERS.values() if any(s in sender for s in p.senders)), None)


def dkim_ok(msg: Message, domain: str) -> bool:
    """Gmail records DKIM results in Authentication-Results (and ARC headers after forwarding)."""
    headers = msg.get_all("Authentication-Results", []) + msg.get_all("ARC-Authentication-Results", [])
    rx = re.compile(rf"dkim=pass[^;]*header\.(?:i|d)=@?(?:[\w.-]+\.)?{re.escape(domain)}\b", re.I)
    return any(rx.search(h) for h in headers)
