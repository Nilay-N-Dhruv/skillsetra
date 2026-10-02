"use client";
import {FormEvent,useState} from "react";
import PublicPage from "../../components/PublicPage";
import {Send,CheckCircle2,Mail,MessageSquareText,ShieldQuestion,Clock3} from "lucide-react";

export default function Contact(){
 const [form,setForm]=useState({name:"",email:"",subject:"",message:""});
 const [busy,setBusy]=useState(false),[done,setDone]=useState(""),[error,setError]=useState("");
 async function submit(e:FormEvent){
  e.preventDefault();setBusy(true);setError("");setDone("");
  try{
   const base=(process.env.NEXT_PUBLIC_API_BASE_URL||"http://localhost:8000").replace(/\/$/,"");
   const controller=new AbortController();const timer=window.setTimeout(()=>controller.abort(),9000);
   const r=await fetch(`${base}/api/v1/contact`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(form),signal:controller.signal});
   window.clearTimeout(timer);
   let data:any={};try{data=await r.json()}catch{}
   if(!r.ok)throw new Error(data.detail||data.message||"The contact service could not accept the message.");
   setDone(data.message||"Your message has been received.");setForm({name:"",email:"",subject:"",message:""});
  }catch(e:any){setError(e.name==="AbortError"?"The contact service took too long to respond. Check that the backend is running and try again.":e.message||"We could not submit your message.");}
  finally{setBusy(false)}
 }
 return <PublicPage eyebrow="Contact" title="A clear place for product, policy and support questions.">
  <div className="contact-layout">
   <section className="contact-intro-panel">
    <div className="contact-card"><Mail/><div><b>Product questions</b><p>Ask about evidence, competency mapping, challenges, projects, roadmaps or AI-assisted features.</p></div></div>
    <div className="contact-card"><MessageSquareText/><div><b>Bug reports</b><p>Include the page, action, visible error and steps to reproduce. Never include passwords or access tokens.</p></div></div>
    <div className="contact-card"><ShieldQuestion/><div><b>Privacy & policy</b><p>For account, data or policy questions, identify the relevant deployment and request without sharing confidential credentials.</p></div></div>
    <div className="contact-card"><Clock3/><div><b>Response expectations</b><p>This demo does not promise a support SLA. Production deployments should publish their own support channel and response commitments.</p></div></div>
   </section>
   <section className="contact-form-panel">
    <div className="form-panel-head"><div><div className="eyebrow">Send a message</div><h2>Tell us what needs attention.</h2></div><Mail size={18}/></div>
    {done&&<div className="notice" role="status"><CheckCircle2 size={15}/> {done}</div>}
    {error&&<div className="error" role="alert">{error}</div>}
    <form className="public-contact-form" onSubmit={submit}>
     <div className="form-grid">
      <div className="field"><label htmlFor="contact-name">NAME</label><input id="contact-name" required autoComplete="name" value={form.name} onChange={e=>setForm(x=>({...x,name:e.target.value}))}/></div>
      <div className="field"><label htmlFor="contact-email">EMAIL</label><input id="contact-email" required type="email" autoComplete="email" value={form.email} onChange={e=>setForm(x=>({...x,email:e.target.value}))}/></div>
      <div className="field full"><label htmlFor="contact-subject">SUBJECT</label><input id="contact-subject" required maxLength={120} value={form.subject} onChange={e=>setForm(x=>({...x,subject:e.target.value}))}/></div>
      <div className="field full"><label htmlFor="contact-message">MESSAGE</label><textarea id="contact-message" required minLength={10} maxLength={4000} className="big-textarea" value={form.message} onChange={e=>setForm(x=>({...x,message:e.target.value}))} placeholder="Describe the question or issue, what you expected, and what happened…"/></div>
     </div>
     <div className="contact-form-foot"><small>Do not include passwords, API keys, GitHub tokens or other secrets.</small><button className="btn primary" disabled={busy}>{busy?"Sending…":<>Send message <Send size={14}/></>}</button></div>
    </form>
   </section>
  </div>
 </PublicPage>
}
