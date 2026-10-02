"use client";
import React,{useEffect,useState} from "react";
import {ArrowRight,MessageSquare,ShieldQuestion,Copy,Check} from "lucide-react";
import type {ScreenId} from "../../types";
import {api} from "../../../../lib/api";
import {runPuter} from "../../../../lib/ai";

export const SocraticDefense:React.FC<{onNavigate:(s:ScreenId)=>void}>=({onNavigate})=>{
 const[d,setD]=useState<any>();const[i,setI]=useState(0);const[answer,setAnswer]=useState("");const[result,setResult]=useState<any>();const[loading,setLoading]=useState(false);const[copied,setCopied]=useState(false);
 useEffect(()=>{api("/api/v1/project-defense").then(setD).catch(()=>setD({questions:[]}))},[]);
 const top=()=>window.requestAnimationFrame(()=>window.scrollTo({top:0,behavior:"smooth"}));
 async function submit(){
  if(!d||!answer.trim())return;setLoading(true);
  try{const r=await api<any>("/api/v1/project-defense",{method:"POST",body:JSON.stringify({project_id:d.project_id,question:d.questions[i],answer,provider:"puter",model:"openai/gpt-oss-20b",language:"English"})});
   let out:any=r;if(r.mode==="puter-client"&&r.prompt){const text=await runPuter(r.prompt,r.model||"openai/gpt-oss-20b");out={...r,ai_note:text,mode:"live"}}
   setResult(out);setAnswer("");top();
  }catch(e:any){setResult({status:"Evaluation unavailable",observed:e.message||"The project defense service could not be reached."});top()}
  finally{setLoading(false)}
 }
 function next(){setI(Math.min(i+1,(d?.questions?.length||1)-1));setResult(null);setAnswer("");top()}
 const ai=result?.ai_note||"";
 return <div className="page space-y-5">
  <div className="page-head"><div><div className="eyebrow">Project defense</div><h1>Defend the decisions behind what you built.</h1><p>Questions adapt to your project context. The result is recorded as reasoning evidence.</p></div><button className="button" onClick={()=>onNavigate("project-upgrade")}>Back to project <ArrowRight size={15}/></button></div>
  <div className="grid grid-2">
   <section className="panel"><div className="eyebrow">Question {i+1} / {d?.questions?.length||0}</div><h2>{d?.questions?.[i]||"Loading…"}</h2><div className="evaluation"><ShieldQuestion size={15}/> No single architecture is assumed correct; explain trade-offs and verification.</div></section>
   <section className="panel">
    <div className="panel-head"><h2>Your defense</h2><MessageSquare/></div>
    <textarea className="big-textarea" value={answer} onChange={e=>setAnswer(e.target.value)} placeholder="Explain the decision, alternative, trade-off and how you would verify it…"/>
    <button className="button primary" style={{marginTop:12}} disabled={loading||!answer.trim()} onClick={submit}>{loading?"Evaluating…":"Submit defense"} <ArrowRight size={15}/></button>
    {result&&<div className="panel" style={{marginTop:12}}>
      <div className="eyebrow">Evaluation · {result.provider||"SKILLsetra"}</div><h3>{result.status||"Evaluation"}</h3><p>{result.observed}</p>
      {ai&&<><div className="answer-toolbar"><button className="button" onClick={()=>{navigator.clipboard?.writeText(ai);setCopied(true);setTimeout(()=>setCopied(false),1200)}}>{copied?<Check size={13}/>:<Copy size={13}/>} {copied?"Copied":"Copy answer"}</button></div><pre className="ai-output">{ai}</pre></>}
      <p><b>Next:</b> {result.next_step||"Answer the next changed-context question."}</p>
      <button className="button" onClick={next} disabled={i>=((d?.questions?.length||1)-1)}>Next question</button>
    </div>}
   </section>
  </div>
 </div>
}
