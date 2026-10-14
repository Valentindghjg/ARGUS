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
let activeBatch=null, importCancelled=false, addingAlias=false;
let displayedScan=null;
const exportChoices=new Map();
const labels = {confirmed:"Confirmed",probable:"Probable",unknown:"Unknown",pending:"Pending",in_progress:"In progress",done:"Done",skipped:"Deferred",critical:"Do first",high:"High",normal:"Normal"};
const titles = {
  dashboard:["Your accounts, in one place.","Find local evidence and secure your accounts with Bitwarden.","Overview"],
  accounts:["Your digital inventory.","Review your clues and keep unknown services in view.","All accounts"],
  security:["Secure the most important accounts first.","Prioritize your mailbox, finance and central services.","Security priorities"],
  bitwarden:["A secure password for every account.","Prepare new vault items and make the changes yourself.","Prepare Bitwarden"],
  setup:["Start with your mailbox.","Import existing messages or set up read-only IMAP access.","Mailbox & Import"]
};
function node(tag, text, className) { const e=document.createElement(tag); if(text!==undefined)e.textContent=text; if(className)e.className=className; return e; }
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
  $("progress-bar").setAttribute("aria-valuenow",s.progress);
  $("demo-banner").classList.toggle("hidden",!state.demo);
  $("rescan-banner").classList.toggle("hidden",!state.stale_evidence);
  $("rescan-banner").textContent=t("{p0} older clues need the current detection rules. Re-import the original emails or start an authorized IMAP scan. Your checklists are preserved.",{p0:(state.stale_evidence||0)});
  const previous=$("category").value;
  $("category").replaceChildren(new Option(t("All categories"),""),...Array.from(new Set(state.accounts.map(a=>a.category))).sort().map(c=>new Option(t(c),c)));
  $("category").value=previous;
  $("profile-email").textContent=t("Configured addresses: {p0}",{p0:(state.emails.join(", "))});
  const domain=(state.emails[0]||"").split("@")[1]||"your-domain.example";
  $("discover-command").textContent=`python -m account_finder discover --domain ${domain} --allow-dns`;
  renderScan(state.active_import||state.last_scan);
  $("cancel-import").classList.toggle("hidden",!activeBatch&&!state.active_import);
  $("add-alias-button").disabled=state.demo||addingAlias||Boolean(activeBatch||state.active_import);
  $("alias-email").disabled=state.demo;$("alias-owned").disabled=state.demo;
  if(state.demo)setMessage("alias-message","Add real own addresses in a personal profile on your computer. The demo profile stays separate.");
  renderRows();renderCandidates();renderExport();
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
    return `${a.name} ${a.category} ${t(a.category)} ${a.registered_emails.join(" ")}`.toLocaleLowerCase(language).includes(query);
  });
}
function renderRows(){
  const rows=filtered();$("visible-count").textContent=t("{p0} items",{p0:(rows.length)});
  const fragment=document.createDocumentFragment();
  for(const a of rows){
    const tr=node("tr");const provider=node("td");const flex=node("div",undefined,"provider-cell");flex.append(node("span",a.name[0],"avatar"));
    const info=node("div");info.append(node("strong",a.name),node("small",a.registered_emails.join(", ")||t(a.category)));flex.append(info);provider.append(flex);
    const detected=node("td");detected.append(node("span",t(labels[a.classification]),`chip ${a.classification}`));detected.append(node("small",a.classification==="confirmed"?t("Reviewed by you"):a.score?t("Clue strength {p0}/100",{p0:(a.score)}):t("No reliable clue"),"evidence-hint"));
    const priority=node("td");priority.append(node("span",t(labels[a.priority]),`priority ${a.priority}`));
    const status=node("td");status.append(node("span",t(labels[a.status]),`status ${a.status}`));
    const action=node("td");const button=node("button",t("Review →"),"row-open");button.setAttribute("aria-label",t("Review {p0}",{p0:(a.name)}));button.onclick=()=>openDetail(a.id);action.append(button);
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
function renderDetail(){
  const a=state.accounts.find(x=>x.id===selected);if(!a)return;
  $("detail-name").textContent=a.name;
  $("detail-meta").replaceChildren(node("span",t(labels[a.classification]),`chip ${a.classification}`),node("p",`${t(a.category)} · ${a.registered_emails.join(", ")||t("Sign-in address not known from evidence")}`),node("p",t(a.reason)));
  const links=[link(t("Official website ↗"),a.website)];
  if(a.password_url){links.push(link(t("Documented password settings ↗"),a.password_url),link(t("Source · checked {p0} ↗",{p0:(a.password_verified)}),a.password_source));}
  else links.push(node("span",t("No verified direct password-settings link."),"small-muted"));
  if(a.historical)links.push(node("span",t("Historical service: check its current status."),"small-muted"));
  $("detail-links").replaceChildren(...links);
  $("login-method").value=a.login_method;$("detail-priority").value=a.priority;
  $("registered-email").replaceChildren(new Option(t("Email evidence only / unknown"),""),...state.emails.map(e=>new Option(e,e)));
  $("registered-email").value=a.manual_email||"";
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
    const label=node("label",undefined,"check-item");const checkbox=node("input");checkbox.type="checkbox";checkbox.checked=a.checklist[key];checkbox.disabled=saving;
    checkbox.onchange=()=>update({checklist:{[key]:checkbox.checked}});
    const text=node("span",title);text.append(node("small",description));label.append(checkbox,text);items.push(label);
  }
  $("checklist").replaceChildren(...items);
  $("detail-evidence").replaceChildren(...(a.evidence.length?a.evidence.map(e=>{const card=node("div",t(e.reason),"evidence-card");let date=t("Date unknown");if(e.date){const parsed=new Date(e.date);if(!Number.isNaN(parsed.getTime()))date=parsed.toLocaleDateString(language==="de"?"de-DE":"en-GB",{day:"numeric",month:"short",year:"numeric"});}card.append(node("small",`${e.sender_domain} · ${date} · ${e.source} · ${t("Strength {score}/100",{score:e.score})}${e.caveat?" · "+translateCaveat(e.caveat):""}`));return card;}):[node("p",t("No local evidence. This does not prove that an account does not exist."),"small-muted")]));
  const required=["reviewed","saved_in_bitwarden","login_tested",...(a.login_method==="password"?["password_changed"]:[])];
  $("finish-account").disabled=saving||!required.every(k=>a.checklist[k]);
  $("finish-account").textContent=a.status==="done"?t("Already done"):t("Mark as done");
  $("login-method").disabled=saving;$("registered-email").disabled=saving;$("detail-priority").disabled=saving;$("defer-account").disabled=saving;
}
async function update(change){
  if(saving)return;saving=true;renderDetail();$("detail-error").classList.add("hidden");
  try{await api(`/api/accounts/${encodeURIComponent(selected)}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify(change)});await refresh();toast(t("Change saved locally."));}
  catch(e){setMessage("detail-error",canonicalMessage(e.message));$("detail-error").classList.remove("hidden");}
  finally{saving=false;renderDetail();}
}
function renderExport(){
  const items=state.accounts.filter(a=>a.classification!=="unknown"&&!a.checklist.saved_in_bitwarden);
  const eligible=new Set(items.map(a=>a.id));
  for(const id of exportChoices.keys())if(!eligible.has(id))exportChoices.delete(id);
  $("export-selection").replaceChildren(...items.map(a=>{
    const label=node("label");const checkbox=node("input");checkbox.type="checkbox";checkbox.value=a.id;checkbox.checked=exportChoices.has(a.id)?exportChoices.get(a.id):a.classification==="confirmed";
    checkbox.onchange=()=>exportChoices.set(a.id,checkbox.checked);label.append(checkbox,node("span",`${a.name} · ${t(labels[a.classification])}`));return label;
  }));
  if(!items.length)$("export-selection").append(node("p",t("No missing items selected. Review your accounts and existing vault items first.")));
}
async function exportMetadata(){
  const ids=Array.from($("export-selection").querySelectorAll("input:checked")).map(x=>x.value);
  if(!ids.length){error(t("Select the accounts you want to add to Bitwarden first."));return;}
  $("export-button").disabled=true;
  try{
    const result=await api("/api/bitwarden",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({ids,language})});
    const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:"application/json"}));
    const a=document.createElement("a");a.href=url;a.download="account-finder-bitwarden.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast(t("Metadata downloaded. No vault was changed."));
  }catch(e){error(e.message);}finally{$("export-button").disabled=false;}
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
$("detail-priority").onchange=()=>update({priority:$("detail-priority").value});
$("defer-account").onclick=()=>update({status:"skipped"});
$("finish-account").onclick=()=>update({status:"done"});
$("export-button").onclick=exportMetadata;
$("import-button").onclick=()=>{navigate("setup");$("email-files").click();};
$("email-files").onchange=importFiles;
$("cancel-import").onclick=cancelImport;
$("alias-form").onsubmit=addAlias;
document.querySelectorAll(".language-control").forEach(e=>e.onchange=()=>applyLanguage(e.value,true));
applyLanguage(language);
refresh().catch(e=>error(e.message));
// Poll only the local server; CLI scans update the same database.
setInterval(()=>{if(!saving && !$("account-dialog").open && !$("email-files").disabled)refresh().catch(e=>error(e.message));},15000);
