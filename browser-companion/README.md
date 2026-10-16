# ARGUS Browser Companion (prototype)

This is an intentionally small, unpacked Chromium extension. It gives the user a
safe way to check whether the **currently active tab** belongs to an official
domain in ARGUS's provider catalogue. It is a navigation helper, not an account
detector.

It never reads page content, forms, browser history, cookies, passwords, session
tokens, downloads, or Bitwarden data. Opening a site in a tab does **not** add,
confirm, or change an account in ARGUS. The extension has no host permissions,
no content scripts, no service worker, no network access, and no native-messaging
host.

## Build and load locally

Run these commands from the repository root with Python 3.11 or newer:

```bash
python browser-companion/scripts/build.py
python browser-companion/tests/validate.py
```

`validate.py` also runs `popup.js` under Node.js with simulated browser APIs
for typical and hostile addresses (lookalike domains, third-party subdomains,
`http:`, `file:` and browser pages) in English and German.

The popup follows the browser language: German text comes from
`_locales/de/messages.json`, everything else falls back to English.

The build creates `browser-companion/dist/`. It contains an independent,
unpacked extension and a reduced copy of the existing public provider catalogue.
The directory is intentionally ignored by Git because it is reproducible.
The build refuses to overwrite an existing directory; remove an earlier generated
`dist/` yourself before rebuilding it.

In Chromium, Chrome, Edge, Brave, or Vivaldi:

1. Open `chrome://extensions` (Edge: `edge://extensions`).
2. Enable **Developer mode**.
3. Choose **Load unpacked**.
4. Select `browser-companion/dist`.
5. Pin the ARGUS Browser Companion and open it while a website is the active tab.

The popup shows one of these local decisions:

| Result | Meaning |
| --- | --- |
| Official ARGUS provider domain | The current HTTPS host is a bundled catalogue domain itself or its `www.` host. |
| Subdomain of an ARGUS catalogue domain | The host is below a catalogue domain (for example a blog or shop subdomain). Other people may publish there, so ARGUS does not call it official; check the address yourself. |
| Not an HTTPS website URL | Plain `http:`, local files and browser pages are never labelled. |
| Known password-management link | ARGUS has a documented, verified password-management URL for that provider. The user can copy it or open it in a new tab. |
| No verified password-management link | Do not guess a settings URL. Use the provider's official help site after manually checking the account. |
| Not in the catalogue | No conclusion about whether an account exists. |

The URL is only read after the user opens the extension popup, through the
minimal `activeTab` browser permission. It stays inside the popup process and is
not stored, sent, logged, or passed to ARGUS. The catalogue is bundled during the
local build; the extension makes no requests to ARGUS, a provider, or any other
server.

## Scope and safety boundary

The prototype does not communicate with the local ARGUS dashboard. That is
deliberate: a website visit is weak evidence and must not become an account
record. It also never drives a password-change workflow, clicks provider pages,
fills forms, initiates password resets, or interacts with Bitwarden.

Only URLs already validated by the main ARGUS catalogue are copied into the
bundle: the build loads the catalogue through the application's own `Registry`
validation instead of a second implementation. The build excludes every catalogue field except provider ID, name,
official website, allowed domains, and an already verified password-management
URL. A link is enabled only when that URL is present in the bundle.

## Future local bridge, not implemented

If a later version needs a local dashboard integration, it should use a separate
opt-in native-messaging host installed by the user for one specific browser
extension ID. The host should accept a fixed schema such as an explicit
`open_provider` request, bind only to the loopback ARGUS service, require its
existing local dashboard token, and reject arbitrary URLs or commands. Its
installer, browser-specific registration, update path, signing, revocation, and
uninstall flow must be reviewed before shipping.

No extension should receive mail credentials, Bitwarden sessions, vault data,
browser cookies, or page content. It must not assert that a visit proves an
account exists. A native host is therefore outside this prototype and requires a
separate security review and user consent.
