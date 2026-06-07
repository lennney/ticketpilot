"""Streaming chat endpoint using Server-Sent Events (SSE)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.schema.ticket import RawTicket
from ticketpilot.drafting.draft_agent import DraftAgent


class StreamingChatRequest(BaseModel):
    """Streaming chat request."""
    message: str
    session_id: str | None = None


async def stream_chat_response(
    message: str,
    session_id: str,
) -> AsyncGenerator[str, None]:
    """
    Generate streaming chat response using SSE.
    
    Yields events:
    - type: "status" - Processing status updates
    - type: "evidence" - Retrieved evidence
    - type: "draft" - Draft reply chunks
    - type: "done" - Final response with metadata
    """
    # Send initial status
    yield f"data: {json.dumps({'type': 'status', 'content': 'processing', 'message': '正在分析您的问题...'})}\n\n"
    
    # Process through pipeline
    raw_ticket = RawTicket(
        original_text=message,
        submitted_at=datetime.now(timezone.utc),
    )
    
    try:
        # Run intake and risk assessment
        yield f"data: {json.dumps({'type': 'status', 'content': 'classifying', 'message': '正在识别问题类型...'})}\n\n"
        
        ticket_output = intake_risk_pipeline(raw_ticket)
        
        # Send classification result
        yield f"data: {json.dumps({'type': 'classification', 'content': {'intent': ticket_output.classification.intent.value, 'confidence': ticket_output.classification.confidence}})}\n\n"
        
        # Send risk assessment
        risk_flags = [flag.value for flag in ticket_output.risk_assessment.flags]
        yield f"data: {json.dumps({'type': 'risk', 'content': {'flags': risk_flags, 'severity': ticket_output.risk_assessment.severity.value}})}\n\n"
        
        # Retrieve evidence
        yield f"data: {json.dumps({'type': 'status', 'content': 'retrieving', 'message': '正在检索知识库...'})}\n\n"
        
        # Send evidence
        evidence_list = []
        if ticket_output.evidence_candidates:
            for candidate in ticket_output.evidence_candidates[:5]:
                evidence_list.append({
                    "chunk_id": str(candidate.chunk_id),
                    "doc_type": candidate.doc_type.value if hasattr(candidate.doc_type, 'value') else str(candidate.doc_type),
                    "title": candidate.title or "",
                    "content": candidate.content[:200] if candidate.content else "",
                    "score": candidate.score,
                })
        yield f"data: {json.dumps({'type': 'evidence', 'content': evidence_list})}\n\n"
        
        # Generate draft with streaming
        yield f"data: {json.dumps({'type': 'status', 'content': 'generating', 'message': '正在生成回复...'})}\n\n"
        
        # Use DraftAgent for generation
        agent = DraftAgent()
        draft_result = agent.generate_draft(
            normalized_text=ticket_output.normalized_ticket.text,
            issue_type=ticket_output.classification.intent.value,
            risk_flags=[f.value for f in ticket_output.risk_assessment.flags],
            severity=ticket_output.risk_assessment.severity.value,
            must_human_review=ticket_output.risk_assessment.must_human_review,
            evidence_candidates=ticket_output.evidence_candidates,
        )
        
        # Stream the draft text in chunks
        draft_text = draft_result.draft_text
        chunk_size = 10  # Characters per chunk
        for i in range(0, len(draft_text), chunk_size):
            chunk = draft_text[i:i + chunk_size]
            yield f"data: {json.dumps({'type': 'draft_chunk', 'content': chunk})}\n\n"
        
        # Send final result
        yield f"data: {json.dumps({'type': 'done', 'content': {'draft_text': draft_text, 'confidence': draft_result.confidence, 'must_human_review': draft_result.must_human_review, 'session_id': session_id}})}\n\n"
        
    except Exception as e:
        # Send error
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'content': {'draft_text': '抱歉，处理您的请求时出现了问题。请稍后重试或联系人工客服。', 'confidence': 0.0, 'must_human_review': True, 'session_id': session_id}})}\n\n"


def register_streaming_routes(app: FastAPI) -> None:
    """Register streaming chat routes on the FastAPI app."""
    
    @app.post("/api/chat/stream")
    async def chat_stream(request: StreamingChatRequest):
        """
        Streaming chat endpoint using Server-Sent Events (SSE).
        
        Returns a stream of events:
        - status: Processing status updates
        - classification: Intent classification result
        - risk: Risk assessment result
        - evidence: Retrieved evidence
        - draft_chunk: Draft reply text chunks
        - done: Final response with metadata
        - error: Error messages
        """
        if not request.message:
            raise HTTPException(status_code=400, detail="No message provided")
        
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        return StreamingResponse(
            stream_chat_response(
                message=request.message,
                session_id=session_id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
