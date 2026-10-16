// SPDX-License-Identifier: MPL-2.0
// Copyright (c) 2026 ARGUS contributors
// Runs popup.js in a sandbox with simulated chrome.* APIs (no browser, no network).
// Usage: node popup_harness.js <extension-dir> <language> <url>...  -> JSON results
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const [directory, language, ...urls] = process.argv.slice(2);
const script = fs.readFileSync(path.join(directory, "popup.js"), "utf8");
const providers = JSON.parse(fs.readFileSync(path.join(directory, "providers.json"), "utf8"));
const messages = JSON.parse(fs.readFileSync(path.join(directory, "_locales", language, "messages.json"), "utf8"));

function element(key) {
  return {textContent: "", hidden: false, dataset: key ? {i18n: key} : {}, addEventListener() {}};
}

async function inspect(url) {
  const ids = {};
  const translated = ["eyebrow", "heading", "notice"].map(element);
  const sandbox = {
    document: {
      documentElement: {lang: ""},
      getElementById: (id) => (ids[id] = ids[id] || element()),
      querySelectorAll: () => translated,
    },
    URL,
    navigator: {clipboard: {writeText: async () => {}}},
    fetch: async () => ({json: async () => providers}),
    chrome: {
      tabs: {query: async () => [{url}], create() {}},
      runtime: {getURL: (name) => name},
      i18n: {getMessage: (key) => (messages[key] || {}).message || "", getUILanguage: () => language},
    },
  };
  vm.runInNewContext(script, sandbox);
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));
  return {url, lang: sandbox.document.documentElement.lang, state: ids.state.textContent,
          details: !ids.details.hidden, domain: ids.domain.textContent, provider: ids.provider.textContent,
          actions: !ids.actions.hidden, heading: translated[1].textContent};
}

(async () => {
  const results = [];
  for (const url of urls) results.push(await inspect(url));
  process.stdout.write(JSON.stringify(results));
})();
