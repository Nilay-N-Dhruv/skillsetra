from pydantic import BaseModel,Field

class ChallengeSubmit(BaseModel):
    answer:str=Field(min_length=1,max_length=12000)
    provider:str|None=None
    model:str|None=None
    language:str="English"

class ProjectAnalyze(BaseModel):
    name:str=Field(min_length=1,max_length=120)
    description:str=Field(min_length=10,max_length=5000)
    provider:str|None=None
    model:str|None=None
    language:str="English"

class GoalUpdate(BaseModel):
    target_role:str
    experience:str
    goal:str

class ProfileUpdate(BaseModel):
    name:str
    target_role:str
    goal:str

class SettingsUpdate(BaseModel):
    ai_provider:str="puter"
    ai_model:str="openai/gpt-oss-20b"
    language:str="English"
    notifications:bool=True
    appearance:str="dark"
    privacy:bool=True

class AskAI(BaseModel):
    question:str=Field(min_length=2,max_length=5000)
    context:str="general"
    language:str="English"
    provider:str|None=None
    model:str|None=None
    provider_model:str|None=None
    role:str=""
    goal:str=""

class AssessmentSubmit(BaseModel):
    assessment_id:str
    answers:dict[str,str]

class UpgradeSubmit(BaseModel):
    project_id:str="demo-project"
    upgrade_id:str

class ResourceSummary(BaseModel):
    resource_id:str
    language:str="English"
    provider:str|None=None
    model:str|None=None

class DefenseSubmit(BaseModel):
    project_id:str="demo-project"
    question:str
    answer:str=Field(min_length=1,max_length=6000)
    provider:str|None=None
    model:str|None=None
    language:str="English"

class GitHubConnectRequest(BaseModel):
    token:str=Field(min_length=1,max_length=5000)

class GitHubAnalyzeRequest(BaseModel):
    url:str=Field(min_length=10,max_length=500)
    provider:str|None=None
    model:str|None=None
    language:str="English"


class LearningLinkCreate(BaseModel):
    field:str=Field(min_length=1,max_length=120)
    language:str="English"
    title:str=Field(min_length=1,max_length=200)
    url:str=Field(min_length=5,max_length=1000)
    kind:str="Course"
    pdf_url:str=""
    description:str=""

class InterviewStart(BaseModel):
    role:str="Software Developer"
    interview_type:str="Technical"
    level:str="Intermediate"
    language:str="English"
    provider:str|None=None
    model:str|None=None
    company:str=""
    focus:str=""
    mode:str="mock"
    question_number:int=1
    total_questions:int=5

class InterviewAnswer(BaseModel):
    session_id:str
    question:str
    answer:str=Field(min_length=1,max_length=12000)
    language:str="English"
    provider:str|None=None
    model:str|None=None


class EvidenceClaimCreate(BaseModel):
    claim:str=Field(min_length=3,max_length=500)
    competency:str=Field(min_length=1,max_length=120)
    target_role:str=''
    evidence_title:str=Field(default="Self-declared claim",min_length=3,max_length=200)
    evidence_description:str=Field(default="",max_length=5000)
    evidence_type:str='Project artifact'
    evidence_url:str=''
    existing_evidence_id:str=''


class AIReviewPayload(BaseModel):
    result:str=Field(min_length=1,max_length=12000)
    provider:str="puter"


class ContactMessage(BaseModel):
    name:str=Field(min_length=1,max_length=120)
    email:str=Field(min_length=5,max_length=320)
    subject:str=Field(min_length=3,max_length=200)
    message:str=Field(min_length=10,max_length=6000)
