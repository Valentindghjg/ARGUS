// SPDX-License-Identifier: MPL-2.0
// Copyright (c) 2026 ARGUS contributors
"use strict";
const $ = id => document.getElementById(id);
let language;
// "account-finder.language" is the pre-rename key; it is read once and replaced.
try { language=localStorage.getItem("argus.language")||localStorage.getItem("account-finder.language"); } catch (_) {}
if(!["en","de"].includes(language))language=(navigator.language||"en").toLowerCase().startsWith("de")?"de":"en";
const translations=window.AF_TRANSLATIONS.de;
const translationSpacing=new WeakMap();
function t(message,values={}) {
  const text=language==="de"&&Object.hasOwn(translations,message)?translations[message]:message;
  return String(text).replace(/\{([a-zA-Z0-9_]+)\}/g,(match,key)=>Object.hasOwn(values,key)?String(values[key]):match);
}
function translateCaveat(value){
  for(const key of ["Generic welcome with advertising indicators; review manually","Multiple own recipients; sign-in address uncertain","Forwarding / recipient association uncertain","Only headers analyzed (message exceeds size limit)","Provider domain not in the catalog; review manually"]){value=value.replaceAll(key,t(key));}
  return value;
}
function setMessage(id,key){$(id).dataset.i18n=key;$(id).textContent=t(key);}
function canonicalMessage(message){return Object.keys(translations).find(key=>translations[key]===message)||message;}
function applyLanguage(next,remember=false){
  if(!["en","de"].includes(next))return;
  language=next;
  if(remember){try{localStorage.setItem("argus.language",language);localStorage.removeItem("account-finder.language");}catch(_){}}
  document.documentElement.lang=language;
  document.querySelectorAll("[data-i18n]").forEach(e=>{
    if(!translationSpacing.has(e))translationSpacing.set(e,[e.textContent.match(/^\s*/)[0],e.textContent.match(/\s*$/)[0]]);
    const [before,after]=translationSpacing.get(e);e.textContent=before+t(e.dataset.i18n)+after;
  });
  for(const attribute of ["aria-label","placeholder"]){
    document.querySelectorAll(`[data-i18n-${attribute}]`).forEach(e=>e.setAttribute(attribute,t(e.getAttribute(`data-i18n-${attribute}`))));
  }
  document.querySelectorAll(".language-control").forEach(e=>e.value=language);
  const scan=displayedScan;
  if(state){renderState();navigate(view,false);if($("account-dialog").open)renderDetail();if($("export-preview").open)renderPreview();}
  if(scan){renderScan(scan);if(!$("import-progress").classList.contains("hidden"))$("import-status").textContent=scan.running&&importCancelled?t("Stopping after the current file. Saved clues are preserved."):scanDescription(scan);}
}
const token = document.querySelector('meta[name="af-token"]').content;
document.querySelector('meta[name="af-token"]').remove();
let state, view = "dashboard", selected = null, saving = false;
let activeBatch=null, importCancelled=false, addingAlias=false, addingAccount=false;
let displayedScan=null;
const exportChoices=new Map();
const worklistChoices=new Map();
let bitwardenAudit=null;
let workflowBusy=false, bitwardenBusy=false;
const workflowSteps={identify:"Identify this account before preparing Bitwarden.",review:"Review this account and confirm it exists.",identity:"Check how you sign in to this account.",bitwarden:"Assign an existing Bitwarden item or prepare a missing one.",change_password:"Use Bitwarden to set a unique password at the provider.",test_signin:"Test the sign-in before completing this account.",mfa:"Review multi-factor authentication and recovery, then complete this step.",done:"This account is complete."};
// The server derives the next step from the account's own steps (ADR-0001).
function accountStep(account){return account.next_step;}
const labels = {confirmed:"Confirmed",probable:"Probable",unknown:"Unknown",critical:"Do first",high:"High",normal:"Normal"};
// Three separate marks (plan D2): evidence (automatic), decision (yours), progress (your steps).
const evidenceLabels={none:"No evidence",weak:"Weak evidence",probable:"Probable",stale:"Older evidence"};
const decisionLabels={undecided:"Open",confirmed:"Confirmed by you",rejected:"Rejected"};
const reasonLabels={not_mine:"Not mine",not_an_account:"Not an account",closed:"Closed"};
const progressLabels={not_started:"Not started",in_progress:"In progress",complete:"Complete"};
const STEP_ORDER=["identity","vault","password","signin_test","mfa_recovery"];
const stepTitles={
  identity:["I checked how I sign in to this account","The sign-in address or username is right and belongs to me."],
  vault:["Stored in Bitwarden","Use an existing item or save a new one directly in Bitwarden, with the password."],
  password:["Unique password set at the provider","Generate it in Bitwarden and change it yourself at the provider. Never enter it here."],
  signin_test:["Sign-in tested","Sign in successfully using the new password, passkey or central identity provider."],
  mfa_recovery:["MFA and recovery reviewed","Enable multi-factor authentication if available and store recovery codes securely."]
};
const stepNames={identity:"Sign-in checked",vault:"Stored in Bitwarden",password:"Unique password",signin_test:"Sign-in tested",mfa_recovery:"MFA and recovery"};
const stateLabels={open:"open",done:"done",not_applicable:"not applicable",prepared:"prepared"};
const titles = {
  dashboard:["Your accounts, in one place.","Find local evidence and secure your accounts with Bitwarden.","Overview"],
  accounts:["Your digital inventory.","Review your clues and keep unknown services in view.","All accounts"],
  security:["Secure the most important accounts first.","Prioritize your mailbox, finance and central services.","Security priorities"],
  bitwarden:["One unique password per account, kept in Bitwarden.","Prepare new vault items and make the changes yourself.","Prepare Bitwarden"],
  workflow:["Secure your accounts, one at a time.","A local worklist that remembers your progress.","Security worklist"],
  setup:["Start with your mailbox.","Import existing messages or set up read-only IMAP access.","Mailbox & Import"]
};
function node(tag, text, className) { const e=document.createElement(tag); if(text!==undefined)e.textContent=text; if(className)e.className=className; return e; }
function accountEmail(account){return account.identity_email||account.manual_email||account.registered_emails[0]||"";}
function accountTitle(account){
  const identity=[account.label,accountEmail(account)].filter(Boolean);
  if(!identity.length&&state.accounts.filter(a=>(a.provider_id||a.id)===(account.provider_id||account.id)).length>1)identity.push(t("Address not assigned"));
  return [account.name,...identity].join(" · ");
}
function reviewTitle(account){
  return state.accounts.some(a=>a.id!==account.id&&(a.provider_id||a.id)===(account.provider_id||account.id))?accountTitle(account):account.name;
}
// A problem is a constant message plus, when known, a constant next step (plan F4).
function problem(id,message,hint){
  const box=$(id),text=node("span");text.dataset.i18n=canonicalMessage(message);text.textContent=t(text.dataset.i18n);
  box.replaceChildren(text);
  if(hint){const next=node("span",undefined,"error-hint");next.dataset.i18n=hint;next.textContent=t(hint);box.append(" ",next);}
  box.classList.remove("hidden");
}
function error(message,hint){problem("error",message,hint);}
function failure(e){error(e.message,e.hint);}
let toastTimer=null,toastBatch=null;
// A toast after a local change offers to undo exactly that change (ADR-0001, rule 3).
function toast(message,batch=null){
  // A modal dialog makes the page behind it inert, so the toast moves into it.
  const host=[$("export-preview"),$("account-dialog")].find(dialog=>dialog.open)||document.body;
  if($("toast").parentElement!==host)host.append($("toast"));
  setMessage("toast-text",canonicalMessage(message));toastBatch=batch;
  $("toast-undo").classList.toggle("hidden",!batch);$("toast").classList.remove("hidden");
  clearTimeout(toastTimer);toastTimer=setTimeout(()=>{$("toast").classList.add("hidden");toastBatch=null;},batch?8000:3000);
}
async function undoChange(batch){
  try{await api("/api/undo",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({batch})});await refresh();if($("account-dialog").open)renderDetail();toast(t("Change undone locally."));}
  catch(e){failure(e);}
}
function localFailure(){
  const failed=new Error("Local request failed.");
  failed.hint="Check that the ARGUS terminal is still running, then reload this page.";
  return failed;
}
async function api(path, options={}) {
  const headers={Authorization:`Bearer ${token}`,...(options.headers||{})};
  let response;
  // A stopped local server must not surface the browser's raw network error.
  try{response=await fetch(path,{...options,headers,cache:"no-store",credentials:"omit"});}
  catch(_){throw localFailure();}
  if(!response.ok){
    const result=await response.json().catch(()=>({}));
    if(!result.error)throw localFailure();
    const failed=new Error(result.error);failed.hint=result.hint;throw failed;
  }
  return response.json();
}
let history=[];
async function refresh() {
  const [snapshot,changes]=await Promise.all([api("/api/accounts"),api("/api/changes")]);
  state=snapshot;history=changes.changes;
  renderState();
}
function renderState() {
  const s=state.summary;
  for(const [id,value] of Object.entries({"found-count":s.found,"confirmed-count":s.confirmed,"probable-count":s.probable,"priority-count":s.high_priority,"done-count":s.done,"provider-count":s.providers,"nav-count":s.found,"progress-label":`${s.progress}%`,"progress-caption":t("{p0} of {p1} accounts done",{p0:(s.done),p1:(s.found)})}))$(id).textContent=value;
  $("progress-fill").style.width=`${s.progress}%`;
  $("services-found-caption").textContent=t("{count} services found",{count:s.services_found??new Set(state.accounts.filter(a=>a.classification!=="unknown").map(a=>a.provider_id||a.id)).size});
  $("progress-bar").setAttribute("aria-valuenow",s.progress);
  $("demo-banner").classList.toggle("hidden",!state.demo);$("demo-guide").classList.toggle("hidden",!state.demo);
  $("rescan-banner").classList.toggle("hidden",!state.stale_evidence);
  $("rescan-banner").textContent=t("{p0} older clues need the current detection rules. Re-import the original emails or start an authorized IMAP scan. Your checklists are preserved.",{p0:(state.stale_evidence||0)});
  const previous=$("category").value;
  $("category").replaceChildren(new Option(t("All categories"),""),...Array.from(new Set(state.accounts.map(a=>a.category))).sort().map(c=>new Option(t(c),c)));
  $("category").value=previous;
  $("profile-email").textContent=t("Configured addresses: {p0}",{p0:(state.emails.join(", "))});
  const scheduled=state.background_scan||{};
  let scheduledText;
  if(scheduled.enabled&&!scheduled.target_confirmed) scheduledText=t("Scheduled IMAP scans wait for approval of the current IMAP settings and will not connect. Run background-imap enable in a local terminal.");
  else if(scheduled.enabled) scheduledText=t("Scheduled read-only IMAP scans are enabled. They run only while this local dashboard is open.");
  else if(scheduled.authorized) scheduledText=t("Scheduled IMAP scans are paused. The authorization stays in your OS keyring until you revoke it.");
  else scheduledText=t("Scheduled IMAP scans are disabled. Enable them from a local terminal after configuring IMAP.");
  if(scheduled.last_error) scheduledText+=" "+t(scheduled.last_error);
  if(scheduled.last_error_hint) scheduledText+=" "+t("Next step: ")+t(scheduled.last_error_hint);
  $("background-scan-status").textContent=scheduledText;
  const domain=(state.emails[0]||"").split("@")[1]||"your-domain.example";
  $("discover-command").textContent=`python -m argus_security discover --domain ${domain} --allow-dns`;
  renderScan(state.active_import||state.last_scan);
  $("cancel-import").classList.toggle("hidden",!activeBatch&&!state.active_import);
  $("add-alias-button").disabled=state.demo||addingAlias||Boolean(activeBatch||state.active_import);
  $("alias-email").disabled=state.demo;$("alias-owned").disabled=state.demo;
  if(state.demo)setMessage("alias-message","Add real own addresses in a personal profile on your computer. The demo profile stays separate.");
  renderRows();renderCandidates();renderExport();renderBitwardenAudit();renderWorklist();renderGuided();renderHandoffs();renderHistory();
  renderStart();renderResult();renderNextTask();
}
// Plan F2: three separate ways in, shown until the profile has its first evidence.
function renderStart(){
  $("start-paths").classList.toggle("hidden",Boolean(state.demo||state.result.clues||state.last_scan));
}
// Plan F3: counts, unclear items and gaps; never a claim of completeness.
function renderResult(){
  const r=state.result,lines=[];
  if(r.messages_processed!==null&&state.last_scan)lines.push(t("{count} messages processed in the latest import or scan.",{count:r.messages_processed}));
  lines.push(t("{clues} clues from your emails point to {accounts} accounts.",{clues:r.clues,accounts:r.accounts_with_evidence}));
  lines.push(t("{confirmed} confirmed by you · {rejected} rejected · {open} with evidence still to decide · {complete} complete.",{confirmed:r.confirmed,rejected:r.rejected,open:r.to_decide,complete:r.complete}));
  const unclear=r.unclear;
  if(unclear.identity_reviews||unclear.unassigned_clues||unclear.unknown_domains)lines.push(t("Unclear: {reviews} sign-in addresses to identify · {clues} clues without a clear account · {domains} sender domains outside the catalog.",{reviews:unclear.identity_reviews,clues:unclear.unassigned_clues,domains:unclear.unknown_domains}));
  const gaps=r.gaps;
  if(gaps.skipped||gaps.errors||gaps.headers_only||gaps.older_clues||gaps.unfinished)lines.push(t("Gaps: {skipped} skipped · {errors} unreadable · {headers} headers only · {older} clues from older rules{unfinished}.",{skipped:gaps.skipped,errors:gaps.errors,headers:gaps.headers_only,older:gaps.older_clues,unfinished:gaps.unfinished?" · "+t("the latest import stopped early"):""}));
  $("result-lines").replaceChildren(...lines.map(line=>node("li",line)));
}
// Plan D1: one next task with its reason; ARGUS never acts at a provider.
const nextTaskTexts={
  import:["Import your first emails","ARGUS has no email evidence yet. Start with a local import; nothing is sent anywhere.","Open import"],
  scan_gaps:["Finish the interrupted import","The latest import or scan stopped early, so some messages are not analyzed yet.","Open import"],
  identify:["Identify {count} sign-in address(es)","These accounts kept progress from an older version without a clear address. Nothing else is offered for them until you choose one.","Open {account}"],
  handoff:["Check an unclear Bitwarden transfer","A transfer may have created an item without a reply. Check Bitwarden before any other transfer.","Open Prepare Bitwarden"],
  review_due:["Review {account} again","You asked to be reminded to check a step of this account again.","Open {account}"],
  continue:["Continue with {account}","This account is next in your worklist.","Continue"],
  decide:["Decide on {count} account(s) with evidence","Your emails point to these accounts, but only you can confirm or reject them. Start with {account}.","Open {account}"],
  secure:["Secure {account} next","It has the highest priority among your open accounts.","Secure next account"],
  done:["No open task","Every account you decided on is complete. ARGUS cannot find accounts without emails; import other sources if you have them.",""]
};
function renderNextTask(){
  const task=state.next_task,account=state.accounts.find(a=>a.id===task.account_id),values={count:task.count,account:account?accountTitle(account):""};
  const [title,reason,action]=nextTaskTexts[task.kind];
  $("next-task-title").textContent=t(title,values);$("next-task-reason").textContent=t(reason,values);
  $("next-task-action").textContent=action?t(action,values)+" →":"";
  $("next-task-action").classList.toggle("hidden",!action);$("next-task-action").disabled=workflowBusy;
}
async function runNextTask(){
  const task=state.next_task;
  if(task.kind==="import"||task.kind==="scan_gaps")navigate("setup");
  else if(task.kind==="handoff")navigate("bitwarden");
  else if(task.kind==="continue"||task.kind==="secure")await startGuided();
  else if(task.account_id)openDetail(task.account_id);
}
function describeChange(change){
  const account=state.accounts.find(a=>a.id===change.account_id),name=account?accountTitle(account):t("Account no longer available");
  if(change.field==="decision")return `${name} · ${t(decisionLabels[change.new.decision])}${change.new.reason?" ("+t(reasonLabels[change.new.reason])+")":""}`;
  if(change.field==="planning")return `${name} · ${t(!change.new.queued?"Removed from the worklist":change.new.deferred?"Deferred in the worklist":"Planned in the worklist")}`;
  const step=change.field.slice(5);
  if(change.old.state===change.new.state&&change.old.review_after!==change.new.review_after)return `${name} · ${t(stepNames[step])}: ${change.new.review_after?t("review on {date}",{date:localDate(change.new.review_after)}):t("no review date")}`;
  return `${name} · ${t(stepNames[step])}: ${t(stateLabels[change.new.state])}`;
}
function renderHistory(){
  const shown=history.slice(0,10);
  $("history-items").replaceChildren(...shown.map(entry=>{
    const card=node("article",undefined,"worklist-item");
    card.append(node("strong",entry.changes.map(describeChange).join(" · ")));
    card.append(node("p",`${localDate(entry.at)}${entry.undo_of?" · "+t("Undo of an earlier change"):""}${entry.undone?" · "+t("Undone"):""}`));
    const actions=node("div",undefined,"bitwarden-actions");
    actions.append(actionButton("Undo",()=>undoChange(entry.batch),entry.undone));card.append(actions);return card;
  }));
  if(!shown.length)$("history-items").append(node("p",t("No local changes yet.")));
}
function scanDescription(scan){
  if(!scan)return t("No scan started yet.");
  // How to close each gap is listed separately as next steps (plan F4).
  const outcome=scan.running?t("Scan running …"):({completed:t("Completed."),limited:t("Message limit reached."),completed_with_gaps:t("Completed with gaps."),partial:t("Interrupted; processed clues remain saved.")}[scan.result]||t("Finished."));
  const headers=scan.headers_only?t(" {p0} messages analyzed using headers only.",{p0:(scan.headers_only)}):"";
  const folders=scan.folders_total!==undefined?t(" {p0}/{p1} selected folders checked.",{p0:(scan.folders_processed||0),p1:(scan.folders_total)}):"";
  return t("{processed} messages processed · New clues: {evidence} · Updated: {updated} · Duplicates: {duplicates} · Skipped: {skipped} · Errors: {errors}. {outcome}{headers}{folders}", {processed:scan.processed+(scan.expected?"/"+scan.expected:""),evidence:scan.evidence,updated:scan.updated_evidence||0,duplicates:scan.duplicates,skipped:scan.skipped,errors:scan.errors,outcome,headers,folders});
}
function renderNextSteps(id,steps){
  $(id).replaceChildren(...(steps||[]).map(step=>node("li",t(step))));
  $(id).classList.toggle("hidden",!(steps||[]).length);
}
function renderScan(scan){
  displayedScan=scan;
  $("scan-card").classList.toggle("hidden",!scan);
  $("scan-summary").textContent=scanDescription(scan);$("setup-scan-summary").textContent=scanDescription(scan);
  renderNextSteps("scan-next-steps",scan&&scan.next_steps);renderNextSteps("setup-next-steps",scan&&scan.next_steps);
  if(!scan)return;
  $("scan-badge").textContent=scan.running?t("Running"):({completed:t("Completed"),limited:t("Limit reached"),completed_with_gaps:t("Completed with gaps"),partial:t("Interrupted")}[scan.result]||t("Finished"));
  const maximum=scan.expected||scan.folders_total;
  if(maximum){$("scan-meter").max=maximum;$("scan-meter").value=scan.expected?scan.processed:(scan.folders_processed||0);}
  else if(scan.running)$("scan-meter").removeAttribute("value");
  else{$("scan-meter").max=1;$("scan-meter").value=1;}
}
function navigate(next,clearError=true){
  view=next;if(clearError)$("error").classList.add("hidden");
  const [title,description,crumb]=titles[next].map(value=>t(value));$("page-title").textContent=t(title);$("page-description").textContent=t(description);$("breadcrumb").textContent=t(crumb);
  document.querySelectorAll("[data-view]").forEach(b=>b.classList.toggle("active",b.dataset.view===next));
  $("dashboard-view").classList.toggle("hidden",next!=="dashboard");
  $("inventory-view").classList.toggle("hidden",!["dashboard","accounts","security"].includes(next));
  $("bitwarden-view").classList.toggle("hidden",next!=="bitwarden");
  $("setup-view").classList.toggle("hidden",next!=="setup");
  $("workflow-view").classList.toggle("hidden",next!=="workflow");
  $("list-title").textContent=next==="security"?t("High-priority accounts"):t("Your account inventory");
  if(state)renderRows();
}
function filtered(){
  const query=$("search").value.toLocaleLowerCase(language);
  const category=$("category").value,choice=$("classification").value,progressFilter=$("status-filter").value;
  return state.accounts.filter(a=>{
    if(view==="security" && (a.priority==="normal" || a.classification==="unknown" || a.progress==="complete"))return false;
    if(category&&a.category!==category)return false;
    if(choice==="found"&&a.classification==="unknown")return false;
    if(choice==="confirmed"&&a.decision!=="confirmed")return false;
    if(choice==="evidence"&&!(a.decision==="undecided"&&a.evidence_level==="probable"))return false;
    if(choice==="unknown"&&!(a.decision==="undecided"&&a.evidence_level!=="probable"))return false;
    if(choice==="rejected"&&a.decision!=="rejected")return false;
    if(progressFilter==="deferred"&&!a.deferred)return false;
    if(progressFilter&&progressFilter!=="deferred"&&a.progress!==progressFilter)return false;
    return `${accountTitle(a)} ${a.category} ${t(a.category)} ${a.registered_emails.join(" ")}`.toLocaleLowerCase(language).includes(query);
  });
}
function evidenceMark(a){return node("span",t(evidenceLabels[a.evidence_level]),`chip mark ${a.evidence_level==="probable"?"probable":"unknown"}`);}
function decisionMark(a){return node("span",t(decisionLabels[a.decision]),`chip mark decision-${a.decision} ${a.decision==="confirmed"?"confirmed":"unknown"}`);}
function progressText(a){
  if(a.progress==="complete")return a.completed_at?t("Complete on {date}",{date:localDate(a.completed_at)}):t("Complete");
  const applicable=STEP_ORDER.filter(step=>a.steps[step].state!=="not_applicable");
  const done=applicable.filter(step=>a.steps[step].state==="done").length;
  return t("{done} of {total} steps",{done,total:applicable.length})+(a.deferred?" · "+t("Deferred"):"");
}
function renderRows(){
  const rows=filtered();$("visible-count").textContent=t("{p0} items",{p0:(rows.length)});
  const fragment=document.createDocumentFragment();
  for(const a of rows){
    const tr=node("tr");const provider=node("td");const flex=node("div",undefined,"provider-cell");flex.append(node("span",a.name[0],"avatar"));
    const info=node("div");info.append(node("strong",accountTitle(a)),node("small",a.identity_review_required?t("Identify this account before preparing Bitwarden."):t(a.category)));flex.append(info);provider.append(flex);
    const evidence=node("td");evidence.append(evidenceMark(a),node("small",a.score?t("Clue strength {p0}/100",{p0:(a.score)}):t("No reliable clue"),"evidence-hint"));
    const decision=node("td");decision.append(decisionMark(a));
    if(a.reconsider)decision.append(node("small",t("New evidence since your decision"),"evidence-hint"));
    const progressCell=node("td");progressCell.append(node("span",progressText(a),`status ${a.progress}`));
    const priority=node("td");priority.append(node("span",t(labels[a.priority]),`priority ${a.priority}`));
    const action=node("td");const button=node("button",t("Review →"),"row-open");button.setAttribute("aria-label",t("Review {p0}",{p0:reviewTitle(a)}));button.onclick=()=>openDetail(a.id);action.append(button);
    tr.append(provider,evidence,decision,progressCell,priority,action);fragment.append(tr);
  }
  $("account-rows").replaceChildren(fragment);$("empty").classList.toggle("hidden",rows.length>0);
}
function renderCandidates(){
  $("candidates-panel").classList.toggle("hidden",state.candidates.length===0);
  $("candidates").replaceChildren(...state.candidates.map(c=>node("span",`${c.domain} · ${c.evidence.length} ${t(c.evidence.length===1?"clue":"clues")}`,"candidate")));
}
function link(text,url){
  const a=node("a",text);a.href=url;a.target="_blank";a.rel="noopener noreferrer";return a;
}
function openDetail(id){selected=id;renderDetail();$("account-dialog").showModal();}
function evidenceCard(e){
  const card=node("div",t(e.reason),"evidence-card");let date=t("Date unknown");
  if(e.date){const parsed=new Date(e.date);if(!Number.isNaN(parsed.getTime()))date=parsed.toLocaleDateString(language==="de"?"de-DE":"en-GB",{day:"numeric",month:"short",year:"numeric"});}
  card.append(node("small",`${e.sender_domain} · ${date} · ${e.source} · ${t("Strength {score}/100",{score:e.score})}${e.caveat?" · "+translateCaveat(e.caveat):""}`));return card;
}
function stepMeta(a,step){
  const value=a.steps[step];
  if(value.state==="prepared")return t("Prepared by ARGUS on {date}: a password-free item exists. Tick this step once the password is stored in Bitwarden.",{date:localDate(value.done_at)});
  if(value.state==="not_applicable"&&step==="password")return t("Not needed: you sign in with single sign-on or a passkey.");
  if(value.state==="not_applicable")return value.done_at?t("Marked not applicable on {date}.",{date:localDate(value.done_at)}):t("Marked not applicable.");
  if(value.state==="done")return value.done_at?t("Done on {date}.",{date:localDate(value.done_at)}):t("Done.");
  return "";
}
function stepRow(a,step,busy){
  const value=a.steps[step],[title,description]=stepTitles[step];
  const label=node("label",undefined,"check-item"),checkbox=node("input",undefined,"step-check");checkbox.type="checkbox";checkbox.dataset.step=step;checkbox.checked=value.state==="done";
  checkbox.disabled=busy||(step==="identity"&&a.identity_review_required)||value.state==="not_applicable";
  checkbox.onchange=()=>setStep(step,{state:checkbox.checked?"done":"open"});
  const text=node("span",t(title));text.append(node("small",t(description)));
  const meta=stepMeta(a,step);if(meta)text.append(node("small",meta,"step-meta"));
  if(a.reviews_due.includes(step))text.append(node("small",t("Review due: check this step again."),"step-meta review-due"));
  const extra=node("span",undefined,"step-extra");
  if(step==="mfa_recovery"){
    const optional=node("input");optional.type="checkbox";optional.checked=value.state==="not_applicable";optional.disabled=busy||value.state==="done";
    optional.setAttribute("aria-label",t("MFA is not offered or not used"));optional.onchange=()=>setStep(step,{state:optional.checked?"not_applicable":"open"});
    const optionalLabel=node("label");optionalLabel.append(optional,node("span",t("Not offered or not used")));extra.append(optionalLabel);
  }
  if(value.state==="done"||value.state==="not_applicable"){
    const picker=node("input");picker.type="date";picker.min=localDateInput(1);picker.max=localDateInput(5*365);picker.value=value.review_after||"";picker.disabled=busy;
    picker.setAttribute("aria-label",t("Review again on"));
    picker.onchange=()=>{if(picker.value)setStep(step,{review_after:picker.value});};
    const pickerLabel=node("label");pickerLabel.append(node("span",t("Review again on")),picker);extra.append(pickerLabel);
    if(value.review_after){const clear=node("button",t("No review date"),"text-button");clear.type="button";clear.disabled=busy;clear.onclick=event=>{event.preventDefault();setStep(step,{review_after:null});};extra.append(clear);}
  }
  if(extra.childNodes.length)text.append(extra);
  label.append(checkbox,text);return label;
}
function renderDetail(){
  const a=state.accounts.find(x=>x.id===selected);if(!a)return;
  const busy=saving||addingAccount;
  $("detail-name").textContent=accountTitle(a);
  const queued=state.workflow.items.find(item=>item.id===a.id);
  $("detail-worklist").disabled=busy||workflowBusy||Boolean(queued)||a.classification==="unknown";
  $("detail-worklist").textContent=t(queued?"In your worklist":"Add to worklist");
  const step=accountStep(a);
  $("detail-next-step").textContent=t(workflowSteps[step]);
  $("guided-detail-copy").textContent=guidedStepCopy(a,step);
  const guidedCurrent=state.workflow.current===a.id&&!state.workflow.paused;
  const providerButton=$("guided-open-provider");
  providerButton.classList.toggle("hidden",step!=="change_password"||!a.password_url);
  providerButton.textContent=t("Open verified provider page ↗");
  providerButton.href=a.password_url||"#";
  const guidedBitwarden=$("guided-prepare-bitwarden");
  guidedBitwarden.classList.toggle("hidden",step!=="bitwarden"||!guidedCurrent||a.steps.vault.state==="prepared");
  guidedBitwarden.disabled=busy||bitwardenBusy||state.demo;
  const completion=guidedCompletion[step];
  const completeButton=$("guided-complete-step");
  completeButton.classList.toggle("hidden",!guidedCurrent||!completion);
  completeButton.dataset.completion=completion||"";
  completeButton.textContent=t("I completed this step");
  completeButton.disabled=busy||!completion;
  $("detail-bitwarden").disabled=busy||bitwardenBusy||a.identity_review_required||a.classification==="unknown"||a.steps.vault.state!=="open";
  $("identity-review-note").classList.toggle("hidden",!a.identity_review_required);
  $("identity-bound-note").classList.toggle("hidden",!a.identity_email);
  $("identity-caution-note").classList.toggle("hidden",!state.accounts.some(other=>other.id!==a.id&&(other.provider_id||other.id)===(a.provider_id||a.id)));
  $("detail-marks").replaceChildren(evidenceMark(a),decisionMark(a),node("span",progressText(a),`chip mark soft`));
  $("detail-meta").replaceChildren(node("p",`${t(a.category)} · ${a.registered_emails.join(", ")||t("Sign-in address not known from evidence")}`),node("p",t(a.evidence_reason)));
  const decided=a.decided_at?localDate(a.decided_at):"";
  $("decision-status").textContent=a.decision==="confirmed"?t("Confirmed by you on {date}.",{date:decided}):a.decision==="rejected"?t("Rejected on {date}: {reason}.",{date:decided,reason:t(reasonLabels[a.decision_reason])}):t("Not decided yet. Evidence alone never confirms an account.");
  $("reconsider-note").classList.toggle("hidden",!a.reconsider);
  $("decide-confirm").disabled=busy||a.decision==="confirmed";
  $("decide-reject").disabled=busy||(a.decision==="rejected"&&a.decision_reason===$("reject-reason").value);
  $("reject-reason").disabled=busy;
  $("decide-reset").disabled=busy||a.decision==="undecided";
  const links=[link(t("Official website ↗"),a.website)];
  if(a.password_url){links.push(link(t("Documented password settings ↗"),a.password_url),link(t("Source · checked {p0} ↗",{p0:(a.password_verified)}),a.password_source));}
  else links.push(node("span",t("No verified direct password-settings link."),"small-muted"));
  if(a.historical)links.push(node("span",t("Historical service: check its current status."),"small-muted"));
  $("detail-links").replaceChildren(...links);
  $("login-method").value=a.login_method;$("detail-priority").value=a.priority;
  $("registered-email").replaceChildren(new Option(t("Email evidence only / unknown"),""),...state.emails.map(e=>new Option(e,e)));
  $("registered-email").value=a.identity_email||a.manual_email||"";
  const addForm=$("add-account-form");
  if(addForm.dataset.account!==a.id){addForm.reset();$("add-account-panel").open=false;addForm.dataset.account=a.id;$("new-account-error").classList.add("hidden");}
  const newAccountEmail=$("new-account-email"),previousEmail=newAccountEmail.value;
  newAccountEmail.replaceChildren(new Option(t("Sign-in address not known from evidence"),""),...state.emails.map(e=>new Option(e,e)));
  newAccountEmail.value=state.emails.includes(previousEmail)?previousEmail:"";
  for(const id of ["new-account-email","new-account-label","new-account-owned","add-account-button"])$(id).disabled=busy;
  $("sso-note").classList.toggle("hidden",a.login_method==="password");
  $("checklist").replaceChildren(...STEP_ORDER.map(step=>stepRow(a,step,busy)));
  $("progress-status").textContent=a.progress==="complete"?t("Complete on {date}: every step is done or not applicable. This is not a security guarantee.",{date:localDate(a.completed_at)}):progressText(a);
  $("detail-evidence").replaceChildren(...(a.evidence.length?a.evidence.map(evidenceCard):[node("p",t("No local evidence. This does not prove that an account does not exist."),"small-muted")]));
  const sharedClues=a.unassigned_evidence||[];
  $("shared-evidence-panel").classList.toggle("hidden",!sharedClues.length);
  $("shared-evidence").replaceChildren(...sharedClues.map(evidenceCard));
  $("login-method").disabled=busy;$("registered-email").disabled=busy||Boolean(a.identity_email);$("detail-priority").disabled=busy;
  $("defer-account").disabled=busy||workflowBusy||(a.evidence_level==="none"&&a.decision==="undecided")||a.deferred||a.decision==="rejected";
}
// Attribute changes (address, sign-in method, priority) use the account update.
async function update(change){
  if(saving||addingAccount)return;saving=true;renderDetail();$("detail-error").classList.add("hidden");
  try{await api(`/api/accounts/${encodeURIComponent(selected)}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify(change)});await refresh();toast(t("Change saved locally."));}
  catch(e){problem("detail-error",e.message,e.hint);}
  finally{saving=false;renderDetail();}
}
// Decisions and steps are logged; the toast offers to undo exactly this change.
async function accountAction(kind,body,message){
  if(saving||addingAccount)return false;saving=true;renderDetail();$("detail-error").classList.add("hidden");
  try{
    const result=await api(`/api/accounts/${encodeURIComponent(selected)}/${kind}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    await refresh();toast(t(message),result.batch);return true;
  }catch(e){problem("detail-error",e.message,e.hint);return false;}
  finally{saving=false;renderDetail();}
}
function decide(decision,reason){return accountAction("decision",reason?{decision,reason}:{decision},"Decision saved locally.");}
function setStep(step,body){return accountAction("steps",{step,...body},"Step saved locally.");}
async function addLocalAccount(event){
  event.preventDefault();if(addingAccount||saving||!$("new-account-owned").checked)return;
  const account=state.accounts.find(a=>a.id===selected);if(!account)return;
  const data={provider_id:account.provider_id||account.id,email:$("new-account-email").value,label:$("new-account-label").value.trim(),confirmed:true};
  addingAccount=true;renderDetail();$("new-account-error").classList.add("hidden");
  try{
    const result=await api("/api/accounts",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
    await refresh();selected=result.id;toast(t("Separate account added to your local inventory."));
  }catch(e){problem("new-account-error",e.message,e.hint);}
  finally{addingAccount=false;renderDetail();}
}
function renderExport(){
  const items=state.accounts.filter(a=>a.classification!=="unknown"&&a.steps.vault.state==="open");
  const eligible=new Set(items.filter(a=>!a.identity_review_required).map(a=>a.id));
  for(const id of exportChoices.keys())if(!eligible.has(id))exportChoices.delete(id);
  $("export-selection").replaceChildren(...items.map(a=>{
    const label=node("label");const checkbox=node("input");checkbox.type="checkbox";checkbox.value=a.id;checkbox.checked=!a.identity_review_required&&(exportChoices.has(a.id)?exportChoices.get(a.id):a.classification==="confirmed");checkbox.disabled=bitwardenBusy||Boolean(a.identity_review_required);
    checkbox.onchange=()=>exportChoices.set(a.id,checkbox.checked);const text=node("span",`${accountTitle(a)} · ${t(labels[a.classification])}`);
    if(a.identity_review_required){label.classList.add("selection-blocked");text.append(node("small",t("Identify this account before preparing Bitwarden.")));}
    label.append(checkbox,text);return label;
  }));
  if(!items.length)$("export-selection").append(node("p",t("No missing items selected. Review your accounts and existing vault items first.")));
  $("bitwarden-cli-button").disabled=bitwardenBusy||state.demo||!eligible.size;
  $("bitwarden-audit-button").disabled=bitwardenBusy||state.demo||!eligible.size;
  $("export-button").disabled=bitwardenBusy||!eligible.size;
}
function renderBitwardenAudit(){
  const panel=$("bitwarden-audit");
  if(!bitwardenAudit||!Array.isArray(bitwardenAudit.accounts)){panel.classList.add("hidden");$("bitwarden-audit-items").replaceChildren();return;}
  const accounts=new Map(state.accounts.map(account=>[account.id,account]));
  panel.classList.remove("hidden");
  $("bitwarden-audit-items").replaceChildren(...bitwardenAudit.accounts.map(result=>{
    const account=accounts.get(result.account_id),item=node("article",undefined,"worklist-item");
    const message=result.match==="found"?t("Matching Bitwarden item found ({count}).",{count:result.count}):result.match==="possible"?t("Possible Bitwarden item found ({count}); review it yourself.",{count:result.count}):t("No matching Bitwarden item found.");
    item.append(node("strong",account?accountTitle(account):t("Account no longer available")),node("p",message));return item;
  }));
}
function actionButton(text,action,disabled=false){
  const button=node("button",t(text),"button secondary");button.onclick=action;button.disabled=disabled;return button;
}
function localDate(value){
  const date=new Date(value);
  return Number.isNaN(date.getTime())?value:date.toLocaleDateString(language==="de"?"de-DE":"en-GB",{day:"numeric",month:"short",year:"numeric"});
}
function localDateInput(days){
  const date=new Date();date.setDate(date.getDate()+days);
  return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,"0")}-${String(date.getDate()).padStart(2,"0")}`;
}
function renderWorklist(){
  const workflow=state.workflow,accounts=new Map(state.accounts.map(a=>[a.id,a]));
  $("worklist-badge").textContent=t(workflow.paused?"Paused":"Ready");
  $("worklist-summary").textContent=t("{done} of {total} completed · {deferred} deferred",workflow);
  $("worklist-progress").max=Math.max(1,workflow.total);$("worklist-progress").value=workflow.done;
  $("worklist-continue").disabled=workflowBusy||workflow.paused||!workflow.current;
  $("worklist-pause").disabled=workflowBusy;
  $("worklist-pause").textContent=t(workflow.paused?"Resume worklist":"Pause worklist");
  $("worklist-items").replaceChildren(...workflow.items.map(item=>{
    const account=accounts.get(item.id),card=node("article",undefined,"worklist-item");
    const status=item.snoozed_until?t("Snoozed until {date}. It will become ready locally on that date.",{date:localDate(item.snoozed_until)}):item.deferred&&item.step!=="done"?t("Deferred. Restore this account when you are ready."):t(workflowSteps[item.step]);
    card.append(node("strong",accountTitle(account)),node("p",status));
    const actions=node("div",undefined,"bitwarden-actions");
    actions.append(actionButton("Review →",()=>continueWorklist(item.id),workflowBusy||workflow.paused),
      actionButton(item.deferred?"Restore":"Defer",()=>changeWorklist({action:item.deferred?"restore":"defer",id:item.id}),workflowBusy||item.step==="done"),
      actionButton("Remove from worklist",()=>changeWorklist({action:"remove",id:item.id}),workflowBusy));
    if(!item.deferred&&item.step!=="done")actions.append(
      actionButton("Tomorrow",()=>changeWorklist({action:"snooze",id:item.id,days:1}),workflowBusy),
      actionButton("In one week",()=>changeWorklist({action:"snooze",id:item.id,days:7}),workflowBusy));
    if(!item.deferred&&item.step!=="done"){
      const picker=node("input",undefined,"snooze-date");picker.type="date";picker.min=localDateInput(1);picker.max=localDateInput(365);picker.setAttribute("aria-label",t("Choose a resume date"));picker.disabled=workflowBusy;
      actions.append(picker,actionButton("Schedule date",()=>{if(!picker.value){error("Choose a future local date");return;}changeWorklist({action:"snooze_until",id:item.id,date:picker.value});},workflowBusy));
    }
    card.append(actions);return card;
  }));
  if(!workflow.items.length)$("worklist-items").append(node("p",t("Your worklist is empty. Choose accounts below.")));
  const queued=new Set(workflow.items.map(item=>item.id));
  const available=state.accounts.filter(a=>a.classification!=="unknown"&&a.progress!=="complete"&&!queued.has(a.id));
  const eligible=new Set(available.map(a=>a.id));
  for(const id of worklistChoices.keys())if(!eligible.has(id))worklistChoices.delete(id);
  $("worklist-selection").replaceChildren(...available.map(account=>{
    const label=node("label"),checkbox=node("input");checkbox.type="checkbox";checkbox.value=account.id;
    checkbox.checked=worklistChoices.get(account.id)||false;checkbox.disabled=workflowBusy;
    checkbox.onchange=()=>worklistChoices.set(account.id,checkbox.checked);
    label.append(checkbox,node("span",`${accountTitle(account)} · ${t(labels[account.priority])}`));return label;
  }));
  $("worklist-add").disabled=workflowBusy||!available.length;
}
function guidedStepCopy(account,step){
  if(step==="identify")return t("This account needs an assigned sign-in address first.");
  if(step==="review")return t("Confirm the account after your own review. Evidence alone never confirms it.");
  if(step==="identity")return t("Make sure the sign-in address or username is right and belongs to you, then complete this step.");
  if(step==="bitwarden")return t("Prepare an empty Bitwarden item for this exact account. ARGUS never generates or handles its password.");
  if(step==="change_password")return account.password_url?t("Open the verified provider page, change the password in your browser, then return here and complete the checklist step."):t("No verified password-settings link is available. Open the provider website and navigate manually.");
  if(step==="test_signin")return t("Test the sign-in yourself, then complete this checklist step.");
  if(step==="mfa")return t("Review multi-factor authentication and recovery options yourself, then complete this checklist step.");
  return t("This account is complete.");
}
function renderGuided(){
  const workflow=state.workflow;
  const current=state.accounts.find(account=>account.id===workflow.current);
  const suggested=state.accounts.find(account=>account.id===workflow.suggested);
  const priorityPreview=(workflow.priority_preview||[]).map(id=>state.accounts.find(account=>account.id===id)).filter(Boolean);
  const account=current||suggested;
  $("guided-priority-preview").classList.toggle("hidden",!priorityPreview.length);
  $("guided-priority-items").replaceChildren(...priorityPreview.map((candidate,index)=>{
    const item=node("article",undefined,"worklist-item"),step=accountStep(candidate);
    item.append(node("strong",`${index+1}. ${accountTitle(candidate)}`),node("p",`${t(labels[candidate.priority])} · ${t(labels[candidate.classification])} · ${t(workflowSteps[step])}`));
    return item;
  }));
  if(!account){
    $("guided-current-card").classList.add("guided-current-blocked");
    $("guided-status").textContent=t("Ready");
    $("guided-current-copy").textContent=t("No incomplete discovered account is ready for a guided session.");
    $("guided-current-open").disabled=true;$("guided-build-worklist").disabled=true;$("guided-current-defer").disabled=true;
    return;
  }
  const step=accountStep(account), actionLabel=current?t("Continue to next account"):t("Secure next account");
  $("guided-current-card").classList.toggle("guided-current-blocked",!current||workflow.paused||account.identity_review_required);
  $("guided-status").textContent=t(account.identity_review_required?"Blocked: identify the sign-in address":workflow.paused?"Paused":current?"Action required":"Ready");
  $("guided-current-copy").textContent=`${accountTitle(account)} · ${guidedStepCopy(account,step)}`;
  $("guided-current-open").textContent=actionLabel;
  $("guided-current-open").disabled=workflowBusy;
  $("guided-build-worklist").disabled=workflowBusy||!priorityPreview.length;
  $("guided-current-defer").disabled=workflowBusy||!current;
}
async function changeWorklist(data){
  if(workflowBusy)return false;workflowBusy=true;renderWorklist();
  try{const result=await api("/api/workflow",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});await refresh();if($("account-dialog").open)renderDetail();return result;}
  catch(e){failure(e);return false;}
  finally{workflowBusy=false;renderWorklist();renderGuided();if($("account-dialog").open)renderDetail();}
}
async function continueWorklist(id=state.workflow.current){
  if(!id||state.workflow.paused)return;
  if(await changeWorklist({action:"focus",id}))openDetail(id);
}
async function startGuided(){
  const result=await changeWorklist({action:"start"});
  if(result&&result.current)openDetail(result.current);
}
async function buildPriorityWorklist(){
  const count=(state.workflow.priority_preview||[]).length;
  if(!count||workflowBusy)return;
  if(!window.confirm(t("ARGUS will add up to 10 highest-priority incomplete accounts to the local worklist. No provider, password or Bitwarden item is changed. Continue?")))return;
  const result=await changeWorklist({action:"prioritize"});
  if(result)toast(t(result.added.length?t("Added {count} priority account(s) to your worklist.",{count:result.added.length}):t("No additional priority accounts are ready.")));
}
function renderHandoffs(){
  const pending=state.bitwarden_handoffs.filter(item=>["running","uncertain"].includes(item.state));
  $("handoff-review").classList.toggle("hidden",!pending.length);
  $("handoff-items").replaceChildren(...pending.map(item=>{
    const account=state.accounts.find(a=>a.id===(item.account_id||item.provider_id)),card=node("article",undefined,"worklist-item");
    card.append(node("strong",`${account?accountTitle(account):item.provider_id}${account&&accountEmail(account)===item.email?"":" · "+(item.email||t("Email evidence only / unknown"))}`),node("p",t(item.state==="running"?"Transfer running. Wait before checking its result.":"Outcome unclear. Check Bitwarden before another attempt.")),node("code",item.operation_id));
    const actions=node("div",undefined,"bitwarden-actions");
    actions.append(actionButton("I found this item in Bitwarden",()=>resolveHandoff(item,true),bitwardenBusy||!item.can_resolve),actionButton("I checked: this item was not created",()=>resolveHandoff(item,false),bitwardenBusy||!item.can_resolve));
    card.append(actions);return card;
  }));
}
async function resolveHandoff(item,created){
  if(bitwardenBusy)return;
  if(!window.confirm(t(created?"Confirm that you found the matching item and transfer ID in Bitwarden.":"Confirm that you checked Bitwarden and this item does not exist. A new attempt may create a duplicate if the previous item exists.")))return;
  bitwardenBusy=true;renderExport();renderHandoffs();
  try{await api("/api/bitwarden/resolve",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id:item.id,created,confirmed:true})});await refresh();toast(t("Transfer review saved locally."));}
  catch(e){failure(e);}finally{bitwardenBusy=false;renderExport();renderHandoffs();}
}
// Every Bitwarden write is shown first, exactly as the server will write it
// (plan B2). The confirmed action reuses the previewed selection and language.
let pendingPreview=null;
async function showPreview(ids,target,action){
  if(bitwardenBusy)return;
  const previewLanguage=language;
  bitwardenBusy=true;renderExport();
  try{
    const preview=await api("/api/bitwarden/preview",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({ids,language:previewLanguage,target})});
    pendingPreview={preview,ids,language:previewLanguage,action};renderPreview();$("export-preview").showModal();
  }catch(e){failure(e);}finally{bitwardenBusy=false;renderExport();}
}
function renderPreview(){
  if(!pendingPreview)return;
  const preview=pendingPreview.preview,accounts=new Map(state.accounts.map(a=>[a.id,a]));
  $("preview-target").textContent=preview.target==="file"?t("Download a Bitwarden JSON file with the folder {folder}. Import it once, then delete it; it contains personal metadata.",{folder:preview.folder}):t("Create these password-free items in your already-unlocked Bitwarden vault. Existing items are never changed. Each item gets a transfer ID so you can find it if the reply is lost.");
  $("preview-items").replaceChildren(...preview.items.map(item=>{
    const row=node("tr"),name=node("td");name.append(node("strong",item.name),node("small",item.notes,"preview-notes"));
    row.append(name,node("td",item.uri),node("td",item.username||t("Empty: no confirmed sign-in address")),node("td",item.fields.join(", ")));
    return row;
  }));
  const skipped=preview.already_created.map(id=>accounts.get(id)).filter(Boolean).map(accountTitle);
  $("preview-skipped").textContent=skipped.length?t("Left out because the local journal records them as created: {names}",{names:skipped.join(", ")}):"";
  $("preview-skipped").classList.toggle("hidden",!skipped.length);
  $("preview-confirm").textContent=t(preview.target==="file"?"Download file":"Create in Bitwarden");
}
async function confirmPreview(){
  const pending=pendingPreview;pendingPreview=null;$("export-preview").close();
  if(pending)await pending.action(pending.ids,pending.language);
}
async function exportMetadata(){
  const ids=selectedBitwardenIds();
  if(!ids.length){error(t("Select the accounts you want to add to Bitwarden first."));return;}
  await showPreview(ids,"file",downloadMetadata);
}
async function downloadMetadata(ids,exportLanguage){
  if(bitwardenBusy)return;
  bitwardenBusy=true;renderExport();
  try{
    const result=await api("/api/bitwarden",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({ids,language:exportLanguage})});
    const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:"application/json"}));
    const a=document.createElement("a");a.href=url;a.download="argus-bitwarden.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast(t("Metadata downloaded. No vault was changed."));
  }catch(e){failure(e);}finally{bitwardenBusy=false;renderExport();}
}
function selectedBitwardenIds(){
  return Array.from($("export-selection").querySelectorAll("input:checked:not(:disabled)")).map(x=>x.value);
}
async function addToUnlockedBitwarden(){
  if(bitwardenBusy||state.demo)return;
  const ids=selectedBitwardenIds();
  if(!ids.length){error(t("Select the accounts you want to add to Bitwarden first."));return;}
  await showPreview(ids,"cli",createInBitwarden);
}
async function createInBitwarden(ids,transferLanguage){
  if(bitwardenBusy||state.demo)return;
  bitwardenBusy=true;renderExport();
  try{
    const result=await api("/api/bitwarden/cli",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({ids,language:transferLanguage,confirmed:true})});
    await refresh();if(result.status==="needs_review")error(t("The transfer result is unclear. Check Bitwarden below before trying again."));else toast(t("Added {count} password-free item(s) to Bitwarden. Generate the new password in Bitwarden, use the verified provider link to change it, then test the sign-in.",{count:result.items}));
  }catch(e){failure(e);try{await refresh();}catch(_){} }finally{bitwardenBusy=false;renderExport();renderHandoffs();}
}
async function auditUnlockedBitwarden(){
  if(bitwardenBusy||state.demo)return;
  const ids=selectedBitwardenIds();
  if(!ids.length){error(t("Select the accounts you want to check in Bitwarden first."));return;}
  if(!window.confirm(t("ARGUS will ask your already-unlocked Bitwarden CLI for selected-item metadata. It returns only a match summary; no vault data is saved or shown. Continue?")))return;
  bitwardenBusy=true;renderExport();
  try{bitwardenAudit=await api("/api/bitwarden/audit",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({ids,language,confirmed:true})});renderBitwardenAudit();}
  catch(e){failure(e);}finally{bitwardenBusy=false;renderExport();}
}
async function prepareGuidedBitwarden(){
  const account=state.accounts.find(item=>item.id===selected);
  if(!account||account.id!==state.workflow.current||accountStep(account)!=="bitwarden"||bitwardenBusy||state.demo)return;
  await showPreview([account.id],"cli",(ids,transferLanguage)=>createGuidedItem(account.id,transferLanguage));
}
async function createGuidedItem(accountId,transferLanguage){
  if(bitwardenBusy||state.demo)return;
  bitwardenBusy=true;renderDetail();renderExport();
  try{
    const result=await api("/api/secure-next/bitwarden",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({account_id:accountId,language:transferLanguage,confirmed:true})});
    await refresh();
    if(result.status==="needs_review")error(t("The transfer result is unclear. Check Bitwarden below before trying again."));
    else toast(t("Bitwarden preparation saved locally. Generate the password in Bitwarden, then continue with the verified provider page."));
  }catch(e){failure(e);try{await refresh();}catch(_){} }
  finally{bitwardenBusy=false;renderExport();renderHandoffs();if($("account-dialog").open)renderDetail();}
}
// Guided step -> what the person confirms: the decision or one dated step.
const guidedCompletion={review:"decision",identity:"identity",change_password:"password",test_signin:"signin_test",mfa:"mfa_recovery"};
async function completeGuidedStep(){
  const account=state.accounts.find(item=>item.id===selected);
  const completion=$("guided-complete-step").dataset.completion;
  if(!account||account.id!==state.workflow.current||!completion||saving)return;
  if(!window.confirm(t("Confirm that you completed this step yourself. ARGUS will only record your confirmation locally.")))return;
  const saved=completion==="decision"?await decide("confirmed"):await setStep(completion,{state:"done"});
  // A finished account hands the dialog to the next account of the worklist.
  const updated=state.accounts.find(item=>item.id===account.id);
  if(saved&&updated&&updated.next_step==="done"&&!state.workflow.paused&&state.workflow.current){selected=state.workflow.current;renderDetail();}
}
// File names stay in this browser tab; the server only learns a skip count.
function skipReason(file){
  if(file.size===0)return "empty file";
  if(!file.name.toLowerCase().endsWith(".eml"))return "not an EML file";
  if(file.size>2*1024*1024)return "larger than 2 MiB";
  return null;
}
function renderSkippedFiles(skipped){
  const shown=skipped.slice(0,20).map(item=>node("li",`${item.name}: ${t(item.reason)}`));
  if(skipped.length>20)shown.push(node("li",t("… and {count} more",{count:skipped.length-20})));
  $("import-skipped-list").replaceChildren(...shown);
  $("import-skipped").classList.toggle("hidden",!skipped.length);
}
async function importFiles(){
  const files=Array.from($("email-files").files);if(!files.length)return;
  const skippedFiles=[];renderSkippedFiles(skippedFiles);
  $("import-progress").classList.remove("hidden");$("import-button").disabled=true;$("email-files").disabled=true;
  $("import-meter").value=0;
  importCancelled=false;let stats=null,failed=false;
  try{
    stats=await api("/api/import/start",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({expected:files.length})});
    activeBatch=stats.id;$("cancel-import").classList.remove("hidden");$("cancel-import").disabled=false;$("add-alias-button").disabled=true;
    renderScan(stats);$("import-status").textContent=scanDescription(stats);
    for(const file of files){
      if(importCancelled)break;
      const reason=skipReason(file);
      if(reason){skippedFiles.push({name:file.name,reason});renderSkippedFiles(skippedFiles);stats=await api("/api/import/skip",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id:activeBatch})});}
      else {stats=await api("/api/import",{method:"POST",headers:{"Content-Type":"message/rfc822","X-Import-ID":activeBatch},body:file});}
      $("import-meter").value=stats.processed*100/files.length;$("import-status").textContent=scanDescription(stats);renderScan(stats);
      if(stats.scope_changed){failed=true;error(t("The address scope changed during import. Restart the import."));break;}
    }
  }catch(e){failed=true;failure(e);}
  finally{
    if(activeBatch){try{stats=await api("/api/import/finish",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id:activeBatch,...(importCancelled||failed?{result:"partial"}:{})})});$("import-status").textContent=scanDescription(stats);renderScan(stats);}catch(e){failure(e);}}
    activeBatch=null;$("cancel-import").classList.add("hidden");$("cancel-import").disabled=false;
    $("import-button").disabled=false;$("email-files").disabled=false;$("email-files").value="";
    try{await refresh();if(stats)toast(stats.result==="completed"?t("Local import completed."):t("Import status saved locally. Clues are preserved."));}catch(e){failure(e);}
  }
}
async function cancelImport(){
  if(activeBatch){importCancelled=true;$("cancel-import").disabled=true;$("import-status").textContent=t("Stopping after the current file. Saved clues are preserved.");return;}
  if(state.active_import){try{await api("/api/import/finish",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id:state.active_import.id,result:"partial"})});await refresh();toast(t("Import canceled; clues remain saved."));}catch(e){failure(e);}}
}
async function addAlias(event){
  event.preventDefault();if(addingAlias)return;addingAlias=true;$("add-alias-button").disabled=true;
  try{
    const result=await api("/api/profile/emails",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({emails:[$("alias-email").value.trim()]})});
    await refresh();$("alias-email").value="";$("alias-owned").checked=false;
    setMessage("alias-message",result.added.length?"Own address added. Re-import older local emails or run the authorized IMAP scan again. Your checklists were preserved.":"This address was already configured. Nothing was changed.");
  }catch(e){failure(e);}finally{addingAlias=false;$("add-alias-button").disabled=state.demo||Boolean(activeBatch||state.active_import);}
}
document.querySelectorAll("[data-view]").forEach(b=>b.onclick=()=>navigate(b.dataset.view));
document.querySelectorAll("[data-go]").forEach(b=>b.onclick=()=>navigate(b.dataset.go));
document.querySelector(".brand").onclick=e=>{e.preventDefault();navigate("dashboard");};
for(const id of ["search","category","classification","status-filter"])$(id).addEventListener(id==="search"?"input":"change",renderRows);
$("close-dialog").onclick=()=>$("account-dialog").close();
$("login-method").onchange=()=>update({login_method:$("login-method").value});
$("registered-email").onchange=()=>{
  const email=$("registered-email").value||null;
  // Binding an address is permanent for this account; require an explicit choice.
  if(email&&!window.confirm(t("Use {p0} as this account's sign-in address? This cannot be changed later; a different address needs a separate account.",{p0:email}))){renderDetail();return;}
  update({registered_email:email});
};
$("add-account-form").onsubmit=addLocalAccount;
$("detail-priority").onchange=()=>update({priority:$("detail-priority").value});
$("defer-account").onclick=()=>changeWorklist({action:"defer",id:selected});
$("decide-confirm").onclick=()=>decide("confirmed");
$("decide-reject").onclick=()=>decide("rejected",$("reject-reason").value);
$("decide-reset").onclick=()=>decide("undecided");
$("reject-reason").onchange=renderDetail;
$("toast-undo").onclick=()=>{const batch=toastBatch;$("toast").classList.add("hidden");toastBatch=null;if(batch)undoChange(batch);};
$("export-button").onclick=exportMetadata;
$("preview-confirm").onclick=confirmPreview;
$("preview-cancel").onclick=()=>$("export-preview").close();
$("preview-close").onclick=()=>$("export-preview").close();
$("export-preview").addEventListener("close",()=>{pendingPreview=null;});
$("bitwarden-cli-button").onclick=addToUnlockedBitwarden;
$("bitwarden-audit-button").onclick=auditUnlockedBitwarden;
$("worklist-add").onclick=()=>{const ids=Array.from($("worklist-selection").querySelectorAll("input:checked")).map(input=>input.value);if(!ids.length){error(t("Select accounts for your worklist first."));return;}changeWorklist({action:"add",ids});};
$("worklist-continue").onclick=()=>continueWorklist();
$("worklist-pause").onclick=()=>changeWorklist({action:state.workflow.paused?"resume":"pause"});
$("next-task-action").onclick=runNextTask;
$("start-import").onclick=()=>{navigate("setup");$("email-files").click();};
$("guided-current-open").onclick=startGuided;
$("guided-build-worklist").onclick=buildPriorityWorklist;
$("guided-current-defer").onclick=()=>{const id=state.workflow.current;if(id)changeWorklist({action:"defer",id});};
$("detail-worklist").onclick=()=>changeWorklist({action:"add",ids:[selected]});
$("detail-bitwarden").onclick=()=>{const account=state.accounts.find(a=>a.id===selected);if(!account||account.identity_review_required)return;exportChoices.clear();exportChoices.set(selected,true);for(const a of state.accounts)if(a.id!==selected)exportChoices.set(a.id,false);$("account-dialog").close();navigate("bitwarden");renderExport();};
$("guided-prepare-bitwarden").onclick=prepareGuidedBitwarden;
$("guided-complete-step").onclick=completeGuidedStep;
$("import-button").onclick=()=>{navigate("setup");$("email-files").click();};
$("email-files").onchange=importFiles;
$("cancel-import").onclick=cancelImport;
$("alias-form").onsubmit=addAlias;
document.querySelectorAll(".language-control").forEach(e=>e.onchange=()=>applyLanguage(e.value,true));
applyLanguage(language);
refresh().catch(failure);
// Poll only the local server; CLI scans update the same database.
setInterval(()=>{if(!saving && !$("account-dialog").open && !$("email-files").disabled)refresh().catch(failure);},15000);
