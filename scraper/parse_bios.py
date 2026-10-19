#!/usr/bin/env python3
"""
Derive structured fellow fields from the fellowship bios.

Until the LinkedIn pipeline (scrape.py) has a data-provider key, the written bio
is the only description we have of each fellow. This script pulls what it can
reliably out of that prose — job title, employer, current location, education
and a coarse industry bucket — and emits SQL that fills the matching columns on
public.fellows.

Everything here is best-effort, and deliberately conservative: a field is
written only when a clear pattern matches, so the table never gains invented
data. Missing values stay NULL and are filled in when the LinkedIn scrape runs.

Usage
-----
    python3 scraper/parse_bios.py --csv data/fellows_bios.csv \
        --sql data/import_fellow_details.sql

    # Preview without writing SQL
    python3 scraper/parse_bios.py --csv data/fellows_bios.csv --sample 15

    # Apply
    psql "$CONN" -f data/import_fellow_details.sql
"""

import argparse
import csv
import json
import re
from collections import Counter

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC",
}
ABBREVS = {v: v for v in STATES.values()}
# Full state names are matched case-insensitively; two-letter codes must appear
# uppercase, otherwise words like "in", "or", "me" would match IN/OR/ME.
_ABBR_ALT = "|".join(re.escape(a) for a in sorted(ABBREVS, key=len, reverse=True))
_NAME_ALT = "|".join(f"(?i:{re.escape(n)})"
                     for n in sorted(STATES, key=len, reverse=True))
STATE_ALT = rf"(?:{_ABBR_ALT}|{_NAME_ALT})"
STATE_RE = re.compile(rf"\b({STATE_ALT})\b")

# Cities that appear in the roster and are unambiguous enough to accept even
# without a trailing state.
NC_CITIES = {
    "raleigh", "charlotte", "greensboro", "durham", "winston-salem",
    "wilmington", "asheville", "fayetteville", "cary", "chapel hill",
    "greenville", "concord", "gastonia", "hickory", "high point",
    "jacksonville", "burlington", "wilson", "rocky mount", "salisbury",
    "kinston", "boone", "new bern", "goldsboro", "statesville", "sanford",
    "matthews", "apex", "huntersville", "mooresville", "monroe", "lincolnton",
    "shelby", "morganton", "lenoir", "albemarle", "wake forest",
    "fuquay-varina", "garner", "clayton", "knightdale", "morrisville",
    "holly springs", "pinehurst", "southern pines", "elizabeth city",
    "edenton", "hendersonville", "brevard", "waynesville", "cullowhee",
    "davidson", "cornelius", "kannapolis", "rockingham", "lumberton",
    "pineville", "clemmons", "lewisville", "mebane", "asheboro",
    "thomasville", "lexington", "mount airy", "reidsville", "eden",
    "moncure", "pittsboro", "siler city", "wadesboro", "troy", "yanceyville",
    "whispering pines", "salemburg", "cherry point", "king",
}

INDUSTRY_KEYWORDS = {
    "Law": [
        "attorney", "lawyer", "laws", "legal", "counsel", "litigat",
        "juris doctor", "judicial", "law clerk", "paralegal", "prosecutor",
        "district attorney", "court of appeals", "superior court",
        "law degree", "judge", "magistrate", "law review",
    ],
    "Government & Public Policy": [
        "public policy", "policy", "government", "general assembly", "senate",
        "house of representatives", "congress", "congressional", "legislative",
        "legislature", "city council", "county commissioner", "mayor",
        "campaign", "political", "politics", "state auditor", "governor",
        "public affairs", "regulatory", "municipal", "lobby", "partisan",
        "election", "ballot", "state government",
    ],
    "Finance & Banking": [
        "bank", "banking", "banker", "financ", "invest", "capital",
        "private equity", "venture", "wealth", "accounting", "accountant",
        "cpa", "audit", "portfolio", "credit union", "treasury", "cfo",
        "economist", "advisory",
    ],
    "Insurance": ["insurance", "underwrit", "actuar", "claims adjust"],
    "Healthcare": [
        "health", "medical", "physician", "nurse", "nursing", "hospital",
        "clinic", "patient", "cancer", "biotech", "pharma", "dental",
        "dentist", "therapist", "mental health", "medicine", "surgeon",
        "healthcare", "pharmacy", "pharmacist",
    ],
    "Education": [
        "teacher", "teaching", "professor", "education", "principal",
        "curriculum", "superintendent", "academy", "classroom", "tutor",
        "higher ed", "instructional", "faculty", "school system",
        "school district", "divinity school",
    ],
    "Technology": [
        "software", "engineer", "developer", "technology", "tech ", "data",
        "information technology", "cyber", "cloud", "saas", "startup",
        "digital", "artificial intelligence", "machine learning", "cto",
        "product manager", "innovation",
    ],
    "Real Estate & Construction": [
        "real estate", "realty", "property", "leasing", "broker", "realtor",
        "construction", "homebuild", "land use", "architecture", "signage",
    ],
    "Nonprofit & Philanthropy": [
        "nonprofit", "non-profit", "foundation", "charit", "ministry",
        "church", "volunteer", "advocacy", "advocate", "philanthrop",
        "boys & girls", "ymca", "think tank",
    ],
    "Media & Communications": [
        "communication", "marketing", "media", "public relations",
        "journalis", "reporter", "editor", "branding", "advertis",
        "writer", "social media", "broadcast", "news", "press", "podcast",
        "radio", "broadcaster",
    ],
    "Energy": [
        "energy", "utility", "utilities", "electric", "power", "oil", "gas",
        "renewable", "solar", "nuclear", "petroleum", "grid",
    ],
    "Agriculture": [
        "farm", "agricultur", "agribusiness", "poultry", "crop", "livestock",
        "agronomy", "forestry",
    ],
    "Manufacturing & Industry": [
        "manufactur", "factory", "production", "industrial", "supply chain",
        "logistics", "textile", "chemical",
    ],
    "Military & Public Safety": [
        "military", "army", "navy", "air force", "marines", "veteran",
        "police", "firefighter", "fire department", "sheriff", "law enforcement",
        "security", "emergency", "ems", "cbrn", "national guard",
        "judge advocate", "surface warfare",
    ],
}

# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

SPLIT_GUARD = {"mr", "mrs", "ms", "dr", "st", "inc", "co", "jr", "sr", "vs",
               "etc", "no", "u.s", "ph.d", "hon"}


def clean(text):
    """Normalise whitespace and smart punctuation."""
    text = (text or "").replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2014", " - ").replace("\u2013", "-")
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text):
    """Split prose into sentences without breaking on initials or abbreviations."""
    out, start = [], 0
    for m in re.finditer(r"([.!?])\s+(?=[A-Z])", text):
        seg = text[start:m.start() + 1].strip()
        words = seg[:-1].split()
        last = words[-1] if words else ""
        # "C.", "B.J." — an initial, not the end of a sentence ("NC." is not).
        if re.fullmatch(r"(?:[A-Z]\.)+", last + "."):
            continue
        if last.lower().rstrip(".") in SPLIT_GUARD:
            continue
        out.append(seg)
        start = m.end()
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


def strip_leading_name(sentence, name):
    """Remove the fellow's name from the start of a sentence."""
    first = name.split()[0] if name else ""
    for candidate in (name, first):
        if candidate and sentence.lower().startswith(candidate.lower() + " "):
            return sentence[len(candidate):].lstrip(" ,")
    return sentence


def strip_leading_pronoun(sentence):
    return re.sub(r"^(?:he|she|they|it)\b[\s,]+", "", sentence, flags=re.IGNORECASE)


def find_state(text):
    m = STATE_RE.search(text)
    if not m:
        return None
    token = m.group(1)
    if token.isupper() and token.upper() in ABBREVS:
        return ABBREVS[token.upper()]
    return STATES.get(token.lower())


def trim_appositive(text):
    """Drop a trailing descriptive clause from an organisation name."""
    text = re.split(r",\s+(?:a|an|the|which|where|who|his|her|their|and\s+operat)\b",
                    text, maxsplit=1)[0]
    text = re.split(r"\s+-\s+", text, maxsplit=1)[0]
    text = re.sub(r"\s*\(.*?\)\s*$", "", text)
    return text.strip(" ,;.")


def strip_leading_the(text):
    return re.sub(r"^the\s+", "", text, flags=re.IGNORECASE).strip(" ,")


def title_case_first(text):
    return text[:1].upper() + text[1:] if text else text


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

LOCATION_VERB = r"(?:lives?|living|resides?|based|located|relocated|moved)"
CITY = r"([A-Z][A-Za-z.'\-]*(?:\s+[A-Z][A-Za-z.'\-]*){0,2})"
CITY_STOP = {"the", "his", "her", "their", "north", "south", "east", "west",
             "united", "new", "this", "that", "congress", "america", "carolina"}

LOCATION_TAIL = re.compile(
    rf",?\s+(?:based|located|living|working)\s+in\s+"
    rf"[A-Z][\w.'\-]*(?:\s+[A-Z][\w.'\-]*)*\s*$"
)
LOCATION_TAIL_STATE = re.compile(
    rf",?\s+(?:based|located|living|working)?\s*in\s+"
    rf"[A-Z][\w.'\-]*(?:\s+[A-Z][\w.'\-]*)*\s*,\s*{STATE_ALT}\s*$"
)


def strip_trailing_location(text):
    """Remove a trailing "... in City" / "... in City, State" from a phrase."""
    text = LOCATION_TAIL_STATE.sub("", text)
    text = LOCATION_TAIL.sub("", text)
    m = re.search(r",?\s+in\s+([A-Z][\w.'\-]*(?:\s+[A-Z][\w.'\-]*)*)\s*$", text)
    if m and m.group(1).lower() in NC_CITIES:
        text = text[:m.start()]
    return text.strip(" ,")


def find_location(text, first_sentence):
    """Return (city, state) for the fellow's current location, or (None, None)."""
    # 1. "<verb> in <City>, <State>"  — strongest signal
    for m in re.finditer(
            rf"\b(?i:{LOCATION_VERB})\s+in\s+{CITY}\s*,\s*({STATE_ALT})\b", text):
        city, state = m.group(1).strip(), find_state(m.group(2))
        if validate_city(city):
            return titlecase_city(city), state

    # 2. "<City>, <State>" in the opening sentence (not an origin)
    for m in re.finditer(rf"\b{CITY}\s*,\s*({STATE_ALT})\b", first_sentence):
        city, state = m.group(1).strip(), find_state(m.group(2))
        before = first_sentence[max(0, m.start() - 12):m.start()].lower()
        if "from" in before or not validate_city(city):
            continue
        return titlecase_city(city), state

    # 3. "<verb> in <City>" — only well-known NC cities
    for m in re.finditer(rf"\b(?i:{LOCATION_VERB})\s+in\s+{CITY}\b", text):
        city = m.group(1).strip()
        if city.lower() in NC_CITIES:
            return titlecase_city(city), "NC"

    # 4. "<City>, NC" anywhere, but only for known NC cities
    for m in re.finditer(rf"\b{CITY}\s*,\s*(?:NC|(?i:north carolina))\b", text):
        city = m.group(1).strip()
        if city.lower() in NC_CITIES:
            return titlecase_city(city), "NC"

    return None, None


def validate_city(city):
    words = city.split()
    if not words or len(words) > 3:
        return False
    if words[0].lower() in CITY_STOP:
        return False
    if words[-1].lower() in {"county", "counties", "parish", "district"}:
        return False
    if any(ch.isdigit() for ch in city):
        return False
    return True


def titlecase_city(city):
    return " ".join(w[:1].upper() + w[1:] for w in city.split())


# ---------------------------------------------------------------------------
# Role (title + employer)
# ---------------------------------------------------------------------------

JOB_HINT = re.compile(
    r"\b(?:analyst|manager|director|attorney|counsel|officer|engineer|"
    r"consultant|strategist|specialist|coordinator|president|founder|partner|"
    r"associate|advisor|adviser|architect|professor|teacher|principal|clerk|"
    r"fellow|representative|senator|commissioner|producer|editor|writer|"
    r"broker|banker|nurse|physician|planner|liaison|administrator|secretary|"
    r"treasurer|supervisor|owner|operator|chairman|chairwoman|ceo|cfo|coo|"
    r"executive|vice president|developer|designer|pastor|judge|magistrate|"
    r"deputy|assistant|general counsel|farmer|pharmacist|investigator|"
    r"broadcaster|reporter|developer|programmer|coach|instructor|librarian)\b",
    re.IGNORECASE,
)

DESCRIPTOR = re.compile(
    r"^(?:a|an|the)?\s*(?:seasoned|veteran|accomplished|dedicated|passionate|"
    r"experienced|longtime|well-known|recognized|rising|emerging)\b"
    r"|^(?:a|an|the)?\s*(?:[A-Z][\w.'\-]*\s+){0,3}native\b"
    r"|\bwith (?:over|more than|nearly|almost|a decade|two decades)\b"
    r"|\byears of experience\b",
    re.IGNORECASE,
)

TRANSITION = re.compile(
    r"^(?:previously|before|prior|formerly|earlier|after|while|during|since|"
    r"in \d{4}|from \d{4}|next|then|there|today|as a result|outside|alongside)\b",
    re.IGNORECASE,
)
PAST_LEAD = re.compile(r"^(?:previously|formerly|once|prior to|former)\b",
                       re.IGNORECASE)

# Separators between a role and its organisation.
SEPARATORS = (" at ", " with ", " for ", " of the ", " in the ")

# Words that mark a string as an organisation rather than a bare clause.
ORG_KEYWORD = re.compile(
    r"\b(?:University|College|School|Institute|Academy|Seminary|Inc|LLC|LLP|"
    r"PLLC|PC|Corp|Corporation|Company|Co|Group|Partners|Firm|Foundation|"
    r"Association|Chamber|Department|Commission|Agency|Center|Centre|Hospital|"
    r"Bank|Services|Systems|Ministries|Church|Council|Authority|Board|Society|"
    r"Union|Alliance|Network|Media|Law|Realty|Real Estate|Consulting|Capital|"
    r"Advisors|Advisory|Insurance|Clinic|Practice|Studio|Labs|Technologies|"
    r"Solutions|Holdings|Government|Assembly|Senate|House|Office|Bureau|"
    r"Administration|College|District|School)\b",
    re.IGNORECASE,
)

# Multi-role bios ("... and a compliance manager") — keep only the first role.
CLAUSE_CUT = re.compile(
    r"(?<![A-Z])\.\s+[A-Z]"
    r"|,\s+as well as\b"
    r"|,\s+(?:owns|operates|publishes|produces|founded)\b"
    r"|,\s+and\s+(?:a|an|the|also|serves|is|was|has|works|resides|lives|"
    r"chairs|owns|vice|currently|formerly|previously|serving|who|which|where)\b"
    r"|\s+and\s+(?:a|an|the|also|serves|is|was|has|works|resides|lives|"
    r"chairs|owns|vice|currently|formerly|previously|founder|co-founder|"
    r"co-owner|owner|president|managing|contracting|provides|operates|"
    r"focusing)\b",
    re.IGNORECASE,
)


def split_role_company(body):
    """Split a role clause into (title, company).

    Multi-role bios ("... and a compliance manager") are trimmed to the first
    role first. Since a clause can contain several separators -- e.g. "Deputy
    General Counsel for the Senate President Pro Tempore at the North Carolina
    General Assembly" or "community engagement director for the North Carolina
    chapter of Americans for Prosperity" -- every separator position is scored
    and the most organisation-like split wins.
    """
    body = CLAUSE_CUT.split(body)[0]
    body = trim_appositive(body).rstrip(".")
    low = body.lower()

    hits = []
    for sep in SEPARATORS:
        start = 0
        while True:
            i = low.find(sep, start)
            if i <= 0:
                break
            hits.append((i, sep))
            start = i + 1

    best = None
    for idx, sep in hits:
        title = body[:idx].strip(" ,")
        company = body[idx + len(sep):].strip(" ,")
        cleaned = clean_org(company)
        if not title or is_junk_org(cleaned):
            continue
        score = len(cleaned) + (25 if ORG_KEYWORD.search(cleaned) else 0)
        if best is None or score > best[0]:
            best = (score, title, company)

    if best:
        return best[1], best[2]
    if hits:
        idx, sep = max(hits)
        return body[:idx].strip(" ,"), None
    return body, None


def clean_org(text):
    text = CLAUSE_CUT.split(text)[0]
    text = strip_trailing_location(text)
    text = trim_appositive(text)
    text = re.sub(r"^(?:the|a|an)\s+", "", text, flags=re.IGNORECASE)
    return text.strip(" ,;.")


ORG_VERB = re.compile(
    r"\b(?:received|graduated|attended|earned|holds|resides|lives|chairs|"
    r"serves|previously|formerly|studied|works|majored|informs|position|"
    r"his|her|their)\b", re.IGNORECASE)


def is_junk_org(text):
    if not text or len(text) < 2 or len(text) > 60:
        return True
    if re.search(r"\.\s+[A-Z]", text):
        return True
    if text.count(",") >= 3:
        return True
    if ORG_VERB.search(text):
        return True
    if re.search(r"\b(?:area|region)\s*$", text, re.IGNORECASE):
        return True
    if re.search(r"\bdistrict\b", text, re.IGNORECASE):
        return True
    if re.search(r"\bcount(?:y|ies)\b", text, re.IGNORECASE) and not re.search(
            r"\b(?:school|department|board|commission|chamber|college|university)\b",
            text, re.IGNORECASE):
        return True
    # "media relations at ...", "industrial contractor Edwards Inc" — a clause,
    # not an organisation name.
    head = text.split()
    if len(head) >= 2 and head[0][:1].islower() and head[1][:1].islower():
        return True
    return False


def clean_title(text):
    text = re.split(r",\s+(?:currently|now|where|and|who|which|focusing)\b", text)[0]
    text = re.sub(r"\s+and\s+(?:a|an|the|also|works|serves|is|was)\b.*$", "",
                  text, flags=re.IGNORECASE)
    text = strip_trailing_location(text)
    text = re.sub(r"\s+(?:living|based|located|working)$", "", text,
                  flags=re.IGNORECASE)
    text = strip_leading_the(text).strip(" ,;.")
    if " at " in text:
        text = text.split(" at ")[0].strip(" ,")
    return text


def extract_role(sentence):
    """Best-effort (title, company) from one sentence."""
    s = sentence.strip().rstrip(".")
    if not s:
        return None, None

    m = re.match(r"^works?\s+(?:for|at)\s+(.+?)\s+as\s+(.+)$", s, re.IGNORECASE)
    if m:
        return clean_title(m.group(2)), clean_org(m.group(1))

    m = re.match(r"^currently\s+works?\s+(?:for|at)\s+(.+)$", s, re.IGNORECASE)
    if m:
        return None, clean_org(m.group(1))

    m = re.match(r"^has\s+(?:taught|worked)\s+at\s+(.+?)\s+since\b", s, re.IGNORECASE)
    if m:
        return None, clean_org(m.group(1))

    if TRANSITION.match(s):
        return None, None

    body = None
    m = re.match(r"^(?:currently\s+)?(?:is|was|serves as|works as)\s+", s, re.IGNORECASE)
    if m:
        body = s[m.end():]
    else:
        m = re.search(r"\bas\s+(?:a|an|the)\s+(.+)$", s, re.IGNORECASE)
        if m and JOB_HINT.search(m.group(1)):
            head = s[:m.start()]
            if not re.search(r"\b(?:served|worked|previously|formerly|was|were)\b",
                             head, re.IGNORECASE):
                body = m.group(1)
    if body is None or PAST_LEAD.match(body):
        return None, None

    # "<state> native who currently serves as <role>"
    m = re.match(r"^(?:a\s+|an\s+)?(?:[A-Z][\w.'\-]*\s+){0,3}native\b\s*"
                 r"(?:who\s+)?(?:currently\s+)?(?:serves as|is)\s+(.+)$",
                 body, re.IGNORECASE)
    if m:
        body = m.group(1)

    if DESCRIPTOR.search(body):
        return None, None

    body = re.sub(r"^(?:currently\s+|also\s+|now\s+)*(?:the|a|an)\s+", "", body,
                  flags=re.IGNORECASE)
    body = re.split(r"\s+(?:where|which|who)\s+", body)[0]

    title, company = split_role_company(body)

    if title:
        if re.search(r"\band more\b", title):
            return None, None
        title = clean_title(title)
        if re.search(r"\b(?:former|formerly|previously|past)\b", title, re.IGNORECASE):
            title = None
        elif len(title) > 80 or len(title.split()) > 12:
            return None, None
        elif title and title == title.lower():
            title = " ".join(w.capitalize() for w in title.split())
    if company:
        company = clean_org(company)
        if is_junk_org(company):
            company = None
    return title or None, company or None


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------

WORD = r"[A-Z][A-Za-z.'\-]*"
CONN = r"(?:of|the|and|&|at|for|in)"
NAME_RUN = rf"{WORD}(?:\s+(?:{WORD}|{CONN})){{0,5}}"
UNI_RE = re.compile(
    rf"({NAME_RUN}\s+(?:University|College|Institute|Academy|Seminary|"
    rf"School(?:\s+of\s+{WORD})?))"
)
EDU_CUES = (
    "graduate", "graduated", "degree", "bachelor", "master", "mba",
    "alumn", "attended", "studied", "earned", "holds a", "received a",
    "law degree", "doctorate", "majored", "undergraduate", "ph.d", "ba in",
)
DEGREE_WORD = (r"(?:bachelor|master|masters|associate|doctor|phd|ph\.d|mba|jd|"
               r"j\.d|ba|bs|b\.a|b\.s|ma|ms|m\.a|m\.s|degree)")
DEGREE_AT_FROM = re.compile(rf"^{DEGREE_WORD}\b.*?\b(?:at|from)\s+(.+)$", re.IGNORECASE)
DEGREE_IN = re.compile(rf"^{DEGREE_WORD}\b.*?\bin\s+(.+)$", re.IGNORECASE)


def clean_edu(name):
    m = DEGREE_AT_FROM.match(name) or DEGREE_IN.match(name)
    return m.group(1) if m else name


def find_education(text):
    found = []
    for m in UNI_RE.finditer(text):
        name = clean_edu(m.group(1).strip())
        low = name.lower()
        if "high school" in low or low.startswith("high "):
            continue
        before = text[max(0, m.start() - 90):m.start()].lower()
        if not any(cue in before for cue in EDU_CUES):
            continue
        if name not in found:
            found.append(name)
    return "; ".join(found[:3]) if found else None


# ---------------------------------------------------------------------------
# Industry
# ---------------------------------------------------------------------------

def find_industry(text):
    low = " " + text.lower() + " "
    scores = {}
    for industry, words in INDUSTRY_KEYWORDS.items():
        score = sum(low.count(w) * (1 + min(len(w), 20) / 20) for w in words)
        if score:
            scores[industry] = score
    if not scores:
        return None
    best = max(scores, key=scores.get)
    return best if scores[best] >= 1.5 else None


# ---------------------------------------------------------------------------
# Per-fellow derivation
# ---------------------------------------------------------------------------

def derive(name, bio):
    bio = clean(bio)
    if not bio:
        return {}

    sentences = split_sentences(bio)
    sentences[0] = strip_leading_name(sentences[0], name)
    first = sentences[0]
    for i in range(1, len(sentences)):
        sentences[i] = strip_leading_pronoun(sentences[i])

    title = company = None
    for s in sentences[:4]:
        t, c = extract_role(s)
        if t or c:
            title, company = t, c
            break

    city, state = find_location(bio, first)

    out = {}
    if title:
        out["current_title"] = title
    if company:
        out["current_company"] = company
    if city:
        out["city"] = city
    if state:
        out["state"] = state
    edu = find_education(bio)
    if edu:
        out["education"] = edu
    ind = find_industry(bio)
    if ind:
        out["industry"] = ind

    # Headline: only when no role was established, so the directory card still
    # has something to show. Skip anything that is really a name or a past job.
    if not title and not company:
        head = re.sub(r"^(?:currently\s+)?(?:is|was|serves as)\s+", "", first,
                      flags=re.IGNORECASE)
        head = re.sub(r"^(?:the|a|an)\s+", "", head, flags=re.IGNORECASE).rstrip(".")
        head = title_case_first(head)
        head = re.sub(r'^(?:"[^"]*"|\([^)]*\))\s*', "", head)
        name_words = {w.strip("\"().,;").lower()
                      for w in re.split(r"\s+", name) if len(w) > 2}
        head_first = head.split()[0].strip("\"().,;") if head.split() else ""
        if re.match(r"^(?:\([^)]*\)\s*)?(?:[A-Z][\w.'\-]*\s+){1,5}"
                    r"(?:is|was|were)\b", head) or \
                re.match(r"^[A-Z][\w.'\-]*\s+(?:was|were)\b", head) or \
                re.match(r"^(?:previously|formerly|once|worked|has worked|"
                         r"native of|resides in|resident of|originally from)\b",
                         head, re.IGNORECASE) or \
                head_first.lower() in name_words:
            head = ""
        if len(head) > 150:
            head = head[:150].rsplit(" ", 1)[0] + "..."
        if head:
            out["headline"] = head
    return out


def sql_escape(value):
    return str(value).replace("'", "''")


def build_sql(records, path):
    lines = [
        "-- Auto-generated by scraper/parse_bios.py",
        "-- Fills structured fellow fields derived from the written bios.",
        "-- Best-effort: the LinkedIn scrape (scrape.py) supersedes these later.",
        "",
        "begin;",
        "",
    ]
    for name, year, fields in records:
        if not fields:
            continue
        sets = ", ".join(f"{k} = '{sql_escape(v)}'" for k, v in fields.items())
        lines.append(
            f"update public.fellows set {sets}, updated_at = now() "
            f"where full_name = '{sql_escape(name)}' and cohort_year = {year};"
        )
    lines += ["", "commit;", ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description="Derive fellow fields from bios")
    ap.add_argument("--csv", required=True, help="CSV with Name, Class Year, Bio")
    ap.add_argument("--sql", help="Write UPDATE statements to this file")
    ap.add_argument("--json", help="Write derived records to this JSON file")
    ap.add_argument("--sample", type=int, default=0, help="Print N examples")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.csv, encoding="utf-8-sig")))
    records, coverage, samples = [], Counter(), []
    for r in rows:
        name = (r.get("Name") or "").strip()
        year = (r.get("Class Year") or "").strip() or 0
        fields = derive(name, r.get("Bio") or "")
        records.append((name, year, fields))
        for key in ("current_title", "current_company", "city", "state",
                    "education", "industry", "headline"):
            if fields.get(key):
                coverage[key] += 1
        if fields.get("current_title") and fields.get("current_company"):
            coverage["title+company"] += 1
        if len(samples) < args.sample:
            samples.append((name, fields))

    total = len(rows)
    print(f"Parsed {total} bios\n")
    for key in ("current_title", "current_company", "title+company", "city",
                "state", "education", "industry", "headline"):
        n = coverage[key]
        print(f"  {key:16s} {n:3d}  ({n * 100 // max(total, 1)}%)")

    if args.sample:
        print("\nExamples:")
        for name, fields in samples:
            print(f"\n  {name}")
            for k, v in fields.items():
                print(f"    {k}: {v}")

    if args.sql:
        build_sql(records, args.sql)
        print(f"\nWrote {args.sql}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump([{"name": n, "year": y, **fl} for n, y, fl in records],
                      f, indent=2, ensure_ascii=False)
        print(f"Wrote {args.json}")


if __name__ == "__main__":
    main()
