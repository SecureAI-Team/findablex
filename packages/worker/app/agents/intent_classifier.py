"""Query intent classification using AI."""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class QueryIntent(str, Enum):
    """Query intent types."""
    INFORMATIONAL = "informational"
    NAVIGATIONAL = "navigational"
    TRANSACTIONAL = "transactional"
    COMMERCIAL = "commercial"
    LOCAL = "local"


class QueryClassification(BaseModel):
    """Query classification result."""
    query: str
    primary_intent: QueryIntent
    secondary_intent: Optional[QueryIntent] = None
    confidence: float
    industry: str
    entities: List[str]
    sentiment: str
    complexity: str
    expected_answer_type: str


class IntentClassifier:
    """Classify query intent using rules and optionally LLM."""
    
    # Intent keywords
    INTENT_KEYWORDS = {
        QueryIntent.INFORMATIONAL: [
            "what", "how", "why", "when", "where", "who",
            "什么", "如何", "为什么", "怎么", "哪里",
            "explain", "define", "guide", "tutorial",
        ],
        QueryIntent.NAVIGATIONAL: [
            "login", "sign in", "website", "official",
            "登录", "官网", "主页", "入口",
        ],
        QueryIntent.TRANSACTIONAL: [
            "buy", "price", "discount", "order", "subscribe",
            "购买", "价格", "优惠", "订购", "下单",
        ],
        QueryIntent.COMMERCIAL: [
            "best", "top", "review", "compare", "vs",
            "最好", "对比", "评测", "推荐", "排名",
        ],
        QueryIntent.LOCAL: [
            "near me", "nearby", "local", "address",
            "附近", "地址", "门店", "位置",
        ],
    }
    
    # Industry keywords
    INDUSTRY_KEYWORDS = {
        "healthcare": ["医院", "健康", "病", "治疗", "医生", "doctor", "health", "medical", "hospital"],
        "finance": ["银行", "理财", "投资", "贷款", "bank", "invest", "finance", "loan"],
        "legal": ["律师", "法律", "诉讼", "lawyer", "legal", "law", "court"],
        "tech": ["软件", "技术", "程序", "代码", "software", "tech", "code", "developer"],
        "retail": ["商品", "购物", "商店", "product", "shop", "store", "buy"],
        "education": ["学习", "课程", "培训", "learn", "course", "education", "school"],
    }
    
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
    
    async def classify(self, query: str) -> QueryClassification:
        """Classify a single query."""
        query_lower = query.lower()
        
        # Determine primary intent
        intent_scores = {intent: 0 for intent in QueryIntent}
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    intent_scores[intent] += 1
        
        # Default to informational if no matches
        max_score = max(intent_scores.values())
        if max_score == 0:
            primary_intent = QueryIntent.INFORMATIONAL
        else:
            primary_intent = max(intent_scores, key=intent_scores.get)
        
        # Determine secondary intent
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
        secondary_intent = sorted_intents[1][0] if sorted_intents[1][1] > 0 else None
        
        # Determine industry
        industry = "general"
        for ind, keywords in self.INDUSTRY_KEYWORDS.items():
            if any(kw.lower() in query_lower for kw in keywords):
                industry = ind
                break
        
        # Extract entities (simple approach)
        entities = self._extract_entities(query)
        
        # Determine complexity
        complexity = self._assess_complexity(query)
        
        # Determine expected answer type
        answer_type = self._determine_answer_type(query, primary_intent)
        
        # Calculate confidence
        confidence = min(0.5 + (max_score * 0.15), 0.95)
        
        return QueryClassification(
            query=query,
            primary_intent=primary_intent,
            secondary_intent=secondary_intent,
            confidence=confidence,
            industry=industry,
            entities=entities,
            sentiment="neutral",
            complexity=complexity,
            expected_answer_type=answer_type,
        )
    
    async def batch_classify(self, queries: List[str]) -> List[QueryClassification]:
        """Classify multiple queries."""
        results = []
        for query in queries:
            result = await self.classify(query)
            results.append(result)
        return results
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract named entities from query."""
        # Simple entity extraction - look for capitalized words
        import re
        
        # Find potential entities
        entities = []
        
        # English entities (capitalized words)
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        entities.extend(words)
        
        # Chinese brand names in quotes
        quoted = re.findall(r'[「『""]([^「『""]+)[」』""]', query)
        entities.extend(quoted)
        
        return list(set(entities))
    
    def _assess_complexity(self, query: str) -> str:
        """Assess query complexity."""
        word_count = len(query.split())
        
        if word_count <= 3:
            return "simple"
        elif word_count <= 10:
            return "medium"
        else:
            return "complex"
    
    def _determine_answer_type(self, query: str, intent: QueryIntent) -> str:
        """Determine expected answer type."""
        query_lower = query.lower()
        
        if intent == QueryIntent.TRANSACTIONAL:
            return "action"
        elif intent == QueryIntent.NAVIGATIONAL:
            return "link"
        elif "列表" in query or "哪些" in query or "list" in query_lower:
            return "list"
        elif "对比" in query or "比较" in query or "vs" in query_lower or "compare" in query_lower:
            return "comparison"
        elif "如何" in query or "怎么" in query or "how to" in query_lower:
            return "how-to"
        else:
            return "fact"
