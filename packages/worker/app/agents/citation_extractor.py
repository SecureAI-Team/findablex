"""Citation extraction using rule-based and LLM approaches."""
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


class CitationExtractor:
    """Extract citations from AI-generated responses."""
    
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
    
    async def extract(self, text: str) -> List[Dict[str, Any]]:
        """Extract citations from text."""
        citations = []
        
        # Rule-based extraction
        url_citations = self._extract_urls(text)
        numbered_citations = self._extract_numbered_refs(text)
        mention_citations = self._extract_source_mentions(text)
        
        citations.extend(url_citations)
        citations.extend(numbered_citations)
        citations.extend(mention_citations)
        
        # Deduplicate
        seen = set()
        unique_citations = []
        for c in citations:
            key = (c.get("url", ""), c.get("source_name", ""), c.get("position", 0))
            if key not in seen:
                seen.add(key)
                unique_citations.append(c)
        
        # Sort by position
        unique_citations.sort(key=lambda x: x.get("position", 0))
        
        # Assign positions
        for i, c in enumerate(unique_citations):
            c["position"] = i + 1
        
        return unique_citations
    
    def _extract_urls(self, text: str) -> List[Dict[str, Any]]:
        """Extract URL citations."""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        citations = []
        
        for match in re.finditer(url_pattern, text):
            url = match.group(0)
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith("www."):
                domain = domain[4:]
            
            citations.append({
                "type": "url",
                "url": url,
                "domain": domain,
                "position": match.start(),
            })
        
        return citations
    
    def _extract_numbered_refs(self, text: str) -> List[Dict[str, Any]]:
        """Extract numbered references like [1], [2]."""
        citations = []
        
        # Find numbered references
        for match in re.finditer(r'\[(\d+)\]', text):
            ref_num = int(match.group(1))
            citations.append({
                "type": "numbered_ref",
                "ref_number": ref_num,
                "position": match.start(),
            })
        
        return citations
    
    def _extract_source_mentions(self, text: str) -> List[Dict[str, Any]]:
        """Extract source mentions from text."""
        citations = []
        
        patterns = [
            # English patterns
            (r'according to (?:the )?([A-Z][a-zA-Z\s]+?)(?:,|\.|;)', "en"),
            (r'source[d]? from ([A-Z][a-zA-Z\s]+?)(?:,|\.|;)', "en"),
            (r'(?:reported|published) by ([A-Z][a-zA-Z\s]+?)(?:,|\.|;)', "en"),
            
            # Chinese patterns
            (r'据([^\s,，。、]+)(?:报道|显示|研究|调查)', "zh"),
            (r'来源[：:]\s*([^\s,，。、]+)', "zh"),
            (r'根据([^\s,，。、]+)的(?:数据|报告|研究)', "zh"),
        ]
        
        for pattern, lang in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                source_name = match.group(1).strip()
                if len(source_name) > 2:  # Filter out too short matches
                    citations.append({
                        "type": "mention",
                        "source_name": source_name,
                        "language": lang,
                        "position": match.start(),
                    })
        
        return citations


class LLMCitationExtractor:
    """LLM-based citation extraction for complex cases."""
    
    EXTRACTION_PROMPT = """
从以下AI生成的回答中提取所有引用信息：

回答内容:
{response_text}

请提取：
1. 明确标注的引用（[1], [source], 等）
2. 内联提及的来源（"据XX报道", "根据XX研究"）
3. URL链接
4. 品牌/机构提及

输出JSON格式:
{{
    "citations": [
        {{
            "position": 1,
            "type": "explicit|implicit|url",
            "source_text": "原文引用片段",
            "source_name": "来源名称",
            "url": "URL如果有",
            "context": "引用上下文"
        }}
    ]
}}
"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    async def extract(self, text: str) -> List[Dict[str, Any]]:
        """Extract citations using LLM."""
        if not self.llm_client:
            return []
        
        # TODO: Implement LLM call
        return []
