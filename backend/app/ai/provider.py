from abc import ABC, abstractmethod
from typing import Any
import httpx
from ..core.config import settings

class AIProvider(ABC):
    name='unknown'; tier=''; model=''
    @abstractmethod
    async def ask(self,prompt:str,model:str|None=None)->str: ...
    async def health(self)->dict[str,Any]:
        return {'connected':False,'configured':False,'message':'Not configured.','models':[]}

class OllamaProvider(AIProvider):
    name='ollama'; tier='server-local'; model=settings.ollama_model
    async def ask(self,prompt:str,model:str|None=None)->str:
        selected=model or settings.ollama_model
        if not selected: raise RuntimeError('No Ollama model selected.')
        async with httpx.AsyncClient(timeout=75) as c:
            r=await c.post(f'{settings.ollama_base_url.rstrip("/")}/api/generate',json={'model':selected,'prompt':prompt,'stream':False,'options':{'temperature':0.22}})
            r.raise_for_status(); d=r.json()
        text=d.get('response','').strip()
        if not text: raise RuntimeError('Ollama returned an empty response.')
        return text
    async def health(self):
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                r=await c.get(f'{settings.ollama_base_url.rstrip("/")}/api/tags'); r.raise_for_status(); models=[m.get('name') for m in r.json().get('models',[]) if m.get('name')]
            return {'connected':True,'configured':True,'message':'Ollama is reachable.','models':models}
        except Exception:
            return {'connected':False,'configured':True,'message':'Ollama is not reachable. Start Ollama to use the secondary AI provider.','models':[]}

def get_provider(name:str|None=None):
    selected=(name or settings.ai_provider).lower()
    if selected=='ollama': return OllamaProvider()
    raise ValueError('Unsupported AI provider. Use Puter AI or Ollama.')

async def server_provider_health(name:str):
    p=get_provider(name); r=await p.health(); return {'id':name,'name':p.name,'tier':p.tier,**r}

async def ask_selected(prompt:str,selected:str,model:str|None=None):
    selected=(selected or settings.ai_provider).lower()
    if selected=='puter': raise RuntimeError('Puter AI runs in the browser; use the Puter handoff.')
    if selected!='ollama': raise RuntimeError('Only Ollama is enabled server-side.')
    answer=await get_provider('ollama').ask(prompt,model)
    return answer,'ollama',None
