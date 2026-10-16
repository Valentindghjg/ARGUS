// SPDX-License-Identifier: MPL-2.0
// Copyright (c) 2026 ARGUS contributors
"use strict";

const byId = (id) => document.getElementById(id);
const state = byId("state");
const details = byId("details");
const providerName = byId("provider");
const domainName = byId("domain");
const passwordNote = byId("password-note");
const actions = byId("actions");
let passwordUrl = null;

// Messages come from _locales/<browser language>/messages.json (English fallback).
function message(key) {
  return chrome.i18n.getMessage(key) || key;
}

function localizePage() {
  document.documentElement.lang = chrome.i18n.getUILanguage().toLowerCase().startsWith("de") ? "de" : "en";
  for (const element of document.querySelectorAll("[data-i18n]")) {
    element.textContent = message(element.dataset.i18n);
  }
}

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

function showUnknown(key) {
  state.textContent = message(key);
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
    showUnknown("tabUnreadable");
    return;
  }
  if (!url) {
    showUnknown("noUrl");
    return;
  }
  let host;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:") {
      showUnknown("notHttps");
      return;
    }
    host = parsed.hostname.toLowerCase().replace(/\.$/, "");
  } catch {
    showUnknown("notWebsite");
    return;
  }
  const response = await fetch(chrome.runtime.getURL("providers.json"));
  const providers = await response.json();
  const found = bestMatch(providers, host);
  if (!found) {
    showUnknown("notInCatalogue");
    return;
  }
  const match = found.provider;
  // Many services let anyone publish on their subdomains (blogs, shops, forms).
  // Only the catalogue domain itself or its www host is labelled as official.
  const exact = host === found.root || host === `www.${found.root}`;
  state.textContent = message(exact ? "official" : "subdomain");
  providerName.textContent = match.name;
  domainName.textContent = found.root;
  details.hidden = false;
  passwordUrl = typeof match.password_url === "string" ? match.password_url : null;
  if (!passwordUrl) {
    passwordNote.textContent = message("noPasswordLink");
    passwordNote.hidden = false;
    actions.hidden = true;
    return;
  }
  passwordNote.textContent = message("passwordLinkAvailable");
  passwordNote.hidden = false;
  actions.hidden = false;
}

byId("copy").addEventListener("click", async () => {
  if (!passwordUrl) return;
  try {
    await navigator.clipboard.writeText(passwordUrl);
    byId("copy").textContent = message("copied");
  } catch {
    state.textContent = message("copyBlocked");
  }
});

byId("open").addEventListener("click", () => {
  if (passwordUrl) chrome.tabs.create({url: passwordUrl});
});

localizePage();
inspectActiveTab().catch(() => showUnknown("catalogueUnreadable"));
