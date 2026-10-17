# A complete demo in five steps

[Deutsch](DEMO_DE.md)

The demo shows the whole path from import to the Bitwarden handover with 18
invented emails for two invented addresses. It never touches your profile,
mailbox or vault, and it never connects to the internet.

```bash
python -m argus_security --data-dir .local/demo demo --serve --open
```

The demo needs its own folder; ARGUS refuses to load it into a profile that has
your own addresses. The overview then shows "What this demo shows" with the
hard cases and a "Try this path" list. Each entry opens the matching view.

1. **What's new.** Everything the import found is new: which providers have
   clues, which are confirmed and what to look at first. "Mark as reviewed"
   moves the marker; the next import shows only what changed since then.
2. **Unclear items.** Here is everything ARGUS cannot decide for you: clues from
   Amazon (guest order), eBay (password reset) and Zalando (newsletter) without
   an account, a domain outside the catalog (`new-service.example`) and the
   look-alike `github.com.attacker.example`, which is not treated as GitHub.
3. **Security worklist.** PayPal is already reviewed. Its next step is to save
   the login in Bitwarden; the checklist explains why and what counts as done.
   GitHub is complete, with one account for each own address; Notion signs in
   with single sign-on and has no separate password step.
4. **Prepare Bitwarden.** Preview the handover for the accounts you choose. The
   JSON file holds names, sign-in addresses and links, never passwords. Nothing
   is written to a vault until you confirm a step with the Bitwarden CLI.
5. **Progress report.** Back on the overview, preview a report with numbers only
   or with one line per task. Sign-in addresses appear only if you add them.

Remove the demo by deleting `.local/demo`. To start with your own emails, use
another folder or the default profile; see the README section
"Your personal profile".
