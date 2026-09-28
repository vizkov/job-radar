"""Generate SYNTHETIC job-alert .eml fixtures (LinkedIn, Indeed, Glassdoor).

These are modelled on the providers' alert layouts (plain-text cards ending in
"View job: <url>", HTML table cards) but are not real emails. Replace or
supplement them with real exported alerts (redact your address) and re-run the
tests before relying on the parser: `python tests/fixtures/alert_email/make_fixtures.py`.
"""
from email.message import EmailMessage
from pathlib import Path

HERE = Path(__file__).parent
DKIM_PASS = ("mx.google.com; dkim=pass header.i=@linkedin.com header.s=d2048-2021 header.b=abc; "
             "spf=pass smtp.mailfrom=jobalerts-noreply@linkedin.com; dmarc=pass header.from=linkedin.com")

TEXT = """Your job alert for application security in United Kingdom
3 new jobs match your preferences.

Senior Application Security Engineer
Deloitte
London, England, United Kingdom
View job: https://www.linkedin.com/comm/jobs/view/4012345678/?trackingId=abc%3D%3D&refId=xyz&midToken=AQ

---------------------------------------------------------

Penetration Tester
Pen Test Partners
Buckingham, England, United Kingdom (Hybrid)
Easy Apply
View job: https://www.linkedin.com/comm/jobs/view/4012345679/?trackingId=def

---------------------------------------------------------

Product Security Engineer
Adyen · Amsterdam, North Holland, Netherlands
Actively recruiting

View job: https://www.linkedin.com/comm/jobs/view/4012345680/?trackingId=ghi

---------------------------------------------------------

See all jobs: https://www.linkedin.com/comm/jobs/search/?keywords=application%20security

This email was intended for Test User.
"""

HTML = """<html><body><table>
<tr><td><table><tr><td>
  <a href="https://www.linkedin.com/comm/jobs/view/4012345678/?trackingId=abc">Senior Application Security Engineer</a>
  <p>Deloitte · London, England, United Kingdom</p>
</td></tr></table></td></tr>
<tr><td><table><tr><td>
  <a href="https://www.linkedin.com/comm/jobs/view/4012345679/?trackingId=def">Penetration Tester</a>
  <p>Pen Test Partners · Buckingham, England, United Kingdom (Hybrid)</p><p>Easy Apply</p>
</td></tr></table></td></tr>
</table></body></html>"""

# HTML-only, and the tracking link carries extra path segments + a lookalike query. The
# parser must rebuild https://www.linkedin.com/jobs/view/<id>/ from the numeric ID only.
HTML_ONLY = """<html><body>
<table><tr><td>
<a href="https://uk.linkedin.com/comm/jobs/view/security-consultant-at-mdsec-4099999999?url=https://evil.example/login">
Security Consultant</a><div>MDSec</div><div>Manchester, England, United Kingdom</div>
</td></tr></table>
<table><tr><td><a href="https://www.linkedin.com/comm/jobs/view/4099999998/">Threat Modeling Lead</a>
<div>Secura</div><div>Eindhoven, North Brabant, Netherlands</div></td></tr></table>
</body></html>"""


INDEED_HTML = """<html><body>
<table><tr><td>
  <a href="https://cts.indeed.com/v3/H4sIAAAA?target=https%3A%2F%2Fuk.indeed.com%2Frc%2Fclk%2Fdl%3Fjk%3D0a1b2c3d4e5f6a7b%26from%3Dja">
    <b>Application Security Engineer</b></a>
  <div>NCC Group</div><div>Manchester</div><div>Easily apply</div>
</td></tr></table>
<table><tr><td>
  <a href="https://uk.indeed.com/rc/clk/dl?jk=1122334455667788&amp;from=ja&amp;qd=x">Senior Security Consultant</a>
  <div>Bridewell - London</div><div>Just posted</div>
</td></tr></table>
</body></html>"""

GLASSDOOR_HTML = """<html><body>
<table><tr><td>
  <a href="https://www.glassdoor.co.uk/partner/jobListing.htm?pos=101&amp;jobListingId=1009876543210&amp;ao=1">
    Product Security Engineer</a>
  <p>Wise</p><p>London</p><p>4.1 ★</p>
</td></tr></table>
</body></html>"""


def dkim(domain):
    return f"mx.google.com; dkim=pass header.i=@{domain} header.s=s1 header.b=abc; spf=pass"


def msg(frm, subject, text=None, html=None, auth=DKIM_PASS, mid="1"):
    m = EmailMessage()
    m["From"] = frm
    m["To"] = "jobalerts-inbox@example.com"
    m["Subject"] = subject
    m["Date"] = "Sun, 27 Sep 2026 07:12:00 +0000"
    m["Message-ID"] = f"<synthetic-{mid}@example.com>"
    if auth:
        m["Authentication-Results"] = auth
    if text:
        m.set_content(text)
        if html:
            m.add_alternative(html, subtype="html")
    else:
        m.set_content(html, subtype="html")
    return m


FIXTURES = {
    "alert_text_and_html.eml": msg("LinkedIn Job Alerts <jobalerts-noreply@linkedin.com>",
                                   "3 new jobs for application security", TEXT, HTML, mid="1"),
    "alert_html_only.eml": msg("LinkedIn <jobalerts-noreply@linkedin.com>", "Security Consultant at MDSec",
                               html=HTML_ONLY, mid="2"),
    "spoofed_no_dkim.eml": msg("LinkedIn Job Alerts <jobalerts-noreply@linkedin.com>", "Urgent: new job",
                               TEXT.replace("Deloitte", "Totally Real Bank"),
                               auth="mx.google.com; dkim=fail header.i=@linkedin.com; spf=softfail", mid="3"),
    "other_sender.eml": msg("Recruiter <jobs@recruiter.example>", "Great role for you", TEXT, mid="4"),
    "indeed_alert.eml": msg("Indeed <alert@indeed.com>", "application security jobs in United Kingdom",
                            html=INDEED_HTML, auth=dkim("indeed.com"), mid="5"),
    "glassdoor_alert.eml": msg("Glassdoor Jobs <noreply@glassdoor.com>", "Product Security Engineer at Wise",
                               html=GLASSDOOR_HTML, auth=dkim("glassdoor.com"), mid="6"),
    # claims to be Indeed but is DKIM-signed by linkedin.com: wrong domain must not pass
    "indeed_wrong_dkim.eml": msg("Indeed <alert@indeed.com>", "jobs", html=INDEED_HTML, mid="7"),
}

if __name__ == "__main__":
    for name, m in FIXTURES.items():
        (HERE / name).write_bytes(bytes(m))
        print("wrote", name)
