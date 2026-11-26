import json
import hashlib
import requests
from urllib.parse import quote
import streamlit as st
from jm_frontend.config import get_config
from jm_frontend.auth import sign_in, sign_up, sign_out_local
from jm_frontend.api import ApiClient
from jm_frontend.schema_ui import render_operation_form, operation_summary, resolve_ref

st.set_page_config(page_title="JurisMind | Legal Intelligence", page_icon="⚖️", layout="wide", initial_sidebar_state="expanded")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {font-family:'DM Sans',sans-serif;}
.block-container {padding-top:1.35rem;padding-bottom:2.8rem;max-width:1500px;}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#101b2d 0%,#14243a 100%);border-right:1px solid #24354b;}
[data-testid="stSidebar"] * {color:#e8eef7;}
[data-testid="stSidebar"] [data-testid="stRadio"] label {padding:.45rem .6rem;border-radius:9px;}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {background:#233852;}
h1,h2,h3 {font-family:'Manrope',sans-serif;letter-spacing:-.035em;}
.jm-brand {font-family:'Manrope',sans-serif;font-size:1.65rem;font-weight:800;letter-spacing:-.06em;color:#fff;}
.jm-kicker {text-transform:uppercase;letter-spacing:.13em;font-size:.68rem;font-weight:700;color:#7892b2;}
.jm-hero {background:linear-gradient(120deg,#132b48 0%,#1d456b 58%,#28658a 100%);padding:1.8rem 2rem;border-radius:18px;color:white;margin-bottom:1.1rem;}
.jm-hero h1 {color:white;margin:.3rem 0 .4rem;font-size:2.15rem;}
.jm-hero p {color:#d6e5f3;margin:0;max-width:760px;}
.jm-stat {border:1px solid rgba(120,140,165,.24);border-radius:15px;padding:1rem 1.1rem;background:var(--secondary-background-color);min-height:116px;}
.jm-stat-label {font-size:.78rem;color:var(--text-color);opacity:.68;}
.jm-stat-value {font-family:'Manrope',sans-serif;font-size:1.5rem;font-weight:800;margin-top:.35rem;}
.jm-panel {border:1px solid rgba(120,140,165,.24);border-radius:14px;padding:1rem 1.1rem;margin:.4rem 0 1rem;}
.jm-pill {display:inline-block;border-radius:999px;padding:.2rem .6rem;background:#e6f2fb;color:#1c5278;font-size:.72rem;font-weight:700;}
div.stButton > button[kind="primary"] {background:#1f6b91;border-color:#1f6b91;}
small,.stCaption {color:#7d8998;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
cfg = get_config()

def init_state():
    defaults={"access_token":None,"refresh_token":None,"user_email":None,"supabase_user_id":None,
              "openapi":None,"last_result":None,"last_endpoint":None,"active_page":"Overview","tenant_id":None,"selected_snapshot_id":None}
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v
init_state()

def show_login():
    a,b,c=st.columns([1,1.1,1])
    with b:
        st.markdown("<div style='height:5vh'></div>",unsafe_allow_html=True)
        st.markdown("<div class='jm-brand' style='color:#17324d'>⚖️ JurisMind</div>",unsafe_allow_html=True)
        st.markdown("<div class='jm-kicker'>LEGAL INTELLIGENCE PLATFORM</div>",unsafe_allow_html=True)
        st.markdown("## Welcome to JurisMind")
        sign_in_tab, sign_up_tab = st.tabs(["Sign in", "Create account"])
        with sign_in_tab:
            st.write("Sign in with your existing JurisMind account.")
            with st.form("signin",clear_on_submit=False):
                email=st.text_input("Email address",placeholder="name@firm.com",key="signin_email")
                password=st.text_input("Password",type="password",key="signin_password")
                submit=st.form_submit_button("Sign in securely",type="primary",use_container_width=True)
            if submit:
                if not email.strip() or not password:
                    st.error("Enter both your email and password.")
                else:
                    with st.spinner("Verifying your Supabase account…"):
                        try:
                            result=sign_in(cfg,email.strip(),password)
                            # Idempotent provisioning also completes sign-ups that
                            # required email confirmation before issuing a session.
                            provision = requests.post(
                                f"{cfg.api_base_url}/auth/provision",
                                headers={"Authorization": f"Bearer {result['access_token']}", "Content-Type": "application/json"},
                                json={"email": result.get("email") or email.strip(), "workspace_name": "My JurisMind Workspace"},
                                timeout=cfg.request_timeout,
                            )
                            if not provision.ok:
                                try: detail=provision.json().get("detail", "Account provisioning failed.")
                                except Exception: detail="Account provisioning failed."
                                raise RuntimeError(f"{detail} (HTTP {provision.status_code})")
                            provision_data = provision.json()
                            st.session_state.tenant_id = provision_data.get("tenant_id")
                            if not st.session_state.tenant_id:
                                raise RuntimeError("Workspace provisioning succeeded but no tenant ID was returned.")
                            st.session_state.access_token=result["access_token"]
                            st.session_state.refresh_token=result.get("refresh_token")
                            st.session_state.user_email=result.get("email") or email.strip()
                            st.session_state.supabase_user_id=result.get("user_id")
                            st.session_state.openapi=None
                            st.rerun()
                        except Exception as e: st.error(str(e))
        with sign_up_tab:
            st.write("Create a Supabase-authenticated JurisMind account and personal workspace.")
            with st.form("signup",clear_on_submit=False):
                new_email=st.text_input("Email address",placeholder="name@firm.com",key="signup_email")
                new_password=st.text_input("Password",type="password",key="signup_password")
                confirm_password=st.text_input("Confirm password",type="password",key="signup_confirm")
                workspace=st.text_input("Workspace name",value="My JurisMind Workspace",max_chars=200)
                accepted=st.checkbox("I understand that JurisMind provides AI-generated legal information, not legal advice.")
                create=st.form_submit_button("Create account",type="primary",use_container_width=True)
            if create:
                if not new_email.strip() or len(new_password)<8:
                    st.error("Enter a valid email and a password of at least 8 characters.")
                elif new_password != confirm_password:
                    st.error("The passwords do not match.")
                elif not accepted:
                    st.error("Please acknowledge the legal-information disclaimer to continue.")
                else:
                    with st.spinner("Creating your Supabase account…"):
                        try:
                            result=sign_up(cfg,new_email.strip(),new_password)
                            if not result.get("access_token"):
                                st.success("Your account was created. Check your email to confirm it, then return here to sign in. Workspace provisioning will complete after confirmation and first sign-in.")
                            else:
                                provision = requests.post(
                                    f"{cfg.api_base_url}/auth/provision",
                                    headers={"Authorization": f"Bearer {result['access_token']}", "Content-Type": "application/json"},
                                    json={"email": result.get("email") or new_email.strip(), "workspace_name": workspace.strip() or "My JurisMind Workspace"},
                                    timeout=cfg.request_timeout,
                                )
                                if not provision.ok:
                                    try: detail=provision.json().get("detail", "Account created, but workspace provisioning could not be completed.")
                                    except Exception: detail="Account created, but workspace provisioning could not be completed."
                                    st.error(f"{detail} Sign in after resolving this with your administrator.")
                                else:
                                    provision_data = provision.json()
                                    st.success("Account and personal workspace created. You can now sign in.")
                        except Exception as e: st.error(str(e))
        st.caption("Authentication is handled by your existing Supabase project. JurisMind does not store your password.")
        st.warning("Legal disclaimer: JurisMind provides AI-generated legal information for research and educational purposes only. It is not legal advice. Verify authorities and consult a qualified advocate before acting.")
        if not cfg.supabase_url or not cfg.supabase_key or not cfg.api_base_url:
            st.warning("Set SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY and JURISMIND_API_URL in your .env file.")

def client():
    return ApiClient(cfg,st.session_state.access_token)

def fetch_openapi():
    if st.session_state.openapi is None:
        try:
            r=client().request("GET","/openapi.json",auth=False)
            if r.ok: st.session_state.openapi=r.json()
            else: st.error(f"Could not load API schema (HTTP {r.status_code}).")
        except Exception as e: st.error(f"Backend connection failed: {e}")

GROUPS = {
"Overview":("Overview","⌂"),
"Legal Research":("Research","⌕"),
"Statutory Intelligence":("Statutory","§"),
"Judgment Intelligence":("Judgments","⚖"),
"Research & Reasoning":("Reasoning","◇"),
"Due Diligence & Risk":("Due Diligence","▤"),
"Legal Drafting":("Drafting","✎"),
"Matter Management":("Platform","▣"),
"Agents & Evidence":("Agents","✧"),
"API Workbench":("Workbench","⌘"),
}
def group_for(path,tag=""):
    p=path.lower()
    if p.startswith("/health") or p=="/": return "Overview"
    if "/statutes" in p: return "Statutory Intelligence"
    if "/judgments" in p: return "Judgment Intelligence"
    if "/reasoning" in p: return "Research & Reasoning"
    if p.startswith("/due-diligence"): return "Due Diligence & Risk"
    if p.startswith("/drafting"): return "Legal Drafting"
    if p.startswith("/platform"): return "Matter Management"
    if any(x in p for x in ["/agents","/agent-runs","/citations","/evidence","/claims","/treatments","/ingestion"]): return "Agents & Evidence"
    if p.startswith("/research"): return "Legal Research"
    return "API Workbench"

def get_operations(schema):
    items=[]
    for path, methods in (schema or {}).get("paths",{}).items():
        for method, op in methods.items():
            if method.lower() not in {"get","post","patch","put","delete"}: continue
            tags=op.get("tags",[])
            items.append({"path":path,"method":method.upper(),"op":op,
                          "group":group_for(path,tags[0] if tags else "")})
    return items

def render_overview():
    st.markdown("<div class='jm-hero'><div class='jm-kicker' style='color:#a9c7df'>YOUR LEGAL WORKSPACE</div><h1>Clarity for complex legal work.</h1><p>Research authorities, analyse judgments, assess transaction risk and prepare evidence-linked legal work from one connected workspace.</p></div>",unsafe_allow_html=True)
    c=client()
    with st.spinner("Connecting to JurisMind services…"):
        health=c.request("GET","/health/ready",auth=False)
        agents=c.request("GET","/research/agents")
        readiness=c.request("GET","/research/corpus-readiness")
    cols=st.columns(4)
    vals=[
        ("Backend status","Online" if health.ok else "Unavailable","●"),
        ("Authenticated API","Connected" if agents.ok else f"HTTP {agents.status_code}","◈"),
        ("Specialist agents",str(len(agents.json())) if agents.ok and isinstance(agents.json(),list) else "Available" if agents.ok else "—","✧"),
        ("Legal corpus","Ready" if readiness.ok else "Check status","§"),
    ]
    for col,(label,value,ico) in zip(cols,vals):
        with col: st.markdown(f"<div class='jm-stat'><div class='jm-stat-label'>{ico} &nbsp;{label}</div><div class='jm-stat-value'>{value}</div></div>",unsafe_allow_html=True)
    if not health.ok:
        st.warning("The API readiness check did not succeed. Confirm that the FastAPI backend is running and JURISMIND_API_URL is correct.")
    if agents.status_code==403:
        st.error("Supabase login succeeded, but the backend does not recognise this user as a provisioned JurisMind account. Check the matching app_users record.")
    elif agents.status_code==401: st.error("The backend rejected the access token. Sign out and sign in again.")
    elif agents.ok: st.success("Supabase authentication and protected FastAPI access are working.")
    st.markdown("### Your workspace")
    tiles=[
      ("Legal Research","Hybrid legal search, research snapshots and corpus readiness.","Legal Research"),
      ("Statutory Intelligence","Versioned provisions, effective dates and commencement history.","Statutory Intelligence"),
      ("Judgment Intelligence","Create judgment analyses and review findings.","Judgment Intelligence"),
      ("Research & Reasoning","Issue workspaces and structured legal reasoning.","Research & Reasoning"),
      ("Due Diligence & Risk","Transaction matters, risk registers and document comparisons.","Due Diligence & Risk"),
      ("Legal Drafting","Create, retrieve and revise legal drafts.","Legal Drafting"),
      ("Matter Management","Tasks, agent reviews, quality checks, reports and audit history.","Matter Management"),
      ("Agents & Evidence","Specialist agents, citations, claims and evidence provenance.","Agents & Evidence"),
    ]
    for row in range(0,len(tiles),4):
        cols=st.columns(4)
        for col,(title,desc,page) in zip(cols,tiles[row:row+4]):
            with col:
                st.markdown(f"<div class='jm-panel' style='min-height:138px'><div class='jm-kicker'>{title}</div><div style='font-size:.88rem;margin-top:.45rem'>{desc}</div></div>",unsafe_allow_html=True)
                if st.button(f"Open {title} →",key=f"tile_{page}",use_container_width=True):
                    st.session_state.active_page=page
                    st.rerun()
    with st.expander("Backend diagnostics"):
        st.write("API URL:",cfg.api_base_url)
        st.write("Readiness:",health.status_code,health.text[:1000])
        if readiness.ok: st.json(readiness.json())


def render_legal_research():
    """Purpose-built UI for the existing authenticated research snapshot APIs."""
    st.title("Legal Research")
    st.caption("Research the indexed legal corpus, save reproducible snapshots and inspect retrieved evidence.")

    tenant_id = st.session_state.get("tenant_id")
    if not tenant_id:
        st.error("Your workspace ID is not available in this session. Please sign out and sign in again.")
        return

    api = client()

    # Official-source research searches official domains and attempts permitted document retrieval.
    with st.container(border=True):
        st.subheader("External official-source research")
        st.caption("Search official Indian legal-source domains and retrieve accessible original documents. Search results and retrieved documents remain unverified until authority review.")
        with st.form("official_source_discovery_form", clear_on_submit=False):
            discovery_question = st.text_area(
                "Legal issue or search query *",
                placeholder="Example: IBC Section 7 admission requirements and Supreme Court interpretation",
                height=90,
                max_chars=500,
            )
            d1, d2 = st.columns(2)
            with d1:
                discovery_jurisdiction = st.selectbox(
                    "Jurisdiction", ["India", "Uttar Pradesh", "Other / not specified"], index=0
                )
            with d2:
                discovery_court = st.selectbox(
                    "Court (optional)", ["", "Supreme Court of India", "Allahabad High Court", "Lucknow Bench"], index=0
                )
            d3, d4, d5 = st.columns(3)
            with d3:
                include_legislation = st.checkbox("Legislation · India Code", value=True)
            with d4:
                include_gazette = st.checkbox("Gazette notifications", value=True)
            with d5:
                include_judgments = st.checkbox("Judgments", value=True)
            discover_submitted = st.form_submit_button("Search official legal sources", type="primary", use_container_width=True)
        if discover_submitted:
            selected_categories = []
            if include_legislation:
                selected_categories.append("legislation")
            if include_gazette:
                selected_categories.append("gazette")
            if include_judgments:
                selected_categories.append("judgment")
            if len(discovery_question.strip()) < 3:
                st.error("Enter a search query of at least 3 characters.")
            elif not selected_categories:
                st.error("Select at least one source category.")
            else:
                payload = {
                    "tenant_id": tenant_id,
                    "question": discovery_question.strip(),
                    "jurisdiction": None if discovery_jurisdiction == "Other / not specified" else discovery_jurisdiction,
                    "court": discovery_court or None,
                    "categories": selected_categories,
                }
                try:
                    response = api.request("POST", "/research/search/official", json_body=payload)
                    if response.ok:
                        external = response.json()
                        search_state = external.get("external_search_status", "unknown")
                        if search_state == "completed":
                            st.success("Official-source search completed. Results still require legal-authority verification.")
                        elif search_state == "partial":
                            st.warning("Official-source search partially completed. One or more providers failed; see source status below.")
                        elif search_state == "provider_error":
                            st.error("Official-source providers failed. No successful search results were returned; see provider errors below.")
                        else:
                            st.info("Official-source search returned no matching results.")
                        metric_cols = st.columns(4)
                        metric_cols[0].metric("Search results", external.get("search_results_count", external.get("result_count", 0)))
                        metric_cols[1].metric("Downloaded", external.get("downloaded_documents_count", external.get("document_count", 0)))
                        metric_cols[2].metric("Text extracted", external.get("extracted_documents_count", external.get("document_count", 0)))
                        metric_cols[3].metric("Verified authorities", external.get("verified_authorities_count", 0))
                        st.caption(f"Failed retrievals: {external.get('failed_retrievals_count', 0)}")
                        if external.get("source_summaries"):
                            with st.expander("Per-source retrieval summary"):
                                for source_id, summary in external["source_summaries"].items():
                                    status = summary.get("search_status", "unknown").upper()
                                    st.write(
                                        f"**{summary.get('source_name', source_id)}** — {status}; "
                                        f"results: {summary.get('search_results_count', 0)}, "
                                        f"downloaded: {summary.get('downloaded_documents_count', 0)}, "
                                        f"extracted: {summary.get('extracted_documents_count', 0)}, "
                                        f"retrieval failures: {summary.get('failed_retrievals_count', 0)}"
                                    )
                                    for source_error in summary.get("search_errors", []):
                                        st.error(
                                            f"{source_error.get('failure_category', 'search_error')}: "
                                            f"HTTP {source_error.get('http_status') or '—'} — "
                                            f"{source_error.get('error', 'Provider search failed')}"
                                        )
                        st.info(external.get("notice", "Results are research leads, not verified authorities."))
                        if external.get("external_search_status") == "no_results":
                            st.warning("No official-domain results were returned. Broaden the query or inspect source access limitations.")
                        for result_index, source in enumerate(external.get("results", [])):
                            # A content hash is not a unique UI identity: different search
                            # results can resolve to identical bytes. Include the result index
                            # and URL digest so every Streamlit widget receives a unique key.
                            source_identity = str(
                                source.get("source_url")
                                or source.get("content_sha256")
                                or source.get("title")
                                or result_index
                            )
                            source_key = hashlib.sha256(
                                f"{result_index}:{source_identity}".encode("utf-8")
                            ).hexdigest()[:16]
                            with st.expander(
                                f"{source.get('source_name')} · {source.get('title') or source.get('category')}"
                            ):
                                st.caption(
                                    f"Retrieval: {source.get('retrieval_status')} · "
                                    f"Downloaded: {bool(source.get('downloaded'))} · "
                                    f"Extracted: {bool(source.get('extracted'))} · "
                                    f"Verification: {source.get('verification_status')}"
                                )
                                st.write(source.get("search_snippet") or "")
                                if source.get("source_url"):
                                    st.link_button(
                                        "Open original official source",
                                        source["source_url"],
                                        key=f"external_link_{source_key}",
                                    )
                                if source.get("extracted_text"):
                                    st.text_area(
                                        "Retrieved source text (preview)",
                                        source["extracted_text"],
                                        height=180,
                                        key=f"external_text_{source_key}",
                                    )
                                if source.get("retrieval_error"):
                                    st.warning(source["retrieval_error"])
                        if external.get("source_errors"):
                            with st.expander("Source search errors"):
                                st.json(external["source_errors"])
                    else:
                        st.error(f"Official-source research failed (HTTP {response.status_code}): {response.text[:1000]}")
                except Exception as exc:
                    st.error(f"Official-source research request failed: {exc}")

    # Corpus status is useful context, but does not certify legal authority.
    with st.container(border=True):
        st.subheader("Research corpus")
        try:
            readiness_response = api.request("GET", "/research/corpus-readiness")
            if readiness_response.ok:
                readiness = readiness_response.json()
                c1, c2, c3 = st.columns(3)
                c1.metric("Searchable chunks", readiness.get("searchable_chunks", "—"))
                c2.metric("Ingestion jobs", readiness.get("searchable_ingestion_jobs", "—"))
                c3.metric("Reviewed authority documents", readiness.get("reviewed_authority_documents", "—"))
                if readiness.get("search_ready"):
                    st.success("Repository reports that ordinary passage search is available.")
                else:
                    st.warning("The repository does not currently report search readiness.")
                if not readiness.get("authority_filtered_search_ready", False):
                    st.info("Authority-filtered search is not marked ready. Searchable passages should not be treated as reviewed legal authorities.")
            else:
                st.warning(f"Corpus readiness could not be loaded (HTTP {readiness_response.status_code}).")
        except Exception as exc:
            st.warning(f"Corpus readiness check failed: {exc}")

    st.subheader("Create a research snapshot")
    with st.form("legal_research_form", clear_on_submit=False):
        question = st.text_area(
            "Research question *",
            placeholder="Example: In what circumstances may a contract be avoided for lack of free consent under Indian contract law?",
            height=120,
            max_chars=5000,
        )
        c1, c2 = st.columns(2)
        with c1:
            jurisdiction = st.text_input("Jurisdiction", value="India", placeholder="e.g. India")
        with c2:
            court = st.text_input("Court (optional)", placeholder="e.g. Supreme Court of India")
        sub_questions_raw = st.text_area(
            "Sub-questions (optional)",
            placeholder="Enter one focused sub-question per line (maximum 8). Leave blank to let the planner generate them.",
            height=110,
        )
        per_query_limit = st.number_input("Results per sub-question", min_value=1, max_value=25, value=10, step=1)
        submitted = st.form_submit_button("Run legal research", type="primary", use_container_width=True)

    if submitted:
        cleaned_question = question.strip()
        sub_questions = [line.strip() for line in sub_questions_raw.splitlines() if line.strip()]
        if len(cleaned_question) < 8:
            st.error("Please enter a research question of at least 8 characters.")
        elif len(sub_questions) > 8:
            st.error("Please provide no more than 8 sub-questions.")
        else:
            payload = {
                "tenant_id": tenant_id,
                "question": cleaned_question,
                "jurisdiction": jurisdiction.strip() or None,
                "court": court.strip() or None,
                "sub_questions": sub_questions or None,
                "per_query_limit": int(per_query_limit),
            }
            with st.spinner("Planning research and retrieving passages…"):
                try:
                    response = api.request("POST", "/research/snapshots", json_body=payload)
                    try:
                        result = response.json()
                    except Exception:
                        result = {"detail": response.text}
                    if response.ok:
                        st.session_state.selected_snapshot_id = result.get("snapshot_id")
                        st.success("Research snapshot created successfully.")
                        st.session_state.last_research_result = result
                    else:
                        st.error(f"Research request failed (HTTP {response.status_code}).")
                        st.json(result)
                        result = None
                except Exception as exc:
                    st.error(f"Could not reach the research service: {exc}")
                    result = None

    latest = st.session_state.get("last_research_result")
    if latest:
        st.divider()
        st.subheader("Latest research snapshot")
        st.caption(f"Snapshot ID: {latest.get('snapshot_id', '—')} · Status: {latest.get('status', '—')}")
        st.markdown("**Research question**")
        st.write(latest.get("question", ""))
        plan = latest.get("plan") or {}
        summary = latest.get("summary") or {}
        with st.expander("Research plan", expanded=True):
            st.write(f"Planning method: {plan.get('planning_method', '—')}")
            for number, subq in enumerate(plan.get("sub_questions", []), start=1):
                st.markdown(f"{number}. {subq}")
            if plan.get("planning_notice"):
                st.caption(plan["planning_notice"])
        a, b, c, d = st.columns(4)
        a.metric("Queries", summary.get("query_count", "—"))
        b.metric("Internal passages", summary.get("result_count", "—"))
        c.metric("External documents", summary.get("external_document_count", 0))
        d.metric("External search", summary.get("external_search_status", "not run"))
        if summary.get("external_research"):
            ext = summary["external_research"]
            st.markdown("**External official-source results**")
            for item in ext.get("results", []):
                with st.expander(f"{item.get('source_name', 'Official source')} · {item.get('title') or 'Untitled result'}"):
                    st.caption(f"Retrieval: {item.get('retrieval_status')} · Verification: {item.get('verification_status')}")
                    st.write(item.get("search_snippet") or "")
                    if item.get("source_url"):
                        st.link_button("Open official document", item["source_url"])
                    if item.get("extracted_text"):
                        st.text(item["extracted_text"][:5000])
        if summary.get("semantic_vectors_enabled") is False:
            st.info("Semantic vector retrieval is currently disabled; this snapshot used the existing hybrid lexical search.")
        if latest.get("limitations"):
            st.warning(latest["limitations"])
        if summary.get("next_action"):
            st.caption(summary["next_action"])

    st.divider()
    st.subheader("Saved research")
    h1, h2 = st.columns([1, 5])
    with h1:
        history_limit = st.selectbox("Rows", [10, 20, 50, 100], index=1, label_visibility="collapsed")
    try:
        history_response = api.request(
            "GET", "/research/snapshots",
            params={"tenant_id": tenant_id, "limit": int(history_limit)}
        )
        if history_response.ok:
            history_data = history_response.json()
            snapshots = history_data.get("snapshots", [])
            if not snapshots:
                st.info("No saved research snapshots yet.")
            else:
                options = {
                    f"{item.get('created_at', 'Date unknown')} · {item.get('question', 'Untitled research')[:100]} · {item.get('status', '')}":
                    item.get("snapshot_id")
                    for item in snapshots
                }
                labels = list(options.keys())
                current_id = st.session_state.get("selected_snapshot_id")
                default_index = next((i for i, label in enumerate(labels) if options[label] == current_id), 0)
                chosen_label = st.selectbox("Select a saved snapshot", labels, index=default_index)
                chosen_id = options[chosen_label]
                if st.button("Load selected snapshot", key="load_research_snapshot"):
                    st.session_state.selected_snapshot_id = chosen_id
                    st.session_state.loaded_snapshot = None
                if st.session_state.get("selected_snapshot_id") == chosen_id:
                    try:
                        detail_response = api.request("GET", f"/research/snapshots/{chosen_id}")
                        if detail_response.ok:
                            detail = detail_response.json()
                            st.session_state.loaded_snapshot = detail
                        else:
                            st.error(f"Could not load snapshot (HTTP {detail_response.status_code}).")
                            detail = None
                    except Exception as exc:
                        st.error(f"Could not load snapshot: {exc}")
                        detail = None

                    detail = st.session_state.get("loaded_snapshot")
                    if detail and detail.get("snapshot_id") == chosen_id:
                        st.markdown("**Snapshot details**")
                        st.write(detail.get("question", ""))
                        st.caption(f"Status: {detail.get('status', '—')} · Created: {detail.get('created_at', '—')}")
                        if detail.get("summary"):
                            st.json(detail["summary"])
                        evidence = detail.get("evidence", [])
                        st.markdown(f"**Retrieved evidence ({len(evidence)})**")
                        if not evidence:
                            st.info("This snapshot contains no retrieved evidence records.")
                        for ev in evidence:
                            title = ev.get("filename") or f"Evidence item {ev.get('ordinal', '')}"
                            locator = ev.get("locator") or "Location not supplied"
                            pages = ""
                            if ev.get("page_start") is not None:
                                pages = f" · pages {ev.get('page_start')}"
                                if ev.get("page_end") is not None and ev.get("page_end") != ev.get("page_start"):
                                    pages += f"–{ev.get('page_end')}"
                            with st.expander(f"{ev.get('ordinal', '')}. {title} · {locator}{pages}"):
                                st.caption(f"Sub-question: {ev.get('sub_question') or '—'}")
                                fields = ev.get("retrieved_fields") or {}
                                if isinstance(fields, dict):
                                    st.json(fields)
                                else:
                                    st.write(fields)
                        st.caption("Evidence records are retrieved passages. Verify the original document, applicable version, authority status and pinpoint before relying on them.")
        else:
            st.warning(f"Saved research could not be loaded (HTTP {history_response.status_code}).")
    except Exception as exc:
        st.warning(f"Saved research request failed: {exc}")


def render_group(page, operations):
    st.title(page)
    descriptions={
      "Legal Research":"Search the indexed legal corpus and manage evidence-grounded research snapshots.",
      "Statutory Intelligence":"Explore statutory instruments, provisions, versions and temporal status.",
      "Judgment Intelligence":"Create and review structured judgment analyses.",
      "Research & Reasoning":"Create legal issue workspaces and review reasoning outputs.",
      "Due Diligence & Risk":"Manage transaction matters, risk registers and comparisons.",
      "Legal Drafting":"Create, retrieve and update source-aware legal drafts.",
      "Matter Management":"Manage matters, tasks, agent review, quality reports and audit history.",
      "Agents & Evidence":"Access specialist-agent runs, citation verification, evidence integrity and authority treatment.",
      "API Workbench":"Browse and invoke all other exposed backend operations.",
    }
    st.caption(descriptions.get(page,"Connected JurisMind backend operations."))
    if not operations:
        st.info("No API operations were found for this section in the backend OpenAPI schema.")
        return
    # Filter operations with simple search
    search=st.text_input("Filter operations",placeholder="Search endpoint, method or description…",key=f"filter_{page}")
    if search:
        operations=[x for x in operations if search.lower() in (x["path"]+" "+x["method"]+" "+x["op"].get("summary","")).lower()]
    for idx,item in enumerate(operations):
        op=item["op"]; method=item["method"]; path=item["path"]
        summary=op.get("summary") or op.get("operationId") or "API operation"
        badge_color={"GET":"#e7f2fa","POST":"#e5f5ee","PATCH":"#f0edfb","PUT":"#fff3df","DELETE":"#fdecec"}.get(method,"#eee")
        with st.expander(f"{method}   {path}     ·     {summary}",expanded=False):
            if op.get("description"): st.caption(op["description"])
            params=op.get("parameters",[])
            path_values={}
            query_values={}
            if params:
                st.markdown("**Parameters**")
                cols=st.columns(min(2,len(params)))
                for i,param in enumerate(params):
                    with cols[i%len(cols)]:
                        value=render_operation_form(param.get("schema",{}),param.get("name"),param.get("required",False),
                                                    f"{page}_{idx}_{param.get('name')}")
                        if param.get("in")=="path": path_values[param["name"]]=value
                        elif param.get("in")=="query" and value not in (None,""): query_values[param["name"]]=value
            body_schema=None
            request_body=op.get("requestBody",{})
            if request_body:
                body_schema=request_body.get("content",{}).get("application/json",{}).get("schema")
            body={}
            if body_schema:
                schema=resolve_ref(body_schema,st.session_state.openapi)
                props=schema.get("properties",{})
                required=set(schema.get("required",[]))
                if props:
                    st.markdown("**Request details**")
                    st.caption("Fields marked * are required by the backend schema.")
                    fields=list(props.items())
                    cols=st.columns(2)
                    for i,(name,field_schema) in enumerate(fields):
                        with cols[i%2]:
                            val=render_operation_form(field_schema,name,name in required,f"{page}_{idx}_body_{name}",st.session_state.openapi)
                            if val is not None and val!="": body[name]=val
                elif schema.get("type")=="array":
                    raw=st.text_area("JSON request body",value="[]",key=f"{page}_{idx}_raw")
                    try: body=json.loads(raw)
                    except Exception: st.error("Enter valid JSON.")
                else:
                    raw=st.text_area("JSON request body",value="{}",key=f"{page}_{idx}_raw")
                    try: body=json.loads(raw)
                    except Exception: st.error("Enter valid JSON.")
            if st.button("Run request",key=f"run_{page}_{idx}",type="primary"):
                resolved=path
                for key,value in path_values.items(): resolved=resolved.replace("{"+key+"}",quote(str(value),safe=""))
                try:
                    response=client().request(method,resolved,params=query_values,json_body=body if body_schema else None)
                    st.session_state.last_endpoint=f"{method} {resolved}"
                    try: result=response.json()
                    except Exception: result=response.text
                    st.session_state.last_result={"status":response.status_code,"endpoint":st.session_state.last_endpoint,"data":result}
                    if response.ok: st.success(f"Request completed · HTTP {response.status_code}")
                    else: st.error(f"Request returned HTTP {response.status_code}")
                    if isinstance(result, (dict, list)):
                        st.json(result)
                    else:
                        st.code(str(result))
                except Exception as e: st.error(str(e))
    if st.session_state.last_result:
        with st.expander("Most recent response",expanded=False):
            st.caption(f"{st.session_state.last_result['endpoint']} · HTTP {st.session_state.last_result['status']}")
            data = st.session_state.last_result["data"]

            if isinstance(data, (dict, list)):
                st.json(data)
            else:
                st.code(str(data))

if not st.session_state.access_token:
    show_login()
else:
    fetch_openapi()
    operations=get_operations(st.session_state.openapi or {})
    with st.sidebar:
        st.markdown("<div class='jm-brand'>⚖️ JurisMind</div>",unsafe_allow_html=True)
        st.markdown("<div class='jm-kicker'>LEGAL INTELLIGENCE</div>",unsafe_allow_html=True)
        st.divider()
        st.caption("SIGNED IN")
        st.markdown(f"**{st.session_state.user_email or 'Workspace user'}**")
        nav=list(GROUPS.keys())
        current=st.session_state.active_page if st.session_state.active_page in nav else "Overview"
        selected=st.radio("WORKSPACE",nav,index=nav.index(current),label_visibility="collapsed")
        st.session_state.active_page=selected
        st.divider()
        st.caption("CONNECTED BACKEND")
        st.code(cfg.api_base_url,language=None)
        if st.button("↻ Refresh API schema",use_container_width=True):
            st.session_state.openapi=None; st.rerun()
        if st.button("Sign out",use_container_width=True):
            try: sign_out_local(cfg,st.session_state.get("access_token"))
            except Exception: pass
            for k in ["access_token","refresh_token","user_email","supabase_user_id","openapi","last_result","last_endpoint","tenant_id","selected_snapshot_id","last_research_result","loaded_snapshot"]:
                st.session_state[k]=None
            st.rerun()
        st.caption("Streamlit frontend · Stage 1–4")
    if selected=="Overview": render_overview()
    else:
        if selected == "Legal Research":
            render_legal_research()
        else:
            selected_ops=[x for x in operations if x["group"]==selected]
            render_group(selected,selected_ops)
        if selected=="API Workbench":
            st.info("The workbench shows every remaining operation exposed by the backend OpenAPI document. Use the specialist sections for the main JurisMind workflows.")
