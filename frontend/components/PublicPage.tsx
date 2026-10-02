"use client";
import Link from "next/link";
import {usePathname} from "next/navigation";
import Logo from "./Logo";
import {ArrowRight, ShieldCheck, Mail, FileText} from "lucide-react";

const links=[
  ["/how-it-works","How it works"],
  ["/features","Features"],
  ["/roadmap","Roadmaps"],
  ["/privacy","Privacy"],
  ["/terms","Terms"],
  ["/contact","Contact"]
] as const;

export default function PublicPage({eyebrow,title,children}:{eyebrow:string;title:string;children:React.ReactNode}){
 const path=usePathname();
 return <div className="marketing public-site">
  <header className="marketing-nav" role="banner">
   <div className="marketing-brand"><Logo/></div>
   <nav aria-label="Public navigation">
    {links.map(([href,label])=><Link key={href} className={path===href?"active":""} href={href}>{label}</Link>)}
   </nav>
   <div className="nav-cta"><Link className="btn ghost small" href="/signin">Sign in</Link><Link className="btn primary small" href="/signup">Get started</Link></div>
  </header>
  <main className="container public-page">
   <div className="public-hero">
    <div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1></div>
    <div className="public-hero-note"><ShieldCheck size={17}/><span>Evidence-first · AI-assisted · learner controlled</span></div>
   </div>
   <div className="public-copy">{children}</div>
   <div className="public-actions">
    <Link className="btn primary" href="/signup">Start with SKILLsetra <ArrowRight size={15}/></Link>
    <Link className="btn ghost" href="/">Back home</Link>
   </div>
  </main>
  <footer className="marketing-footer">
   <div className="container footer-grid">
    <div className="footer-brand-block"><div className="marketing-brand footer-brand"><Logo/></div><p>Learn · Build · Prove · Grow</p><small>Competency intelligence for practical, transferable skills.</small></div>
    <div><b>Product</b><Link href="/how-it-works">How it works</Link><Link href="/features">Features</Link><Link href="/roadmap">Roadmaps</Link></div>
    <div><b>Trust & policy</b><Link href="/privacy">Privacy policy</Link><Link href="/terms">Terms of use</Link><Link href="/contact">Contact</Link></div>
    <div><b>Support</b><span><Mail size={13}/> Product questions</span><span><FileText size={13}/> Policy & account requests</span><span>AI output should be reviewed before consequential decisions.</span></div>
   </div>
   <div className="container footer-bottom"><span>© 2026 SKILLsetra</span><span>Built for evidence-driven learning</span></div>
  </footer>
 </div>
}
