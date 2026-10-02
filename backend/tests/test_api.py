from app.core.config import settings
settings.demo_mode=True
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_health():
    r=client.get("/api/health"); assert r.status_code==200; assert r.json()["status"]=="ok"

def test_private_competencies():
    r=client.get("/api/competencies"); assert r.status_code==200; assert len(r.json()["items"])>=15

def test_assessment():
    r=client.get("/api/assessment"); assert r.status_code==200; assert len(r.json()["questions"])>=10

def test_challenge_submit():
    r=client.post("/api/challenges/debug-1/submit",json={"answer":"I would reproduce the issue, isolate malformed records, add edge case tests and verify the failure path."})
    assert r.status_code==200; assert r.json()["evidence_added"] is True

def test_ai_providers_and_subjects():
    providers=client.get('/api/ai/providers'); assert providers.status_code==200
    assert [p['id'] for p in providers.json()['providers']]==['puter','ollama']
    subjects=client.get('/api/subjects?language=English'); assert subjects.status_code==200
    assert len(subjects.json()['items'])>=10

def test_ai_chat_demo_provider_contract():
    r=client.post('/api/ai/ask',json={'question':'make me a roadmap for SQL','provider':'puter','language':'English','role':'ML Engineer','goal':'Become job-ready'})
    assert r.status_code==200
    assert r.json().get('answer') or r.json().get('mode')=='puter-client'

def test_github_url_parser():
    from app.github_intelligence import parse_repo_url
    assert parse_repo_url('https://github.com/owner/repo') == ('owner','repo')
    assert parse_repo_url('owner/repo.git') == ('owner','repo')

def test_evidence_claim_and_target_evidence():
    r=client.get('/api/evidence'); assert r.status_code==200
    body=r.json(); assert 'target_evidence' in body and body['target_evidence']
    created=client.post('/api/evidence/claims',json={
        'claim':'I can design reliable APIs',
        'competency':'APIs',
        'target_role':'Backend Developer',
        'evidence_title':'API test suite',
        'evidence_description':'A repeatable suite covers success and failure paths.',
        'evidence_type':'Project artifact'
    })
    assert created.status_code==200 and created.json()['saved'] is True

def test_public_contact():
    r=client.post('/api/contact',json={'name':'Test','email':'test@example.com','subject':'Hello','message':'This is a valid contact smoke test.'})
    assert r.status_code==200 and r.json()['received'] is True
