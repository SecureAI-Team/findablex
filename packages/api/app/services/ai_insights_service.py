"""
AI-driven optimization insights service.

Analyzes crawl results and generates personalized GEO improvement suggestions
using LLM APIs (Qwen / OpenAI / DeepSeek).

Falls back to a rule-based engine if no LLM API key is configured.
"""
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import dynamic
from app.models.crawler import CrawlResult, CrawlTask
from app.models.project import Project, QueryItem

logger = logging.getLogger(__name__)


class AIInsightsService:
    """Generates AI-powered optimization insights from crawl data."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_insights(
        self,
        project_id: UUID,
    ) -> Dict[str, Any]:
        """
        Generate insights for a project based on its latest crawl data.
        
        Tries LLM first, falls back to rule-based analysis.
        """
        # Gather project data
        project_data = await self._gather_project_data(project_id)
        
        if not project_data:
            return {"insights": [], "source": "none", "error": "No data available"}
        
        # Try LLM-based insights
        llm_result = await self._generate_llm_insights(project_data)
        if llm_result:
            return llm_result
        
        # Fall back to rule-based insights
        return self._generate_rule_based_insights(project_data)
    
    async def _gather_project_data(self, project_id: UUID) -> Optional[Dict]:
        """Gather all relevant data for analysis."""
        # Get project
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return None
        
        # Get queries
        q_result = await self.db.execute(
            select(QueryItem).where(QueryItem.project_id == project_id)
        )
        queries = list(q_result.scalars().all())
        
        # Get latest crawl tasks and results
        task_result = await self.db.execute(
            select(CrawlTask)
            .where(CrawlTask.project_id == project_id)
            .order_by(desc(CrawlTask.created_at))
            .limit(20)
        )
        tasks = list(task_result.scalars().all())
        
        # Get crawl results for these tasks
        task_ids = [t.id for t in tasks]
        if task_ids:
            cr_result = await self.db.execute(
                select(CrawlResult)
                .where(CrawlResult.task_id.in_(task_ids))
                .order_by(desc(CrawlResult.created_at))
                .limit(100)
            )
            results = list(cr_result.scalars().all())
        else:
            results = []
        
        # Aggregate data
        engines_seen = set()
        engine_stats: Dict[str, Dict] = {}
        mention_count = 0
        citation_count = 0
        
        for r in results:
            engine = r.engine if hasattr(r, 'engine') else 'unknown'
            engines_seen.add(engine)
            
            if engine not in engine_stats:
                engine_stats[engine] = {"total": 0, "mentioned": 0, "cited": 0}
            
            engine_stats[engine]["total"] += 1
            
            data = r.data if hasattr(r, 'data') and r.data else {}
            if data.get("brand_mentioned"):
                engine_stats[engine]["mentioned"] += 1
                mention_count += 1
            if data.get("citations"):
                engine_stats[engine]["cited"] += 1
                citation_count += 1
        
        return {
            "project_name": project.name,
            "target_domains": project.target_domains or [],
            "queries": [q.text for q in queries],
            "total_results": len(results),
            "engines": list(engines_seen),
            "engine_stats": engine_stats,
            "mention_count": mention_count,
            "citation_count": citation_count,
            "mention_rate": mention_count / len(results) if results else 0,
            "citation_rate": citation_count / len(results) if results else 0,
        }
    
    async def _generate_llm_insights(self, data: Dict) -> Optional[Dict]:
        """Try to generate insights using LLM API."""
        api_key = await dynamic.get("ai.qwen_api_key", "")
        if not api_key:
            api_key = await dynamic.get("ai.openai_api_key", "")
        
        if not api_key:
            return None  # No LLM configured
        
        try:
            import httpx
            
            model = await dynamic.get("ai.qwen_model", "qwen-turbo")
            
            prompt = f"""你是一位 GEO（生成式引擎优化）专家。根据以下品牌在 AI 搜索引擎中的体检数据，生成 3-5 条具体的、可操作的优化建议。

品牌/项目: {data['project_name']}
目标域名: {', '.join(data['target_domains']) if data['target_domains'] else '未指定'}
监测查询词: {', '.join(data['queries'][:10])}
覆盖引擎: {', '.join(data['engines'])}
总结果数: {data['total_results']}
品牌提及率: {data['mention_rate']:.1%}
引用率: {data['citation_rate']:.1%}

各引擎表现:
{json.dumps(data['engine_stats'], ensure_ascii=False, indent=2)}

请输出 JSON 格式:
{{
  "insights": [
    {{
      "priority": "high|medium|low",
      "category": "content|technical|authority|monitoring",
      "title": "建议标题",
      "description": "详细描述",
      "actions": ["具体行动1", "具体行动2"]
    }}
  ],
  "summary": "一句话总结当前状态"
}}"""
            
            # Call Qwen/DashScope API
            base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                    },
                )
                
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    # Try to parse JSON from response
                    try:
                        # Handle markdown code blocks
                        if "```json" in content:
                            content = content.split("```json")[1].split("```")[0]
                        elif "```" in content:
                            content = content.split("```")[1].split("```")[0]
                        
                        parsed = json.loads(content.strip())
                        return {**parsed, "source": "llm"}
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse LLM response as JSON")
                        return None
                else:
                    logger.warning(f"LLM API returned {response.status_code}")
                    return None
        
        except Exception as e:
            logger.warning(f"LLM insights generation failed: {e}")
            return None
    
    def _generate_rule_based_insights(self, data: Dict) -> Dict[str, Any]:
        """Generate insights using rule-based analysis."""
        insights = []
        
        mention_rate = data["mention_rate"]
        citation_rate = data["citation_rate"]
        engines = data["engines"]
        engine_stats = data["engine_stats"]
        
        # Overall visibility assessment
        if mention_rate < 0.3:
            insights.append({
                "priority": "high",
                "category": "content",
                "title": "品牌可见性偏低，需要重点提升",
                "description": f"品牌在 AI 搜索中的提及率仅为 {mention_rate:.0%}，远低于健康水平（60%+）。",
                "actions": [
                    "在权威媒体发布品牌相关的深度文章",
                    "优化官网的结构化数据标记（JSON-LD Schema）",
                    "创建并维护品牌百科词条",
                ],
            })
        elif mention_rate < 0.6:
            insights.append({
                "priority": "medium",
                "category": "content",
                "title": "品牌可见性中等，仍有提升空间",
                "description": f"品牌提及率为 {mention_rate:.0%}，建议进一步优化内容覆盖。",
                "actions": [
                    "增加行业长尾关键词内容覆盖",
                    "发布更多产品对比和评测类内容",
                ],
            })
        
        # Citation rate
        if citation_rate < 0.2 and mention_rate > 0.3:
            insights.append({
                "priority": "high",
                "category": "authority",
                "title": "引用率偏低，品牌权威性需加强",
                "description": f"虽然品牌被提及（{mention_rate:.0%}），但引用率仅 {citation_rate:.0%}。",
                "actions": [
                    "发布更多带有数据和引用的原创研究报告",
                    "提升官网页面的E-E-A-T（经验、专业、权威、信任）信号",
                    "争取行业权威网站的外链和引用",
                ],
            })
        
        # Engine-specific analysis
        weak_engines = []
        strong_engines = []
        for engine, stats in engine_stats.items():
            rate = stats["mentioned"] / stats["total"] if stats["total"] > 0 else 0
            if rate < 0.3:
                weak_engines.append(engine)
            elif rate > 0.7:
                strong_engines.append(engine)
        
        if weak_engines:
            insights.append({
                "priority": "medium",
                "category": "monitoring",
                "title": f"在 {', '.join(weak_engines)} 中表现较弱",
                "description": "不同 AI 引擎的数据来源和排名逻辑不同，需要针对性优化。",
                "actions": [
                    "研究这些引擎的数据来源偏好",
                    "增加在对应平台（如知乎、豆瓣、百科等）的内容覆盖",
                    "持续监测这些引擎的变化趋势",
                ],
            })
        
        # Technical recommendations
        insights.append({
            "priority": "low",
            "category": "technical",
            "title": "定期复测追踪变化",
            "description": "AI 引擎的排名和引用行为会不断变化，建议定期监测。",
            "actions": [
                "每 1-2 周进行一次体检",
                "关注重大搜索引擎更新后的表现变化",
                "建立品牌可见性基准线",
            ],
        })
        
        # Summary
        if mention_rate >= 0.6:
            summary = "品牌 AI 可见性处于健康水平，继续保持并关注引用率提升。"
        elif mention_rate >= 0.3:
            summary = "品牌可见性中等，建议从内容和权威性两方面加强。"
        else:
            summary = "品牌 AI 可见性偏低，需要系统性地提升内容覆盖和权威性。"
        
        return {
            "insights": insights,
            "summary": summary,
            "source": "rules",
        }
