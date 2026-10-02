from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name:str="SKILLSETRA API"
    environment:str="demo"
    demo_mode:bool=True
    supabase_url:str=""
    supabase_anon_key:str=""
    supabase_service_role_key:str=""
    ai_provider:str="puter"
    puter_model:str="openai/gpt-oss-20b"
    ollama_base_url:str="http://localhost:11434"
    ollama_model:str="llama3.2:3b"
    github_client_id:str=""
    github_client_secret:str=""
    github_token:str=""
    cors_origins:str="http://localhost:3000"
    rate_limit_per_minute:int=60
    request_timeout_seconds:int=20
    model_config=SettingsConfigDict(env_file=".env",extra="ignore",case_sensitive=False)
settings=Settings()
