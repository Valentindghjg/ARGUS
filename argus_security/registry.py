# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Extensible, strictly validated provider catalogue; never follows email links."""
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from .errors import UserFacingError

CATALOG = Path(__file__).with_name("data") / "providers.json"


def normalize_domain(value: str) -> str:
    value = value.strip().rstrip(".").lower()
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError:
        raise UserFacingError("Invalid domain") from None
    if len(value) > 253 or "." not in value or any(
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in value.split(".")
    ):
        raise UserFacingError("Invalid domain")
    return value


def is_subdomain(host: str, root: str) -> bool:
    return host == root or host.endswith("." + root)


# Delivery infrastructure that sends mail for many companies (plan E5). Such a
# sender domain never identifies a provider and cannot enter any catalog.
SHARED_SENDERS = (
    "amazonses.com", "sendgrid.net", "mailgun.org", "mcsv.net", "mcdlv.net", "rsgsv.net",
    "list-manage.com", "mandrillapp.com", "sparkpostmail.com", "exct.net", "hubspotemail.net",
    "cmail19.com", "cmail20.com", "bnc3.mailjet.com",
)


def is_shared_sender(domain: str) -> bool:
    try:
        domain = normalize_domain(domain)
    except ValueError:
        return False
    return any(is_subdomain(domain, shared) or is_subdomain(shared, domain) for shared in SHARED_SENDERS)


def validate_url(value: str, domains: tuple[str, ...]) -> str:
    parts = urlsplit(value)
    if (parts.scheme != "https" or not parts.hostname or parts.username or
            parts.password or parts.port not in (None, 443) or parts.fragment):
        raise ValueError("Provider links must be valid HTTPS URLs")
    if not any(is_subdomain(normalize_domain(parts.hostname), d) for d in domains):
        raise ValueError("The link is outside the provider domains")
    return value


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    website: str
    category: str
    domains: tuple[str, ...]
    priority: str = "normal"
    password_url: str | None = None
    password_source: str | None = None
    password_verified: str | None = None
    historical: bool = False
    # "builtin", "extra" (--providers file) or "personal" (added in this profile).
    source: str = "builtin"

    def public(self) -> dict:
        return asdict(self)


def _rows(path: Path, source: str):
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["providers"] if isinstance(data, dict) else data
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Invalid provider entry")
    return [(row, source) for row in rows]


class Registry:
    def __init__(self, custom: Path | None = None, personal: Path | None = None):
        self.custom, self.personal = custom, personal
        rows = _rows(CATALOG, "builtin")
        if custom:
            rows += _rows(custom, "extra")
        if personal and personal.is_file() and not personal.is_symlink():
            rows += _rows(personal, "personal")
        self.providers: dict[str, Provider] = {}
        owners: dict[str, str] = {}
        for row, source in rows:
            domains = tuple(normalize_domain(d) for d in row["domains"])
            if any(is_shared_sender(domain) for domain in domains):
                raise ValueError("A shared sending service cannot identify a provider")
            if not domains or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", row["id"]):
                raise ValueError("Invalid provider entry")
            if row["id"] in self.providers:
                raise ValueError("Duplicate provider ID")
            if not isinstance(row["name"], str) or not 1 <= len(row["name"]) <= 100:
                raise ValueError("Invalid provider name")
            if not isinstance(row["category"], str) or not 1 <= len(row["category"]) <= 60:
                raise ValueError("Invalid category")
            for domain in domains:
                if domain in owners:
                    raise ValueError("Ambiguous domain in the catalog: " + domain)
                owners[domain] = row["id"]
            website = validate_url(row["website"], domains)
            password_url = row.get("password_url")
            source_url, verified = row.get("password_source"), row.get("password_verified")
            if password_url:
                validate_url(password_url, domains)
                if not source_url or not verified or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", verified):
                    raise ValueError("A password link requires documented verification")
                validate_url(source_url, domains)
            if row.get("priority", "normal") not in {"critical", "high", "normal"}:
                raise ValueError("Invalid priority")
            self.providers[row["id"]] = Provider(
                row["id"], row["name"], website, row["category"], domains,
                row.get("priority", "normal"), password_url, source_url, verified,
                bool(row.get("historical", False)), source,
            )
        self._domains = sorted(owners, key=len, reverse=True)
        self._owners = owners

    def with_personal(self, path: Path):
        """This catalog plus the profile's own providers (plan E5), as a new registry."""
        if path == self.personal or not path.is_file():
            return self
        return Registry(self.custom, path)

    def match(self, domain: str) -> Provider | None:
        try:
            domain = normalize_domain(domain)
        except ValueError:
            return None
        for root in self._domains:
            if is_subdomain(domain, root):
                return self.providers[self._owners[root]]
        return None
