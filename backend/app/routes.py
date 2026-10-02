import json
import re
import httpx
import asyncio
from copy import deepcopy
from fastapi import APIRouter,Depends,HTTPException
from .schemas import *
from .core.auth import current_user
from .core.config import settings
from .core.db import fetch_profile,upsert_profile,fetch_settings,upsert_settings,fetch_catalog,fetch_user_competencies
from .ai.provider import get_provider,ask_selected,server_provider_health
from .data import *
from .github_intelligence import analyze_public_repo
from .materials import scan_materials, ROOT as MATERIALS_ROOT
from .core.workspace import workspace_store

router=APIRouter(prefix="/api/v1")

state=workspace_store

def owned_profile(user):
    p=deepcopy(state["profile"])
    if user["mode"]=="supabase":
        p["id"]=user["id"];p["email"]=user["email"];p["name"]=p.get("name") or user["email"].split("@")[0];p["target_role"]=p.get("target_role") or ""
    return p

def selected_ai_provider(value=None):
    candidate=(value or state.get("settings",{}).get("ai_provider") or settings.ai_provider).lower()
    return candidate if candidate in {"puter","ollama"} else "puter"

def competency_items(user_id=None):
    if not settings.demo_mode and user_id:
        rows=fetch_user_competencies(user_id)
        return [{"name":r.get("competencies",{}).get("name",r.get("competency_id","Competency")),"description":r.get("competencies",{}).get("description",''),"status":r.get("status","developing").replace('_',' ').title(),"evidence":r.get("evidence_strength") or 0,"level":r.get("depth_level","Beginner"),"observed":f"{r.get('evidence_count',0)} evidence events are stored for this competency.","uncertain":"Confidence reflects the evidence currently connected to this workspace.","next":f"Create a new verification artifact for {r.get('competencies',{}).get('name','this competency')}."} for r in rows]
    overrides=state.get("competency_progress",{}) or {}
    out=[]
    for n,d,s,e,l in COMPETENCIES:
        value=max(0,min(100,int(overrides.get(n,e))))
        status="Strong Evidence" if value>=75 else "Developing" if value>=45 else "Limited"
        out.append({"name":n,"description":d,"status":status,"evidence":value,"level":l,"observed":f"Current recorded evidence supports {status.lower()} in {n}.","uncertain":"Confidence reflects evidence currently connected to this workspace; AI interpretation is shown separately.","next":f"Create a new verification artifact for {n} and re-test in a changed context."})
    return out

def target_goal_progress(role,user_id=None):
    r=next((x for x in ROLES if x["name"]==role),ROLES[0])
    by={x["name"]:x.get("evidence",0) for x in competency_items(user_id)}
    vals=[by.get(skill,0) for skill in r["skills"]]
    return round(sum(vals)/len(vals)) if vals else 0

def _parse_ai_review(raw:str):
    text=(raw or "").strip()
    # Accept a fenced JSON response, plain JSON, or a JSON object embedded in text.
    candidates=[text.replace("```json","").replace("```","").strip()]
    match=re.search(r"\{.*\}", text, re.S)
    if match: candidates.append(match.group(0))
    for candidate in candidates:
        try:
            obj=json.loads(candidate)
            if isinstance(obj,dict):
                supported=bool(obj.get("supported",False))
                conf=str(obj.get("confidence","none")).lower()
                if conf not in {"high","medium","low","none"}: conf="none"
                try: score=max(0,min(100,int(float(obj.get("evidence_score",0)))))
                except Exception: score=0
                detected=obj.get("detected") or []
                if not isinstance(detected,list): detected=[str(detected)]
                return {"supported":supported,"confidence":conf,"evidence_score":score,
                        "claim_match":str(obj.get("claim_match","unknown")),
                        "ownership_score":max(0,min(100,int(float(obj.get("ownership_score",0))))),
                        "verification_score":max(0,min(100,int(float(obj.get("verification_score",0))))),
                        "message":str(obj.get("message") or ("Evidence detected and supports the claim." if supported else "No detected evidence for this claim.")),
                        "detected":[str(x) for x in detected][:8]}
        except Exception:
            continue
    # Safe fallback when an AI provider returns malformed output: do not turn a claim into proof.
    lower=text.lower()
    explicit_no=any(x in lower for x in ["no evidence","not enough evidence","unsupported","cannot verify","no detected"])
    concrete=sum(1 for x in ["github.com","repository","repo","project","code","tests","test","deployed","deployment","api","demo","certificate","assessment","screenshot","commit","result","benchmark"] if x in lower)
    score=0 if explicit_no else min(70,concrete*10)
    supported=score>=45 and not explicit_no
    return {"supported":supported,"confidence":"medium" if score>=60 else "low" if score>=45 else "none","evidence_score":score,
            "claim_match":"possible" if supported else "not demonstrated","ownership_score":score if supported else 0,
            "verification_score":min(100,score+10) if supported else 0,
            "message":("Evidence signals were detected, but the provider response was not structured; review is limited." if supported else "No detected evidence for this claim."),
            "detected":([f"Detected {concrete} concrete evidence signal(s) in the supplied response."] if supported else [])}

def _apply_ai_review(claim, review, provider):
    supported=bool(review.get("supported"))
    confidence=str(review.get("confidence","none")).lower()
    try: score=max(0,min(100,int(review.get("evidence_score",0))))
    except Exception: score=0
    # The progression is driven by the AI's evidence score, not by a fixed +8/-3 result.
    # 50 is neutral; strong evidence raises progression, weak/no evidence lowers it.
    delta=max(-12,min(12,round((score-50)/5)))
    if not supported and score>30: score=min(score,30); delta=max(-4,round((score-50)/5))
    if score>=75: confidence="high" if confidence=="none" else confidence
    if score<25: confidence="none"
    claim["ai_review"]={"provider":provider,"supported":supported,"confidence":confidence,"evidence_score":score,
                         "claim_match":review.get("claim_match","unknown"),"ownership_score":review.get("ownership_score",0),
                         "verification_score":review.get("verification_score",0),
                         "message":review.get("message") or ("Evidence detected and supports the claim." if supported else "No detected evidence for this claim."),
                         "detected":review.get("detected") or []}
    claim["status"]="ai-supported" if supported else "no-detection"
    claim["progress_delta"]=delta
    skill=claim.get("competency","")
    if skill:
        current=next((x.get("evidence",0) for x in competency_items() if str(x.get("name")).lower()==skill.lower()),0)
        state["competency_progress"][skill]=max(0,min(100,current+delta))
    if supported:
        eid=f"ai-ev-{claim['id']}"
        if not any(e.get("id")==eid for e in state["evidence"]):
            state["evidence"].insert(0,{"id":eid,"activity":"AI-reviewed claim evidence","competency":skill,
                "evidence":claim.get("evidence_description") or claim.get("evidence_title") or claim.get("claim"),
                "result":"AI-supported","confidence":confidence.title(),"date":str(date.today()),"claim_id":claim["id"],"source_url":claim.get("evidence_url","")})
    state["notifications"].insert(0,{"id":f"n-{len(state['notifications'])+1}","title":"AI evidence review completed",
        "body":claim["ai_review"]["message"],"read":False,"created_at":str(date.today())})
    state.persist()
    return claim

def career_data(role,user_id=None):
    r=next((x for x in ROLES if x["name"]==role),ROLES[0]);names=r["skills"]
    by_name={x["name"]:x for x in competency_items(user_id) if x.get("name")}
    strong=[n for n in names if by_name.get(n,{}).get("evidence",0)>=75];developing=[n for n in names if 45<=by_name.get(n,{}).get("evidence",0)<75];limited=[n for n in names if 0<by_name.get(n,{}).get("evidence",0)<45];not_yet=[n for n in names if n not in strong+developing+limited]
    market=[] if not settings.demo_mode else [{"level":a,"location":b,"range_inr":c,"demo_reference":True,"source":None,"last_updated":None} for a,b,c in SALARY.get(role,SALARY["ML Engineer"])]
    return {"role":role,"strong":strong,"developing":developing,"limited":limited,"not_yet":not_yet,"gaps":limited+not_yet,"market":market,"market_available":bool(market),"market_status":"DEMO REFERENCE ONLY" if settings.demo_mode else "NOT VERIFIED — REQUIRES EXTERNAL MARKET DATA SOURCE"}

@router.get("/health")
async def health(): return {"status":"ok","mode":"demo" if settings.demo_mode else "production"}

@router.post("/demo/reset")
async def reset_demo_workspace():
    if not settings.demo_mode:
        raise HTTPException(404,"Demo reset is available only in demo mode")
    workspace_store.reset("demo-user")
    return {"reset":True,"target_role":"","message":"Fresh demo workspace created."}

@router.get("/dashboard",dependencies=[Depends(current_user)])
async def dashboard(user=Depends(current_user)):
    items=competency_items(user["id"])
    summary={"strong":sum(x["status"]=="Strong Evidence" for x in items),"developing":sum(x["status"]=="Developing" for x in items),"needs":sum(x["status"]=="Limited" for x in items),"transfer":sum(x["status"]=="Transfer Gap" for x in items)}
    role=state["profile"]["target_role"]
    trend=list(reversed(deepcopy(state["evidence"])))
    learner=(fetch_profile(user["id"]) if user["mode"]=="supabase" else None) or owned_profile(user)
    lowest=min(items,key=lambda x:x.get("evidence",0)) if items else {"name":"a competency gap","evidence":0}
    return {"learner":learner,"summary":summary,"competencies":items,"evidence":deepcopy(state["evidence"]),"evidence_claims":deepcopy(state.get("evidence_claims",[])),"trend":[{"date":e["date"],"evidence":(80 if e.get("confidence")=="High" else 60 if e.get("confidence")=="Medium" else 40 if e.get("confidence") else 0)} for e in trend],"career":career_data(role,user["id"]),"next":{"title":f"Strengthen {lowest.get('name','the next gap')} evidence","reason":f"The lowest recorded evidence strength is {lowest.get('evidence',0)}%. Practice the gap, create proof and re-test.","href":"/challenges"},"goal_progress":target_goal_progress(role,user["id"]) }

@router.get("/competencies",dependencies=[Depends(current_user)])
async def competencies(user=Depends(current_user)):
    return {"items":competency_items(user["id"]),"timeline":deepcopy(state["evidence"])}

@router.get("/evidence",dependencies=[Depends(current_user)])
async def evidence_workspace(user=Depends(current_user)):
    role=state["profile"].get("target_role") or "ML Engineer"
    role_obj=next((r for r in ROLES if r["name"]==role),ROLES[0])
    ledger=deepcopy(state.get("evidence",[]))
    claims=deepcopy(state.get("evidence_claims",[]))
    requirements=[]
    for skill in role_obj["skills"]:
        # Claim-generated records are deliberately excluded from verified/observed coverage.
        # A claim only becomes stronger when it is linked to an independently recorded artifact.
        matching=[e for e in ledger if str(e.get("competency","")).lower()==skill.lower() and (not e.get("claim_id") or any(c.get("id")==e.get("claim_id") and c.get("status")=="ai-supported" for c in claims))]
        claimed=[c for c in claims if str(c.get("competency","")).lower()==skill.lower()]
        requirements.append({
            "competency":skill,
            "status":"covered" if matching else ("claimed" if claimed else "missing"),
            "evidence_count":len(matching),
            "claim_count":len(claimed),
            "recommended_proof":f"Create a concrete {skill} artifact, explain the decision, and record how the result was verified."
        })
    return {"target_role":role,"claims":claims,"ledger":ledger,"target_evidence":requirements,"summary":{
        "total_evidence":len(ledger),"claims":len(claims),"covered":sum(x["status"]=="covered" for x in requirements),
        "claimed":sum(x["status"]=="claimed" for x in requirements),"missing":sum(x["status"]=="missing" for x in requirements),"goal_progress":target_goal_progress(role,user["id"])
    }}

@router.post("/evidence/claims",dependencies=[Depends(current_user)])
async def create_evidence_claim(payload:EvidenceClaimCreate):
    evidence_id=payload.existing_evidence_id or ""
    if evidence_id and not any(e.get("id")==evidence_id for e in state.get("evidence",[])):
        raise HTTPException(404,"Selected evidence artifact was not found")
    claim_id=f"claim-{len(state.get('evidence_claims',[]))+1}"
    item={"id":claim_id,"claim":payload.claim,"competency":payload.competency,"target_role":payload.target_role or state["profile"].get("target_role",""),"evidence_id":evidence_id,"evidence_title":payload.evidence_title,"evidence_description":payload.evidence_description,"evidence_type":payload.evidence_type,"evidence_url":payload.evidence_url,"status":"reviewing","created_at":str(date.today())}
    state["evidence_claims"].insert(0,item)
    if evidence_id:
        for e in state["evidence"]:
            if e.get("id")==evidence_id:e.setdefault("linked_claim_ids",[]).append(claim_id);break
    state.persist()
    linked=next((e for e in state.get("evidence",[]) if e.get("id")==evidence_id),None) if evidence_id else None
    linked_context=(f"\nLINKED OBSERVED ARTIFACT: activity={linked.get('activity')}; competency={linked.get('competency')}; evidence={linked.get('evidence')}; result={linked.get('result')}; confidence={linked.get('confidence')}" if linked else "")
    prompt="""You are SKILLSETRA's evidence verifier. Review ONLY the user's supplied evidence for this competency claim. Do not infer ownership or skill from the claim alone.
CLAIM: %s
COMPETENCY: %s
TARGET ROLE: %s
EVIDENCE TYPE: %s
EVIDENCE TITLE: %s
EVIDENCE DESCRIPTION: %s
EVIDENCE URL: %s
%s
Return ONLY one JSON object with exactly these fields: supported (boolean), confidence (high/medium/low/none), evidence_score (0-100), claim_match (strong/partial/weak/none), ownership_score (0-100), verification_score (0-100), message (short user-facing explanation), detected (array of concrete evidence signals).
Rules: compare the CLAIM against the supplied EVIDENCE DESCRIPTION/TITLE/URL; do not award credit merely because the user says they know the competency. Give high scores only when the evidence contains concrete, competency-relevant work and a way to verify it. Ownership means the evidence indicates what the user personally did. Verification means the result can be inspected, tested, linked, or otherwise checked. If the material does not provide concrete support, return supported=false, evidence_score 0-30, confidence=none, message='No detected evidence for this claim.', detected=[].""" % (payload.claim,payload.competency,payload.target_role or state["profile"].get("target_role",""),payload.evidence_type,payload.evidence_title,payload.evidence_description,payload.evidence_url,linked_context)
    selected=selected_ai_provider()
    try:
        answer,provider,_=await ask_selected(prompt,selected,state.get("settings",{}).get("ai_model") or None)
        review=_parse_ai_review(answer); reviewed=_apply_ai_review(item,review,provider)
        return {"saved":True,"claim":reviewed,"ai":{"mode":"server","provider":provider,"review":reviewed["ai_review"]},"goal_progress":target_goal_progress(reviewed.get("target_role") or state["profile"].get("target_role",""))}
    except Exception as server_error:
        return {"saved":True,"claim":item,"ai":{"mode":"puter-client","provider":"puter","model":state.get("settings",{}).get("ai_model") or settings.puter_model,"prompt":prompt},"goal_progress":target_goal_progress(item.get("target_role") or state["profile"].get("target_role","")),"fallback_note":str(server_error)}

@router.post("/evidence/claims/{claim_id}/ai-review",dependencies=[Depends(current_user)])
async def finalize_ai_evidence_review(claim_id:str,payload:AIReviewPayload):
    claim=next((c for c in state.get("evidence_claims",[]) if c.get("id")==claim_id),None)
    if not claim: raise HTTPException(404,"Evidence claim not found")
    review=_parse_ai_review(payload.result)
    reviewed=_apply_ai_review(claim,review,payload.provider or "puter")
    return {"saved":True,"claim":reviewed,"ai":reviewed["ai_review"],"goal_progress":target_goal_progress(reviewed.get("target_role") or state["profile"].get("target_role",""))}

@router.post("/evidence/claims/{claim_id}/review",dependencies=[Depends(current_user)])
async def review_evidence_claim(claim_id:str):
    claim=next((c for c in state.get("evidence_claims",[]) if c.get("id")==claim_id),None)
    if not claim: raise HTTPException(404,"Evidence claim not found")
    claim["status"]="reviewed";claim["reviewed_at"]=str(date.today());state.persist()
    return {"saved":True,"claim":deepcopy(claim),"message":"Claim reviewed. Review does not convert a self-declared claim into independent evidence."}

@router.get("/profile",dependencies=[Depends(current_user)])
async def profile(user=Depends(current_user)):
    p=fetch_profile(user["id"]) if user["mode"]=="supabase" else None
    p=p or owned_profile(user)
    return {**p,"evidence_count":len(state["evidence"]),"projects":1}

@router.post("/profile",dependencies=[Depends(current_user)])
async def update_profile(payload:ProfileUpdate,user=Depends(current_user)):
    state["profile"].update(payload.model_dump())
    saved=upsert_profile(user["id"],{"name":payload.name,"target_role":payload.target_role,"primary_goal":payload.goal,"experience_level":state["profile"].get("experience","Intermediate")}) if user["mode"]=="supabase" else None
    return {"saved":True,**(saved or state["profile"])}

@router.post("/profile/goal",dependencies=[Depends(current_user)])
async def update_goal(payload:GoalUpdate,user=Depends(current_user)):
    state["profile"].update(payload.model_dump())
    saved=upsert_profile(user["id"],{"name":state["profile"]["name"],"target_role":payload.target_role,"primary_goal":payload.goal,"experience_level":payload.experience}) if user["mode"]=="supabase" else None
    return {"saved":True,"profile":saved or state["profile"]}

@router.get("/settings",dependencies=[Depends(current_user)])
async def get_settings(user=Depends(current_user)):
    saved=fetch_settings(user["id"]) if user["mode"]=="supabase" else None
    return saved or deepcopy(state["settings"])

@router.post("/settings",dependencies=[Depends(current_user)])
async def save_settings(payload:SettingsUpdate,user=Depends(current_user)):
    state["settings"].update({**payload.model_dump(),"ai_provider": payload.ai_provider if payload.ai_provider in {"puter","ollama"} else "puter"})
    saved=upsert_settings(user["id"],{"ai_provider":payload.ai_provider,"ai_model":payload.ai_model,"notifications":payload.notifications,"appearance":payload.appearance,"retain_evidence":payload.privacy,"language":payload.language}) if user["mode"]=="supabase" else None
    return {"saved":True,"message":"Settings saved to Supabase." if saved else "Settings saved to demo state.","settings":saved or deepcopy(state["settings"])}

@router.get("/challenges/next",dependencies=[Depends(current_user)])
async def next_challenge():
    c=deepcopy(CHALLENGES[min(state["retest_index"],len(CHALLENGES)-1)])
    c.pop("rubric",None)
    return c

@router.post("/challenges/test",dependencies=[Depends(current_user)])
async def run_demo_test(payload:dict):
    answer=(payload.get("answer") or "").lower()
    passed=7+int("test" in answer)+int("edge" in answer)+int("debug" in answer)
    passed=min(passed,10)
    return {"passed":passed,"total":10,"mode":"DEMO DETERMINISTIC TEST","summary":f"{passed}/10 cases pass. The adapter checks whether your explanation addresses isolation, verification and edge cases."}

@router.post("/challenges/{challenge_id}/submit",dependencies=[Depends(current_user)])
async def submit_challenge(challenge_id:str,payload:ChallengeSubmit):
    challenge=next((c for c in CHALLENGES if c["id"]==challenge_id),None)
    if not challenge: raise HTTPException(404,"Challenge not found")
    answer=payload.answer.strip(); low=answer.lower()
    criteria=[]
    for item in challenge.get("rubric",[]):
        met=any(term.lower() in low for term in item.get("terms",[]))
        criteria.append({"label":item["label"],"met":met,"detail":item["met_detail"] if met else item["miss_detail"]})
    score=round(100*sum(1 for x in criteria if x["met"])/max(1,len(criteria)))
    selected=selected_ai_provider(payload.provider)
    prompt=f"""Evaluate ONLY this specific challenge.
TITLE: {challenge["title"]}
QUESTION: {challenge["statement"]}
CONSTRAINTS: {", ".join(challenge["constraints"])}
ANSWER: {answer}
Return a concise structured evaluation with strengths, missing points, risks, and a next verification step. Do not reuse an answer from another challenge."""
    ai=""; provider_name="deterministic"
    if selected=="puter":
        provider_name="puter"
    else:
        try: ai,provider_name,_=await ask_selected(prompt,selected,payload.model)
        except Exception: provider_name="deterministic"
    observed="; ".join(x["label"] for x in criteria if x["met"]) or "The submitted answer did not clearly address the challenge-specific rubric yet."
    uncertain="; ".join(x["label"] for x in criteria if not x["met"]) or "No rubric item was left unmatched."
    state["evidence"].insert(0,{"id":f"ev-{len(state['evidence'])+1}","activity":f"Challenge completed: {challenge['title']}","competency":"Debugging","evidence":observed,"result":"Strong" if score>=80 else "Developing" if score>=50 else "Needs Evidence","confidence":"Medium","date":str(date.today())})
    state["challenge_attempts"].append({"id":f"ca-{len(state['challenge_attempts'])+1}","challenge_id":challenge_id,"score":score,"completed_at":str(date.today()),"answer":answer})
    state["notifications"].insert(0,{"id":f"n-{len(state['notifications'])+1}","title":"Challenge checked","body":f"{challenge['title']} was checked against its own rubric: {score}%.","read":False,"created_at":str(date.today())})
    return {"challenge_id":challenge_id,"status":"Strong" if score>=80 else "Developing" if score>=50 else "Needs Evidence","score":score,"evaluation":{"mode":"puter-client" if selected=="puter" else "live" if provider_name=="ollama" else "deterministic","criteria":criteria,"observed":observed,"evidence":"Question-specific challenge response + verification plan","uncertain":uncertain,"next_step":"Strengthen the missing rubric items and submit a changed-context solution.","ai_note":ai,"prompt":prompt if selected=="puter" else None,"model":payload.model or settings.puter_model,"provider":provider_name},"evidence_added":True}

@router.post("/challenges/{challenge_id}/retest",dependencies=[Depends(current_user)])
async def retest(challenge_id:str):
    state["retest_index"]=min(state["retest_index"]+1,len(CHALLENGES)-1)
    return deepcopy(CHALLENGES[state["retest_index"]])


@router.get("/projects",dependencies=[Depends(current_user)])
async def projects():
    return {"items":[{"id":"demo-project","name":"skillsetra-api","stack":["FastAPI","Next.js","PostgreSQL"],"status":"Analyzed"}]}

@router.post("/projects/analyze",dependencies=[Depends(current_user)])
async def analyze_project(payload:ProjectAnalyze):
    project_id=f"project-{len(state['projects'])+1}";project={"id":project_id,"name":payload.name,"description":payload.description,"created_at":str(date.today())};state["projects"].append(project)
    selected=selected_ai_provider(payload.provider); ai_note=""; provider_name="demo"
    prompt=f"Analyze this project description for competency evidence. Separate observed facts from inference, list strengths, gaps, risks and concrete proof artifacts. Do not invent repository facts. Respond in {payload.language}. Project: {payload.name}. Description: {payload.description}"
    if selected=="puter": ai_note=prompt;provider_name="puter"
    else:
        try: ai_note,provider_name,_=await ask_selected(prompt,selected,payload.model)
        except Exception as exc: ai_note=f"AI analysis unavailable ({type(exc).__name__}); deterministic project evidence was still recorded."
    return {"mode":"demo" if settings.demo_mode else "production","project":project,"strengths":["Clear API boundaries","Readable application structure","Good separation of UI and business concerns"],"gaps":["Testing depth","Production error handling","Deployment evidence"],"evidence_created":"Architecture + engineering evidence","ai_analysis":ai_note,"ai_provider":provider_name,"upgrades":[
      {"id":"validation","title":"Add explicit request validation","problem":"Malformed requests can reach business logic.","why":"Creates stronger reliability and API engineering evidence.","competency":"FastAPI","difficulty":"Medium","implementation":"Add Pydantic models, structured validation errors and boundary tests.","evidence":"Validated API behavior","status":"Not Started"},
      {"id":"integration","title":"Add integration test suite","problem":"Current tests do not sufficiently cover failure paths.","why":"Creates direct testing evidence and protects future upgrades.","competency":"Testing","difficulty":"Medium","implementation":"Add database/API integration tests and edge-case assertions.","evidence":"Repeatable failure-path coverage","status":"Not Started"},
      {"id":"docker","title":"Containerize the service","problem":"Local setup depends on developer-specific environment state.","why":"Creates reproducibility and deployment evidence.","competency":"Docker","difficulty":"Easy","implementation":"Add Dockerfile, health check and documented run command.","evidence":"Reproducible container run","status":"Not Started"}]}

@router.post("/projects/upgrades",dependencies=[Depends(current_user)])
async def complete_upgrade(payload:UpgradeSubmit):
    state["evidence"].insert(0,{"id":f"ev-{len(state['evidence'])+1}","activity":"Project upgrade recorded","competency":"Testing" if payload.upgrade_id=="integration" else "Engineering","evidence":f"Completed upgrade `{payload.upgrade_id}` and created a new evidence event.","result":"Observed completion","confidence":"Low","date":str(date.today())})
    return {"status":"Recorded","message":"Upgrade completion was recorded. It is not independently verified yet."}


@router.get("/projects/recommendations",dependencies=[Depends(current_user)])
async def project_recommendations():
    role=state["profile"]["target_role"]
    return {"items":[
      {"id":"rec-1","title":"Production-grade ML inference service","why":f"Targets the testing, FastAPI and deployment gaps relevant to {role}.","gap":"Testing + Deployment","skills":["Python","FastAPI","Testing","Docker"],"technologies":["FastAPI","PostgreSQL","Docker"],"difficulty":"Intermediate","effort_hours":28,"milestones":["Add request validation","Build integration tests","Containerize","Document deployment"],"evidence":"API engineering + testing + deployment proof"},
      {"id":"rec-2","title":"Data quality and model-monitoring pipeline","why":"Introduces reliability and observability without repeating a basic notebook project.","gap":"Engineering + Transfer","skills":["SQL","Pandas","Monitoring","ML"],"technologies":["Python","PostgreSQL","scikit-learn"],"difficulty":"Intermediate","effort_hours":36,"milestones":["Define data checks","Build pipeline","Add drift checks","Defend trade-offs"],"evidence":"Data engineering + adaptation + reasoning proof"}
    ]}

@router.get("/project-defense",dependencies=[Depends(current_user)])
async def project_defense():
    return {"project_id":"demo-project","questions":[
      "Why did you choose this technology and what trade-off did it introduce?",
      "How would you scale this system if usage increased 10×?",
      "What failure would you investigate first in production and why?",
      "How would you test a requirement that changed after launch?",
      "What security boundary matters most in this architecture?"
    ]}

@router.post("/project-defense",dependencies=[Depends(current_user)])
async def submit_defense(payload:DefenseSubmit):
    selected=selected_ai_provider(payload.provider)
    prompt=f"""Evaluate this project-defense answer for reasoning quality.
Question: {payload.question}
Answer: {payload.answer}
Return strengths, trade-off quality, missing evidence, verification step, and one changed-context follow-up. Do not invent project facts."""
    note=""; provider_name=selected
    if selected=="puter":
        mode="puter-client"
    else:
        try:
            note,provider_name,_=await ask_selected(prompt,selected,payload.model); mode="live"
        except Exception:
            mode="fallback"; provider_name="ollama"; note="Ollama was unavailable; the recorded defense evidence remains limited to the submitted answer."
    state["evidence"].insert(0,{"id":f"ev-{len(state['evidence'])+1}","activity":"Project defense answer","competency":"Reasoning","evidence":"Explained a project decision and its trade-offs in a defense session.","result":"Developing","confidence":"Medium","date":str(date.today())})
    sessions=state.get("project_defense_sessions",[]);sessions.append({"project_id":payload.project_id,"question":payload.question,"answer":payload.answer,"provider":provider_name,"created_at":str(date.today())});state["project_defense_sessions"]=sessions
    state["notifications"].insert(0,{"id":f"n-{len(state['notifications'])+1}","title":"Project defense recorded","body":"Your defense answer was recorded as reasoning evidence.","read":False,"created_at":str(date.today())})
    return {"mode":mode,"status":"Developing","observed":"The defense answer creates reasoning evidence, but one answer is not enough to establish broad competency.","next_step":"Answer the next changed-context question.","ai_note":note,"prompt":prompt if selected=="puter" else None,"model":payload.model or settings.puter_model,"provider":provider_name}

@router.get("/github",dependencies=[Depends(current_user)])
async def github():
    saved=state.get("github_connection")
    if settings.demo_mode and not saved:
        repos=[
          {"id":"demo-repo-101","name":"demo/ml-inference-api","description":"Seeded demo repository. Not user data.","language":"Python","signals":["FastAPI","Tests","Dockerfile","README"],"selected":"demo-repo-101" in state["selected_repos"],"is_demo":True,"html_url":"https://github.com/"},
          {"id":"demo-repo-102","name":"demo/forecast-lab","description":"Seeded demo repository. Not user data.","language":"Python","signals":["scikit-learn","Pandas","Experiments"],"selected":"demo-repo-102" in state["selected_repos"],"is_demo":True,"html_url":"https://github.com/"}
        ]
        return {"connection":{"username":"demo-user","connected":bool(state["selected_repos"]),"is_demo":True},"repositories":repos,"notice":"Demo repositories are seeded examples and are never presented as real user GitHub data."}
    if saved:
        return {"connection":{"username":saved.get("username"),"connected":True,"is_demo":False},"repositories":saved.get("repositories",[]),"notice":"GitHub connection restored for this workspace. The access token is never returned by the API."}
    return {"connection":{"username":None,"connected":False,"is_demo":False},"repositories":[],"notice":"Connect GitHub to inspect repositories. No repository is assumed or fabricated."}

@router.get("/github/connection",dependencies=[Depends(current_user)])
async def github_connection():
    return await github()

@router.post("/github/connect",dependencies=[Depends(current_user)])
async def github_connect(payload:GitHubConnectRequest):
    try:
        me=await github_request("/user", payload.token)
        repos=await github_request("/user/repos?per_page=50&sort=updated", payload.token)
        items=[{"id":str(r.get("id")),"name":r.get("full_name"),"description":r.get("description") or "No description","language":r.get("language") or "Unknown","html_url":r.get("html_url"),"private":r.get("private",False),"updated_at":r.get("updated_at")} for r in repos if isinstance(repos,list)]
        state["github_connection"]={"username":me.get("login"),"name":me.get("name"),"repositories":items,"connected_at":str(date.today())}
        state["notifications"].insert(0,{"id":f"n-{len(state['notifications'])+1}","title":"GitHub connected","body":f"Connected GitHub as {me.get('login')}.","read":False,"created_at":str(date.today())})
        return {"connected":True,"username":me.get("login"),"name":me.get("name"),"repositories":items,"token_session":"workspace"}
    except Exception as exc:
        raise HTTPException(401, f"GitHub connection failed: {type(exc).__name__}")

@router.post("/github/disconnect",dependencies=[Depends(current_user)])
async def github_disconnect():
    state["github_connection"]=None; state["selected_repos"]=[]
    return {"connected":False}

@router.post("/github/repositories/{repo_id}/select",dependencies=[Depends(current_user)])
async def select_repo(repo_id:str):
    if settings.demo_mode:
        allowed={"demo-repo-101","demo-repo-102"}
    else:
        allowed=set()
    if repo_id not in allowed: raise HTTPException(404,"Repository not found or not connected")
    if repo_id not in state["selected_repos"]: state["selected_repos"].append(repo_id)
    state["evidence"].insert(0,{"id":f"ev-{len(state['evidence'])+1}","activity":"GitHub repository analyzed","competency":"Python","evidence":f"Selected repository {repo_id} exposed repeatable engineering signals.","result":"Strong","confidence":"Medium","date":str(date.today())})
    return {"message":"Repository selected and analyzed. New evidence was added.","data":await github()}

@router.post("/github/analyze",dependencies=[Depends(current_user)])
async def analyze_github(payload:GitHubAnalyzeRequest,user=Depends(current_user)):
    try:
        analysis = await analyze_public_repo(payload.url, settings.github_token)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"GitHub analysis failed: {type(exc).__name__}")
    ws=state
    facts=analysis["facts"]
    ws["github_analysis"]=analysis
    evidence_id=f"gh-{len(ws['evidence'])+1}"
    ws["evidence"].insert(0,{"id":evidence_id,"activity":"GitHub repository analyzed","competency":"Engineering","evidence":f"Observed {facts['repository']} with languages {', '.join(facts['languages']) or 'none detected'} and signals {', '.join(facts['signals']) or 'none detected'}.","result":"Observed","confidence":"High","date":str(date.today()),"evidence_type":"GitHub repository","source_url":payload.url})
    analysis["evidence_id"]=evidence_id
    selected=selected_ai_provider(payload.provider)
    ai_note=""
    if selected != "puter":
        prompt=("You are analyzing GitHub evidence for SKILLSETRA. Never invent facts. "
                "Separate observed repository facts from interpretation. Based ONLY on this JSON, "
                "give 4 concise insights, 3 improvement suggestions, and 3 questions for a project defense. "
                f"Respond in {payload.language}. JSON facts: {json.dumps(facts)[:14000]}")
        try:
            ai_note, used, notice = await ask_selected(prompt, selected, payload.model)
            analysis["ai"]={"provider":used,"text":ai_note,"notice":notice}
        except Exception:
            analysis["ai"]={"provider":"deterministic","text":"AI interpretation unavailable; showing evidence-only analysis.","notice":""}
    else:
        analysis["ai"]={"provider":"puter","mode":"puter-client","prompt":f"Analyze this GitHub evidence without inventing facts. Separate observed facts, interpretations, limitations and recommendations. Respond in {payload.language}. Evidence: {json.dumps(facts)[:14000]}","model":settings.puter_model}
    return analysis

@router.get("/github/analysis",dependencies=[Depends(current_user)])
async def github_analysis():
    return state.get("github_analysis") or {"facts":None,"claims":[],"suggestions":[],"ai":None}

@router.get("/career/intelligence",dependencies=[Depends(current_user)])
async def career_intelligence(user=Depends(current_user)):
    role=state["profile"].get("target_role") or ROLES[0]["name"]
    data=career_data(role,user["id"])
    by_name={x["name"]:x for x in competency_items(user["id"])}
    matrix=[{"skill":skill,"evidence":by_name.get(skill,{}).get("evidence",0),"status":by_name.get(skill,{}).get("status","Not yet evidenced"),"next":by_name.get(skill,{}).get("next",f"Create evidence for {skill}.")} for skill in next(r["skills"] for r in ROLES if r["name"]==role)]
    return {**data,"matrix":matrix,"interview_plan":["Role fundamentals","Project defense","AI interview","Re-test gaps"],"portfolio_plan":["Select a relevant project","Add tests and documentation","Connect repository evidence","Defend trade-offs"],"learning_plan":["Close the largest evidence gap","Practice in a new context","Reassess and record evidence"]}

@router.get("/career/roles",dependencies=[Depends(current_user)])
async def career_roles():
    return {"roles":ROLES,"current_role":state["profile"]["target_role"]}

@router.get("/career/{role}",dependencies=[Depends(current_user)])
async def career(role:str,user=Depends(current_user)):
    if not any(x["name"]==role for x in ROLES): raise HTTPException(404,"Role not found")
    return career_data(role,user["id"])

@router.get("/subjects",dependencies=[Depends(current_user)])
async def subjects(language:str="English",category:str="all"):
    items=deepcopy(SUBJECTS) if settings.demo_mode else fetch_catalog("subjects")
    _,folder_subjects=scan_materials()
    by_id={x.get("id"):x for x in items}
    for fs in folder_subjects:
        slug=fs["id"]
        if slug in by_id:
            by_id[slug]["resources"]=by_id[slug].get("resources",[])+fs["resources"]
        else: items.append(fs)
    if category.lower()!="all": items=[x for x in items if x.get("category","").lower()==category.lower()]
    for item in items:
        item["resources"]= [r for r in item.get("resources",[]) if language in item.get("languages",["English"]) or language=="English"]
    return {"items":items,"language":language,"categories":sorted({x["category"] for x in items})}

@router.get("/materials",dependencies=[Depends(current_user)])
async def learning_materials():
    resources, subjects = scan_materials()
    return {"items":resources,"subjects":subjects,"root":"learning-materials","notice":"Scanned from the project learning-materials folder at request time."}

@router.get("/materials/file/{file_path:path}",dependencies=[Depends(current_user)])
async def learning_material_file(file_path:str):
    from fastapi.responses import FileResponse
    target=(MATERIALS_ROOT / file_path).resolve()
    root=MATERIALS_ROOT.resolve()
    if root not in target.parents or not target.is_file(): raise HTTPException(404,"Learning material not found")
    return FileResponse(target)

@router.get("/resources",dependencies=[Depends(current_user)])
async def resources():
    folder_resources,_=scan_materials()
    base=deepcopy(RESOURCES) if settings.demo_mode else fetch_catalog("learning_resources")
    return {"items":base+folder_resources,"notice":"Catalog resources plus materials scanned from the project learning-materials folder."}

@router.post("/resources/summary",dependencies=[Depends(current_user)])
async def resource_summary(payload:ResourceSummary):
    item=next((x for x in RESOURCES if x["id"]==payload.resource_id),None)
    if not item: raise HTTPException(404,"Resource not found")
    selected=selected_ai_provider(payload.provider)
    if selected=="puter":
        return {"summary":"","mode":"puter-client","prompt":f"Explain in {payload.language} why this resource matters to a learner with a {item['competency']} gap. Resource: {item['title']}. Give a short personalized explanation.","model":settings.puter_model}
    answer,used,notice=await ask_selected(f"Give a short personalized explanation in {payload.language} for why this learning resource matters to a learner with a {item['competency']} gap. Resource: {item['title']}.",selected,payload.model)
    return {"summary":answer,"mode":used,"provider":used,"notice":notice}

@router.get("/roadmap",dependencies=[Depends(current_user)])
async def roadmap(user=Depends(current_user)):
    role=state["profile"].get("target_role") or "Target role";items=competency_items(user["id"]);gaps=sorted(items,key=lambda x:x.get("evidence",0))[:5]
    stages=[("TARGET",f"Clarify the {role} target and constraints.","Target profile is the anchor for every later decision."),("ASSESS","Run an adaptive baseline and record the result.","A baseline makes gaps observable."),("MAP","Map the lowest evidence strengths to role requirements.","Role-weighted gaps determine what matters next."),("PRACTICE","Complete a focused challenge for the largest gap.","Practice should create an artifact, not only passive completion."),("PROVE","Create or upgrade a project artifact.","A project turns practice into inspectable proof."),("VERIFY","Defend the decision under a changed constraint.","Transfer evidence is stronger than recall."),("LEARN","Complete resources tied to the remaining gap.","Learning should be attached to a specific need."),("BUILD","Add the next role-relevant project milestone.","Build work that closes the evidence gap."),("RETEST","Attempt a different context for the same competency.","Retesting checks transfer."),("EVIDENCE","Review observed evidence, confidence and limitations.","The ledger is the source of truth."),("ROADMAP","Generate the next version from the new state.","Roadmaps are revised as evidence changes.")]
    steps=[]
    for i,(title,obj,why) in enumerate(stages):
      status="completed" if i==0 and state.get("profile",{}).get("target_role") else ("current" if i==1 else "planned")
      skills=[g.get("name") for g in gaps[:3]] if i>=2 else []
      steps.append({"id":f"step-{i}","title":title,"objective":obj,"why":why,"skills":skills,"evidence_required":f"Recorded {title.lower()} event tied to {role}","estimate":"1–7 days","status":status,"resources":[r for r in RESOURCES if any(k.lower() in r.get("competency","").lower() for k in skills)][:2]})
    return {"title":f"{role} evidence roadmap","description":"Generated from the current target and stored evidence state. Update the roadmap after assessments, challenges, learning or GitHub analysis.","steps":steps,"generated_from":{"target_role":role,"gaps":[g.get("name") for g in gaps],"evidence_count":len(state.get("evidence",[]))}}

@router.post("/roadmap/generate",dependencies=[Depends(current_user)])
async def generate_roadmap(user=Depends(current_user)): return await roadmap(user)

@router.get("/assessments/catalog",dependencies=[Depends(current_user)])
async def assessments_catalog():
    return {"items":[
      {"id":"logic-reasoning","title":"Logic & Reasoning","difficulty":"Adaptive","skills":["Reasoning","Problem Solving"],"time":"20 min","questions":10},
      {"id":"debugging","title":"Debugging & Failure Analysis","difficulty":"Adaptive","skills":["Debugging","Testing"],"time":"25 min","questions":10},
      {"id":"ai-engineering","title":"AI Engineering","difficulty":"Intermediate","skills":["AI Engineering","Evaluation"],"time":"30 min","questions":12},
      {"id":"system-design","title":"System Design","difficulty":"Advanced","skills":["System Design","Architecture"],"time":"35 min","questions":8},
      {"id":"frontend","title":"Frontend Engineering","difficulty":"Intermediate","skills":["React","Accessibility","Testing"],"time":"25 min","questions":10},
      {"id":"backend","title":"Backend Engineering","difficulty":"Intermediate","skills":["APIs","SQL","Testing"],"time":"25 min","questions":10}
    ]}

@router.get("/assessment",dependencies=[Depends(current_user)])
async def assessment():
    role=state["profile"].get("target_role","ML Engineer")
    questions=[
      {"id":"q1","competency":"Reasoning","difficulty":"Intermediate","question":"A production API returns correct results but has no tests for malformed input. What evidence is most useful next?","options":["Add a README paragraph","Add failure-path tests and observe the behavior","Increase the UI animation","Rename the endpoint"],"correct":1,"explanation":"Failure-path tests directly verify the boundary behavior and create observable evidence."},
      {"id":"q2","competency":"Testing","difficulty":"Intermediate","question":"Which test best checks a boundary between your service and a downstream dependency?","options":["A screenshot test","An integration test with controlled dependency behavior","A spelling check","A line-count check"],"correct":1,"explanation":"Controlled integration behavior verifies the contract and failure paths across the boundary."},
      {"id":"q3","competency":"Debugging","difficulty":"Beginner","question":"A bug appears only with one input shape. What should you do first?","options":["Rewrite everything","Add random features","Reproduce and isolate the smallest failing case","Delete the input"],"correct":2,"explanation":"A minimal reproducible failure reduces the search space and makes verification repeatable."},
      {"id":"q4","competency":"Engineering","difficulty":"Intermediate","question":"Why should validation happen near an API boundary?","options":["It makes code longer","It makes failures explicit before invalid data spreads into business logic","It replaces testing","It guarantees security"],"correct":1,"explanation":"Early validation creates a clear contract and prevents invalid data from propagating."},
      {"id":"q5","competency":"Transfer","difficulty":"Intermediate","question":"A familiar solution stops working after requirements change. What demonstrates adaptation?","options":["Repeat the same solution","Explain the changed constraint, revise the approach and verify the new behavior","Avoid the requirement","Guess an output"],"correct":1,"explanation":"Adaptation is observable when the changed constraint drives a revised, verified solution."},
      {"id":"q6","competency":"Security","difficulty":"Intermediate","question":"A server accepts a GitHub URL for analysis. Which control is essential?","options":["Fetch any URL the user enters","Allow only validated GitHub URLs and approved API endpoints","Disable all logging","Trust redirects from the URL"],"correct":1,"explanation":"URL validation and an allowlist reduce SSRF risk and keep fetching inside the intended GitHub surface."},
      {"id":"q7","competency":"APIs","difficulty":"Intermediate","question":"What should a production API return when a requested AI provider is unavailable and fallback is disabled?","options":["Pretend another provider answered","Return a clear unavailable error with provider context","Return an empty success response","Silently use a demo model"],"correct":1,"explanation":"The requested provider must remain explicit; silent substitution would make the result untrustworthy."},
      {"id":"q8","competency":"Data Engineering","difficulty":"Intermediate","question":"A learner refreshes after completing a roadmap step. What should determine the displayed state?","options":["A local animation flag","Persisted completion data","The browser URL","A random percentage"],"correct":1,"explanation":"Persistent completion must be stored and read from the database-backed workspace state."},
      {"id":"q9","competency":"Accessibility","difficulty":"Beginner","question":"Which behavior is required for a sidebar toggle?","options":["Mouse hover only","Keyboard operation with an accessible label and visible focus","Hidden control on mobile","No focus indication"],"correct":1,"explanation":"Keyboard access, naming and focus visibility are core interaction requirements."},
      {"id":"q10","competency":"System Design","difficulty":"Advanced","question":"A service needs retries for a downstream request. Which approach is safer?","options":["Retry every operation forever","Retry only safe/idempotent operations with bounded backoff","Retry without a timeout","Retry after returning success"],"correct":1,"explanation":"Bounded retries with idempotency awareness prevent retry storms and duplicate side effects."},
      {"id":"q11","competency":"Evidence","difficulty":"Intermediate","question":"Which statement is the strongest evidence claim?","options":["The learner is a master because a README says so","Observed tests passed in the recorded challenge run","The filename proves production expertise","The AI says the learner is excellent"],"correct":1,"explanation":"Evidence should point to an observed, recorded artifact or event rather than an unsupported claim."},
      {"id":"q12","competency":"Learning","difficulty":"Beginner","question":"What should happen after a learner completes a learning path?","options":["Only show a congratulations message","Verify stored completion, assess covered topics, explain results and unlock the next role-relevant step if passed","Delete the learning history","Reset the target"],"correct":1,"explanation":"Completion should create a verification loop tied to the actual material and the learner's target."},
    ]
    return {"id":"adaptive-v1","title":f"{role} adaptive competency assessment","role":role,"question_count":len(questions),"questions":[{k:v for k,v in q.items() if k!='correct'} for q in questions]}

@router.post("/assessment/submit",dependencies=[Depends(current_user)])
async def assessment_submit(payload:AssessmentSubmit):
    if not payload.answers: raise HTTPException(400,"At least one answer is required")
    result=await assessment();by_id={q["id"]:q for q in result["questions"]}
    # Correct answers are intentionally resolved server-side from the canonical question set.
    correct_map={"q1":1,"q2":1,"q3":2,"q4":1,"q5":1,"q6":1,"q7":1,"q8":1,"q9":1,"q10":1,"q11":1,"q12":1}
    explanations={q["id"]:q["explanation"] for q in [
      {"id":"q1","explanation":"Failure-path tests directly verify the boundary behavior and create observable evidence."},{"id":"q2","explanation":"Controlled integration behavior verifies the contract and failure paths across the boundary."},{"id":"q3","explanation":"A minimal reproducible failure reduces the search space and makes verification repeatable."},{"id":"q4","explanation":"Early validation creates a clear contract and prevents invalid data from propagating."},{"id":"q5","explanation":"Adaptation is observable when the changed constraint drives a revised, verified solution."},{"id":"q6","explanation":"URL validation and an allowlist reduce SSRF risk and keep fetching inside the intended GitHub surface."},{"id":"q7","explanation":"The requested provider must remain explicit; silent substitution would make the result untrustworthy."},{"id":"q8","explanation":"Persistent completion must be stored and read from the database-backed workspace state."},{"id":"q9","explanation":"Keyboard access, naming and focus visibility are core interaction requirements."},{"id":"q10","explanation":"Bounded retries with idempotency awareness prevent retry storms and duplicate side effects."},{"id":"q11","explanation":"Evidence should point to an observed, recorded artifact or event rather than an unsupported claim."},{"id":"q12","explanation":"Completion should create a verification loop tied to the actual material and the learner's target."}
    ]}
    details=[];score=0
    for qid,chosen in payload.answers.items():
      q=by_id.get(qid)
      if not q:continue
      try:idx=int(chosen)
      except Exception:idx=-1
      ok=idx==correct_map.get(qid,-2);score+=int(ok)
      details.append({"question_id":qid,"competency":q["competency"],"selected":idx,"correct":correct_map.get(qid),"is_correct":ok,"expected":q["options"][correct_map[qid]],"why":explanations[qid],"next":f"Practice {q['competency']} with a new applied task."})
    total=len(by_id);pct=round(score/total*100) if total else 0;passed=pct>=70
    attempt={"id":f"assessment-{len(state['assessment_attempts'])+1}","assessment_id":payload.assessment_id,"score":pct,"passed":passed,"answers":details,"completed_at":str(date.today())};state["assessment_attempts"].append(attempt)
    if passed:state["evidence"].insert(0,{"id":f"ev-{len(state['evidence'])+1}","activity":"Assessment completed","competency":"Reasoning","evidence":f"Completed adaptive assessment at {pct}% with {score}/{total} correct responses.","result":"Verified","confidence":"Medium","date":str(date.today())})
    state["notifications"].insert(0,{"id":f"n-{len(state['notifications'])+1}","title":"Assessment completed","body":f"Score {pct}%. {'Continue journey is available.' if passed else 'Targeted practice and a retest are recommended.'}","read":False,"created_at":str(date.today())})
    return {"score":pct,"correct":score,"total":total,"passed":passed,"details":details,"summary":"Results are based on the submitted answers and the canonical server-side answer key.","next_step":"Continue journey → role-relevant gaps and projects" if passed else "Targeted learning → practice → retest"}

@router.post("/profile/verify-goal",dependencies=[Depends(current_user)])
async def verify_goal(payload:GoalUpdate):
    selected=selected_ai_provider()
    prompt=f"Verify a learner target plan. Target role: {payload.target_role}. Experience: {payload.experience}. Goal: {payload.goal}. Explain whether the goal is coherent for the role, what 3 competency areas should be verified first, and what evidence should count. Respond in plain language."
    if selected=="puter":
        return {"role":payload.target_role,"goal":payload.goal,"verification":"","mode":"puter-client","prompt":prompt,"model":settings.puter_model,"provider":"puter"}
    answer,used,notice=await ask_selected(prompt,selected)
    return {"role":payload.target_role,"goal":payload.goal,"verification":answer,"provider":used,"notice":notice}

@router.get("/ai/providers",dependencies=[Depends(current_user)])
async def ai_providers():
    specs=[("puter","Puter AI","Browser AI",settings.puter_model,False),("ollama","Ollama","Local AI",settings.ollama_model,True)]
    result=await server_provider_health("ollama")
    providers=[{"id":"puter","name":"Puter AI","tier":"Browser AI","model":settings.puter_model,"status":"Primary · runs in the browser through Puter.js.","connected":True,"server_side":False,"models":[]},
               {"id":"ollama","name":"Ollama","tier":"Local AI","model":settings.ollama_model,"status":result.get("message","Ollama status unavailable."),"connected":result.get("connected",False),"server_side":True,"models":result.get("models",[])}]
    return {"default":"puter","providers":providers}

@router.post("/ai/test",dependencies=[Depends(current_user)])
async def ai_test(payload:dict):
    provider=(payload.get("provider") or selected_ai_provider()).lower()
    if provider=="puter": return {"provider":"puter","mode":"puter-client","status":"browser-check","message":"Puter AI is the primary browser provider. The browser will verify the connection when a request is sent.","model":payload.get("model") or settings.puter_model}
    result=await server_provider_health("ollama")
    if result.get("connected"):
        try: result["test_response"]=await get_provider("ollama").ask("Reply with exactly: SKILLSETRA connection OK.",payload.get("model"))
        except Exception as exc: result["connected"]=False; result["message"]=f"Ollama connection works, but the selected model failed: {type(exc).__name__}."
    return result

@router.get("/ai/models",dependencies=[Depends(current_user)])
async def ai_models(provider:str="puter"):
    provider=provider.lower()
    if provider=="puter":
        return {"provider":"puter","models":[
          {"id":"openai/gpt-oss-20b","label":"GPT-OSS 20B · Puter","recommended":True},
          {"id":"deepseek/deepseek-chat","label":"DeepSeek Chat · Puter"},
          {"id":"qwen/qwen3-coder","label":"Qwen Coder · Puter"},
          {"id":"meta-llama/llama-3.3-70b-instruct","label":"Llama 3.3 70B · Puter"}
        ]}
    if provider=="ollama":
        health=await server_provider_health("ollama"); models=health.get("models",[]) or [settings.ollama_model]
        return {"provider":"ollama","connected":health.get("connected",False),"status":health.get("message"),"models":[{"id":m,"label":m,"recommended":m==settings.ollama_model} for m in models if m]}
    raise HTTPException(400,"Unsupported AI provider. Choose Puter AI or Ollama.")

@router.post("/ai/fallback",dependencies=[Depends(current_user)])
async def ai_fallback(payload:dict):
    prompt=str(payload.get("prompt") or "").strip()
    if not prompt: raise HTTPException(400,"AI fallback prompt is required.")
    try:
        answer,used,notice=await ask_selected(prompt,"ollama",payload.get("model"))
        return {"answer":answer,"provider":used,"mode":"ollama-fallback","notice":notice}
    except Exception as exc:
        raise HTTPException(502,f"Puter AI and Ollama are unavailable: {type(exc).__name__}")

@router.post("/ai/ask",dependencies=[Depends(current_user)])
async def ask_ai(payload:AskAI):
    selected=selected_ai_provider(payload.provider)
    model = payload.model or payload.provider_model
    prompt=f"Target role: {payload.role or state['profile']['target_role']}. Goal: {payload.goal or state['profile'].get('goal') or state['profile'].get('primary_goal','')}. Preferred language: {payload.language}. Workspace context: {payload.context}. Learner question: {payload.question}"
    qlower=payload.question.lower()
    matched=[]
    for subject in SUBJECTS:
        if subject["name"].lower() in qlower or subject["id"].replace("-"," ") in qlower:
            matched.extend(subject["resources"])
    if not matched:
        for resource in RESOURCES:
            if resource["competency"].lower() in qlower or any(token in qlower for token in resource["competency"].lower().split() if len(token)>3):
                matched.append({"title":resource["title"],"type":resource["kind"].title(),"url":resource["url"]})
    related_links=[]; seen=set()
    for item in matched:
        if item["url"] not in seen:
            related_links.append(item); seen.add(item["url"])
        if len(related_links)>=4: break
    if selected=="puter":
        return {"answer":"","mode":"puter-client","prompt":prompt,"model":model or settings.puter_model,"related_links":related_links}
    # Puter is the primary browser provider. Ollama is the secondary server provider.
    try:
        answer,used,notice=await ask_selected(prompt,selected,model)
        if used=="demo":
            return {"answer":"","mode":"puter-client","prompt":prompt,"model":settings.puter_model,"provider":"puter","notice":"Puter AI is the primary browser provider; Ollama is the secondary server provider.","related_links":related_links}
        return {"answer":answer,"mode":used,"provider":used,"model":model if used==selected else getattr(get_provider(used),"model",None),"notice":notice,"related_links":related_links}
    except Exception:
        return {"answer":"","mode":"puter-client","prompt":prompt,"model":settings.puter_model,"provider":"puter","notice":"Puter AI is unavailable; retry after starting Puter or Ollama.","related_links":related_links}



@router.get("/learning-links",dependencies=[Depends(current_user)])
async def learning_links(field:str="",language:str=""):
    links=deepcopy(state.get("learning_links",[]))
    if field: links=[x for x in links if x.get("field"," ").lower()==field.lower()]
    if language: links=[x for x in links if x.get("language")==language]
    return {"items":links,"fields":sorted({x.get("field") for x in state.get("learning_links",[]) if x.get("field")})}

@router.post("/learning-links",dependencies=[Depends(current_user)])
async def create_learning_link(payload:LearningLinkCreate):
    item={"id":f"learn-{len(state.get('learning_links',[]))+1}",**payload.model_dump()}
    state["learning_links"].append(item)
    return {"saved":True,"item":item,"items":deepcopy(state["learning_links"])}

@router.delete("/learning-links/{link_id}",dependencies=[Depends(current_user)])
async def delete_learning_link(link_id:str):
    before=len(state["learning_links"]);state["learning_links"]=[x for x in state["learning_links"] if x.get("id")!=link_id]
    if len(state["learning_links"])==before: raise HTTPException(404,"Learning link not found")
    return {"deleted":True}

@router.post("/interview/start",dependencies=[Depends(current_user)])
async def interview_start(payload:InterviewStart):
    selected=selected_ai_provider(payload.provider); round_no=max(1,payload.question_number)
    styles=["fundamentals","applied scenario","debugging / diagnosis","trade-off decision","system design / architecture","behavioral evidence","follow-up challenge"]
    style=styles[(round_no-1)%len(styles)]
    prompt=(f"Act as a rigorous {payload.interview_type} interviewer for a {payload.role} role at {payload.level} level. "
      f"This is round {round_no} of {payload.total_questions}; use a {style} question. Focus: {payload.focus or 'role fundamentals'}. "
      f"Company context: {payload.company or 'general hiring interview'}. Ask ONE realistic question, no answer or hints. "
      "Prefer questions that reveal reasoning, assumptions, verification, trade-offs and communication rather than trivia. Language: "+payload.language)
    sid=f"int-{len(state['interview_sessions'])+1}"
    if selected=="puter": return {"mode":"puter-client","prompt":prompt,"model":payload.model or settings.puter_model,"provider":"puter","session_id":sid,"rubric":["correctness","reasoning","structure","trade-offs","communication","evidence"]}
    try:
        answer,used,notice=await ask_selected(prompt,selected,payload.model); state['interview_sessions'].append({"id":sid,"role":payload.role,"type":payload.interview_type,"level":payload.level,"questions":[answer]})
        return {"mode":"live","question":answer,"model":payload.model or getattr(get_provider(used),'model',None),"provider":used,"session_id":sid,"notice":notice,"round_style":style}
    except Exception as exc:
        return {"mode":"puter-client","prompt":prompt,"model":settings.puter_model,"provider":"puter","session_id":sid,"notice":f"Server AI unavailable: {type(exc).__name__}. Continue with Puter in the browser.","rubric":["correctness","reasoning","structure","trade-offs","communication","evidence"]}

@router.post("/interview/evaluate",dependencies=[Depends(current_user)])
async def interview_evaluate(payload:InterviewAnswer):
    prompt=("Evaluate only the supplied interview answer. Do not invent candidate experience. Return JSON with keys: overall_score_10, "
      "correctness, reasoning, structure, communication, evidence, tradeoffs (each 0-10), strengths (array), gaps (array), "
      "assumptions (array), follow_up_question, improved_outline (array), verdict. "
      f"Question: {payload.question}\nCandidate answer: {payload.answer}\nLanguage: {payload.language}")
    selected=selected_ai_provider(payload.provider)
    if selected=="puter": return {"mode":"puter-client","prompt":prompt,"model":payload.model or settings.puter_model,"provider":"puter"}
    try:
        answer,used,notice=await ask_selected(prompt,selected,payload.model)
        parsed=None
        try:
            clean=answer.strip(); clean=re.sub(r'^```(?:json)?\s*|\s*```$','',clean,flags=re.I); parsed=json.loads(clean)
        except Exception: parsed=None
        return {"mode":"live","evaluation":answer,"structured":parsed,"provider":used,"notice":notice}
    except Exception as exc:
        return {"mode":"puter-client","prompt":prompt,"model":settings.puter_model,"provider":"puter","notice":f"Server AI unavailable: {type(exc).__name__}"}

@router.post("/reasoning/analyze",dependencies=[Depends(current_user)])
async def reasoning_analyze(payload:dict):
    problem=str(payload.get("problem") or "").strip(); answer=str(payload.get("answer") or "").strip(); selected=selected_ai_provider(payload.get("provider")); model=payload.get("model")
    if not problem or not answer: raise HTTPException(400,"Both the reasoning case and your answer are required.")
    prompt=f"Analyze this reasoning response. Separate assumptions, causal chain, evidence, alternative explanations, trade-offs, risks, missing evidence and verification steps. Do not invent facts. Respond in {payload.get('language','English')}.\nCASE: {problem}\nANSWER: {answer}"
    if selected=="puter": return {"mode":"puter-client","prompt":prompt,"model":model or settings.puter_model,"provider":"puter"}
    try:
        text,used,notice=await ask_selected(prompt,selected,model)
        return {"mode":"live","analysis":text,"provider":used,"notice":notice}
    except Exception as exc:
        return {"mode":"fallback","analysis":"AI provider unavailable. Use this evidence checklist: assumptions → causal chain → observed evidence → alternative explanations → trade-offs → verification steps.","provider":"fallback","notice":f"AI unavailable: {type(exc).__name__}"}

@router.post("/interpret/analyze",dependencies=[Depends(current_user)])
async def interpret_analyze(payload:dict):
    source=str(payload.get("source") or "").strip(); selected=selected_ai_provider(payload.get("provider")); model=payload.get("model")
    if not source: raise HTTPException(400,"Source material is required.")
    prompt=f"Interpret this technical material in {payload.get('language','English')}. Return a structured map with: FACTS, IMPLICATIONS, AMBIGUITIES, ASSUMPTIONS, RISKS, TERMINOLOGY, ACTIONS. Do not invent facts.\nSOURCE:\n{source}"
    if selected=="puter": return {"mode":"puter-client","prompt":prompt,"model":model or settings.puter_model,"provider":"puter"}
    try:
        text,used,notice=await ask_selected(prompt,selected,model)
        return {"mode":"live","analysis":text,"provider":used,"notice":notice}
    except Exception as exc:
        return {"mode":"fallback","analysis":"AI provider unavailable. Review the source using this structure: FACTS → IMPLICATIONS → AMBIGUITIES → ASSUMPTIONS → RISKS → TERMINOLOGY → ACTIONS.","provider":"fallback","notice":f"AI unavailable: {type(exc).__name__}"}

@router.post("/contact")
async def contact_message(payload:ContactMessage):
    item={"id":f"contact-{len(state.get('contact_messages',[]))+1}",**payload.model_dump(),"created_at":str(date.today())}
    state["contact_messages"].insert(0,item)
    state["contact_messages"]=state["contact_messages"][:50]
    return {"received":True,"message":"Your message was recorded in the SKILLSETRA workspace demo. In production, connect this endpoint to your support mailbox or ticketing system.","id":item["id"]}

@router.get("/jobs",dependencies=[Depends(current_user)])
async def jobs():
    return {"notice":"Demo market bands only","roles":[{"role":k,"bands":[{"level":a,"location":b,"range_inr":c} for a,b,c in v]} for k,v in SALARY.items()]}


@router.get("/notifications",dependencies=[Depends(current_user)])
async def notifications():
    return {"items":deepcopy(state.get("notifications",[]))[:50]}

@router.post("/notifications/{notification_id}/read",dependencies=[Depends(current_user)])
async def notification_read(notification_id:str):
    for item in state["notifications"]:
        if item.get("id")==notification_id:item["read"]=True;return {"saved":True}
    raise HTTPException(404,"Notification not found")

@router.get("/search",dependencies=[Depends(current_user)])
async def global_search(q:str=""):
    q=q.strip().lower()
    if not q:return {"items":[]}
    items=[]
    for s in SUBJECTS:
        if q in s["name"].lower() or q in s.get("description","").lower():items.append({"type":"subject","id":s["id"],"title":s["name"],"description":s.get("description",""),"href":"/learn"})
    for r in RESOURCES:
        if q in r["title"].lower() or q in r["competency"].lower():items.append({"type":"resource","id":r["id"],"title":r["title"],"description":r.get("why","") ,"href":"/learn#resources"})
    for c in CHALLENGES:
        if q in c["title"].lower() or q in c["statement"].lower():items.append({"type":"challenge","id":c["id"],"title":c["title"],"description":c["statement"],"href":"/challenges"})
    for role in ROLES:
        if q in role["name"].lower() or q in role["description"].lower():items.append({"type":"role","id":role["name"],"title":role["name"],"description":role["description"],"href":"/career"})
    for e in state.get("evidence",[]):
        text=f"{e.get('activity','')} {e.get('competency','')} {e.get('evidence','')}".lower()
        if q in text:items.append({"type":"evidence","id":e["id"],"title":e.get("activity","Evidence"),"description":e.get("evidence",""),"href":"/evidence"})
    return {"items":items[:30]}

@router.get("/workspace",dependencies=[Depends(current_user)])
async def workspace(user=Depends(current_user)):
    return {"user":owned_profile(user),"settings":deepcopy(state["settings"]),"demo":settings.demo_mode,"evidence_count":len(state["evidence"]),"notifications_unread":sum(not n.get("read") for n in state.get("notifications",[]))}

@router.get("/analytics",dependencies=[Depends(current_user)])
async def analytics():
    attempts=state.get("assessment_attempts",[]);challenges=state.get("challenge_attempts",[]);progress=state.get("learning_progress",{})
    return {"assessment_scores":[{"date":a.get("completed_at"),"score":a.get("score",0)} for a in attempts],"challenge_scores":[{"date":a.get("completed_at"),"score":a.get("score",0)} for a in challenges],"learning_completion":round(100*sum(1 for v in progress.values() if v.get("status")=="completed")/max(1,len(progress))),"evidence_count":len(state.get("evidence",[]))}

@router.get("/learning/progress",dependencies=[Depends(current_user)])
async def learning_progress():return {"items":deepcopy(state.get("learning_progress",{}))}

@router.post("/learning/progress",dependencies=[Depends(current_user)])
async def save_learning_progress(payload:dict):
    resource_id=str(payload.get("resource_id") or "").strip();status=str(payload.get("status") or "in_progress")
    if not resource_id:raise HTTPException(400,"resource_id is required")
    if status not in {"not_started","in_progress","completed","bookmarked","unbookmarked","skipped"}:raise HTTPException(400,"Unsupported progress state")
    state["learning_progress"][resource_id]={"status":status,"updated_at":str(date.today())}
    if status=="completed":state["evidence"].insert(0,{"id":f"learn-{len(state['evidence'])+1}","activity":"Learning resource completed","competency":payload.get("competency","Learning"),"evidence":f"Completed resource {resource_id}.","result":"Observed","confidence":"Low","date":str(date.today())})
    return {"saved":True,"resource_id":resource_id,"status":status}

@router.get("/roadmap/materials",dependencies=[Depends(current_user)])
async def roadmap_materials(field:str="",topic:str=""):
    items=deepcopy(ROADMAP_MATERIALS)+deepcopy(state.get("roadmap_materials",[]))
    scanned,_=scan_materials()
    for resource in scanned:
        title=str(resource.get("title") or "Learning resource")
        topic_name=title.split(" - ",1)[0].strip() if " - " in title else str(resource.get("kind") or "Resource").title()
        items.append({
            "id":f"lm-{resource.get('id')}",
            "field":resource.get("competency") or "Learning",
            "topic":topic_name,
            "title":title,
            "description":resource.get("why") or f"Curated {resource.get('kind','resource')} for {resource.get('competency','learning')}",
            "url":resource.get("url"),
            "kind":str(resource.get("kind") or "Resource").upper()
        })
    if field: items=[x for x in items if x.get("field","").lower()==field.lower()]
    if topic: items=[x for x in items if x.get("topic","").lower()==topic.lower()]
    return {"items":items,"fields":sorted({x.get("field") for x in items if x.get("field")}),"topics":sorted({x.get("topic") for x in items if x.get("topic")})}

@router.post("/roadmap/materials",dependencies=[Depends(current_user)])
async def add_roadmap_material(payload:dict):
    field=str(payload.get("field") or "").strip();topic=str(payload.get("topic") or field).strip();title=str(payload.get("title") or "").strip();url=str(payload.get("url") or "").strip()
    if not field or not title or not url: raise HTTPException(400,"Field, title and URL are required.")
    item={"id":f"rm-custom-{len(state.get('roadmap_materials',[]))+1}","field":field,"topic":topic,"title":title,"description":str(payload.get("description") or "Custom roadmap material"),"url":url,"kind":str(payload.get("kind") or "Resource")}
    rm=state.get("roadmap_materials",[]);rm.append(item);state["roadmap_materials"]=rm
    return {"saved":True,"item":item}

@router.get("/roadmap/state",dependencies=[Depends(current_user)])
async def roadmap_state(user=Depends(current_user)):
    if state.get("roadmap"):return deepcopy(state["roadmap"])
    r=await roadmap(user);state["roadmap"]=r;return r

@router.post("/roadmap/steps/{step_id}/complete",dependencies=[Depends(current_user)])
async def complete_roadmap_step(step_id:str,user=Depends(current_user)):
    r=state.get("roadmap") or await roadmap(user)
    found=False
    for step in r["steps"]:
        if step["id"]==step_id:step["status"]="completed";found=True
    if not found:raise HTTPException(404,"Roadmap step not found")
    state["roadmap"]=r;state["notifications"].insert(0,{"id":f"n-{len(state['notifications'])+1}","title":"Roadmap updated","body":f"Completed roadmap step {step_id}.","read":False,"created_at":str(date.today())});return r

@router.post("/learning-paths/{path_id}/completion-assessment",dependencies=[Depends(current_user)])
async def completion_assessment(path_id:str):
    completed=[k for k,v in state.get("learning_progress",{}).items() if v.get("status")=="completed"]
    if not completed:raise HTTPException(409,"Learning path completion cannot be verified because no completed resources are stored.")
    r=await assessment();return {"path_id":path_id,"verified_completion":True,"question_count":max(10,min(20,len(r["questions"]))),"assessment":r,"covered_resources":completed}


@router.get("/ai/history",dependencies=[Depends(current_user)])
async def ai_history(): return {"items":deepcopy(state.get("ai_history",[]))[-40:]}

@router.post("/ai/history",dependencies=[Depends(current_user)])
async def save_ai_history(payload:dict):
    item=payload.get("item")
    if not isinstance(item,dict) or item.get("role") not in {"user","ai"}: raise HTTPException(400,"Invalid AI history item")
    state["ai_history"].append({"role":item["role"],"text":str(item.get("text",''))[:12000],"created_at":str(date.today())});state["ai_history"]=state["ai_history"][-40:]
    return {"saved":True}
