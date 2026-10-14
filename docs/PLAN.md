# Technical plan

1. **Local detection and dashboard first:** Python 3.11+, standard library,
   extensible provider JSON, deterministic MIME analysis, SQLite, responsive local
   dashboard and a separate synthetic demo.
2. **Then mailbox ingestion:** EML/Maildir/mbox import and TLS IMAP with certificate
   verification, EXAMINE/read-only and bounded BODY.PEEK. App passwords or short-lived
   OAuth2 tokens are entered only in a hidden terminal prompt, never stored.
3. **Setup:** explicitly authorized MX lookup of the mail domain only. MX identifies
   the receiving route, not necessarily the actual IMAP host. Verify settings with
   the provider before authorizing a connection; never try guessed host lists.
4. **Evidence assessment:** label-boundary sender matching, own-recipient checks,
   local HTML parsing without downloads, attachment/forwarding limits, separate
   account events and weak marketing/guest/reset clues. Only personal review can
   mark an account Confirmed; email evidence reaches at most Probable.
5. **Bitwarden:** official metadata-only JSON with empty password fields and null
   TOTP. Explicit account selection and separate import folder, excluding assigned
   entries. No vault access or password generation by this app. The user creates
   passwords in Bitwarden and changes them directly at providers.
6. **Privacy:** no outgoing network by default; dashboard only on 127.0.0.1 with
   a memory-only bearer token, Host/Origin checks, CSP and no external assets.
   Minimal evidence metadata instead of message bodies. Private local directories
   and files; use drive encryption and protected backups.
7. **Validation:** synthetic regression tests for false positives, spoofing, MIME,
   deduplication, status, read-only IMAP, errors, export format and HTTP protections,
   plus browser interaction checks and an extracted-archive demo.
8. **Version 1.1:** durable multi-file scan sessions, cancellation and limit/gap
   reporting; safe alias additions, versioned evidence and atomic reclassification.
9. **Version 1.2:** English interface, CLI, messages, categories, notes, examples and
   docs. Preserve bilingual detection, stable IDs and existing data. Display legacy
   German explanations in English without rewriting the underlying stored values.

No service passwords are changed, no online accounts are created, and missing
email clues never prove absence. Historical clues do not prove a currently active
account. The app is designed for a trusted user's own computer.

## Bilingual presentation (1.3)

Use a shared bundled translation catalog; browser and CLI language selection
remain independent of email detection. Keep machine identifiers and persisted
evidence stable. Verify state preservation, metadata safety, language fallback
and mobile layout with artificial data. Provide complete German and English guides.
