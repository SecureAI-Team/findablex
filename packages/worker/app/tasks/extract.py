"""Citation extraction tasks."""
import asyncio
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select

from app.celery_app import celery_app


@celery_app.task(bind=True, name="app.tasks.extract.extract_citations")
def extract_citations(self, run_id: str) -> Dict[str, Any]:
    """Extract citations from run responses."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_extract_citations(run_id))
        return result
    finally:
        loop.close()


async def _extract_citations(run_id: str) -> Dict[str, Any]:
    """Async implementation of citation extraction."""
    from app.db import get_db_session
    from app.models import Run, Project, QueryItem, Citation
    
    async with get_db_session() as db:
        run_uuid = UUID(run_id)
        
        # Load run and project
        run_result = await db.execute(
            select(Run).where(Run.id == run_uuid)
        )
        run = run_result.scalar_one_or_none()
        
        if not run:
            return {"error": f"Run {run_id} not found"}
        
        # Load project for target domains
        project_result = await db.execute(
            select(Project).where(Project.id == run.project_id)
        )
        project = project_result.scalar_one_or_none()
        
        if not project:
            return {"error": f"Project not found for run {run_id}"}
        
        target_domains = project.target_domains or []
        
        # Load query items for this run
        query_items_result = await db.execute(
            select(QueryItem).where(QueryItem.run_id == run_uuid)
        )
        query_items = query_items_result.scalars().all()
        
        if not query_items:
            return {"error": f"No query items found for run {run_id}"}
        
        # Extract citations from each query item
        total_citations = 0
        target_citations = 0
        
        for query_item in query_items:
            # Get citations from metadata (from crawler)
            metadata = query_item.metadata_json or {}
            raw_citations = metadata.get("citations", [])
            
            # Also extract from response text
            if query_item.response_text:
                text_citations = extract_citations_from_text(query_item.response_text)
                # Merge with raw citations
                raw_citations.extend(text_citations)
            
            # Save citations to database
            for position, citation_data in enumerate(raw_citations):
                url = citation_data.get("url", "")
                domain = citation_data.get("domain", "") or extract_domain(url)
                
                is_target = is_target_domain(domain, target_domains)
                
                citation = Citation(
                    run_id=run_uuid,
                    query_item_id=query_item.id,
                    position=position,
                    source_url=url,
                    source_domain=domain,
                    source_title=citation_data.get("title", ""),
                    snippet=citation_data.get("snippet", ""),
                    is_target_domain=is_target,
                    relevance_score=Decimal(str(citation_data.get("relevance_score", 0))),
                    raw_response=citation_data,
                    extracted_at=datetime.now(timezone.utc),
                )
                db.add(citation)
                
                total_citations += 1
                if is_target:
                    target_citations += 1
            
            run.processed_queries += 1
        
        await db.commit()
        
        # Trigger scoring task
        from app.tasks.score import calculate_metrics
        calculate_metrics.delay(run_id)
        
        return {
            "run_id": run_id,
            "status": "success",
            "total_citations": total_citations,
            "target_citations": target_citations,
            "query_items_processed": len(query_items),
        }


def is_target_domain(domain: str, target_domains: List[str]) -> bool:
    """Check if domain matches any target domain."""
    if not domain or not target_domains:
        return False
    
    domain = domain.lower()
    for target in target_domains:
        target = target.lower()
        # Exact match or subdomain match
        if domain == target or domain.endswith(f".{target}"):
            return True
    
    return False


def extract_citations_from_text(text: str) -> List[Dict[str, Any]]:
    """Extract citations from response text."""
    citations = []
    
    # Pattern 1: [1], [2], etc. with corresponding links
    numbered_refs = re.findall(r'\[(\d+)\]', text)
    
    # Pattern 2: URLs in text
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, text)
    
    # Pattern 3: "According to X" or "据X报道"
    source_patterns = [
        r'according to (?:the )?([A-Z][a-z]+ ?[A-Z]?[a-z]*)',
        r'据([^\s,，。]+)(?:报道|显示|研究)',
        r'来源[：:]\s*([^\s,，。]+)',
    ]
    
    for url in urls:
        parsed = urlparse(url)
        citations.append({
            "type": "url",
            "url": url,
            "domain": parsed.netloc,
            "position": text.find(url),
        })
    
    for pattern in source_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            citations.append({
                "type": "mention",
                "source_name": match.group(1),
                "position": match.start(),
            })
    
    return citations


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


@celery_app.task(bind=True, name="app.tasks.extract.enrich_citations")
def enrich_citations(self, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enrich citations with additional metadata."""
    enriched = []
    
    for citation in citations:
        if citation.get("url"):
            # Add domain info
            citation["domain"] = extract_domain(citation["url"])
            
            # TODO: Fetch page title and snippet
            # TODO: Calculate authority score
        
        enriched.append(citation)
    
    return enriched
