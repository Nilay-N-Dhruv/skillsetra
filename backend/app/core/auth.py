from fastapi import Depends,HTTPException,status
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from .config import settings
from .workspace import workspace_store
security=HTTPBearer(auto_error=False)
async def current_user(creds:HTTPAuthorizationCredentials=Depends(security)):
 if settings.demo_mode:
  workspace_store.bind('demo-user',None);return {'id':'demo-user','email':'demo@skillsetra.local','mode':'demo'}
 if not creds:raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail='Authentication required')
 if not settings.supabase_url or not settings.supabase_service_role_key:raise HTTPException(status_code=503,detail='Supabase production authentication is not configured')
 try:
  from supabase import create_client
  sb=create_client(settings.supabase_url,settings.supabase_service_role_key)
  result=sb.auth.get_user(creds.credentials)
  if not result.user:raise ValueError('No user')
  uid=str(result.user.id);workspace_store.bind(uid,creds.credentials)
  return {'id':uid,'email':result.user.email or '', 'mode':'supabase','token':creds.credentials}
 except Exception as exc:raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail='Invalid or expired session') from exc
