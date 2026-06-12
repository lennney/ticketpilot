"""FastAPI backend for TicketPilot AI Customer Service Copilot.

Provides REST API endpoints for:
- Chat-based customer service interaction
- Ticket processing pipeline
- Review decision management
- Evaluation metrics
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.schema.ticket import RawTicket, TicketOutput
from ticketpilot.drafting.generate import generate_draft
from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.api.streaming import register_streaming_routes
from ticketpilot.multi_agent import generate_draft_with_orchestrator

# Initialize FastAPI app
app = FastAPI(
    title="TicketPilot API",
    description="AI Customer Service Copilot API",
    version="1.0.0",
    openapi_tags=[
        {"name": "chat", "description": "AI copilot chat interaction"},
        {"name": "tickets", "description": "Ticket processing pipeline"},
        {"name": "reviews", "description": "Human review decisions"},
        {"name": "evaluation", "description": "Evaluation metrics"},
        {"name": "health", "description": "Service health checks"},
    ],
)

# CORS origins from environment variable (Issue #17)
_cors_origins_raw = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
)
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register streaming routes
register_streaming_routes(app)


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """Chat message from user."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Chat request with message history."""
    messages: List[ChatMessage]
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response with AI-generated reply."""
    message: ChatMessage
    evidence: List[dict] = []
    risk_flags: List[str] = []
    risk_severity: str = "LOW"
    intent: str = "other"
    confidence: float = 0.0
    session_id: str = ""


class TicketRequest(BaseModel):
    """Ticket processing request."""
    text: str
    order_number: Optional[str] = None
    customer_id: Optional[str] = None


class TicketResponse(BaseModel):
    """Ticket processing response."""
    ticket_id: str
    intent: str
    confidence: float
    risk_flags: List[str]
    risk_severity: str
    evidence: List[dict]
    draft_reply: Optional[str] = None
    processing_time_ms: float = 0.0


class ReviewDecision(BaseModel):
    """Review decision for a ticket."""
    ticket_id: str
    decision: str  # "approve", "edit", "escalate", "reject"
    edited_reply: Optional[str] = None
    reason: Optional[str] = None
    reviewer_id: str = "human_reviewer"


class EvaluationResult(BaseModel):
    """Evaluation metrics result."""
    total_tickets: int
    intent_accuracy: float
    severity_accuracy: float
    risk_flag_f1: float
    evidence_recall: float
    faithfulness: float
    answer_relevancy: float
    overall_pass_rate: float


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "TicketPilot API",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message and return AI response.
    
    This endpoint handles multi-turn conversation with the AI copilot.
    It processes the user's message through the pipeline and generates
    an evidence-grounded response.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")
    
    # Get the latest user message
    user_message = request.messages[-1]
    if user_message.role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from user")
    
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())
    
    # Process through pipeline
    start_time = datetime.now(timezone.utc)
    
    raw_ticket = RawTicket(
        original_text=user_message.content,
        submitted_at=datetime.now(timezone.utc),
    )
    
    try:
        ticket_output = intake_risk_pipeline(raw_ticket)
        
        # Generate draft using multi-agent orchestrator
        draft_result = generate_draft_with_orchestrator(
            normalized_text=ticket_output.normalized_ticket.text,
            issue_type=ticket_output.classification.intent.value,
            risk_flags=[f.value for f in ticket_output.risk_assessment.flags],
            severity=ticket_output.risk_assessment.severity.value,
            must_human_review=ticket_output.risk_assessment.must_human_review,
            evidence_candidates=ticket_output.evidence_candidates,
        )
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        # Extract evidence for response
        evidence_list = []
        if ticket_output.evidence_candidates:
            for candidate in ticket_output.evidence_candidates[:5]:  # Top 5 evidence
                evidence_list.append({
                    "chunk_id": str(candidate.chunk_id),
                    "doc_type": candidate.doc_type.value if hasattr(candidate.doc_type, 'value') else str(candidate.doc_type),
                    "title": candidate.title or "",
                    "content": candidate.content[:200] if candidate.content else "",  # Truncate for API
                    "score": candidate.score,
                })
        
        # Extract risk flags
        risk_flags = [flag.value for flag in ticket_output.risk_assessment.flags]
        
        # Build response
        assistant_message = ChatMessage(
            role="assistant",
            content=draft_result.draft_text if hasattr(draft_result, 'draft_text') else "感谢您的咨询，我正在为您处理...",
            timestamp=datetime.now(timezone.utc),
        )
        
        return ChatResponse(
            message=assistant_message,
            evidence=evidence_list,
            risk_flags=risk_flags,
            risk_severity=ticket_output.risk_assessment.severity.value,
            intent=ticket_output.classification.intent.value,
            confidence=ticket_output.classification.confidence,
            session_id=session_id,
        )
        
    except Exception as e:
        # Fallback response on error
        assistant_message = ChatMessage(
            role="assistant",
            content="抱歉，处理您的请求时出现了问题。请稍后重试或联系人工客服。",
            timestamp=datetime.now(timezone.utc),
        )
        
        return ChatResponse(
            message=assistant_message,
            evidence=[],
            risk_flags=["low_confidence"],
            risk_severity="LOW",
            intent="other",
            confidence=0.0,
            session_id=session_id,
        )


@app.post("/api/tickets", response_model=TicketResponse)
async def process_ticket(request: TicketRequest):
    """Process a customer service ticket through the full pipeline.
    
    This endpoint runs the complete ticket processing pipeline:
    1. Intake - normalize and extract entities
    2. Classification - determine intent
    3. Risk assessment - evaluate risk flags
    4. Evidence retrieval - search knowledge base
    5. Draft generation - create response draft
    """
    start_time = datetime.now(timezone.utc)
    ticket_id = str(uuid.uuid4())
    
    raw_ticket = RawTicket(
        original_text=request.text,
        submitted_at=datetime.now(timezone.utc),
    )
    
    try:
        # Run pipeline
        ticket_output = intake_risk_pipeline(raw_ticket)
        
        # Generate draft
        draft_result = generate_draft(ticket_output)
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        # Extract evidence
        evidence_list = []
        if ticket_output.evidence_candidates:
            for candidate in ticket_output.evidence_candidates[:10]:
                evidence_list.append({
                    "chunk_id": str(candidate.chunk_id),
                    "doc_type": candidate.doc_type.value if hasattr(candidate.doc_type, 'value') else str(candidate.doc_type),
                    "title": candidate.title or "",
                    "content": candidate.content[:200] if candidate.content else "",
                    "score": candidate.score,
                })
        
        return TicketResponse(
            ticket_id=ticket_id,
            intent=ticket_output.classification.intent.value,
            confidence=ticket_output.classification.confidence,
            risk_flags=[flag.value for flag in ticket_output.risk_assessment.flags],
            risk_severity=ticket_output.risk_assessment.severity.value,
            evidence=evidence_list,
            draft_reply=draft_result.draft_text if hasattr(draft_result, 'draft_text') else None,
            processing_time_ms=processing_time,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.post("/api/reviews")
async def submit_review(decision: ReviewDecision):
    """Submit a review decision for a ticket.
    
    This endpoint records human review decisions for audit trail.
    In a real system, this would persist to a database.
    """
    # In demo mode, just acknowledge the decision
    return {
        "status": "accepted",
        "ticket_id": decision.ticket_id,
        "decision": decision.decision,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": f"Review decision '{decision.decision}' recorded for ticket {decision.ticket_id}",
    }


@app.get("/api/evaluation", response_model=EvaluationResult)
async def get_evaluation_metrics():
    """Get current evaluation metrics.
    
    Returns the latest evaluation results from the evaluation pipeline.
    """
    # In demo mode, return sample metrics
    # In production, this would read from evaluation reports
    return EvaluationResult(
        total_tickets=101,
        intent_accuracy=0.53,
        severity_accuracy=0.54,
        risk_flag_f1=0.72,
        evidence_recall=0.919,
        faithfulness=0.989,
        answer_relevancy=0.944,
        overall_pass_rate=0.933,
    )


@app.get("/api/health")
async def health_check():
    """Detailed health check with component status."""
    return {
        "status": "healthy",
        "components": {
            "api": "operational",
            "pipeline": "operational",
            "database": "not_connected",  # Would check PostgreSQL in production
            "embedding": "local_bge_small_zh",
            "llm": "deepseek_chat",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Run with: uvicorn ticketpilot.api.app:app --reload --port 8000
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)