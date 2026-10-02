from contextvars import ContextVar
from copy import deepcopy
from pathlib import Path
import json, sqlite3
from ..data import DEMO_PROFILE,EVIDENCE
from .config import settings

_workspace_user:ContextVar[str]=ContextVar('skillsetra_workspace_user',default='demo-user')
_workspace_token:ContextVar[str|None]=ContextVar('skillsetra_workspace_token',default=None)
_ROOT=Path(__file__).resolve().parents[2]
_DB=_ROOT/'data'/'skillsetra_demo.db'
_BASE_TEMPLATE={
 'profile':{'id':'','name':'','email':'','target_role':'','experience':'','goal':'','primary_goal':''},
 'settings':{'ai_provider':settings.ai_provider,'ai_model':settings.puter_model,'notifications':True,'appearance':'dark','privacy':True,'language':'English'},
 'evidence':[],'evidence_claims':[],'competency_progress':{},'retest_index':0,'selected_repos':[],'github_analysis':None,'learning_links':[],'interview_sessions':[],
 'notifications':[],'contact_messages':[],'github_connection':None,'roadmap_materials':[],'learning_progress':{},'bookmarks':[],'roadmap':None,'assessment_attempts':[],'challenge_attempts':[],'projects':[],'ai_history':[]
}
_DEMO_TEMPLATE=deepcopy(_BASE_TEMPLATE)
_DEMO_TEMPLATE['profile']=deepcopy(DEMO_PROFILE)
_DEMO_TEMPLATE['evidence']=deepcopy(EVIDENCE)

def _sqlite():
 _DB.parent.mkdir(parents=True,exist_ok=True); c=sqlite3.connect(_DB);c.execute('create table if not exists workspace_snapshots(user_id text primary key,data text not null,updated_at text default current_timestamp)');c.commit();return c

def _supabase_client():
 if not settings.supabase_url or not settings.supabase_anon_key:return None
 token=_workspace_token.get()
 if not token:return None
 try:
  from supabase import create_client
  sb=create_client(settings.supabase_url,settings.supabase_anon_key)
  sb.postgrest.auth(token)
  return sb
 except Exception:return None

class WorkspaceStore:
 def __init__(self): self._cache={}
 def bind(self,user_id:str,token:str|None=None): _workspace_user.set(user_id);_workspace_token.set(token);return user_id
 def _load(self,uid):
  if settings.demo_mode:
   c=_sqlite();r=c.execute('select data from workspace_snapshots where user_id=?',(uid,)).fetchone();c.close()
   if r:
    try:
     loaded=json.loads(r[0]);base=deepcopy(_DEMO_TEMPLATE if settings.demo_mode else _BASE_TEMPLATE)
     for key,value in base.items(): loaded.setdefault(key,deepcopy(value))
     return loaded
    except Exception:pass
   return deepcopy(_DEMO_TEMPLATE if settings.demo_mode else _BASE_TEMPLATE)
  sb=_supabase_client()
  if sb:
   try:
    r=sb.table('workspace_snapshots').select('data').eq('user_id',uid).maybe_single().execute()
    if r.data and r.data.get('data'):
     loaded=r.data['data'];base=deepcopy(_DEMO_TEMPLATE if settings.demo_mode else _BASE_TEMPLATE)
     for key,value in base.items(): loaded.setdefault(key,deepcopy(value))
     return loaded
   except Exception:pass
  return deepcopy(_DEMO_TEMPLATE if settings.demo_mode else _BASE_TEMPLATE)
 def _current(self):
  uid=_workspace_user.get()
  if uid not in self._cache:self._cache[uid]=self._load(uid)
  return self._cache[uid]
 def persist(self):
  uid=_workspace_user.get();data=self._cache.get(uid)
  if data is None:return
  if settings.demo_mode:
   c=_sqlite();c.execute('insert into workspace_snapshots(user_id,data,updated_at) values(?,?,current_timestamp) on conflict(user_id) do update set data=excluded.data,updated_at=current_timestamp',(uid,json.dumps(data)));c.commit();c.close();return
  sb=_supabase_client()
  if sb:
   sb.table('workspace_snapshots').upsert({'user_id':uid,'data':data}).execute()
 def reset(self,uid:str):
  self._cache.pop(uid,None)
  if settings.demo_mode:
   c=_sqlite();c.execute('delete from workspace_snapshots where user_id=?',(uid,));c.commit();c.close()
  return self.bind(uid,None)

 def __getitem__(self,key):return self._current()[key]
 def __setitem__(self,key,value):self._current()[key]=value
 def get(self,key,default=None):return self._current().get(key,default)

workspace_store=WorkspaceStore()
