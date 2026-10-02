"use client";
import {useRouter} from "next/navigation";
import {PublicLanding} from "../components/stitch-source/components/Screens/PublicLanding";
import {useApp} from "../components/AppProvider";
export default function Home(){const router=useRouter();const {demo,startDemo,user}=useApp();const begin=async()=>{if(demo){await startDemo();router.push("/onboarding")}else router.push("/signup")};return <PublicLanding demo={demo} signedIn={!!user} onDemo={begin}/>;}
