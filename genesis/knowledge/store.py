"""SQLite knowledge ledger.

A claim is a proposition, not a fact. Evidence records preserve source and
independence groups. Automatic evaluation reports corroboration or conflict;
it never upgrades a claim to objective truth.
"""
import sqlite3
from pathlib import Path
from uuid import uuid4


class KnowledgeError(ValueError):
    """Raised when a knowledge record is invalid."""


class KnowledgeStore:
    STATUSES = {"proposed", "corroborated", "contested", "refuted"}
    STANCES = {"supports", "refutes"}
    REVIEW_OUTCOMES = {"accept", "reject", "inconclusive"}

    def __init__(self, database: str | Path):
        self.database = str(database)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS claims (
                    claim_id TEXT PRIMARY KEY, world_id TEXT NOT NULL,
                    creator_agent_id TEXT NOT NULL, proposition TEXT NOT NULL,
                    claim_type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'proposed',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_claims_world_status ON claims(world_id, status);
                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY,
                    claim_id TEXT NOT NULL REFERENCES claims(claim_id),
                    contributor_agent_id TEXT NOT NULL, source_type TEXT NOT NULL,
                    source_ref TEXT NOT NULL, independence_key TEXT NOT NULL,
                    stance TEXT NOT NULL, confidence REAL NOT NULL, summary TEXT NOT NULL,
                    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_evidence_claim ON evidence(claim_id);
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id TEXT PRIMARY KEY,
                    claim_id TEXT NOT NULL REFERENCES claims(claim_id),
                    reviewer_id TEXT NOT NULL, outcome TEXT NOT NULL,
                    method TEXT NOT NULL, rationale TEXT NOT NULL,
                    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_reviews_claim ON reviews(claim_id);
            """)

    def _connect(self):
        db = sqlite3.connect(self.database)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def create_claim(self, world_id: str, creator_agent_id: str,
                     proposition: str, claim_type: str = "observation") -> str:
        values = (world_id, creator_agent_id, proposition, claim_type)
        if any(not isinstance(v, str) or not v.strip() for v in values):
            raise KnowledgeError("world, creator, proposition, and claim_type are required")
        claim_id = str(uuid4())
        with self._connect() as db:
            db.execute("""INSERT INTO claims
                (claim_id, world_id, creator_agent_id, proposition, claim_type)
                VALUES (?, ?, ?, ?, ?)""",
                (claim_id, world_id.strip(), creator_agent_id.strip(), proposition.strip(), claim_type.strip()))
        return claim_id

    def add_evidence(self, claim_id: str, contributor_agent_id: str,
                     source_type: str, source_ref: str, independence_key: str,
                     stance: str, confidence: float, summary: str) -> str:
        required = (claim_id, contributor_agent_id, source_type, source_ref, independence_key, stance, summary)
        if any(not isinstance(v, str) or not v.strip() for v in required):
            raise KnowledgeError("All evidence fields are required")
        if stance not in self.STANCES:
            raise KnowledgeError(f"stance must be one of {sorted(self.STANCES)}")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise KnowledgeError("confidence must be a number between 0 and 1")
        evidence_id = str(uuid4())
        with self._connect() as db:
            if db.execute("SELECT 1 FROM claims WHERE claim_id = ?", (claim_id,)).fetchone() is None:
                raise KeyError(claim_id)
            db.execute("""INSERT INTO evidence
                (evidence_id, claim_id, contributor_agent_id, source_type, source_ref,
                 independence_key, stance, confidence, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (evidence_id, claim_id, contributor_agent_id.strip(), source_type.strip(),
                 source_ref.strip(), independence_key.strip(), stance, float(confidence), summary.strip()))
            self._evaluate_in_transaction(db, claim_id)
        return evidence_id

    def _evaluate_in_transaction(self, db, claim_id: str) -> str:
        rows = db.execute("SELECT stance, independence_key FROM evidence WHERE claim_id = ?", (claim_id,)).fetchall()
        support = {r["independence_key"] for r in rows if r["stance"] == "supports"}
        refute = {r["independence_key"] for r in rows if r["stance"] == "refutes"}
        if support and refute:
            status = "contested"
        elif len(support) >= 2:
            status = "corroborated"
        elif len(refute) >= 2:
            status = "refuted"
        else:
            status = "proposed"
        db.execute("UPDATE claims SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE claim_id = ?",
                   (status, claim_id))
        return status

    def evaluate_claim(self, claim_id: str) -> dict:
        with self._connect() as db:
            if db.execute("SELECT 1 FROM claims WHERE claim_id = ?", (claim_id,)).fetchone() is None:
                raise KeyError(claim_id)
            status = self._evaluate_in_transaction(db, claim_id)
            claim = db.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()
            rows = db.execute("""SELECT stance, COUNT(DISTINCT independence_key) AS n
                FROM evidence WHERE claim_id = ? GROUP BY stance""", (claim_id,)).fetchall()
            counts = {r["stance"]: r["n"] for r in rows}
        return {**dict(claim), "status": status,
                "independent_supporting_sources": counts.get("supports", 0),
                "independent_refuting_sources": counts.get("refutes", 0),
                "interpretation": self._interpret(status)}

    @staticmethod
    def _interpret(status: str) -> str:
        return {
            "proposed": "Insufficient independent evidence for corroboration or refutation.",
            "corroborated": "At least two independent source groups support this claim; this is not proof of truth.",
            "contested": "Evidence exists on both sides; further investigation is required.",
            "refuted": "At least two independent source groups refute this claim; review evidence and context.",
        }[status]

    def add_review(self, claim_id: str, reviewer_id: str, outcome: str,
                   method: str, rationale: str) -> str:
        if outcome not in self.REVIEW_OUTCOMES:
            raise KnowledgeError(f"outcome must be one of {sorted(self.REVIEW_OUTCOMES)}")
        if any(not isinstance(v, str) or not v.strip() for v in (claim_id, reviewer_id, method, rationale)):
            raise KnowledgeError("claim, reviewer, method, and rationale are required")
        review_id = str(uuid4())
        with self._connect() as db:
            if db.execute("SELECT 1 FROM claims WHERE claim_id = ?", (claim_id,)).fetchone() is None:
                raise KeyError(claim_id)
            db.execute("""INSERT INTO reviews
                (review_id, claim_id, reviewer_id, outcome, method, rationale)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (review_id, claim_id, reviewer_id.strip(), outcome, method.strip(), rationale.strip()))
        return review_id

    def get_claim(self, claim_id: str) -> dict:
        with self._connect() as db:
            claim = db.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()
            if claim is None:
                raise KeyError(claim_id)
            evidence = db.execute("SELECT * FROM evidence WHERE claim_id = ? ORDER BY recorded_at, evidence_id", (claim_id,)).fetchall()
            reviews = db.execute("SELECT * FROM reviews WHERE claim_id = ? ORDER BY recorded_at, review_id", (claim_id,)).fetchall()
        return {"claim": dict(claim), "evidence": [dict(r) for r in evidence],
                "reviews": [dict(r) for r in reviews]}

    def list_claims(self, world_id: str, status: str | None = None, limit: int = 100) -> list[dict]:
        if not isinstance(world_id, str) or not world_id.strip():
            raise KnowledgeError("world_id is required")
        if limit < 1:
            raise KnowledgeError("limit must be positive")
        if status is not None and status not in self.STATUSES:
            raise KnowledgeError(f"status must be one of {sorted(self.STATUSES)}")
        with self._connect() as db:
            if status is None:
                rows = db.execute("SELECT * FROM claims WHERE world_id = ? ORDER BY created_at, claim_id LIMIT ?", (world_id, limit)).fetchall()
            else:
                rows = db.execute("SELECT * FROM claims WHERE world_id = ? AND status = ? ORDER BY created_at, claim_id LIMIT ?", (world_id, status, limit)).fetchall()
        return [dict(r) for r in rows]
