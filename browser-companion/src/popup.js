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
    host = new URL(url).hostname.toLowerCase().replace(/\.$/, "");
  } catch {
    showUnknown("This tab does not use a website URL.");
    return;
  }
  const response = await fetch(chrome.runtime.getURL("providers.json"));
  const providers = await response.json();
  const match = providers.find((provider) => provider.domains.some((root) => hostMatches(host, root)));
  if (!match) {
    showUnknown("This domain is not in the bundled ARGUS provider catalogue. This says nothing about whether an account exists.");
    return;
  }
  state.textContent = "Official ARGUS provider domain";
  providerName.textContent = match.name;
  domainName.textContent = host;
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
