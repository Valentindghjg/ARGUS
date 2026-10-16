# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Deterministic, entirely local MIME classification. Mail is untrusted input."""
from dataclasses import dataclass
from datetime import timezone
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from hashlib import sha256
from html.parser import HTMLParser
import re

from .errors import UserFacingError
from .registry import Registry, normalize_domain

MAX_MESSAGE_BYTES = 2 * 1024 * 1024
# Internal marker prepended to header-only IMAP fetches. It is part of the
# message fingerprint, so it keeps its pre-rename name: changing it would
# duplicate evidence for large messages that were already analyzed.
HEADERS_ONLY_MARKER = b"X-Account-Finder-Headers-Only"
MAX_TEXT = 100_000
ANALYSIS_VERSION = 2
LABELS = {
    "account_created": "Registration / account creation reported",
    "email_verified": "Email verification completed",
    "password_changed": "Password change reported",
    "login_activity": "Sign-in or new device reported",
    "verification_requested": "Email verification requested; completion unknown",
    "welcome_account": "Welcome message with account context",
    "reset_requested": "Reset request; not evidence of an account",
    "order_only": "Order / invoice; guest checkout possible",
    "newsletter": "Newsletter / advertising; not evidence of an account",
}
# Plan E2: what a clue says about an account, separate from its strength.
KINDS = {
    "account_created": "account", "email_verified": "account", "password_changed": "account",
    "login_activity": "account", "verification_requested": "account", "welcome_account": "account",
    "reset_requested": "reset", "order_only": "order", "newsletter": "marketing",
}
# Plan E1: short codes for the rule features behind a clue. They are stored
# instead of message text and explained in the dashboard.
FEATURES = frozenset({
    "matched_subject", "matched_body", "recipient_to", "recipient_indirect", "multiple_recipients",
    "catalog_domain", "unknown_domain", "mailing_list_header", "advertising_words", "subscription_wording",
    "forwarded", "headers_only", "generic_welcome",
})
# Specific completed events outrank generic welcome/verification wording.
LEGACY_CAVEATS = {
    "Allgemeine Begrüßung mit Werbemerkmalen; manuell prüfen": "Generic welcome with advertising indicators; review manually",
    "Mehrere eigene Empfänger; Anmeldeadresse unklar": "Multiple own recipients; sign-in address uncertain",
    "Weiterleitung / Empfängerzuordnung unklar": "Forwarding / recipient association uncertain",
    "Nur Header ausgewertet (Nachricht über Größenlimit)": "Only headers analyzed (message exceeds size limit)",
    "Anbieter-Domain nicht im Katalog; manuell prüfen": "Provider domain not in the catalog; review manually",
}


def english_caveat(value: str | None) -> str | None:
    """Display old program-generated caveats in English without modifying user data."""
    if value is not None:
        for old, new in LEGACY_CAVEATS.items():
            value = value.replace(old, new)
    return value


RULES = [
    ("password_changed", 92, r"(?:password (?:has been|was|is successfully) (?:changed|updated)|changed your password|passwort (?:wurde|ist|erfolgreich).{0,35}(?:geändert|aktualisiert)|dein passwort.{0,20}geändert)"),
    ("email_verified", 88, r"(?:e-?mail (?:address )?(?:(?:has been|was|is now)(?: successfully)?|successfully) (?:verified|confirmed)|e-mail.{0,30}(?:erfolgreich bestätigt|wurde bestätigt|wurde verifiziert))"),
    ("account_created", 90, r"(?:your (?:new )?account (?:has been|was|is now|is)(?: successfully)? (?:created|activated)|registration (?:is )?(?:complete|successful)|(?:thanks|thank you) for (?:signing up|registering)|you have successfully registered|konto.{0,35}(?:wurde erstellt|erfolgreich erstellt|wurde aktiviert)|registrierung.{0,25}(?:abgeschlossen|erfolgreich)|danke.{0,30}(?:registrierung|registriert))"),
    ("login_activity", 85, r"(?:new (?:sign-in|signin|login|log in) (?:to|on|from)|new device.{0,50}(?:account|signed in)|signed in to your account|neue anmeldung|anmeldung.{0,35}(?:neuen gerät|neuem gerät)|neues gerät.{0,40}(?:konto|angemeldet))"),
    ("reset_requested", 25, r"(?:reset your password|password reset (?:request|code|link)|passwort zurücksetzen|passwort-zurücksetzung|angeforderte passwortänderung)"),
    ("verification_requested", 68, r"(?:verify your (?:e-?mail|account)|confirm your (?:e-?mail|account)|activate your account|complete your registration|(?:bestätige|bestätigen sie|verifiziere).{0,25}(?:e-mail|email|konto)|(?:e-mail|email).{0,25}(?:bestätigen|verifizieren)|(?:aktiviere|aktivieren sie).{0,20}konto|registrierung abschließen)"),
    ("welcome_account", 70, r"(?:welcome.{0,80}(?:your account|your new account)|willkommen.{0,80}(?:dein konto|ihr konto|deinem konto))"),
    ("order_only", 20, r"(?:order confirmation|your order|invoice|bestellbestätigung|deine bestellung|ihre bestellung|rechnung)"),
]
PATTERNS = [(name, score, re.compile(pattern, re.I)) for name, score, pattern in RULES]
PROMOTION = re.compile(r"newsletter|unsubscribe|abbestellen|sale\b|rabatt|special offers|werbung|marketing", re.I)
SUBSCRIPTION = re.compile(r"(?:subscribe.{0,45}(?:newsletter|mailing list)|(?:welcome|willkommen)\s+(?:to (?:the |our )?|zum |zu unserem |im )?(?:newsletter|mailing list)|(?:thanks|thank you|danke).{0,20}(?:signing up|registering|subscribing|anmeldung).{0,25}(?:newsletter|mailing list)|newsletter.{0,35}(?:anmeldung|abonnement|subscription|bestätigen|confirm)|anmeldung.{0,25}newsletter|(?:confirm|verify|bestätige).{0,40}(?:newsletter|mailing list))", re.I)
ACCOUNT_CONTEXT = re.compile(r"(?:your (?:new )?account|account (?:settings|registration|activation)|dein(?:em|es)? (?:neues? )?konto|ihr(?:em|es)? konto|kontoeinstellungen|kontoerstellung|registrierung)", re.I)
AD_OFFER = re.compile(r"\bsale\b|rabatt|special offers|werbung|marketing", re.I)
NEGATED = re.compile(r"\b(?:not|never|nicht|keine|kein)\b", re.I)
FORWARDED = re.compile(r"^(?:(?:re|fw|fwd|aw|wg)\s*:\s*)|(?:forwarded message|weitergeleitete nachricht|original message|ursprüngliche nachricht)", re.I)
URL = re.compile(r"(?:https?://|www\.)\S+", re.I)


def normalize_email(value: str) -> str:
    value = value.strip()
    if len(value) > 254 or any(c.isspace() or ord(c) < 32 for c in value) or value.count("@") != 1:
        raise UserFacingError("Invalid email address")
    local, domain = value.rsplit("@", 1)
    if not local or len(local) > 64:
        raise UserFacingError("Invalid email address")
    return local.casefold() + "@" + normalize_domain(domain)


class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "head", "blockquote", "template"}:
            self.hidden.append(tag)
        elif tag in {"p", "div", "br", "li", "tr"} and not self.hidden:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if self.hidden and tag == self.hidden[-1]:
            self.hidden.pop()

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


@dataclass(frozen=True)
class Evidence:
    provider_id: str | None
    sender_domain: str
    registered_email: str | None
    signal: str
    score: int
    fingerprint: str
    date: str | None
    source: str
    caveat: str | None = None
    features: tuple[str, ...] = ()


def _addresses(message, fields):
    values = [str(v)[:4096] for name in fields for v in message.get_all(name, [])]
    result = set()
    for _, address in getaddresses(values):
        try:
            result.add(normalize_email(address))
        except ValueError:
            continue
    return result


def _body(message):
    plain, html = [], []
    # Do not descend into attached or forwarded RFC822 messages.
    stack = [message]
    parts_seen = 0
    while stack and parts_seen < 100:
        part = stack.pop()
        parts_seen += 1
        if part.get_content_disposition() == "attachment" or part.get_content_type() == "message/rfc822":
            continue
        if part.is_multipart():
            stack.extend(reversed(part.get_payload()))
            continue
        kind = part.get_content_type()
        if kind not in {"text/plain", "text/html"}:
            continue
        payload = part.get_payload(decode=True) or b""
        charset = part.get_content_charset() or "utf-8"
        try:
            content = payload[:MAX_TEXT * 4].decode(charset, errors="replace")[:MAX_TEXT]
        except LookupError:
            content = payload[:MAX_TEXT].decode("utf-8", errors="replace")
        (plain if kind == "text/plain" else html).append(content)
    if plain:
        content = " ".join(plain)[:MAX_TEXT]
    else:
        parser = PlainHTML()
        parser.feed(" ".join(html)[:MAX_TEXT])
        content = " ".join(parser.parts)[:MAX_TEXT]
    # Quoted replies are not fresh evidence.
    content = " ".join(line for line in content.splitlines() if not line.lstrip().startswith(">"))
    return content


def analyze(raw: bytes, registry: Registry, own_emails: list[str], source="eml") -> Evidence | None:
    if not raw or len(raw) > MAX_MESSAGE_BYTES:
        return None
    message = BytesParser(policy=policy.default).parsebytes(raw)
    # A conflicting/duplicated From is too ambiguous to assign a provider.
    if len(message.get_all("From", [])) != 1:
        return None
    senders = _addresses(message, ["From"])
    if len(senders) != 1:
        return None
    sender = next(iter(senders))
    targets = {normalize_email(x) for x in own_emails}
    if sender in targets:
        return None
    direct = _addresses(message, ["To"]) & targets
    delivered = _addresses(message, ["Delivered-To", "X-Original-To", "Envelope-To", "Cc"]) & targets
    if not direct and not delivered:
        return None
    domain = sender.rsplit("@", 1)[1]
    provider = registry.match(domain)
    subject = str(message.get("Subject", ""))[:2048]
    body = _body(message)
    subject_text = re.sub(r"\s+", " ", URL.sub(" ", subject))
    body_text = re.sub(r"\s+", " ", URL.sub(" ", body))
    # Separate subject and body: unrelated text must not form a new rule match.
    text = subject_text + "\n" + body_text
    marketing = bool(message.get("List-Unsubscribe") or message.get("List-Id") or PROMOTION.search(text))
    signal, score = "newsletter", 0
    features = set()
    for candidate, strength, pattern in PATTERNS:
        in_subject = any(not NEGATED.search(match.group(0)) for match in pattern.finditer(subject_text))
        in_body = any(not NEGATED.search(match.group(0)) for match in pattern.finditer(body_text))
        if in_subject or in_body:
            signal, score = candidate, strength
            features.add("matched_subject" if in_subject else "matched_body")
            break
    if message.get("List-Unsubscribe") or message.get("List-Id"):
        features.add("mailing_list_header")
    if PROMOTION.search(text):
        features.add("advertising_words")
    if signal == "newsletter" and not marketing:
        return None
    caveat = None
    # An unsubscribe footer alone is not proof that a transactional mail is advertising.
    if signal in {"welcome_account", "verification_requested", "account_created", "email_verified"}:
        intro = re.split(r"[.!?](?:\s|$)", body_text, maxsplit=1)[0][:700]
        subscription_subject = bool(SUBSCRIPTION.search(subject_text))
        explicit_account_subject = any(name == "account_created" and pattern.search(subject_text) and
                                       re.search(r"account|konto", subject_text, re.I)
                                       for name, _, pattern in PATTERNS)
        subscription = subscription_subject or (bool(SUBSCRIPTION.search(intro)) and not explicit_account_subject)
        context = bool(ACCOUNT_CONTEXT.search(subject_text) or ACCOUNT_CONTEXT.search(body_text[:700]))
        advertising = bool(message.get("List-Id") or AD_OFFER.search(subject_text + " " + body_text[:700]))
        if subscription or (advertising and signal in {"welcome_account", "verification_requested"}):
            signal, score = "newsletter", 0
            if subscription:
                features.add("subscription_wording")
        elif marketing and signal == "welcome_account" and not context:
            score = 35
            caveat = "Generic welcome with advertising indicators; review manually"
            features.add("generic_welcome")
    forwarded = bool(FORWARDED.search(subject) or FORWARDED.search(body) or
                     any(message.get(name) for name in ("Resent-From", "Resent-To")))
    if forwarded:
        features.add("forwarded")
    features.add("multiple_recipients" if len(direct) > 1 else "recipient_to" if direct else "recipient_indirect")
    if forwarded or len(direct) != 1:
        score = min(score, 35)
        ambiguity = "Multiple own recipients; sign-in address uncertain" if len(direct) > 1 else "Forwarding / recipient association uncertain"
        caveat = caveat + "; " + ambiguity if caveat else ambiguity
    if message.get(HEADERS_ONLY_MARKER.decode("ascii")):
        features.add("headers_only")
        score = min(score, 70)
        header_note = "Only headers analyzed (message exceeds size limit)"
        caveat = caveat + "; " + header_note if caveat else header_note
    # An unknown domain cannot be called an official provider.
    if provider is None:
        if score < 60:
            return None
        caveat = "Provider domain not in the catalog; review manually"
    features.add("catalog_domain" if provider else "unknown_domain")
    date = None
    try:
        parsed = parsedate_to_datetime(str(message.get("Date", "")))
        if parsed:
            date = parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        pass
    return Evidence(provider.id if provider else None, domain,
                    next(iter(direct)) if len(direct) == 1 and not forwarded and provider and score >= 60 else None,
                    signal, score, sha256(raw).hexdigest(), date, source, caveat, tuple(sorted(features)))
