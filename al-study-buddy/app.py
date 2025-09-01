import os
from datetime import datetime
from typing import List, Dict
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, ForeignKey, DateTime
import requests
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///study_buddy.db")  # Fallback for local quickstart
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")
HF_QG_MODEL = os.getenv("HF_QG_MODEL", "iarfmoose/t5-base-question-generator")

app = Flask(__name__)
CORS(app)

# ---------------- SQLAlchemy setup ----------------
class Base(DeclarativeBase):
    pass

class FlashcardSet(Base):
    __tablename__ = "flashcard_sets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    source_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    cards: Mapped[List["Flashcard"]] = relationship("Flashcard", cascade="all, delete-orphan", back_populates="set")

class Flashcard(Base):
    __tablename__ = "flashcards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    set_id: Mapped[int] = mapped_column(ForeignKey("flashcard_sets.id"))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    set: Mapped["FlashcardSet"] = relationship("FlashcardSet", back_populates="cards")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

# ---------------- Utilities ----------------
def naive_question_generator(text: str, k: int = 5) -> List[Dict[str, str]]:
    """
    Fallback generator if HF is not configured or fails.
    Creates simple 'definition' style questions from sentences.
    """
    # slice into sentences by ., ?, !
    import re
    sentences = [s.strip() for s in re.split(r'[.?!]\s+', text) if len(s.split()) > 3]
    selected = sentences[:k] if len(sentences) >= k else sentences
    cards = []
    for i, s in enumerate(selected, 1):
        # pick a keyword-ish phrase (first 6 words) for a naive question
        words = s.split()
        topic = " ".join(words[:6])
        q = f"What is the main idea behind: \"{topic}...\"?"
        a = s
        cards.append({"question": q, "answer": a})
    # pad if fewer than k
    while len(cards) < k and sentences:
        cards.append({"question": f"Summarize: \"{sentences[0][:40]}...\"",
                      "answer": sentences[0]})
    return cards

def call_hf_qg(text: str, k: int = 5, model: str | None = None) -> List[Dict[str, str]]:
    """
    Calls Hugging Face Inference API to generate questions.
    Attempts to parse Q/A pairs if provided by the model; otherwise returns questions only.
    """
    if not HF_API_TOKEN:
        return naive_question_generator(text, k)
    model_name = model or HF_QG_MODEL
    url = f"https://api-inference.huggingface.co/models/{model_name}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    prompt = f"Generate {k} quiz flashcard questions and answers based on the following study notes.\n" \
             f"Return them as numbered lines in the format 'Q: ... A: ...'.\n\nNotes:\n{text}\n"
    try:
        resp = requests.post(url, headers=headers, json={
            "inputs": prompt,
            "parameters": {"max_new_tokens": 512, "return_full_text": False, "do_sample": False}
        }, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        # Inference API may return list of dicts with 'generated_text' or direct strings
        if isinstance(data, list) and data:
            generated = data[0].get("generated_text", "") if isinstance(data[0], dict) else str(data[0])
        elif isinstance(data, dict) and "generated_text" in data:
            generated = data["generated_text"]
        else:
            generated = str(data)
        # Parse lines like: "1. Q: ... A: ..." or "Q: ... A: ..."
        import re
        lines = [l.strip("-• ").strip() for l in generated.splitlines() if l.strip()]
        qa_pairs = []
        for line in lines:
            m = re.search(r"Q\s*:\s*(.+?)\s*A\s*:\s*(.+)", line, flags=re.IGNORECASE)
            if m:
                qa_pairs.append({"question": m.group(1).strip(), "answer": m.group(2).strip()})
        if not qa_pairs:
            # try to extract just questions
            for line in lines:
                if line.lower().startswith("q:"):
                    qa_pairs.append({"question": line.split(":",1)[1].strip(), "answer": ""})
        if not qa_pairs:
            return naive_question_generator(text, k)
        return qa_pairs[:k]
    except Exception:
        return naive_question_generator(text, k)

# ---------------- Routes ----------------
@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/generate")
def api_generate():
    payload = request.get_json(force=True)
    notes = (payload.get("notes") or "").strip()
    k = int(payload.get("num_questions", 5))
    model = payload.get("model")
    if not notes:
        return jsonify({"error": "notes required"}), 400
    cards = call_hf_qg(notes, k=k, model=model)
    return jsonify({"cards": cards})

@app.post("/api/save")
def api_save():
    payload = request.get_json(force=True)
    title = (payload.get("title") or "My Flashcards").strip()
    source_text = payload.get("source_text") or ""
    cards = payload.get("cards") or []
    if not isinstance(cards, list) or not cards:
        return jsonify({"error": "cards array required"}), 400
    with SessionLocal() as db:
        s = FlashcardSet(title=title, source_text=source_text)
        db.add(s)
        db.flush()
        for c in cards:
            q = (c.get("question") or "").strip()
            a = (c.get("answer") or "").strip()
            if q:
                db.add(Flashcard(set_id=s.id, question=q, answer=a))
        db.commit()
        return jsonify({"ok": True, "set_id": s.id})

@app.get("/api/sets")
def api_sets():
    with SessionLocal() as db:
        rows = db.query(FlashcardSet).order_by(FlashcardSet.created_at.desc()).limit(20).all()
        return jsonify({"sets": [{
            "id": r.id, "title": r.title, "created_at": r.created_at.isoformat()
        } for r in rows]})

@app.get("/api/sets/<int:set_id>")
def api_set_detail(set_id: int):
    with SessionLocal() as db:
        s = db.query(FlashcardSet).filter(FlashcardSet.id == set_id).first()
        if not s:
            return jsonify({"error": "not found"}), 404
        return jsonify({
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "cards": [{"id": c.id, "question": c.question, "answer": c.answer} for c in s.cards]
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
