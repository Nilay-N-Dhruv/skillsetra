import time,uuid
from fastapi import FastAPI,Request,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from .materials import ROOT as MATERIALS_ROOT
from .core.config import settings
from .routes import router
from .core.workspace import workspace_store
app=FastAPI(title=settings.app_name,version='3.0.0',docs_url='/docs',redoc_url='/redoc')
@app.exception_handler(HTTPException)
async def http_error(request:Request,exc:HTTPException):
 rid=request.headers.get('x-skillsetra-request-id') or str(uuid.uuid4());return JSONResponse(status_code=exc.status_code,content={'success':False,'error':{'code':f'HTTP_{exc.status_code}','message':str(exc.detail),'request_id':rid}},headers={'X-Request-ID':rid})
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(',') if x.strip()],allow_credentials=True,allow_methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'],allow_headers=['*'])
@app.middleware('http')
async def request_guard(request:Request,call_next):
 if request.url.path.startswith('/api/') and not request.url.path.startswith('/api/v1/'):
  request.scope['path']='/api/v1/'+request.url.path[len('/api/'): ]
 rid=request.headers.get('x-skillsetra-request-id') or str(uuid.uuid4());start=time.perf_counter()
 try:
  response=await call_next(request)
  if request.url.path.startswith('/api/v1'):workspace_store.persist()
  response.headers['X-Request-ID']=rid;response.headers['X-Content-Type-Options']='nosniff';response.headers['X-Frame-Options']='DENY';response.headers['Referrer-Policy']='strict-origin-when-cross-origin';response.headers['Permissions-Policy']='camera=(),microphone=(),geolocation=()';response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline' https://js.puter.com; connect-src 'self' https: http://localhost:11434; frame-ancestors 'none'; frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com"
  return response
 except Exception as exc:
  return JSONResponse(status_code=500,content={'success':False,'error':{'code':'INTERNAL_ERROR','message':'Unexpected server error','request_id':rid}},headers={'X-Request-ID':rid})
app.include_router(router)
if MATERIALS_ROOT.exists():
 app.mount("/materials-static", StaticFiles(directory=str(MATERIALS_ROOT)), name="learning-materials-static")
@app.get('/')
async def root():return {'name':'SKILLSETRA API','status':'running','docs':'/docs','mode':'demo' if settings.demo_mode else 'production'}
