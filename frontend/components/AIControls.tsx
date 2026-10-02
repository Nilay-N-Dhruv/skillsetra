"use client";
import {useEffect,useState} from "react";
import {api} from "../lib/api";

type Props={provider:string;model:string;onProvider:(v:string)=>void;onModel:(v:string)=>void};
export default function AIControls({provider,model,onProvider,onModel}:Props){
 const [models,setModels]=useState<any[]>([]);
 useEffect(()=>{api<any>(`/api/v1/ai/models?provider=${encodeURIComponent(provider)}`).then(r=>{const list=r.models||[];setModels(list);if(list.length&&!list.some((m:any)=>(m.id||m)===model))onModel(list[0].id||list[0])}).catch(()=>setModels([]))},[provider]);
 return <div className="ai-controls"><label>AI PROVIDER<select value={provider} onChange={e=>onProvider(e.target.value)}><option value="puter">PUTER AI · PRIMARY</option><option value="ollama">OLLAMA · SECONDARY</option></select></label><label>AI MODEL<select value={model} onChange={e=>onModel(e.target.value)}>{(models.length?models:[{id:model,label:model}]).map((m:any)=><option key={m.id||m} value={m.id||m}>{m.label||m.id||m}</option>)}</select></label></div>
}
