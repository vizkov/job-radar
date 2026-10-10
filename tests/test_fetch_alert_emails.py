"""tools/fetch_alert_emails.py: the only code that sees the mailbox password."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import fetch_alert_emails as fae  # noqa: E402

RAW = (Path(__file__).parent / "fixtures" / "alert_email" / "alert_text_and_html.eml").read_bytes()


class FakeIMAP:
    calls = []

    def __init__(self, host, timeout=None):
        FakeIMAP.calls = [("connect", host)]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, user, pw):
        FakeIMAP.calls.append(("login", user))

    def select(self, mailbox, readonly=False):
        FakeIMAP.calls.append(("select", mailbox, readonly))
        return "OK", [b"1"]

    def uid(self, cmd, *args):
        FakeIMAP.calls.append(("uid", cmd) + args)
        if cmd == "SEARCH":
            return "OK", [b"7 9" if "jobalerts-noreply@linkedin.com" in args[-1] else b""]
        return "OK", [(b"7 (BODY[] {10}", RAW)]


def run(tmp_path, monkeypatch, env=True, extra=()):
    monkeypatch.setattr(fae.imaplib, "IMAP4_SSL", FakeIMAP)
    if env:
        monkeypatch.setenv("JOBALERT_IMAP_USER", "alerts@example.com")
        monkeypatch.setenv("JOBALERT_IMAP_PASSWORD", "app-password-123")
    else:
        monkeypatch.delenv("JOBALERT_IMAP_USER", raising=False)
        monkeypatch.delenv("JOBALERT_IMAP_PASSWORD", raising=False)
    assert fae.main(["--out", str(tmp_path), *extra]) == 0
    return json.loads((tmp_path / "_status.json").read_text())


def test_read_only_and_peek(tmp_path, monkeypatch):
    status = run(tmp_path, monkeypatch)
    assert status["ok"] and status["fetched"] == 2
    assert ("select", '"INBOX"', True) in FakeIMAP.calls                        # EXAMINE, never SELECT rw
    fetches = [c for c in FakeIMAP.calls if c[:2] == ("uid", "FETCH")]
    assert fetches and all(c[3] == "(BODY.PEEK[])" for c in fetches)          # never sets \Seen
    assert not any(c[0] in ("store", "expunge") or (len(c) > 1 and c[1] in ("STORE", "EXPUNGE"))
                   for c in FakeIMAP.calls)
    assert sorted(p.name for p in tmp_path.glob("*.eml")) == ["7.eml", "9.eml"]


def test_missing_credentials_reported_not_raised(tmp_path, monkeypatch, capsys):
    status = run(tmp_path, monkeypatch, env=False)
    assert not status["ok"] and "JOBALERT_IMAP_USER" in status["error"]
    assert "app-password" not in capsys.readouterr().out


def test_password_never_written_or_printed(tmp_path, monkeypatch, capsys):
    run(tmp_path, monkeypatch)
    assert "app-password-123" not in capsys.readouterr().out
    assert "app-password-123" not in (tmp_path / "_status.json").read_text()


def test_old_mail_is_cleared(tmp_path, monkeypatch):
    (tmp_path / "stale.eml").write_bytes(b"old")
    run(tmp_path, monkeypatch)
    assert not (tmp_path / "stale.eml").exists()


def test_unknown_provider_reported(tmp_path, monkeypatch):
    status = run(tmp_path, monkeypatch, extra=("--providers", "linkedin,myspace"))
    assert not status["ok"] and "myspace" in status["error"]


def test_runs_with_standard_library_only():
    """-I -S: no site-packages at all. If the script (or alert_providers) imported any
    third-party package, this would fail with ModuleNotFoundError."""
    r = subprocess.run([sys.executable, "-I", "-S", str(ROOT / "tools" / "fetch_alert_emails.py"), "--help"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    r = subprocess.run([sys.executable, "-I", "-S", "-c",
                        "import sys; sys.path.insert(0, r'%s'); import jobradar.alert_providers as m; "
                        "mods = [k for k in sys.modules if k.split('.')[0] not in sys.stdlib_module_names "
                        "and k.split('.')[0] not in ('jobradar', '__main__')]; print(mods)" % ROOT],
                       capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip() == "[]", (r.stdout, r.stderr)


class GmailIMAP(FakeIMAP):
    """Gmail-like: an All Mail folder, and LinkedIn mail from an alert sender plus another address."""

    def list(self):
        return "OK", [b'(\HasNoChildren) "/" "INBOX"', b'(\All \HasNoChildren) "/" "[Google Mail]/All Mail"']

    def uid(self, cmd, *args):
        FakeIMAP.calls.append(("uid", cmd) + args)
        if cmd == "SEARCH":
            who = args[-1]
            return "OK", [b"7 9" if "jobalerts-noreply@linkedin.com" in who else b"7 9 11" if who == '"linkedin.com"' else b""]
        if "HEADER.FIELDS" in args[-1]:
            return "OK", [(b"11 (BODY[HEADER.FIELDS (FROM)] {40}", b"From: LinkedIn <messages-noreply@linkedin.com>\r\n")]
        return "OK", [(b"7 (BODY[] {10}", RAW)]


def test_all_mail_and_sender_diagnostics(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fae.imaplib, "IMAP4_SSL", GmailIMAP)
    monkeypatch.setenv("JOBALERT_IMAP_USER", "alerts@example.com")
    monkeypatch.setenv("JOBALERT_IMAP_PASSWORD", "app-password-123")
    assert fae.main(["--out", str(tmp_path), "--providers", "linkedin"]) == 0
    status = json.loads((tmp_path / "_status.json").read_text())
    assert status["mailbox"] == "[Google Mail]/All Mail" and ("select", '"[Google Mail]/All Mail"', True) in FakeIMAP.calls
    assert status["providers"]["linkedin"] == {"from_domain": 3, "alert_senders": 2,
                                               "other_senders": {"messages-noreply@linkedin.com": 1}}
    headers = [c for c in FakeIMAP.calls if c[:2] == ("uid", "FETCH") and "HEADER" in c[-1]]
    assert headers and all("PEEK" in c[-1] for c in headers)          # addresses only, never marks read
    out = capsys.readouterr().out
    assert "messages-noreply@linkedin.com (1)" in out and "app-password-123" not in out


def test_configured_providers_follow_sources_yaml(tmp_path):
    import fetch_alert_emails as f  # tools/ is on the path in this module's other tests
    y = tmp_path / "sources.yaml"
    y.write_text("sources:\n  other:\n    providers: [nope]\n  alert_email:\n    enabled: true\n"
                 "    providers: [linkedin, 'indeed']   # note\n    eml_dir: x\n  next:\n    providers: [glassdoor]\n")
    assert f.configured_providers(y) == ["linkedin", "indeed"]
    assert f.configured_providers(tmp_path / "missing.yaml") == list(f.PROVIDERS)
    y.write_text("sources:\n  alert_email:\n    enabled: true\n")
    assert f.configured_providers(y) == list(f.PROVIDERS)
