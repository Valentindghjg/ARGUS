"""Forward the old entry point to ARGUS with a one-line deprecation notice."""
import sys

from argus_security.cli import main as argus_main
from argus_security.i18n import cli_language, translate


def main(argv=None):
    print(translate("account-finder / account_finder is deprecated; use the argus command or python -m argus_security.",
                    cli_language(argv)), file=sys.stderr)
    return argus_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
