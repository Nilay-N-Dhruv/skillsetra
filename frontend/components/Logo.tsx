import Link from "next/link";

export default function Logo({compact=false}:{compact?:boolean}){
  return <Link href="/" className={`skillsetra-logo ${compact?"compact":""}`} aria-label="Skillsetra home">
    <img src="/skillsetra-logo.png" alt="Skillsetra — Learn, Build, Prove, Grow" />
  </Link>;
}
