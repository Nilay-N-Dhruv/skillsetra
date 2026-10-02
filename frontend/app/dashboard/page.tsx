"use client";
import {useRouter} from "next/navigation";
import {StitchShell} from "../../components/StitchShell";import {useApp} from "../../components/AppProvider";import {useEffect} from "react";
import { Dashboard } from "../../components/stitch-source/components/Screens/Dashboard";
import type {ScreenId} from "../../components/stitch-source/types";
export default function Page(){
 const router=useRouter();const {demo,user,loading}=useApp();
 useEffect(()=>{if(!loading&&demo&&user&&!user.targetRole)router.replace("/onboarding")},[loading,demo,user,router]);
 if(demo&&user&&!user.targetRole)return <main className="boot" aria-label="Loading SKILLsetra"><img className="loading-logo" src="/skillsetra-logo.png" alt="SKILLsetra"/><div className="boot-line" aria-hidden="true"><span/></div></main>;
 const onNavigate=(s:ScreenId)=>{const map:Record<ScreenId,string>={landing:"/",dashboard:"/dashboard",competencies:"/competencies",challenges:"/challenges","project-upgrade":"/projects",career:"/career",roadmap:"/roadmap","project-defense":"/project-defense",diagnostic:"/assessment",profile:"/profile",settings:"/settings"};router.push(map[s]||"/dashboard")};
 return <StitchShell screen="dashboard"><Dashboard onNavigate={onNavigate}/></StitchShell>
}
