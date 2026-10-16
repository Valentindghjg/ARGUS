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

    def public(self) -> dict:
        return asdict(self)


class Registry:
    def __init__(self, custom: Path | None = None):
        rows = json.loads(CATALOG.read_text(encoding="utf-8"))["providers"]
        if custom:
            extra = json.loads(custom.read_text(encoding="utf-8"))
            rows += extra["providers"] if isinstance(extra, dict) else extra
        self.providers: dict[str, Provider] = {}
        owners: dict[str, str] = {}
        for row in rows:
            domains = tuple(normalize_domain(d) for d in row["domains"])
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
            source, verified = row.get("password_source"), row.get("password_verified")
            if password_url:
                validate_url(password_url, domains)
                if not source or not verified or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", verified):
                    raise ValueError("A password link requires documented verification")
                validate_url(source, domains)
            if row.get("priority", "normal") not in {"critical", "high", "normal"}:
                raise ValueError("Invalid priority")
            self.providers[row["id"]] = Provider(
                row["id"], row["name"], website, row["category"], domains,
                row.get("priority", "normal"), password_url, source, verified,
                bool(row.get("historical", False)),
            )
        self._domains = sorted(owners, key=len, reverse=True)
        self._owners = owners

    def match(self, domain: str) -> Provider | None:
        try:
            domain = normalize_domain(domain)
        except ValueError:
            return None
        for root in self._domains:
            if is_subdomain(domain, root):
                return self.providers[self._owners[root]]
        return None
