"""Shared helpers: load config, fetch a board with a time cap, classify job location/title."""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ats_scrapers.scrapers import get_scraper

from jobradar.paths import ROOT, profile_path

CONFIG = json.loads(profile_path("config.json").read_text(encoding="utf-8"))

# Fallback when a scraper doesn't populate country_iso: match the location text.
# Country names are trusted anywhere; city names are ignored when the location is
# clearly North American/Australian ("Cambridge, MA", "London, ON", "Perth, WA").
_COUNTRY_NAMES = {
    "GB": ["united kingdom", "england", "scotland", r"(?<!new south )wales", "northern ireland", "uk", "gb", "gbr"],
    "NL": ["netherlands", "nederland", "holland", "nld"],
    "IE": [r"(?<!northern )ireland", "irl"],
    "CH": ["switzerland", "schweiz", "suisse", "svizzera", "che"],
    "DE": ["germany", "deutschland", "deu"],
    "SE": ["sweden", "sverige", "swe"],
    "FR": ["france"], "ES": ["spain", "españa"], "IT": ["italy", "italia"], "DK": ["denmark"],
    "FI": ["finland"], "NO": ["norway"], "AT": ["austria"], "BE": ["belgium"], "LU": ["luxembourg"],
    "PT": ["portugal"], "EE": ["estonia"], "LT": ["lithuania"], "PL": ["poland"], "CZ": ["czech republic", "czechia"],
    # Outside Europe: never targets, but naming them lets the status card say where dropped listings were.
    "IN": ["india"], "US": ["united states", "united states of america"], "CA": ["canada"],
    "AU": ["australia"], "SG": ["singapore"], "AE": ["united arab emirates", "uae"], "IL": ["israel"],
}
_CITY_NAMES = {
    "GB": ["london", "manchester", "edinburgh", "glasgow", "cambridge", "bristol", "reading", "leeds",
           "birmingham", "belfast", "guildford", "cheltenham", "southampton", "norwich", "newbury",
           "swindon", "abingdon", "durham", "ipswich",
           # seen dropped as "location not recognised" (2026-09); not "york" (it would match New York)
           "harrow", "frimley", "milton keynes", "basingstoke", "gloucester", "farnborough", "slough", "woking",
           "bracknell", "maidenhead", "winchester", "portsmouth", "bournemouth", "poole", "brighton", "crawley",
           "watford", "luton", "stevenage", "hatfield", "hemel hempstead", "uxbridge", "wembley", "croydon",
           "osterley", "chelmsford", "colchester", "oxford", "coventry", "warwick", "leicester", "nottingham",
           "derby", "sheffield", "liverpool", "newcastle", "sunderland", "knutsford", "exeter", "plymouth",
           "cardiff", "newport", "swansea", "neath", "aberdeen", "dundee", "stirling", "livingston"],
    "NL": ["amsterdam", "the hague", "den haag", "rotterdam", "utrecht", "eindhoven", "delft", "amstelveen",
           "amersfoort", "leusden", "veldhoven", "zoetermeer", "maastricht", "haarlem", "leiden", "groningen",
           "arnhem", "nijmegen", "breda", "tilburg", "hilversum", "hoofddorp", "schiphol", "almere", "enschede",
           "hertogenbosch", "den bosch", "zwolle", "apeldoorn", "deventer", "dordrecht", "gouda", "alkmaar"],
    "IE": ["dublin", "cork", "galway", "limerick", "waterford", "dundalk"],
    "CH": ["zurich", "zürich", "geneva", "genève", "geneve", "bern", "lausanne", "basel", "baar", "aarau",
           "rapperswil"],
    "DE": ["berlin", "munich", "münchen", "muenchen", "frankfurt", "hamburg", "stuttgart", "cologne", "köln",
           "koeln", "heidelberg", "düsseldorf", "dusseldorf", "bonn", "walldorf", "ulm", "bochum", "freiburg",
           "tübingen", "tuebingen", "lüneburg", "hannover", "hanover", "nuremberg", "nürnberg", "leipzig",
           "dresden", "karlsruhe", "mannheim", "darmstadt", "wiesbaden", "mainz", "essen", "dortmund", "bremen",
           "potsdam", "augsburg", "münster", "aachen", "erlangen", "ingolstadt"],
    "SE": ["stockholm", "gothenburg", "göteborg", "malmö", "malmo", "linköping", "karlskrona", "kista"],
    "FR": ["paris", "lyon", "montpellier", "roubaix"], "ES": ["madrid", "barcelona", "bilbao"],
    "IT": ["milan", "milano", "rome"], "DK": ["copenhagen", "aarhus"], "FI": ["helsinki", "espoo"],
    "NO": ["oslo"], "AT": ["vienna", "wien"], "BE": ["brussels"], "PT": ["lisbon", "porto"],
    "EE": ["tallinn"], "LT": ["vilnius"], "PL": ["krakow", "kraków", "warsaw"], "CZ": ["prague", "praha", "brno"],
    "IN": ["bengaluru", "bangalore", "hyderabad", "pune", "chennai", "mumbai", "gurugram", "gurgaon", "noida",
           "new delhi", "delhi", "kolkata"],
    "SG": ["singapore"], "AE": ["dubai", "abu dhabi"],
}


def _words_re(words):
    return re.compile(r"\b(?:" + "|".join(words) + r")\b", re.I)


_COUNTRY_RE = {c: _words_re(w) for c, w in _COUNTRY_NAMES.items()}
_CITY_RE = {c: _words_re(w) for c, w in _CITY_NAMES.items()}
# A bare country code closing the location, any case ("…, NDS, de"). Target countries only: other
# two-letter tails are too often US/Canadian state codes.
_TRAILING_ISO = re.compile(r",\s*(de|nl|gb|uk|ie|ch|se)\s*$", re.I)
_REMOTE_EUROPE = re.compile(r"remote.*(europe|emea|\beu\b)|(europe|emea|\beu\b).*remote", re.I)
# Upper-case state/province codes after a comma. DE and IN are left out on purpose:
# "Berlin, DE" is common and must not be read as Delaware.
_NON_EUROPE = re.compile(
    r"(?i:united states|\busa\b|\bu\.s\.|canada|australia|\baus\b)"
    r"|,\s*(?:AL|AK|AZ|AR|CA|CO|CT|FL|GA|HI|ID|IL|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY"
    r"|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC|ON|BC|QC|AB|NSW|VIC|QLD)\b")

ISO_ALIASES = {"UK": "GB"}


def target_countries() -> set[str]:
    s = set(CONFIG["priority_countries"])
    if CONFIG.get("include_extra_countries"):
        s |= set(CONFIG["extra_countries"])
    return s


def all_europe() -> set[str]:
    return set(CONFIG["priority_countries"]) | set(CONFIG["extra_countries"])


def countries_for(country_iso: str | None, location: str | None) -> set[str]:
    """Countries a posting is in, from a scraper-supplied ISO code and/or location text.

    A non-European ISO code is trusted over the text (so ``US`` + "Cambridge, MA" stays
    US). A European code is extended with text matches, which catches multi-location
    postings like "London; Amsterdam"."""
    found = set()
    iso = (country_iso or "").upper()
    iso = ISO_ALIASES.get(iso, iso)
    loc = location or ""
    if iso:
        found.add(iso)
    if not iso or iso in all_europe():
        non_europe = bool(_NON_EUROPE.search(loc))
        for c, rx in _COUNTRY_RE.items():
            if rx.search(loc):
                found.add(c)
        if not non_europe:
            for c, rx in _CITY_RE.items():
                if rx.search(loc):
                    found.add(c)
        if not found and (tail := _TRAILING_ISO.search(loc)):  # "Lüneburg, NDS, de"
            found.add(ISO_ALIASES.get(tail.group(1).upper(), tail.group(1).upper()))
        if non_europe and not found:
            found.add("OUTSIDE-EUROPE")  # e.g. "Sunnyvale, CA": clearly not Europe, country not named
    if _REMOTE_EUROPE.search(loc):
        found.add("REMOTE-EU")
    return found


def job_countries(job) -> set[str]:
    """Countries an ats-scrapers Job is in."""
    return countries_for(getattr(job, "country_iso", None), getattr(job, "location", None))


def keyword_re(words: list[str]) -> re.Pattern:
    """Whole-word match per keyword; a trailing * matches word prefixes ("pentest*" → "pentester")."""
    parts = []
    for w in words:
        w = w.strip().lower()
        if w.endswith("*"):
            parts.append(r"\b" + re.escape(w[:-1]))
        else:
            parts.append(r"\b" + re.escape(w) + r"\b")
    return re.compile("|".join(parts) or r"(?!x)x", re.I)


_TITLE_INCLUDE = keyword_re(CONFIG["title_include"])
_TITLE_EXCLUDE = keyword_re(CONFIG["title_exclude"])


# Permanent roles only: these mark contract, temporary or student work, in a title or in the
# employment type an ATS reports. "Smart contract" (a security specialism) is not a contract type.
DEFAULT_EMPLOYMENT_EXCLUDE = ["contract", "contractor", "temporary", "temp", "fixed-term", "fixed term", "ftc",
                              "interim", "freelance*", "maternity cover", "parental leave cover", "secondment",
                              "internship", "intern", "apprentice*", "working student", "werkstudent*",
                              "befristet*", "tijdelijk*", "vikariat", "zeitarbeit", "praktik*"]
_EMPLOYMENT_EXCLUDE = keyword_re(CONFIG.get("employment_exclude", DEFAULT_EMPLOYMENT_EXCLUDE))
_SMART_CONTRACT = re.compile(r"smart[- ]contracts?", re.I)


def not_permanent(text: str) -> bool:
    """True when a title or employment-type text says contract / temporary / student work."""
    return bool(_EMPLOYMENT_EXCLUDE.search(_SMART_CONTRACT.sub(" ", text or "")))


def title_matches(title: str) -> bool:
    if _TITLE_EXCLUDE.search(title or ""):
        return False
    return bool(_TITLE_INCLUDE.search(title or ""))


@dataclass
class BoardResult:
    url: str
    ats: str
    ok: bool = False
    error: str = ""
    jobs: list = field(default_factory=list)


async def fetch_board(ats: str, slug: str, url: str, sem: asyncio.Semaphore) -> BoardResult:
    res = BoardResult(url=url, ats=ats)
    timeout = CONFIG.get("board_timeout_seconds", 180)
    async with sem:
        try:
            kwargs = {"include_descriptions": False, "timeout": 30.0}
            if ats == "workday":
                kwargs["max_fetch_seconds"] = float(timeout - 10)
                # Big tenants (Nvidia, Palo Alto) get throttled deep into pagination and the library gives up
                # after 3 tries; it has no option for this, only a module constant.
                import ats_scrapers.scrapers.workday as _wd
                _wd.MAX_RETRIES = max(_wd.MAX_RETRIES, int(CONFIG.get("workday_max_retries", 6)))
            scraper = get_scraper(ats, slug, **kwargs)
            res.jobs = await asyncio.wait_for(scraper.afetch(), timeout=timeout)
            res.ok = True
        except asyncio.TimeoutError:
            res.error = f"timeout after {timeout}s"
        except Exception as e:  # scrapers raise many things; record and move on
            res.error = f"{type(e).__name__}: {str(e)[:200]}"
    return res


async def fetch_many(boards: list[tuple[str, str, str]], progress: bool = True) -> dict[str, BoardResult]:
    """boards: list of (ats, scraper_slug, url). Returns url -> BoardResult."""
    sem = asyncio.Semaphore(CONFIG.get("concurrency", 6))
    tasks = [asyncio.create_task(fetch_board(a, s, u, sem)) for a, s, u in boards]
    out = {}
    for i, t in enumerate(asyncio.as_completed(tasks), 1):
        r = await t
        out[r.url] = r
        if progress:
            status = f"{len(r.jobs)} jobs" if r.ok else f"ERROR {r.error[:60]}"
            print(f"[{i}/{len(tasks)}] {r.ats:15} {r.url[:70]:70} {status}", flush=True)
    return out
