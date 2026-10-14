"""Local presentation translations. Machine identifiers and stored evidence stay stable."""
import argparse
from functools import lru_cache
import json
import locale
from pathlib import Path
import sys


@lru_cache(maxsize=1)
def catalog():
    return json.loads((Path(__file__).with_name("data") / "translations.json").read_text(encoding="utf-8"))


def validate_language(language):
    if language not in {"en", "de"}:
        raise ValueError("Unsupported language; choose en or de")
    return language


def translate(message, language="en", **values):
    validate_language(language)
    if message is None:
        return None
    text = catalog()["de"].get(message, message) if language == "de" else message
    # Composite caveats are program-generated labels, never raw message content.
    if language == "de" and text == message and "; " in message:
        from .analysis import LEGACY_CAVEATS
        for caveat in sorted(LEGACY_CAVEATS.values(), key=len, reverse=True):
            text = text.replace(caveat, catalog()["de"].get(caveat, caveat))
    if language == "de" and text == message and message.startswith("Ambiguous domain in the catalog: "):
        text = "Mehrdeutige Domain im Katalog: " + message.split(": ", 1)[1]
    return text.format(**values) if values else text


def cli_language(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    # Pre-read the global flag so even --help and parser errors use its language.
    for index, argument in reversed(list(enumerate(arguments))):
        if argument.startswith("--language="):
            return argument.partition("=")[2] if argument.partition("=")[2] in {"en", "de"} else "en"
        if argument == "--language" and index + 1 < len(arguments):
            return arguments[index + 1] if arguments[index + 1] in {"en", "de"} else "en"
    try:
        system_language = locale.getlocale()[0] or "en"
    except (ValueError, TypeError):
        system_language = "en"
    return "de" if system_language.lower().startswith("de") else "en"


class LocalizedArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, language="en", **kwargs):
        self.language = language
        super().__init__(*args, **kwargs)

    def add_subparsers(self, **kwargs):
        kwargs.setdefault("parser_class", lambda **options: LocalizedArgumentParser(language=self.language, **options))
        return super().add_subparsers(**kwargs)

    def _headings(self, text):
        if self.language == "de":
            for english, german in [("usage:", "Aufruf:"), ("positional arguments:", "Positionsargumente:"), ("options:", "Optionen:"), ("show this help message and exit", "Diese Hilfe anzeigen und beenden")]:
                text = text.replace(english, german)
        return text

    def format_help(self):
        return self._headings(super().format_help())

    def format_usage(self):
        return self._headings(super().format_usage())

    def error(self, message):
        if self.language == "de":
            self.print_usage(sys.stderr)
            self.exit(2, translate("Invalid command or arguments. Use --help for available options.", "de") + "\n")
        super().error(message)


def localize_snapshot(snapshot, language="en"):
    validate_language(language)
    for account in snapshot["accounts"]:
        account["category_label"] = translate(account["category"], language)
        for field in ["reason", "confidence"]:
            account[field] = translate(account[field], language)
        for evidence in account["evidence"]:
            evidence["reason"] = translate(evidence["reason"], language)
            evidence["caveat"] = translate(evidence["caveat"], language)
    for candidate in snapshot["candidates"]:
        candidate["reason"] = translate(candidate["reason"], language)
        for evidence in candidate["evidence"]:
            evidence["reason"] = translate(evidence["reason"], language)
            evidence["caveat"] = translate(evidence["caveat"], language)
    return snapshot


def localize_discovery(result, language="en"):
    """Translate explanatory strings, keeping hosts, addresses, IDs and JSON keys."""
    validate_language(language)
    def visit(value):
        if isinstance(value, list):
            return [visit(item) for item in value]
        if isinstance(value, dict):
            return {key: translate(item, language) if key in {"note", "warning"} and isinstance(item, str) else visit(item)
                    for key, item in value.items()}
        return value
    return visit(result)
