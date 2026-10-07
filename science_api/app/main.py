import json
import os
import random
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
with (BASE_DIR / "science_questions.json").open(encoding="utf-8") as f:
    DATA: dict[str, Any] = json.load(f)

SUBJECTS = DATA.get("subjects", [])
SUBJECT_MAP = {s["subjectId"]: s for s in SUBJECTS}

app = FastAPI(
    title="理科基礎問題 API",
    version="2.0.0",
    description="物理基礎・化学基礎・生物基礎・地学基礎の問題を提供する公開用API",
)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
origins = ["*"] if allowed_origins == "*" else [x.strip() for x in allowed_origins.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False if origins == ["*"] else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RATE_LIMIT = int(os.getenv("RATE_LIMIT", "120"))
RATE_WINDOW = int(os.getenv("RATE_WINDOW", "60"))
requests_by_ip: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(request: Request) -> None:
    now = time.time()
    ip = request.client.host if request.client else "unknown"
    q = requests_by_ip[ip]
    while q and q[0] <= now - RATE_WINDOW:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many requests")
    q.append(now)


def get_subject(subject_id: str) -> dict[str, Any]:
    subject = SUBJECT_MAP.get(subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


def get_question(subject_id: str, question_id: int) -> dict[str, Any]:
    subject = get_subject(subject_id)
    for q in subject.get("questions", []):
        if q.get("id") == question_id:
            return q
    raise HTTPException(status_code=404, detail="Question not found")


def public_question(q: dict[str, Any]) -> dict[str, Any]:
    # 正解・解説は回答APIまで公開しない
    return {
        "id": q["id"],
        "category": q.get("category"),
        "unit": q.get("unit"),
        "difficulty": q.get("difficulty"),
        "question": q["question"],
        "choices": q["choices"],
    }


class AnswerRequest(BaseModel):
    choiceIndex: int = Field(ge=0)


@app.get("/")
def root():
    return {"name": DATA.get("title", "理科基礎問題集"), "version": "2.0.0", "docs": "/docs"}


@app.get("/api/subjects")
def api_subjects(request: Request):
    check_rate_limit(request)
    return [
        {"subjectId": s["subjectId"], "subject": s["subject"], "questionCount": len(s.get("questions", []))}
        for s in SUBJECTS
    ]


@app.get("/api/subjects/{subject_id}")
def api_subject(subject_id: str, request: Request):
    check_rate_limit(request)
    s = get_subject(subject_id)
    return {"subjectId": s["subjectId"], "subject": s["subject"], "questionCount": len(s.get("questions", []))}


@app.get("/api/subjects/{subject_id}/categories")
def api_categories(subject_id: str, request: Request):
    check_rate_limit(request)
    s = get_subject(subject_id)
    counts: dict[str, int] = {}
    for q in s.get("questions", []):
        key = q.get("category")
        counts[key] = counts.get(key, 0) + 1
    return [{"category": k, "questionCount": v} for k, v in counts.items()]


@app.get("/api/subjects/{subject_id}/units")
def api_units(subject_id: str, request: Request, category: str | None = Query(None)):
    check_rate_limit(request)
    s = get_subject(subject_id)
    counts: dict[str, int] = {}
    for q in s.get("questions", []):
        if category and q.get("category") != category:
            continue
        key = q.get("unit")
        counts[key] = counts.get(key, 0) + 1
    return [{"unit": k, "questionCount": v} for k, v in counts.items()]


@app.get("/api/subjects/{subject_id}/questions")
def api_questions(
    subject_id: str,
    request: Request,
    category: str | None = Query(None),
    unit: str | None = Query(None),
    difficulty: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
):
    check_rate_limit(request)
    s = get_subject(subject_id)
    result = []
    for q in s.get("questions", []):
        if category and q.get("category") != category:
            continue
        if unit and q.get("unit") != unit:
            continue
        if difficulty and q.get("difficulty") != difficulty:
            continue
        result.append(public_question(q))
    return {"subjectId": subject_id, "subject": s["subject"], "count": len(result), "questions": result[:limit]}


@app.get("/api/subjects/{subject_id}/questions/{question_id}")
def api_question(subject_id: str, question_id: int, request: Request):
    check_rate_limit(request)
    return public_question(get_question(subject_id, question_id))


@app.get("/api/subjects/{subject_id}/random")
def api_random(
    subject_id: str,
    request: Request,
    category: str | None = Query(None),
    unit: str | None = Query(None),
    difficulty: str | None = Query(None),
):
    check_rate_limit(request)
    s = get_subject(subject_id)
    candidates = [
        q for q in s.get("questions", [])
        if (not category or q.get("category") == category)
        and (not unit or q.get("unit") == unit)
        and (not difficulty or q.get("difficulty") == difficulty)
    ]
    if not candidates:
        raise HTTPException(status_code=404, detail="No matching questions")
    return public_question(random.choice(candidates))


@app.post("/api/subjects/{subject_id}/questions/{question_id}/answer")
def api_answer(subject_id: str, question_id: int, payload: AnswerRequest, request: Request):
    check_rate_limit(request)
    q = get_question(subject_id, question_id)
    if payload.choiceIndex >= len(q.get("choices", [])):
        raise HTTPException(status_code=400, detail="Invalid choiceIndex")
    return {
        "subjectId": subject_id,
        "questionId": question_id,
        "correct": payload.choiceIndex == q["correctChoiceIndex"],
        "correctChoiceIndex": q["correctChoiceIndex"],
        "answer": q.get("answer"),
        "explanation": q.get("explanation"),
        "formula": q.get("formula"),
    }
