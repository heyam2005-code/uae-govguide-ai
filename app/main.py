from __future__ import annotations
from pathlib import Path
from typing import Literal
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from app.core import GovAgent
from app.dialogue import DialogueAgent
from app.cloud import capabilities
import json, os

ROOT=Path(__file__).resolve().parents[1]
app=FastAPI(title='UAE GovGuide AI',version='0.5.0',description='Source-grounded government-service navigation MVP. Not an official government service.')
agent=GovAgent()
dialogue=DialogueAgent(gov=agent)

class Profile(BaseModel):
    category:Literal['unknown','citizen','resident','gcc']='unknown'
    emirate:str|None=None
    age:int|None=Field(None,ge=0,le=120)
    expiry_months:float|None=Field(None,ge=-120,le=200)
    passport_valid_months:float|None=Field(None,ge=-120,le=200)
    has_photo:bool|None=None
    urgent:bool=False

class ChatRequest(BaseModel):
    message:str=Field('',max_length=1000)
    session_id:str|None=Field(None,max_length=100)
    service_id:Literal['renew','replace','new']|None=None
    profile:Profile=Field(default_factory=Profile)
    advance:bool=False

class ScenarioRequest(BaseModel):
    step:int=Field(ge=1,le=3)
    session_id:str|None=None

@app.get('/')
def home():return FileResponse(ROOT/'static'/'index.html')

@app.get('/locator')
def locator_home():
    return FileResponse(ROOT/'static'/'locator.html')

@app.get('/assistant')
def assistant_home():
    return FileResponse(ROOT/'static'/'assistant.html')

class AssistantRequest(BaseModel):
    message:str=Field('',max_length=1000)
    session_id:str|None=Field(None,max_length=100)
    advance:bool=False

class AssistantReset(BaseModel):
    session_id:str|None=Field(None,max_length=100)

@app.post('/api/assistant')
def assistant_chat(req:AssistantRequest):
    return dialogue.respond(req.message,req.session_id,req.advance)

@app.post('/api/assistant/reset')
def assistant_reset(req:AssistantReset):
    return dialogue.reset(req.session_id)

@app.get('/health')
def health():return {'status':'ok','kb_chunks':len(agent.kb.chunks),'services':len(agent.services),'llm_available':capabilities()['configured']}

@app.post('/api/chat')
def chat(req:ChatRequest):return agent.answer(req.message,req.session_id,req.service_id,req.profile.model_dump(),req.advance)

@app.post('/api/scenario')
def scenario(req:ScenarioRequest):return agent.scenario(req.step,req.session_id)

@app.get('/api/services')
def services():return [{'id':s['id'],'name_ar':s['name_ar'],'name_en':s['name_en'],'source':agent.sources[s['source_id']]['url']} for s in agent.services.values()]

@app.get('/api/policy-gaps')
def gaps():return json.loads((ROOT/'docs'/'policy_gap_hypotheses.json').read_text(encoding='utf-8'))

@app.get('/api/llm-status')
def llm_status():
    return capabilities()

@app.get('/api/centres/recommend')
def recommend_centres(emirate:str,service_id:Literal['renew','replace','new'],category:Literal['citizen','resident','gcc'],urgent:bool=False,area:str|None=None):
    return agent.locator.recommend(emirate,service_id,category,urgent=urgent,area=area)

@app.get('/api/services/catalog')
def service_catalog():
    import csv
    with (ROOT/'data'/'services_catalog.csv').open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))
