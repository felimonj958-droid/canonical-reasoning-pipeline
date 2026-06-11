import os
import pandas as pd
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Depends, Request, Header 

from pydantic import BaseModel

class LSATQuestion(BaseModel):
    question:str

from fastapi.middleware.cors import CORSMiddleware

from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from security import (
    limiter,
    LimitUploadSize,
    get_current_role,
)

API_KEY = os.getenv("LOCAL_API_KEY", "")

app = FastAPI(title="LSAT/MCAT Analytics Backend")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Limit upload size for all requests (DoS protection)
app.add_middleware(LimitUploadSize)


# Enable CORS for Base44 integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Path Configuration ---
DATA_PATHS = {
    "lsat": {
        "questions": "data/lsat/lr_questions.csv",
        "attempts": "data/lsat/lr_attempts.csv"
    },
    "mcat": {
        "questions": "data/mcat/mcat_questions.csv",
        "attempts": "data/mcat/mcat_attempts.csv"
    }
}

# --- Request Models ---
class AttemptRequest(BaseModel):
    exam: str  # "lsat" | "mcat"
    question_id: str
    selected_answer: str
    time_taken: int
    confidence: int

class ExplainRequest(BaseModel):
    exam: str
    question_id: str
    user_answer: str

# --- Helper Functions ---
def load_data(exam: str, data_type: str):
    path = DATA_PATHS.get(exam, {}).get(data_type)
    if not path or not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)

# --- Endpoints ---

@app.get("/health")
def health():
    return {"status": "online", "local_only": True}


@app.get("/api/analytics/summary")
def get_summary(exam: str = Query(..., regex="^(lsat|mcat)$")):
    q_df = load_data(exam, "questions")
    a_df = load_data(exam, "attempts")

    if a_df.empty:
        return {"total_questions": len(q_df), "accuracy": 0, "avg_time": 0, "streak": 0, "total_attempts": 0}

    # Calculate Accuracy
    merged = a_df.merge(q_df[['question_id', 'correct_option']], on='question_id')
    is_correct = merged['selected_answer'] == merged['correct_option']
    accuracy = is_correct.mean()

    # Calculate Streak (using last N attempts)
    streak = 0
    for val in reversed(is_correct.tolist()):
        if val: streak += 1
        else: break

    summary = {
        "total_questions": len(q_df),
        "total_attempts": len(a_df),
        "accuracy": round(accuracy, 2),
        "avg_time": round(a_df['time_taken'].mean(), 1),
        "current_streak": streak,
    }

    # LSAT specific: Siren Call Score (Mocked as % of high-confidence errors)
    if exam == "lsat":
        siren_mask = (~is_correct) & (a_df['confidence'] >= 4)
        summary["siren_call_score"] = int(siren_mask.sum())
    
    return summary

@app.get("/api/analytics/breakdown")
def get_breakdown(
    exam: str = Query(...),
    by: str = Query(...),
    role: str = Depends(get_current_role),
):
    """
    'by' values for LSAT: 'category' (Logic Heatmap)
    'by' values for MCAT: 'content_domain' or 'aamc_skill'
    """
    q_df = load_data(exam, "questions")
    a_df = load_data(exam, "attempts")
    
    if a_df.empty:
        return []

    merged = a_df.merge(q_df, on="question_id")
    merged["is_correct"] = (
        merged["selected_answer"] == merged["correct_option"]
    ).astype(int)
    
    if by not in merged.columns:
        raise HTTPException(status_code=400, detail=f"Column '{by}' not found in data.")

    grouped = merged.groupby(by).agg(
        accuracy=("is_correct", "mean"),
        attempts=("is_correct", "count"),
    ).reset_index()

    return [
        {
            "label": row[by],
            "value": round(row["accuracy"] * 100, 1),
            "attempts": int(row["attempts"]),
        }
        for _, row in grouped.iterrows()
    ]


@app.get("/api/question/next")
def get_next(
    exam: str,
    section_id: Optional[str] = None,
    role: str = Depends(get_current_role),
):
    q_df = load_data(exam, "questions")
    if q_df.empty:
        raise HTTPException(status_code=404, detail="No questions found.")
    
    # Simple random selection for demo; can be replaced with spaced-repetition logic
    row = q_df.sample(1).iloc[0]
    
    return {
        "question_id": str(row["question_id"]),
        "text": row["question_text"],
        "options": {
            "A": row["option_a"],
            "B": row["option_b"],
            "C": row["option_c"],
            "D": row["option_d"],
            "E": row.get("option_e", None),  # MCAT usually has 4, LSAT has 5
        },
        "metadata": {
            "difficulty": row.get("difficulty", "Medium"),
            "type": row.get("category" if exam == "lsat" else "content_domain", "General"),
        },
    }


@app.post("/api/attempt")
def post_attempt(req: AttemptRequest, role: str = Depends(get_current_role)):
    # Load and Append to CSV
    path = DATA_PATHS[req.exam]["attempts"]
    new_data = pd.DataFrame([req.dict()])
    
    # Append logic (creates file if it doesn't exist)
    new_data.to_csv(path, mode='a', header=not os.path.exists(path), index=False)

    # Fetch correct answer for feedback
    q_df = load_data(req.exam, "questions")
    correct_ans = q_df[q_df['question_id'] == req.question_id]['correct_option'].values[0]
    
    return {
        "correct": req.selected_answer == correct_ans,
        "correct_answer": correct_ans,
        "explanation_snippet": f"The correct answer is {correct_ans}.",
        "new_accuracy": 0.0  # Placeholder for client refresh
    }

@app.post("/api/explain")
async def post_explain(
    req: ExplainRequest,
    request: Request,
    role: str = Depends(get_current_role),
):
    # Rate limit only non-admin roles
    if role != "admin":
        limit_decorator = limiter.limit("10/minute")

        @limit_decorator
        async def _inner(request: Request):
            return

        await _inner(request)

    # Here is where you'd typically call a LLM. 
    # For now, we return a structured response for the Base44 UI.
    return {
        "explanation": (
            f"### Deep Dive\nQuestion {req.question_id} involves complex reasoning. "
            f"You selected {req.user_answer}..."
        ),
        "tags": ["Analysis", "Critical Reasoning"],
    }

@app.post("/lsat")
async def lsat_endpoint(payload: LSATQuestion, x_api_key: str = Header(default="")):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    question_text = payload.question

    # TODO: call your LM Studio / analysis logic here.
    # For now, return a stub so we can test the wiring.
    return {
        "answer": f"Stub LSAT answer for: {question_text[:120]}..."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)