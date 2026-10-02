const BASE=(process.env.NEXT_PUBLIC_API_BASE_URL||"").replace(/\/$/,"");
function v1(path:string){
  if(path.startsWith('/api/v1/')) return path;
  if(path.startsWith('/api/')) return path.replace(/^\/api\//,'/api/v1/');
  return path.startsWith('/')?`/api/v1${path}`:`/api/v1/${path}`;
}
export async function api<T=unknown>(path:string, options:RequestInit={}):Promise<T>{
  const controller=new AbortController();
  const timeout=window.setTimeout(()=>controller.abort(),Number(process.env.NEXT_PUBLIC_API_TIMEOUT_MS||20000));
  const headers=new Headers(options.headers);
  if(options.body&&!headers.has('Content-Type')) headers.set('Content-Type','application/json');
  headers.set('X-SKILLSETRA-Request-ID',crypto.randomUUID?.()||`${Date.now()}-${Math.random()}`);
  if(typeof window!=='undefined'){
    const token=localStorage.getItem('skillsetra_access_token');
    if(token) headers.set('Authorization',`Bearer ${token}`);
  }
  try{
    const response=await fetch(`${BASE}${v1(path)}`,{...options,headers,cache:'no-store',signal:controller.signal});
    if(!response.ok){
      let data:any={};try{data=await response.json()}catch{}
      const err:any=new Error(data?.error?.message||data?.detail||data?.message||`Request failed (${response.status})`);
      err.code=data?.error?.code||`HTTP_${response.status}`;
      err.status=response.status;
      err.requestId=data?.error?.request_id||response.headers.get('x-request-id')||undefined;
      throw err;
    }
    return await response.json() as T;
  }finally{window.clearTimeout(timeout)}
}
export {BASE};
