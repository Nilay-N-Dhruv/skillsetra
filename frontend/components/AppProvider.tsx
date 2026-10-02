"use client";
import {createContext,useContext,useEffect,useMemo,useState} from "react";
import {supabase} from "../lib/supabase";
import Logo from "./Logo";

type User={id:string;name:string;email:string;targetRole:string};
type Ctx={user:User|null;loading:boolean;demo:boolean;language:string;setLanguage:(x:string)=>void;theme:"dark"|"light";setTheme:(x:"dark"|"light")=>void;startDemo:()=>Promise<void>;setTargetRole:(x:string)=>void;signIn:(e:string,p:string)=>Promise<void>;signUp:(n:string,e:string,p:string)=>Promise<{authenticated:boolean}>;signOut:()=>Promise<void>};
const demoEnabled=process.env.NEXT_PUBLIC_DEMO_MODE === "true";
const C=createContext<Ctx>({user:null,loading:true,demo:demoEnabled,language:"English",setLanguage:()=>{},theme:"dark",setTheme:()=>{},startDemo:async()=>{},signIn:async()=>{},signUp:async()=>({authenticated:false}),signOut:async()=>{},setTargetRole:()=>{}});
function saveSessionCookie(name:string){document.cookie=`${name}=1; Path=/; SameSite=Lax`}
function clearSessionCookie(name:string){document.cookie=`${name}=; Path=/; Max-Age=0; SameSite=Lax`}
function saveDemo(u:User){localStorage.setItem("skillsetra_demo_user",JSON.stringify(u));saveSessionCookie("skillsetra_demo_session")}
function clearDemo(){localStorage.removeItem("skillsetra_demo_user");clearSessionCookie("skillsetra_demo_session")}
export function AppProvider({children}:{children:React.ReactNode}){
 const [user,setUser]=useState<User|null>(null),[loading,setLoading]=useState(true),[language,setLanguageState]=useState("English"),[theme,setThemeState]=useState<"dark"|"light">("dark");
 useEffect(()=>{
  document.documentElement.dataset.theme=theme;
  localStorage.setItem("skillsetra_theme",theme);
 },[theme]);
 useEffect(()=>{
  const l=localStorage.getItem("skillsetra_language");const t=localStorage.getItem("skillsetra_theme");const chosen=localStorage.getItem("skillsetra_theme_user_set");if(l)setLanguageState(l);if(chosen==="1"&&(t==="dark"||t==="light"))setThemeState(t);else{setThemeState("dark");localStorage.setItem("skillsetra_theme","dark")}
  (async()=>{
   if(demoEnabled){
    const raw=localStorage.getItem("skillsetra_demo_user");
    if(raw){
      try{setUser(JSON.parse(raw))}
      catch{clearDemo();}
    }
    if(!localStorage.getItem("skillsetra_demo_user")){
      const demoUser={id:"demo-user",name:"Demo Learner",email:"demo@skillsetra.local",targetRole:""};
      saveDemo(demoUser);setUser(demoUser);
    }
    setLoading(false);return;
  }
   if(!supabase){setLoading(false);return;}
   const {data}=await supabase.auth.getSession();if(data.session){const u=data.session.user;localStorage.setItem("skillsetra_access_token",data.session.access_token);saveSessionCookie("skillsetra_session");setUser({id:u.id,name:u.user_metadata?.name||u.email?.split("@")[0]||"Learner",email:u.email||"",targetRole:u.user_metadata?.target_role||"ML Engineer"})}
   const {data:listener}=supabase.auth.onAuthStateChange((_event,session)=>{if(session){localStorage.setItem("skillsetra_access_token",session.access_token);saveSessionCookie("skillsetra_session");setUser({id:session.user.id,name:session.user.user_metadata?.name||session.user.email?.split("@")[0]||"Learner",email:session.user.email||"",targetRole:session.user.user_metadata?.target_role||"ML Engineer"})}else{localStorage.removeItem("skillsetra_access_token");clearSessionCookie("skillsetra_session");setUser(null)}});setLoading(false);return()=>listener.subscription.unsubscribe();
  })();
 },[]);
 useEffect(()=>{document.documentElement.dataset.theme=theme;document.documentElement.lang=language==="Hindi"?"hi":language==="Gujarati"?"gu":language==="Spanish"?"es":"en";localStorage.setItem("skillsetra_language",language);localStorage.setItem("skillsetra_theme",theme)},[language,theme]);
 const startDemo=async()=>{if(!demoEnabled)return;localStorage.removeItem("skillsetra_demo_user");localStorage.removeItem("skillsetra_access_token");const u={id:"demo-user",name:"Demo Learner",email:"demo@skillsetra.local",targetRole:""};
  // Reset the backend before navigation so the first-session target/evidence flow cannot race the reset.
  try{await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL||"http://localhost:8000"}/api/v1/demo/reset`,{method:"POST"})}catch{}
  saveDemo(u);setUser(u);
 };
 const signIn=async(e:string,p:string)=>{if(demoEnabled){if(!e.includes("@")||p.length<6)throw new Error("Enter a valid email and a password of at least 6 characters.");const u={id:"demo-user",name:e.split("@")[0],email:e,targetRole:"ML Engineer"};saveDemo(u);setUser(u);return;}if(!supabase)throw new Error("Supabase is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.");const {data,error}=await supabase.auth.signInWithPassword({email:e,password:p});if(error||!data.session)throw new Error(error?.message||"Unable to sign in");localStorage.setItem("skillsetra_access_token",data.session.access_token);saveSessionCookie("skillsetra_session");setUser({id:data.user.id,name:data.user.user_metadata?.name||e.split("@")[0],email:e,targetRole:data.user.user_metadata?.target_role||"ML Engineer"});};
 const signUp=async(n:string,e:string,p:string)=>{if(p.length<8)throw new Error("Use at least 8 characters.");if(demoEnabled){const u={id:"demo-user",name:n,email:e,targetRole:"ML Engineer"};saveDemo(u);setUser(u);return {authenticated:true}}if(!supabase)throw new Error("Supabase is not configured.");const {data,error}=await supabase.auth.signUp({email:e,password:p,options:{data:{name:n,target_role:"ML Engineer"}}});if(error)throw new Error(error.message);if(data.session){localStorage.setItem("skillsetra_access_token",data.session.access_token);saveSessionCookie("skillsetra_session");setUser({id:data.user!.id,name:n,email:e,targetRole:"ML Engineer"});return {authenticated:true}}return {authenticated:false};};
 const setTargetRole=(role:string)=>{setUser(u=>u?{...u,targetRole:role}:u);const raw=localStorage.getItem("skillsetra_demo_user");if(raw){try{const u=JSON.parse(raw);u.targetRole=role;localStorage.setItem("skillsetra_demo_user",JSON.stringify(u))}catch{}}};
 const signOut=async()=>{if(demoEnabled){clearDemo();setUser(null);return;}if(supabase)await supabase.auth.signOut();localStorage.removeItem("skillsetra_access_token");clearSessionCookie("skillsetra_session");setUser(null)};
 const value=useMemo(()=>({user,loading,demo:demoEnabled,language,setLanguage:(x:string)=>{setLanguageState(x);localStorage.setItem("skillsetra_language",x)},theme,setTheme:(x:string)=>{localStorage.setItem("skillsetra_theme_user_set","1");setThemeState(x)},startDemo,setTargetRole,signIn,signUp,signOut}),[user,loading,language,theme]);
 return <C.Provider value={value}>{children}</C.Provider>
}
export const useApp=()=>useContext(C);
export function RequireAuth({children}:{children:React.ReactNode}){const {user,loading,demo}=useApp();if(loading)return <main className="boot" aria-label="Loading SKILLsetra"><img className="loading-logo" src="/skillsetra-logo.png" alt="SKILLsetra"/><div className="boot-line" aria-hidden="true"><span/></div></main>;if(!user)return <div className="locked"><div className="auth-card"><Logo/><h2>Your competency workspace is private.</h2><p>Sign in to continue your evidence-driven career workspace.</p><a className="button primary" href="/signin">Sign in</a></div></div>;return <>{children}</>}
