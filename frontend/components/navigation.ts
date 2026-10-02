import { LayoutDashboard, Target, FileCheck2, FlaskConical, BrainCircuit, Brain, ShieldQuestion, FolderKanban, Github, Route, BookOpen, Library, BriefcaseBusiness, UserRound, Settings2, Bell, FileText, MessageSquareText, Mic2, Search, Scale, LifeBuoy, ClipboardCheck, ScanSearch, BarChart3 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type NavGroup = 'WORKSPACE'|'TEST / PROVE'|'BUILD'|'LEARN'|'CAREER'|'ACCOUNT'|'LEGAL';
export type NavItem = { id:string; label:string; href:string; icon:LucideIcon; group:NavGroup; keywords?:string[] };
export const NAVIGATION:NavItem[] = [
 {id:'dashboard',label:'Dashboard',href:'/dashboard',icon:LayoutDashboard,group:'WORKSPACE',keywords:['home','overview']},
 {id:'competencies',label:'Competencies',href:'/competencies',icon:Target,group:'WORKSPACE',keywords:['skills','gaps']},
 {id:'evidence',label:'Evidence',href:'/evidence',icon:FileCheck2,group:'WORKSPACE',keywords:['proof','verification','claim evidence','target evidence']},
 {id:'assessment',label:'Assessment',href:'/assessment',icon:FlaskConical,group:'TEST / PROVE',keywords:['test','diagnostic']},
 {id:'assessments',label:'Assessment Studio',href:'/assessments',icon:ClipboardCheck,group:'TEST / PROVE',keywords:['assessment','quiz','adaptive','reasoning']},
 {id:'reasoning',label:'Reasoning Lab',href:'/reasoning',icon:Brain,group:'TEST / PROVE',keywords:['logic','reasoning','interpretation']},
 {id:'interpret',label:'Interpretation',href:'/interpret',icon:ScanSearch,group:'BUILD',keywords:['interpret','analyze','explain']},
 {id:'challenges',label:'Challenges',href:'/challenges',icon:BrainCircuit,group:'TEST / PROVE',keywords:['coding','debugging','practice']},
 {id:'project-defense',label:'Project Defense',href:'/project-defense',icon:ShieldQuestion,group:'TEST / PROVE',keywords:['socratic','defense']},
 {id:'interview',label:'AI Interviewer',href:'/interview',icon:Mic2,group:'TEST / PROVE',keywords:['interview','practice']},
 {id:'projects',label:'Projects',href:'/projects',icon:FolderKanban,group:'BUILD',keywords:['portfolio','build']},
 {id:'github',label:'GitHub Intelligence',href:'/github',icon:Github,group:'BUILD',keywords:['repository','repo','code']},
 {id:'roadmap',label:'Roadmap',href:'/roadmap',icon:Route,group:'BUILD',keywords:['plan','journey']},
 {id:'learn',label:'Learning Paths',href:'/learn',icon:BookOpen,group:'LEARN',keywords:['learn','courses','subjects']},
 {id:'resources',label:'Resources',href:'/learn?view=resources',icon:Library,group:'LEARN',keywords:['docs','videos','pdf']},
 {id:'practice',label:'Practice',href:'/practice',icon:FileText,group:'LEARN',keywords:['exercise','lab']},
 {id:'career',label:'Career Intelligence',href:'/career',icon:BriefcaseBusiness,group:'CAREER',keywords:['roles','jobs','salary']},
 {id:'roles',label:'Roles',href:'/career?view=roles',icon:Scale,group:'CAREER',keywords:['role','readiness']},
 {id:'jobs',label:'Jobs / Opportunities',href:'/career?view=jobs',icon:LifeBuoy,group:'CAREER',keywords:['jobs','opportunities']},
 {id:'profile',label:'Profile',href:'/profile',icon:UserRound,group:'ACCOUNT',keywords:['account','target']},
 {id:'settings',label:'Settings',href:'/settings',icon:Settings2,group:'ACCOUNT',keywords:['preferences','AI']},
 {id:'analytics',label:'Analytics',href:'/analytics',icon:BarChart3,group:'ACCOUNT',keywords:['progress','insights','metrics']},
 {id:'notifications',label:'Notifications',href:'/notifications',icon:Bell,group:'ACCOUNT',keywords:['alerts','notifications']},
 {id:'privacy',label:'Privacy',href:'/privacy',icon:ShieldQuestion,group:'LEGAL',keywords:['data','security']},
 {id:'terms',label:'Terms',href:'/terms',icon:FileText,group:'LEGAL'},
 {id:'contact',label:'Contact',href:'/contact',icon:MessageSquareText,group:'LEGAL'},
];
export const GROUPS:NavGroup[]=['WORKSPACE','TEST / PROVE','BUILD','LEARN','CAREER','ACCOUNT','LEGAL'];
export function searchNavigation(query:string){const q=query.trim().toLowerCase(); if(!q)return []; return NAVIGATION.filter(n=>[n.label,n.id,n.group,...(n.keywords||[])].join(' ').toLowerCase().includes(q)).slice(0,12);}
