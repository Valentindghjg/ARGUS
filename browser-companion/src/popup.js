"use strict";

const byId = (id) => document.getElementById(id);
const state = byId("state");
const details = byId("details");
const providerName = byId("provider");
const domainName = byId("domain");
const passwordNote = byId("password-note");
const actions = byId("actions");
let passwordUrl = null;

function hostMatches(host, root) {
  return host === root || host.endsWith(`.${root}`);
}

// The most specific catalogue domain wins, independent of bundle order.
function bestMatch(providers, host) {
  let best = null;
  for (const provider of providers) {
    for (const root of provider.domains) {
      if (hostMatches(host, root) && (!best || root.length > best.root.length)) best = {provider, root};
    }
  }
  return best;
}

function showUnknown(message) {
  state.textContent = message;
  details.hidden = true;
  passwordNote.hidden = true;
  actions.hidden = true;
}

async function activeUrl() {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  return typeof tab?.url === "string" ? tab.url : null;
}

async function inspectActiveTab() {
  let url;
  try {
    url = await activeUrl();
  } catch {
    showUnknown("ARGUS could not read the active tab URL.");
    return;
  }
  if (!url) {
    showUnknown("No active tab URL is available.");
    return;
  }
  let host;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:") {
      showUnknown("This tab does not use an HTTPS website URL. ARGUS only labels HTTPS pages.");
      return;
    }
    host = parsed.hostname.toLowerCase().replace(/\.$/, "");
  } catch {
    showUnknown("This tab does not use a website URL.");
    return;
  }
  const response = await fetch(chrome.runtime.getURL("providers.json"));
  const providers = await response.json();
  const found = bestMatch(providers, host);
  if (!found) {
    showUnknown("This domain is not in the bundled ARGUS provider catalogue. This says nothing about whether an account exists.");
    return;
  }
  const match = found.provider;
  // Many services let anyone publish on their subdomains (blogs, shops, forms).
  // Only the catalogue domain itself or its www host is labelled as official.
  const exact = host === found.root || host === `www.${found.root}`;
  state.textContent = exact
    ? "Official ARGUS provider domain"
    : "Subdomain of an ARGUS catalogue domain. Other people may publish pages here; check the address yourself.";
  providerName.textContent = match.name;
  domainName.textContent = found.root;
  details.hidden = false;
  passwordUrl = typeof match.password_url === "string" ? match.password_url : null;
  if (!passwordUrl) {
    passwordNote.textContent = "ARGUS has no verified password-management link for this provider. Do not guess one.";
    passwordNote.hidden = false;
    actions.hidden = true;
    return;
  }
  passwordNote.textContent = "A documented password-management link is available. Opening it does not change anything automatically.";
  passwordNote.hidden = false;
  actions.hidden = false;
}

byId("copy").addEventListener("click", async () => {
  if (!passwordUrl) return;
  try {
    await navigator.clipboard.writeText(passwordUrl);
    byId("copy").textContent = "Copied";
  } catch {
    state.textContent = "The browser blocked copying. You can open the verified link instead.";
  }
});

byId("open").addEventListener("click", () => {
  if (passwordUrl) chrome.tabs.create({url: passwordUrl});
});

inspectActiveTab().catch(() => showUnknown("The local catalogue could not be read."));
