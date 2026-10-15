"use strict";
const $ = id => document.getElementById(id);
let language;
try { language=localStorage.getItem("account-finder.language"); } catch (_) {}
if(!["en","de"].includes(language))language=(navigator.language||"en").toLowerCase().startsWith("de")?"de":"en";
const translations=window.AF_TRANSLATIONS.de;
const translationSpacing=new WeakMap();
function t(message,values={}) {
  const text=language==="de"?(translations[message]||message):message;
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
  if(remember){try{localStorage.setItem("account-finder.language",language);}catch(_){}}
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
  if(state){renderState();navigate(view,false);if($("account-dialog").open)renderDetail();}
  if(scan){renderScan(scan);if(!$("import-progress").classList.contains("hidden"))$("import-status").textContent=scan.running&&importCancelled?t("Stopping after the current file. Saved clues are preserved."):scanDescription(scan);}
}
const token = document.querySelector('meta[name="af-token"]').content;
document.querySelector('meta[name="af-token"]').remove();
let state, view = "dashboard", selected = null, saving = false;
let activeBatch=null, importCancelled=false, addingAlias=false, addingAccount=false;
let displayedScan=null;
const exportChoices=new Map();
const worklistChoices=new Map();
let workflowBusy=false, bitwardenBusy=false;
const workflowSteps={identify:"Identify this account before preparing Bitwarden.",review:"Review this account and confirm it exists.",bitwarden:"Assign an existing Bitwarden item or prepare a missing one.",change_password:"Use Bitwarden to set a unique password at the provider.",test_signin:"Test the sign-in before completing this account.",finish:"Required steps are checked. You can mark this account done.",done:"This account is complete."};
function accountStep(account){return account.identity_review_required?"identify":account.status==="done"?"done":!account.checklist.reviewed?"review":!account.checklist.saved_in_bitwarden?"bitwarden":account.login_method==="password"&&!account.checklist.password_changed?"change_password":!account.checklist.login_tested?"test_signin":"finish";}
const labels = {confirmed:"Confirmed",probable:"Probable",unknown:"Unknown",pending:"Pending",in_progress:"In progress",done:"Done",skipped:"Deferred",critical:"Do first",high:"High",normal:"Normal"};
const titles = {
  dashboard:["Your accounts, in one place.","Find local evidence and secure your accounts with Bitwarden.","Overview"],
  accounts:["Your digital inventory.","Review your clues and keep unknown services in view.","All accounts"],
  security:["Secure the most important accounts first.","Prioritize your mailbox, finance and central services.","Security priorities"],
  bitwarden:["A secure password for every account.","Prepare new vault items and make the changes yourself.","Prepare Bitwarden"],
  workflow:["Secure your accounts, one at a time.","A local worklist that remembers your progress.","Security worklist"],
  setup:["Start with your mailbox.","Import existing messages or set up read-only IMAP access.","Mailbox & Import"],
  plans:["Choose your local edition.","Account Compass Free is available now; Pro is a transparent preview.","Plans"]
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
function error(message) { setMessage("error",canonicalMessage(message)); $("error").classList.remove("hidden"); }
function toast(message) { setMessage("toast",canonicalMessage(message)); $("toast").classList.remove("hidden"); setTimeout(()=>$("toast").classList.add("hidden"),3000); }
async function api(path, options={}) {
  const headers={Authorization:`Bearer ${token}`,...(options.headers||{})};
  const response=await fetch(path,{...options,headers,cache:"no-store",credentials:"omit"});
  if(!response.ok){const result=await response.json().catch(()=>({}));throw new Error(result.error||t("Local request failed."));}
  return response.json();
}
async function refresh() {
  state=await api("/api/accounts");
  renderState();
}
function renderState() {
  const s=state.summary;
  for(const [id,value] of Object.entries({"found-count":s.found,"confirmed-count":s.confirmed,"probable-count":s.probable,"priority-count":s.high_priority,"done-count":s.done,"provider-count":s.providers,"nav-count":s.found,"progress-label":`${s.progress}%`,"progress-caption":t("{p0} of {p1} accounts done",{p0:(s.done),p1:(s.found)})}))$(id).textContent=value;
  $("progress-fill").style.width=`${s.progress}%`;
  $("services-found-caption").textContent=t("{count} services found",{count:s.services_found??new Set(state.accounts.filter(a=>a.classification!=="unknown").map(a=>a.provider_id||a.id)).size});
  $("progress-bar").setAttribute("aria-valuenow",s.progress);
  $("demo-banner").classList.toggle("hidden",!state.demo);
  $("rescan-banner").classList.toggle("hidden",!state.stale_evidence);
  $("rescan-banner").textContent=t("{p0} older clues need the current detection rules. Re-import the original emails or start an authorized IMAP scan. Your checklists are preserved.",{p0:(state.stale_evidence||0)});
  const previous=$("category").value;
  $("category").replaceChildren(new Option(t("All categories"),""),...Array.from(new Set(state.accounts.map(a=>a.category))).sort().map(c=>new Option(t(c),c)));
  $("category").value=previous;
  $("profile-email").textContent=t("Configured addresses: {p0}",{p0:(state.emails.join(", "))});
  const scheduled=state.background_scan||{};
  let scheduledText;
  if(scheduled.enabled) scheduledText=t("Scheduled read-only IMAP scans are enabled. They run only while this local dashboard is open.");
  else if(scheduled.authorized) scheduledText=t("Scheduled IMAP scans are paused. The authorization stays in your OS keyring until you revoke it.");
  else scheduledText=t("Scheduled IMAP scans are disabled. Enable them from a local terminal after configuring IMAP.");
  if(scheduled.last_error) scheduledText+=" "+t(scheduled.last_error);
  $("background-scan-status").textContent=scheduledText;
  const domain=(state.emails[0]||"").split("@")[1]||"your-domain.example";
  $("discover-command").textContent=`python -m account_finder discover --domain ${domain} --allow-dns`;
  renderScan(state.active_import||state.last_scan);
  $("cancel-import").classList.toggle("hidden",!activeBatch&&!state.active_import);
  $("add-alias-button").disabled=state.demo||addingAlias||Boolean(activeBatch||state.active_import);
  $("alias-email").disabled=state.demo;$("alias-owned").disabled=state.demo;
  if(state.demo)setMessage("alias-message","Add real own addresses in a personal profile on your computer. The demo profile stays separate.");
  renderRows();renderCandidates();renderExport();renderPlans();renderWorklist();renderGuided();renderHandoffs();
}
function renderPlans(){
  const product=state.product;
  $("free-plan-name").textContent=product.name;
  $("free-plan-features").replaceChildren(...product.free_features.map(feature=>node("li",t(feature))));
  $("pro-plan-features").replaceChildren(...product.pro_preview.map(feature=>node("li",t(feature))));
  const license=product.license;
  $("license-activation").classList.toggle("hidden",!license.activation_enabled);
  $("license-status").textContent=t(license.message);
  setMessage("pro-preview-note",license.state==="active"?"Account Compass Pro is active.":"Pro is in development and not for sale. This app does not collect payment details, create an online account or send telemetry.");
  $("activate-license").disabled=!license.activation_enabled;
}
function scanDescription(scan){
  if(!scan)return t("No scan started yet.");
  const outcome=scan.running?t("Scan running …"):({completed:t("Completed."),limited:t("Message limit reached; run the IMAP scan again to continue."),completed_with_gaps:t("Completed with gaps; review skipped or failed messages."),partial:t("Interrupted; processed clues remain saved.")}[scan.result]||t("Finished."));
  const headers=scan.headers_only?t(" {p0} messages analyzed using headers only.",{p0:(scan.headers_only)}):"";
  const folders=scan.folders_total!==undefined?t(" {p0}/{p1} selected folders checked.",{p0:(scan.folders_processed||0),p1:(scan.folders_total)}):"";
  const scope=scan.scope_changed?t(" The address scope changed; restart the analysis."):"";
  return t("{processed} messages processed · New clues: {evidence} · Updated: {updated} · Duplicates: {duplicates} · Skipped: {skipped} · Errors: {errors}. {outcome}{headers}{folders}{scope}", {processed:scan.processed+(scan.expected?"/"+scan.expected:""),evidence:scan.evidence,updated:scan.updated_evidence||0,duplicates:scan.duplicates,skipped:scan.skipped,errors:scan.errors,outcome,headers,folders,scope});
}
function renderScan(scan){
  displayedScan=scan;
  $("scan-card").classList.toggle("hidden",!scan);
  $("scan-summary").textContent=scanDescription(scan);$("setup-scan-summary").textContent=scanDescription(scan);
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
  $("plans-view").classList.toggle("hidden",next!=="plans");
  $("workflow-view").classList.toggle("hidden",next!=="workflow");
  $("list-title").textContent=next==="security"?t("High-priority accounts"):t("Your account inventory");
  if(state)renderRows();
}
function filtered(){
  const query=$("search").value.toLocaleLowerCase(language);
  const category=$("category").value,classification=$("classification").value,status=$("status-filter").value;
  return state.accounts.filter(a=>{
    if(view==="security" && (a.priority==="normal" || a.classification==="unknown" || a.status==="done"))return false;
    if(category&&a.category!==category)return false;
    if(classification==="found"&&a.classification==="unknown")return false;
    if(!["found","all"].includes(classification)&&a.classification!==classification)return false;
    if(status&&a.status!==status)return false;
    return `${accountTitle(a)} ${a.category} ${t(a.category)} ${a.registered_emails.join(" ")}`.toLocaleLowerCase(language).includes(query);
  });
}
function renderRows(){
  const rows=filtered();$("visible-count").textContent=t("{p0} items",{p0:(rows.length)});
  const fragment=document.createDocumentFragment();
  for(const a of rows){
    const tr=node("tr");const provider=node("td");const flex=node("div",undefined,"provider-cell");flex.append(node("span",a.name[0],"avatar"));
    const info=node("div");info.append(node("strong",accountTitle(a)),node("small",a.identity_review_required?t("Identify this account before preparing Bitwarden."):t(a.category)));flex.append(info);provider.append(flex);
    const detected=node("td");detected.append(node("span",t(labels[a.classification]),`chip ${a.classification}`));detected.append(node("small",a.classification==="confirmed"?t("Reviewed by you"):a.score?t("Clue strength {p0}/100",{p0:(a.score)}):t("No reliable clue"),"evidence-hint"));
    const priority=node("td");priority.append(node("span",t(labels[a.priority]),`priority ${a.priority}`));
    const status=node("td");status.append(node("span",t(labels[a.status]),`status ${a.status}`));
    const action=node("td");const button=node("button",t("Review →"),"row-open");button.setAttribute("aria-label",t("Review {p0}",{p0:reviewTitle(a)}));button.onclick=()=>openDetail(a.id);action.append(button);
    tr.append(provider,detected,priority,status,action);fragment.append(tr);
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
  guidedBitwarden.classList.toggle("hidden",step!=="bitwarden"||!guidedCurrent);
  guidedBitwarden.disabled=busy||bitwardenBusy||state.demo;
  const completion={review:"reviewed",change_password:"password_changed",test_signin:"login_tested",finish:"done"}[step];
  const completeButton=$("guided-complete-step");
  completeButton.classList.toggle("hidden",!guidedCurrent||!completion);
  completeButton.dataset.completion=completion||"";
  completeButton.textContent=t(completion==="done"?"Mark account done":"I completed this step");
  completeButton.disabled=busy||!completion;
  $("detail-bitwarden").disabled=busy||bitwardenBusy||a.identity_review_required||a.classification==="unknown"||a.checklist.saved_in_bitwarden;
  $("identity-review-note").classList.toggle("hidden",!a.identity_review_required);
  $("identity-bound-note").classList.toggle("hidden",!a.identity_email);
  $("identity-caution-note").classList.toggle("hidden",!state.accounts.some(other=>other.id!==a.id&&(other.provider_id||other.id)===(a.provider_id||a.id)));
  $("detail-meta").replaceChildren(node("span",t(labels[a.classification]),`chip ${a.classification}`),node("p",`${t(a.category)} · ${a.registered_emails.join(", ")||t("Sign-in address not known from evidence")}`),node("p",t(a.reason)));
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
  const steps=[
    ["reviewed",t("I verified that this account exists"),t("Confirm only after your own review. An email clue alone is not enough.")],
    ["saved_in_bitwarden",t("Assigned in Bitwarden"),t("Use an existing item or save a new one directly in Bitwarden.")],
    ["password_changed",t("Unique password set at the provider"),t("Generate it in Bitwarden and change it yourself at the provider. Never enter it here.")],
    ["login_tested",t("Sign-in tested"),t("Sign in successfully using the new password, passkey or central identity provider.")],
    ["mfa_checked",t("MFA and recovery reviewed (recommended)"),t("Enable multi-factor authentication if available and store recovery codes securely.")]
  ];
  const items=[];
  for(const [key,title,description] of steps){
    if(key==="password_changed"&&a.login_method!=="password")continue;
    const label=node("label",undefined,"check-item");const checkbox=node("input");checkbox.type="checkbox";checkbox.checked=a.checklist[key];checkbox.disabled=busy;
    checkbox.onchange=()=>update({checklist:{[key]:checkbox.checked}});
    const text=node("span",title);text.append(node("small",description));label.append(checkbox,text);items.push(label);
  }
  $("checklist").replaceChildren(...items);
  $("detail-evidence").replaceChildren(...(a.evidence.length?a.evidence.map(evidenceCard):[node("p",t("No local evidence. This does not prove that an account does not exist."),"small-muted")]));
  const sharedClues=a.unassigned_evidence||[];
  $("shared-evidence-panel").classList.toggle("hidden",!sharedClues.length);
  $("shared-evidence").replaceChildren(...sharedClues.map(evidenceCard));
  const required=["reviewed","saved_in_bitwarden","login_tested",...(a.login_method==="password"?["password_changed"]:[])];
  $("finish-account").disabled=busy||a.identity_review_required||!required.every(k=>a.checklist[k]);
  $("finish-account").textContent=a.status==="done"?t("Already done"):t("Mark as done");
  $("login-method").disabled=busy;$("registered-email").disabled=busy||Boolean(a.identity_email);$("detail-priority").disabled=busy;$("defer-account").disabled=busy;
}
async function update(change){
  if(saving||addingAccount)return;saving=true;renderDetail();$("detail-error").classList.add("hidden");
  try{await api(`/api/accounts/${encodeURIComponent(selected)}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify(change)});await refresh();toast(t("Change saved locally."));if(change.status==="done"&&view==="workflow"&&!state.workflow.paused&&state.workflow.current)selected=state.workflow.current;}
  catch(e){setMessage("detail-error",canonicalMessage(e.message));$("detail-error").classList.remove("hidden");}
  finally{saving=false;renderDetail();}
}
async function addLocalAccount(event){
  event.preventDefault();if(addingAccount||saving||!$("new-account-owned").checked)return;
  const account=state.accounts.find(a=>a.id===selected);if(!account)return;
  const data={provider_id:account.provider_id||account.id,email:$("new-account-email").value,label:$("new-account-label").value.trim(),confirmed:true};
  addingAccount=true;renderDetail();$("new-account-error").classList.add("hidden");
  try{
    const result=await api("/api/accounts",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
    await refresh();selected=result.id;toast(t("Separate account added to your local inventory."));
  }catch(e){setMessage("new-account-error",canonicalMessage(e.message));$("new-account-error").classList.remove("hidden");}
  finally{addingAccount=false;renderDetail();}
}
function renderExport(){
  const items=state.accounts.filter(a=>a.classification!=="unknown"&&!a.checklist.saved_in_bitwarden);
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
  $("export-button").disabled=bitwardenBusy||!eligible.size;
}
function actionButton(text,action,disabled=false){
  const button=node("button",t(text),"button secondary");button.onclick=action;button.disabled=disabled;return button;
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
    card.append(node("strong",accountTitle(account)),node("p",t(item.deferred&&item.step!=="done"?"Deferred. Restore this account when you are ready.":workflowSteps[item.step])));
    const actions=node("div",undefined,"bitwarden-actions");
    actions.append(actionButton("Review →",()=>continueWorklist(item.id),workflowBusy||workflow.paused),
      actionButton(item.deferred?"Restore":"Defer",()=>changeWorklist({action:item.deferred?"restore":"defer",id:item.id}),workflowBusy||item.step==="done"),
      actionButton("Remove from worklist",()=>changeWorklist({action:"remove",id:item.id}),workflowBusy));
    card.append(actions);return card;
  }));
  if(!workflow.items.length)$("worklist-items").append(node("p",t("Your worklist is empty. Choose accounts below.")));
  const queued=new Set(workflow.items.map(item=>item.id));
  const available=state.accounts.filter(a=>a.classification!=="unknown"&&a.status!=="done"&&!queued.has(a.id));
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
  if(step==="review")return t("Confirm the account after your own review, then complete this checklist step.");
  if(step==="bitwarden")return t("Prepare an empty Bitwarden item for this exact account. ARGUS never generates or handles its password.");
  if(step==="change_password")return account.password_url?t("Open the verified provider page, change the password in your browser, then return here and complete the checklist step."):t("No verified password-settings link is available. Open the provider website and navigate manually.");
  if(step==="test_signin")return t("Test the sign-in yourself, then complete this checklist step.");
  if(step==="finish")return t("Required steps are checked. You can mark this account done.");
  return t("This account is complete.");
}
function renderGuided(){
  const workflow=state.workflow;
  const current=state.accounts.find(account=>account.id===workflow.current);
  const suggested=state.accounts.find(account=>account.id===workflow.suggested);
  const account=current||suggested;
  if(!account){
    $("guided-dashboard-title").textContent=t("Your current security work is complete.");
    $("guided-dashboard-copy").textContent=t("No incomplete discovered account is ready for a guided session.");
    $("guided-dashboard-start").disabled=true;
    $("guided-current-card").classList.add("guided-current-blocked");
    $("guided-status").textContent=t("Ready");
    $("guided-current-copy").textContent=t("No incomplete discovered account is ready for a guided session.");
    $("guided-current-open").disabled=true;$("guided-build-worklist").disabled=true;$("guided-current-defer").disabled=true;
    return;
  }
  const step=accountStep(account), actionLabel=current?t("Continue to next account"):t("Secure next account");
  $("guided-dashboard-title").textContent=t("Secure {p0} next",{p0:accountTitle(account)});
  $("guided-dashboard-copy").textContent=guidedStepCopy(account,step);
  $("guided-dashboard-start").textContent=actionLabel+" →";
  $("guided-dashboard-start").disabled=workflowBusy;
  $("guided-current-card").classList.toggle("guided-current-blocked",!current||workflow.paused||account.identity_review_required);
  $("guided-status").textContent=t(account.identity_review_required?"Blocked: identify the sign-in address":workflow.paused?"Paused":current?"Action required":"Ready");
  $("guided-current-copy").textContent=`${accountTitle(account)} · ${guidedStepCopy(account,step)}`;
  $("guided-current-open").textContent=actionLabel;
  $("guided-current-open").disabled=workflowBusy;
  $("guided-build-worklist").disabled=workflowBusy||!suggested;
  $("guided-current-defer").disabled=workflowBusy||!current;
}
async function changeWorklist(data){
  if(workflowBusy)return false;workflowBusy=true;renderWorklist();
  try{const result=await api("/api/workflow",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});await refresh();if($("account-dialog").open)renderDetail();return result;}
  catch(e){error(e.message);return false;}
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
  if(!state.workflow.suggested||workflowBusy)return;
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
  catch(e){error(e.message);}finally{bitwardenBusy=false;renderExport();renderHandoffs();}
}
async function exportMetadata(){
  if(bitwardenBusy)return;
  const ids=selectedBitwardenIds();
  if(!ids.length){error(t("Select the accounts you want to add to Bitwarden first."));return;}
  bitwardenBusy=true;renderExport();
  try{
    const result=await api("/api/bitwarden",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({ids,language})});
    const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:"application/json"}));
    const a=document.createElement("a");a.href=url;a.download="account-finder-bitwarden.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast(t("Metadata downloaded. No vault was changed."));
  }catch(e){error(e.message);}finally{bitwardenBusy=false;renderExport();}
}
function selectedBitwardenIds(){
  return Array.from($("export-selection").querySelectorAll("input:checked:not(:disabled)")).map(x=>x.value);
}
async function addToUnlockedBitwarden(){
  if(bitwardenBusy||state.demo)return;
  const ids=selectedBitwardenIds();
  if(!ids.length){error(t("Select the accounts you want to add to Bitwarden first."));return;}
  if(!window.confirm(t("ARGUS will create password-free items in your already-unlocked Bitwarden vault. Existing items are never changed. Continue?")))return;
  bitwardenBusy=true;renderExport();
  try{
    const result=await api("/api/bitwarden/cli",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({ids,language})});
    await refresh();if(result.status==="needs_review")error(t("The transfer result is unclear. Check Bitwarden below before trying again."));else toast(t("Added {count} password-free item(s) to Bitwarden. Generate the new password in Bitwarden, use the verified provider link to change it, then test the sign-in.",{count:result.items}));
  }catch(e){error(canonicalMessage(e.message));try{await refresh();}catch(_){} }finally{bitwardenBusy=false;renderExport();renderHandoffs();}
}
async function prepareGuidedBitwarden(){
  const account=state.accounts.find(item=>item.id===selected);
  if(!account||account.id!==state.workflow.current||accountStep(account)!=="bitwarden"||bitwardenBusy||state.demo)return;
  if(!window.confirm(t("ARGUS will create one password-free item for this exact account in your already-unlocked Bitwarden vault. Existing items are never changed. Continue?")))return;
  bitwardenBusy=true;renderDetail();renderExport();
  try{
    const result=await api("/api/secure-next/bitwarden",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({account_id:account.id,language,confirmed:true})});
    await refresh();
    if(result.status==="needs_review")error(t("The transfer result is unclear. Check Bitwarden below before trying again."));
    else toast(t("Bitwarden preparation saved locally. Generate the password in Bitwarden, then continue with the verified provider page."));
  }catch(e){error(canonicalMessage(e.message));try{await refresh();}catch(_){} }
  finally{bitwardenBusy=false;renderExport();renderHandoffs();if($("account-dialog").open)renderDetail();}
}
async function completeGuidedStep(){
  const account=state.accounts.find(item=>item.id===selected);
  const completion=$("guided-complete-step").dataset.completion;
  if(!account||account.id!==state.workflow.current||!completion||saving)return;
  const change=completion==="done"?{status:"done"}:{checklist:{[completion]:true}};
  const message=completion==="done"?"Confirm that you completed every required step for this account.":"Confirm that you completed this step yourself. ARGUS will only record your confirmation locally.";
  if(!window.confirm(t(message)))return;
  await update(change);
}
async function activateLicense(){
  const file=$("license-file").files[0];
  if(!file){error(t("Choose a license file first."));return;}
  $("activate-license").disabled=true;
  try{
    const license=JSON.parse(await file.text());
    const result=await api("/api/license/activate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({license})});
    await refresh();toast(t(result.message));
  }catch(e){error(e instanceof SyntaxError?t("Invalid license file."):e.message);}
  finally{if(state)$('activate-license').disabled=!state.product.license.activation_enabled;}
}
async function importFiles(){
  const files=Array.from($("email-files").files);if(!files.length)return;
  $("import-progress").classList.remove("hidden");$("import-button").disabled=true;$("email-files").disabled=true;
  $("import-meter").value=0;
  importCancelled=false;let stats=null,failed=false;
  try{
    stats=await api("/api/import/start",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({expected:files.length})});
    activeBatch=stats.id;$("cancel-import").classList.remove("hidden");$("cancel-import").disabled=false;$("add-alias-button").disabled=true;
    renderScan(stats);$("import-status").textContent=scanDescription(stats);
    for(const file of files){
      if(importCancelled)break;
      if(!file.name.toLowerCase().endsWith(".eml")||file.size>2*1024*1024||file.size===0){stats=await api("/api/import/skip",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id:activeBatch})});}
      else {stats=await api("/api/import",{method:"POST",headers:{"Content-Type":"message/rfc822","X-Import-ID":activeBatch},body:file});}
      $("import-meter").value=stats.processed*100/files.length;$("import-status").textContent=scanDescription(stats);renderScan(stats);
      if(stats.scope_changed){failed=true;error(t("The address scope changed during import. Restart the import."));break;}
    }
  }catch(e){failed=true;error(e.message);}
  finally{
    if(activeBatch){try{stats=await api("/api/import/finish",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id:activeBatch,...(importCancelled||failed?{result:"partial"}:{})})});$("import-status").textContent=scanDescription(stats);renderScan(stats);}catch(e){error(e.message);}}
    activeBatch=null;$("cancel-import").classList.add("hidden");$("cancel-import").disabled=false;
    $("import-button").disabled=false;$("email-files").disabled=false;$("email-files").value="";
    try{await refresh();if(stats)toast(stats.result==="completed"?t("Local import completed."):t("Import status saved locally. Clues are preserved."));}catch(e){error(e.message);}
  }
}
async function cancelImport(){
  if(activeBatch){importCancelled=true;$("cancel-import").disabled=true;$("import-status").textContent=t("Stopping after the current file. Saved clues are preserved.");return;}
  if(state.active_import){try{await api("/api/import/finish",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id:state.active_import.id,result:"partial"})});await refresh();toast(t("Import canceled; clues remain saved."));}catch(e){error(e.message);}}
}
async function addAlias(event){
  event.preventDefault();if(addingAlias)return;addingAlias=true;$("add-alias-button").disabled=true;
  try{
    const result=await api("/api/profile/emails",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({emails:[$("alias-email").value.trim()]})});
    await refresh();$("alias-email").value="";$("alias-owned").checked=false;
    setMessage("alias-message",result.added.length?"Own address added. Re-import older local emails or run the authorized IMAP scan again. Your checklists were preserved.":"This address was already configured. Nothing was changed.");
  }catch(e){error(e.message);}finally{addingAlias=false;$("add-alias-button").disabled=state.demo||Boolean(activeBatch||state.active_import);}
}
document.querySelectorAll("[data-view]").forEach(b=>b.onclick=()=>navigate(b.dataset.view));
document.querySelectorAll("[data-go]").forEach(b=>b.onclick=()=>navigate(b.dataset.go));
document.querySelector(".brand").onclick=e=>{e.preventDefault();navigate("dashboard");};
for(const id of ["search","category","classification","status-filter"])$(id).addEventListener(id==="search"?"input":"change",renderRows);
$("close-dialog").onclick=()=>$("account-dialog").close();
$("login-method").onchange=()=>update({login_method:$("login-method").value});
$("registered-email").onchange=()=>update({registered_email:$("registered-email").value||null});
$("add-account-form").onsubmit=addLocalAccount;
$("detail-priority").onchange=()=>update({priority:$("detail-priority").value});
$("defer-account").onclick=()=>update({status:"skipped"});
$("finish-account").onclick=()=>update({status:"done"});
$("export-button").onclick=exportMetadata;
$("bitwarden-cli-button").onclick=addToUnlockedBitwarden;
$("worklist-add").onclick=()=>{const ids=Array.from($("worklist-selection").querySelectorAll("input:checked")).map(input=>input.value);if(!ids.length){error(t("Select accounts for your worklist first."));return;}changeWorklist({action:"add",ids});};
$("worklist-continue").onclick=()=>continueWorklist();
$("worklist-pause").onclick=()=>changeWorklist({action:state.workflow.paused?"resume":"pause"});
$("guided-dashboard-start").onclick=startGuided;
$("guided-current-open").onclick=startGuided;
$("guided-build-worklist").onclick=buildPriorityWorklist;
$("guided-current-defer").onclick=()=>{const id=state.workflow.current;if(id)changeWorklist({action:"defer",id});};
$("detail-worklist").onclick=()=>changeWorklist({action:"add",ids:[selected]});
$("detail-bitwarden").onclick=()=>{const account=state.accounts.find(a=>a.id===selected);if(!account||account.identity_review_required)return;exportChoices.clear();exportChoices.set(selected,true);for(const a of state.accounts)if(a.id!==selected)exportChoices.set(a.id,false);$("account-dialog").close();navigate("bitwarden");renderExport();};
$("guided-prepare-bitwarden").onclick=prepareGuidedBitwarden;
$("guided-complete-step").onclick=completeGuidedStep;
$("activate-license").onclick=activateLicense;
$("import-button").onclick=()=>{navigate("setup");$("email-files").click();};
$("email-files").onchange=importFiles;
$("cancel-import").onclick=cancelImport;
$("alias-form").onsubmit=addAlias;
document.querySelectorAll(".language-control").forEach(e=>e.onchange=()=>applyLanguage(e.value,true));
applyLanguage(language);
refresh().catch(e=>error(e.message));
// Poll only the local server; CLI scans update the same database.
setInterval(()=>{if(!saving && !$("account-dialog").open && !$("email-files").disabled)refresh().catch(e=>error(e.message));},15000);
