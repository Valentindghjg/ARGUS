# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Errors whose fixed message may be shown to the user (CLI or dashboard)."""


class UserFacingError(ValueError):
    """A constant, translatable explanation that is safe to display.

    Never build the message from user data, paths, server text or secrets: the
    dashboard returns it verbatim and translates it locally. Other ValueErrors
    stay behind a generic message.
    """
