import {api} from "./api";

export type AIProviderId = "puter" | "ollama";
export type AIProviderInfo = {
  id: AIProviderId;
  name: string;
  tier: string;
  model: string;
  status: string;
  connected: boolean;
  server_side: boolean;
  models?: string[] | {id:string;label:string;recommended?:boolean}[];
};

export function extractPuterText(result:any):string {
  const raw = typeof result === "string" ? result : result?.message?.content ?? result?.text ?? result?.content ?? "";
  if (Array.isArray(raw)) return raw.map((x:any)=>x?.text ?? x?.content ?? "").join("");
  return String(raw || "").trim();
}

export async function runPuter(prompt:string, model:string) {
  let puterError:unknown=null;
  try {
    if (typeof window === "undefined") throw new Error("Puter AI requires a browser.");
    const deadline=Date.now()+8000;
    while(!window.puter?.ai?.chat && Date.now()<deadline){await new Promise(r=>setTimeout(r,200));}
    if(!window.puter?.ai?.chat) throw new Error("Puter AI did not finish loading.");
    const result = await window.puter.ai.chat(prompt, {model, temperature:0.35, normalize:true});
    const text = extractPuterText(result);
    if (text) return text;
    throw new Error("Puter AI returned an empty response.");
  } catch (error) {
    puterError=error;
  }
  // Secondary path: the exact same prompt is sent to Ollama through the backend.
  try {
    const fallback=await api<{answer:string}>("/api/v1/ai/fallback",{method:"POST",body:JSON.stringify({prompt})});
    if(fallback.answer?.trim()) return fallback.answer.trim();
  } catch (fallbackError:any) {
    throw new Error(`Puter AI unavailable and Ollama fallback failed. ${fallbackError?.message||String(puterError||"Try again.")}`);
  }
  throw new Error(`Puter AI unavailable. ${String(puterError||"Try again.")}`);
}

export async function getAIProviders() {
  return api<{default:string;providers:AIProviderInfo[]}>('/api/v1/ai/providers');
}
