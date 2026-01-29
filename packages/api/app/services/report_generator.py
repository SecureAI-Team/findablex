"""
Report Generator Service - 独创的报告生成系统

包含两种报告类型：
1. 研究报告 (Research Report) - 基于 AI 爬虫数据
2. GEO 体检报告 (Health Check Report) - 基于健康度分析

独创评分体系:
- AVI (AI Visibility Index): AI 可见性指数
- CQS (Citation Quality Score): 引用质量评分
- CPI (Competitive Position Index): 竞争定位指数
"""
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from collections import defaultdict
from urllib.parse import urlparse

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, QueryItem
from app.models.crawler import CrawlTask, CrawlResult
from app.models.report import Report


class ReportGenerator:
    """独创的报告生成器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ========== 研究报告生成 ==========
    
    async def generate_research_report(
        self,
        project_id: UUID,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成研究报告 - 基于 AI 爬虫结果
        
        独创指标:
        - AVI (AI Visibility Index): AI 可见性指数 0-100
        - CQS (Citation Quality Score): 引用质量评分 0-100
        - CPI (Competitive Position Index): 竞争定位指数 0-100
        """
        # 获取项目和目标域名
        project = await self._get_project(project_id)
        if not project:
            raise ValueError("Project not found")
        
        target_domains = project.target_domains or []
        
        # 获取所有查询词和爬虫结果
        query_items = await self._get_query_items(project_id)
        crawl_results = await self._get_crawl_results([q.id for q in query_items])
        
        if not crawl_results:
            return self._empty_research_report(project, title)
        
        # 计算独创指标
        avi_data = self._calculate_avi(crawl_results, target_domains, query_items)
        cqs_data = self._calculate_cqs(crawl_results, target_domains)
        cpi_data = self._calculate_cpi(crawl_results, target_domains)
        
        # 引擎覆盖分析
        engine_analysis = self._analyze_engine_coverage(crawl_results, target_domains)
        
        # 查询词效果分析
        query_analysis = self._analyze_query_effectiveness(crawl_results, target_domains, query_items)
        
        # 竞争对手分析
        competitor_analysis = self._analyze_competitors(crawl_results, target_domains)
        
        # 生成优化建议
        recommendations = self._generate_research_recommendations(
            avi_data, cqs_data, cpi_data, engine_analysis, target_domains
        )
        
        # 问题分布分析 (按阶段/角色/风险)
        query_distribution = self._analyze_query_distribution(query_items, crawl_results, target_domains)
        
        # Top引用来源分析 (谁在定义行业叙事)
        top_citation_sources = self._analyze_top_citation_sources(crawl_results)
        
        # 口径错误摘要 (如果有)
        calibration_summary = await self._get_calibration_summary(project_id)
        
        # 漂移预警
        drift_warning = self._generate_drift_warning(crawl_results)
        
        # 综合评分
        overall_score = round(
            avi_data['score'] * 0.4 +
            cqs_data['score'] * 0.3 +
            cpi_data['score'] * 0.3
        )
        
        return {
            'report_type': 'research',
            'title': title or f'{project.name} - AI 可见性研究报告',
            'project_id': str(project_id),
            'project_name': project.name,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'overall_score': overall_score,
                'status': self._get_status(overall_score),
                'total_queries': len(query_items),
                'total_results': len(crawl_results),
                'target_domains': target_domains,
            },
            'scores': {
                'avi': avi_data,
                'cqs': cqs_data,
                'cpi': cpi_data,
            },
            'engine_analysis': engine_analysis,
            'query_analysis': query_analysis,
            'query_distribution': query_distribution,  # 新增: 问题分布
            'top_citation_sources': top_citation_sources,  # 新增: Top引用来源
            'competitor_analysis': competitor_analysis,
            'calibration_summary': calibration_summary,  # 新增: 口径错误摘要
            'drift_warning': drift_warning,  # 新增: 漂移预警
            'recommendations': recommendations,
            'metadata': {
                'analysis_period': self._get_analysis_period(crawl_results),
                'engines_analyzed': list(set(r.engine for r in crawl_results)),
                'version': '2.0',  # 升级版本
                'next_retest_date': self._calculate_next_retest_date(),  # 建议复测日期
            }
        }
    
    def _calculate_avi(
        self,
        results: List[CrawlResult],
        target_domains: List[str],
        query_items: List[QueryItem],
    ) -> Dict[str, Any]:
        """
        计算 AVI (AI Visibility Index) - AI 可见性指数
        
        公式: AVI = (CR * 40) + (PS * 30) + (EC * 20) + (CS * 10)
        - CR: Citation Rate (引用率)
        - PS: Position Score (位置分数)
        - EC: Engine Coverage (引擎覆盖率)
        - CS: Consistency Score (一致性分数)
        """
        if not results or not target_domains:
            return {'score': 0, 'breakdown': {}, 'trend': 'stable'}
        
        # Citation Rate: 被引用的查询占比
        queries_with_citations = set()
        total_citations = 0
        target_citations = 0
        position_scores = []
        engines_with_brand = set()
        
        for result in results:
            citations = result.citations or []
            if citations:
                queries_with_citations.add(result.query_item_id)
            
            for idx, citation in enumerate(citations):
                total_citations += 1
                domain = self._extract_domain(citation.get('url', ''))
                
                if self._domain_matches(domain, target_domains):
                    target_citations += 1
                    engines_with_brand.add(result.engine)
                    # 位置分数: 第1个引用=100分, 递减
                    position_scores.append(max(0, 100 - idx * 10))
        
        # 计算各项指标
        citation_rate = (target_citations / total_citations * 100) if total_citations > 0 else 0
        position_score = sum(position_scores) / len(position_scores) if position_scores else 0
        
        all_engines = set(r.engine for r in results)
        engine_coverage = (len(engines_with_brand) / len(all_engines) * 100) if all_engines else 0
        
        # 一致性: 跨查询的引用稳定性
        query_citation_counts = defaultdict(int)
        for result in results:
            for citation in (result.citations or []):
                domain = self._extract_domain(citation.get('url', ''))
                if self._domain_matches(domain, target_domains):
                    query_citation_counts[result.query_item_id] += 1
        
        if query_citation_counts:
            counts = list(query_citation_counts.values())
            avg = sum(counts) / len(counts)
            variance = sum((c - avg) ** 2 for c in counts) / len(counts)
            consistency_score = max(0, 100 - math.sqrt(variance) * 10)
        else:
            consistency_score = 0
        
        # 综合 AVI 分数
        avi_score = round(
            citation_rate * 0.4 +
            position_score * 0.3 +
            engine_coverage * 0.2 +
            consistency_score * 0.1
        )
        
        return {
            'score': min(100, avi_score),
            'breakdown': {
                'citation_rate': round(citation_rate, 1),
                'position_score': round(position_score, 1),
                'engine_coverage': round(engine_coverage, 1),
                'consistency_score': round(consistency_score, 1),
            },
            'details': {
                'total_citations': total_citations,
                'target_citations': target_citations,
                'engines_with_brand': list(engines_with_brand),
            },
            'interpretation': self._interpret_avi(avi_score),
        }
    
    def _calculate_cqs(
        self,
        results: List[CrawlResult],
        target_domains: List[str],
    ) -> Dict[str, Any]:
        """
        计算 CQS (Citation Quality Score) - 引用质量评分
        
        评估维度:
        - Title Presence: 标题中是否包含品牌
        - Context Relevance: 引用上下文相关性
        - Source Authority: 来源权威性
        - Recency: 时效性
        """
        if not results or not target_domains:
            return {'score': 0, 'breakdown': {}, 'quality_distribution': {}}
        
        quality_scores = []
        quality_distribution = {'high': 0, 'medium': 0, 'low': 0}
        
        for result in results:
            for citation in (result.citations or []):
                domain = self._extract_domain(citation.get('url', ''))
                if not self._domain_matches(domain, target_domains):
                    continue
                
                # 计算单个引用的质量分数
                title = citation.get('title', '')
                url = citation.get('url', '')
                
                # 标题得分 (30%)
                title_score = 100 if any(td.lower() in title.lower() for td in target_domains) else 50
                
                # 来源得分 (40%) - 基于域名层级
                path_depth = url.count('/') - 2  # 减去协议的 //
                source_score = max(0, 100 - path_depth * 15)
                
                # URL 质量得分 (30%) - 检查是否是主页或高质量页面
                if '?' in url or '#' in url:
                    url_score = 60
                elif path_depth <= 2:
                    url_score = 100
                else:
                    url_score = 80
                
                total_score = round(
                    title_score * 0.3 +
                    source_score * 0.4 +
                    url_score * 0.3
                )
                
                quality_scores.append(total_score)
                
                # 分类
                if total_score >= 80:
                    quality_distribution['high'] += 1
                elif total_score >= 50:
                    quality_distribution['medium'] += 1
                else:
                    quality_distribution['low'] += 1
        
        avg_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return {
            'score': round(avg_score),
            'breakdown': {
                'average_quality': round(avg_score, 1),
                'total_brand_citations': len(quality_scores),
            },
            'quality_distribution': quality_distribution,
            'interpretation': self._interpret_cqs(avg_score),
        }
    
    def _calculate_cpi(
        self,
        results: List[CrawlResult],
        target_domains: List[str],
    ) -> Dict[str, Any]:
        """
        计算 CPI (Competitive Position Index) - 竞争定位指数
        
        评估品牌在 AI 引擎中相对于竞争对手的位置
        - Share of Voice: 品牌引用占总引用的比例
        - Ranking Position: 在引用列表中的平均排名
        - Dominance Score: 作为首选引用的频率
        """
        if not results or not target_domains:
            return {'score': 0, 'breakdown': {}, 'competitive_landscape': {}}
        
        total_citations = 0
        brand_citations = 0
        first_position_count = 0
        all_positions = []
        domain_counts = defaultdict(int)
        
        for result in results:
            citations = result.citations or []
            for idx, citation in enumerate(citations):
                total_citations += 1
                domain = self._extract_domain(citation.get('url', ''))
                domain_counts[domain] += 1
                
                if self._domain_matches(domain, target_domains):
                    brand_citations += 1
                    all_positions.append(idx + 1)
                    if idx == 0:
                        first_position_count += 1
        
        # Share of Voice
        sov = (brand_citations / total_citations * 100) if total_citations > 0 else 0
        
        # Average Ranking (越低越好，转换为0-100分数)
        avg_position = sum(all_positions) / len(all_positions) if all_positions else 10
        ranking_score = max(0, 100 - (avg_position - 1) * 15)
        
        # Dominance Score
        dominance = (first_position_count / len(results) * 100) if results else 0
        
        # 综合 CPI
        cpi_score = round(sov * 0.4 + ranking_score * 0.35 + dominance * 0.25)
        
        # 竞争格局
        top_competitors = sorted(
            [(d, c) for d, c in domain_counts.items() if not self._domain_matches(d, target_domains)],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            'score': min(100, cpi_score),
            'breakdown': {
                'share_of_voice': round(sov, 1),
                'ranking_score': round(ranking_score, 1),
                'dominance_score': round(dominance, 1),
            },
            'details': {
                'average_position': round(avg_position, 2),
                'first_position_count': first_position_count,
            },
            'competitive_landscape': {
                'top_competitors': [
                    {'domain': d, 'citations': c, 'share': round(c/total_citations*100, 1)}
                    for d, c in top_competitors
                ],
                'brand_rank': self._get_brand_rank(domain_counts, target_domains),
            },
            'interpretation': self._interpret_cpi(cpi_score),
        }
    
    def _analyze_engine_coverage(
        self,
        results: List[CrawlResult],
        target_domains: List[str],
    ) -> Dict[str, Any]:
        """分析各 AI 引擎的品牌覆盖情况"""
        engine_data = defaultdict(lambda: {
            'total_queries': 0,
            'total_citations': 0,
            'brand_citations': 0,
            'brand_queries': 0,
        })
        
        for result in results:
            engine = result.engine
            engine_data[engine]['total_queries'] += 1
            
            citations = result.citations or []
            engine_data[engine]['total_citations'] += len(citations)
            
            has_brand = False
            for citation in citations:
                domain = self._extract_domain(citation.get('url', ''))
                if self._domain_matches(domain, target_domains):
                    engine_data[engine]['brand_citations'] += 1
                    has_brand = True
            
            if has_brand:
                engine_data[engine]['brand_queries'] += 1
        
        engine_scores = {}
        for engine, data in engine_data.items():
            coverage_rate = (data['brand_queries'] / data['total_queries'] * 100) if data['total_queries'] > 0 else 0
            citation_rate = (data['brand_citations'] / data['total_citations'] * 100) if data['total_citations'] > 0 else 0
            
            engine_scores[engine] = {
                'coverage_rate': round(coverage_rate, 1),
                'citation_rate': round(citation_rate, 1),
                'score': round(coverage_rate * 0.6 + citation_rate * 0.4),
                'total_queries': data['total_queries'],
                'brand_mentions': data['brand_citations'],
            }
        
        # 排序
        sorted_engines = sorted(engine_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        
        return {
            'engines': dict(sorted_engines),
            'best_engine': sorted_engines[0][0] if sorted_engines else None,
            'worst_engine': sorted_engines[-1][0] if sorted_engines else None,
            'coverage_gap': self._identify_coverage_gaps(engine_scores),
        }
    
    def _analyze_query_effectiveness(
        self,
        results: List[CrawlResult],
        target_domains: List[str],
        query_items: List[QueryItem],
    ) -> Dict[str, Any]:
        """分析查询词效果"""
        query_map = {str(q.id): q.query_text for q in query_items}
        query_scores = defaultdict(lambda: {'citations': 0, 'brand_citations': 0, 'engines': set()})
        
        for result in results:
            qid = str(result.query_item_id)
            citations = result.citations or []
            query_scores[qid]['citations'] += len(citations)
            
            for citation in citations:
                domain = self._extract_domain(citation.get('url', ''))
                if self._domain_matches(domain, target_domains):
                    query_scores[qid]['brand_citations'] += 1
                    query_scores[qid]['engines'].add(result.engine)
        
        query_analysis = []
        for qid, data in query_scores.items():
            effectiveness = (data['brand_citations'] / data['citations'] * 100) if data['citations'] > 0 else 0
            query_analysis.append({
                'query_id': qid,
                'query_text': query_map.get(qid, 'Unknown'),
                'effectiveness_score': round(effectiveness, 1),
                'brand_citations': data['brand_citations'],
                'total_citations': data['citations'],
                'engine_coverage': len(data['engines']),
            })
        
        query_analysis.sort(key=lambda x: x['effectiveness_score'], reverse=True)
        
        return {
            'queries': query_analysis,
            'best_performing': query_analysis[:3] if query_analysis else [],
            'needs_improvement': [q for q in query_analysis if q['effectiveness_score'] < 10][:3],
            'avg_effectiveness': round(
                sum(q['effectiveness_score'] for q in query_analysis) / len(query_analysis), 1
            ) if query_analysis else 0,
        }
    
    def _analyze_competitors(
        self,
        results: List[CrawlResult],
        target_domains: List[str],
    ) -> Dict[str, Any]:
        """分析竞争对手情况"""
        domain_data = defaultdict(lambda: {
            'count': 0,
            'engines': set(),
            'queries': set(),
            'positions': [],
        })
        
        for result in results:
            for idx, citation in enumerate(result.citations or []):
                domain = self._extract_domain(citation.get('url', ''))
                if domain and not self._domain_matches(domain, target_domains):
                    domain_data[domain]['count'] += 1
                    domain_data[domain]['engines'].add(result.engine)
                    domain_data[domain]['queries'].add(str(result.query_item_id))
                    domain_data[domain]['positions'].append(idx + 1)
        
        competitors = []
        for domain, data in domain_data.items():
            avg_position = sum(data['positions']) / len(data['positions']) if data['positions'] else 10
            competitors.append({
                'domain': domain,
                'citations': data['count'],
                'engine_coverage': len(data['engines']),
                'query_coverage': len(data['queries']),
                'avg_position': round(avg_position, 2),
                'threat_level': self._calculate_threat_level(data),
            })
        
        competitors.sort(key=lambda x: x['citations'], reverse=True)
        
        return {
            'top_competitors': competitors[:10],
            'total_competitor_domains': len(competitors),
            'threat_summary': {
                'high': len([c for c in competitors if c['threat_level'] == 'high']),
                'medium': len([c for c in competitors if c['threat_level'] == 'medium']),
                'low': len([c for c in competitors if c['threat_level'] == 'low']),
            },
        }
    
    def _generate_research_recommendations(
        self,
        avi: Dict,
        cqs: Dict,
        cpi: Dict,
        engine_analysis: Dict,
        target_domains: List[str],
    ) -> List[Dict[str, Any]]:
        """生成研究报告的优化建议"""
        recommendations = []
        
        # 基于 AVI 的建议
        if avi['score'] < 30:
            recommendations.append({
                'priority': 'critical',
                'category': 'visibility',
                'title': '紧急提升 AI 可见性',
                'description': f'您的 AI 可见性指数仅为 {avi["score"]}，品牌在 AI 引擎中几乎不可见。',
                'actions': [
                    '确保网站内容包含结构化数据 (Schema.org)',
                    '优化页面标题和元描述，突出品牌关键词',
                    '创建针对常见问题的专题内容页面',
                    '提升网站的 E-E-A-T 信号 (专业性、权威性、可信度)',
                ],
                'expected_impact': 'high',
            })
        elif avi['score'] < 60:
            recommendations.append({
                'priority': 'high',
                'category': 'visibility',
                'title': '优化内容可发现性',
                'description': '您的品牌有一定可见性，但仍有较大提升空间。',
                'actions': [
                    '增加行业相关的深度内容',
                    '建立更多高质量外链',
                    '确保移动端体验良好',
                ],
                'expected_impact': 'medium',
            })
        
        # 基于 CQS 的建议
        if cqs['score'] < 50:
            recommendations.append({
                'priority': 'high',
                'category': 'quality',
                'title': '提升引用质量',
                'description': '当前引用质量较低，可能影响品牌形象。',
                'actions': [
                    '创建更多权威性内容页面',
                    '优化关键页面的 URL 结构',
                    '确保被引用页面内容完整、专业',
                ],
                'expected_impact': 'medium',
            })
        
        # 基于 CPI 的建议
        if cpi['breakdown']['share_of_voice'] < 10:
            competitors = cpi.get('competitive_landscape', {}).get('top_competitors', [])
            top_comp = competitors[0]['domain'] if competitors else '竞争对手'
            recommendations.append({
                'priority': 'high',
                'category': 'competition',
                'title': '提升市场份额',
                'description': f'您的市场声量仅 {cpi["breakdown"]["share_of_voice"]}%，{top_comp} 占据主导。',
                'actions': [
                    '分析领先竞争对手的内容策略',
                    '创建差异化的专业内容',
                    '增加品牌相关的问答内容',
                ],
                'expected_impact': 'high',
            })
        
        # 基于引擎覆盖的建议
        coverage_gaps = engine_analysis.get('coverage_gap', [])
        if coverage_gaps:
            recommendations.append({
                'priority': 'medium',
                'category': 'coverage',
                'title': '扩大引擎覆盖',
                'description': f'您在 {", ".join(coverage_gaps[:2])} 等引擎中覆盖不足。',
                'actions': [
                    '研究各引擎的内容偏好差异',
                    '针对弱势引擎优化内容格式',
                    '增加多样化的内容类型',
                ],
                'expected_impact': 'medium',
            })
        
        # 如果没有目标域名
        if not target_domains:
            recommendations.insert(0, {
                'priority': 'critical',
                'category': 'setup',
                'title': '设置目标域名',
                'description': '您尚未设置目标域名，无法追踪品牌可见性。',
                'actions': [
                    '在项目设置中添加您的品牌域名',
                    '可以添加多个域名（如主站和博客）',
                ],
                'expected_impact': 'critical',
            })
        
        # 排序：critical > high > medium > low
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 4))
        
        return recommendations
    
    # ========== 增强分析方法 ==========
    
    def _analyze_query_distribution(
        self,
        query_items: List[QueryItem],
        results: List[CrawlResult],
        target_domains: List[str],
    ) -> Dict[str, Any]:
        """
        分析问题分布 (按阶段/角色/风险)
        
        返回各维度的分布情况及其可见性表现
        """
        # 按query_item_id索引结果
        results_by_query = defaultdict(list)
        for r in results:
            results_by_query[str(r.query_item_id)].append(r)
        
        def calculate_visibility(query_ids: List[str]) -> Dict:
            """计算一组查询词的可见性"""
            total = 0
            cited = 0
            for qid in query_ids:
                query_results = results_by_query.get(qid, [])
                for r in query_results:
                    total += 1
                    for c in (r.citations or []):
                        if self._domain_matches(self._extract_domain(c.get('url', '')), target_domains):
                            cited += 1
                            break
            return {
                "total_queries": len(query_ids),
                "total_responses": total,
                "cited_count": cited,
                "visibility_rate": round(cited / total * 100, 1) if total > 0 else 0,
            }
        
        # 按阶段分布
        by_stage = defaultdict(list)
        for q in query_items:
            stage = getattr(q, 'stage', None) or 'unknown'
            by_stage[stage].append(str(q.id))
        
        stage_distribution = {}
        for stage, qids in by_stage.items():
            stage_distribution[stage] = {
                **calculate_visibility(qids),
                "count": len(qids),
                "label": {
                    "awareness": "认知阶段",
                    "consideration": "考虑阶段",
                    "decision": "决策阶段",
                    "retention": "留存阶段",
                    "unknown": "未分类",
                }.get(stage, stage),
            }
        
        # 按风险分布
        by_risk = defaultdict(list)
        for q in query_items:
            risk = getattr(q, 'risk_level', None) or 'unknown'
            by_risk[risk].append(str(q.id))
        
        risk_distribution = {}
        for risk, qids in by_risk.items():
            risk_distribution[risk] = {
                **calculate_visibility(qids),
                "count": len(qids),
                "label": {
                    "critical": "关键风险",
                    "high": "高风险",
                    "medium": "中等风险",
                    "low": "低风险",
                    "unknown": "未分类",
                }.get(risk, risk),
            }
        
        # 按角色分布
        by_role = defaultdict(list)
        for q in query_items:
            role = getattr(q, 'target_role', None) or 'unknown'
            by_role[role].append(str(q.id))
        
        role_distribution = {}
        for role, qids in by_role.items():
            role_distribution[role] = {
                **calculate_visibility(qids),
                "count": len(qids),
                "label": {
                    "marketing": "市场",
                    "sales": "销售",
                    "compliance": "合规",
                    "technical": "技术",
                    "management": "管理层",
                    "unknown": "未分类",
                }.get(role, role),
            }
        
        # 找出问题区域 (可见性低的高风险问题)
        problem_areas = []
        for risk in ["critical", "high"]:
            if risk in risk_distribution:
                data = risk_distribution[risk]
                if data["visibility_rate"] < 30 and data["total_queries"] > 0:
                    problem_areas.append({
                        "type": "risk",
                        "value": risk,
                        "label": data["label"],
                        "visibility_rate": data["visibility_rate"],
                        "query_count": data["total_queries"],
                    })
        
        return {
            "by_stage": stage_distribution,
            "by_risk": risk_distribution,
            "by_role": role_distribution,
            "problem_areas": problem_areas,
        }
    
    def _analyze_top_citation_sources(
        self,
        results: List[CrawlResult],
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        分析Top引用来源 - 谁在定义行业叙事
        
        识别被AI引擎频繁引用的来源，了解行业话语权分布
        """
        source_data = defaultdict(lambda: {
            "count": 0,
            "engines": set(),
            "positions": [],
            "titles": set(),
        })
        
        for result in results:
            for idx, citation in enumerate(result.citations or []):
                url = citation.get('url', '')
                domain = self._extract_domain(url)
                if not domain:
                    continue
                
                source_data[domain]['count'] += 1
                source_data[domain]['engines'].add(result.engine)
                source_data[domain]['positions'].append(idx + 1)
                if citation.get('title'):
                    source_data[domain]['titles'].add(citation['title'][:50])
        
        # 构建排名列表
        sources = []
        total_citations = sum(d['count'] for d in source_data.values())
        
        for domain, data in source_data.items():
            avg_pos = sum(data['positions']) / len(data['positions']) if data['positions'] else 10
            sources.append({
                "domain": domain,
                "citation_count": data['count'],
                "share_of_voice": round(data['count'] / total_citations * 100, 1) if total_citations > 0 else 0,
                "engine_coverage": len(data['engines']),
                "avg_position": round(avg_pos, 2),
                "sample_titles": list(data['titles'])[:3],
                "influence_score": self._calculate_influence_score(data, total_citations),
            })
        
        sources.sort(key=lambda x: x['citation_count'], reverse=True)
        top_sources = sources[:limit]
        
        # 分类统计
        media_types = {
            "official": 0,  # 官方/品牌
            "media": 0,     # 媒体
            "wiki": 0,      # 百科类
            "forum": 0,     # 论坛/社区
            "other": 0,
        }
        
        for s in top_sources:
            domain = s['domain'].lower()
            if any(x in domain for x in ['wikipedia', 'baike', 'zhihu.com/special']):
                media_types['wiki'] += s['citation_count']
            elif any(x in domain for x in ['zhihu', 'reddit', 'quora', 'tieba']):
                media_types['forum'] += s['citation_count']
            elif any(x in domain for x in ['news', 'sina', '163.com', 'sohu', 'qq.com', 'toutiao']):
                media_types['media'] += s['citation_count']
            else:
                media_types['other'] += s['citation_count']
        
        return {
            "top_sources": top_sources,
            "total_unique_sources": len(sources),
            "total_citations": total_citations,
            "source_type_distribution": media_types,
            "concentration_index": self._calculate_concentration_index(top_sources[:10], total_citations),
            "insights": self._generate_source_insights(top_sources, media_types),
        }
    
    def _calculate_influence_score(self, data: Dict, total: int) -> int:
        """计算来源的影响力分数"""
        if total == 0:
            return 0
        
        share = data['count'] / total
        position_score = 1 / (sum(data['positions']) / len(data['positions'])) if data['positions'] else 0
        coverage_score = len(data['engines']) / 5  # 假设最多5个引擎
        
        return round((share * 0.5 + position_score * 0.3 + coverage_score * 0.2) * 100)
    
    def _calculate_concentration_index(self, top_sources: List, total: int) -> Dict:
        """计算来源集中度 (CR10指数)"""
        if total == 0:
            return {"cr10": 0, "status": "无数据"}
        
        top10_citations = sum(s['citation_count'] for s in top_sources[:10])
        cr10 = top10_citations / total * 100
        
        if cr10 > 70:
            status = "高度集中"
            insight = "前10来源占据大部分引用，话语权较为集中"
        elif cr10 > 40:
            status = "适度集中"
            insight = "来源分布较为均衡"
        else:
            status = "分散"
            insight = "来源高度分散，没有明显主导者"
        
        return {
            "cr10": round(cr10, 1),
            "status": status,
            "insight": insight,
        }
    
    def _generate_source_insights(self, top_sources: List, type_dist: Dict) -> List[str]:
        """生成来源分析洞察"""
        insights = []
        
        if top_sources:
            insights.append(f"最常被引用的来源是 {top_sources[0]['domain']}，占总引用的 {top_sources[0]['share_of_voice']}%")
        
        max_type = max(type_dist, key=type_dist.get) if type_dist else None
        if max_type == 'wiki':
            insights.append("百科类内容是主要引用来源，建议优化百科词条")
        elif max_type == 'forum':
            insights.append("问答社区贡献大量引用，建议加强社区运营")
        elif max_type == 'media':
            insights.append("媒体报道是主要来源，建议加强公关传播")
        
        return insights
    
    async def _get_calibration_summary(self, project_id: UUID) -> Dict[str, Any]:
        """获取口径错误摘要"""
        from app.models.calibration import CalibrationError
        
        # 统计各严重程度的错误数
        result = await self.db.execute(
            select(CalibrationError.severity, func.count(CalibrationError.id))
            .where(CalibrationError.project_id == project_id)
            .where(CalibrationError.review_status != 'dismissed')
            .group_by(CalibrationError.severity)
        )
        severity_counts = dict(result.all())
        
        total = sum(severity_counts.values())
        
        if total == 0:
            return {
                "has_errors": False,
                "total": 0,
                "by_severity": {},
                "needs_attention": False,
            }
        
        critical = severity_counts.get('critical', 0)
        high = severity_counts.get('high', 0)
        
        return {
            "has_errors": True,
            "total": total,
            "by_severity": severity_counts,
            "critical_count": critical,
            "high_count": high,
            "needs_attention": critical > 0 or high > 3,
            "message": f"发现 {total} 个口径问题，其中 {critical} 个严重错误需要立即处理" if critical > 0 else f"发现 {total} 个口径问题需要复核",
        }
    
    def _generate_drift_warning(self, results: List[CrawlResult]) -> Dict[str, Any]:
        """生成漂移预警"""
        if not results:
            return {"has_warning": False}
        
        # 获取最新和最早的爬取时间
        crawl_times = [r.crawled_at for r in results if r.crawled_at]
        if not crawl_times:
            return {"has_warning": False}
        
        latest = max(crawl_times)
        now = datetime.now(timezone.utc)
        
        # 如果数据超过7天，建议复测
        days_since_crawl = (now - latest).days if latest.tzinfo else (now.replace(tzinfo=None) - latest).days
        
        if days_since_crawl > 30:
            return {
                "has_warning": True,
                "warning_level": "critical",
                "message": f"数据已超过 {days_since_crawl} 天未更新，AI引擎结果可能已发生显著变化",
                "days_since_update": days_since_crawl,
                "recommendation": "建议立即进行复测",
            }
        elif days_since_crawl > 14:
            return {
                "has_warning": True,
                "warning_level": "high",
                "message": f"距上次更新已 {days_since_crawl} 天，建议进行复测",
                "days_since_update": days_since_crawl,
                "recommendation": "建议本周内进行复测",
            }
        elif days_since_crawl > 7:
            return {
                "has_warning": True,
                "warning_level": "medium",
                "message": f"距上次更新已 {days_since_crawl} 天",
                "days_since_update": days_since_crawl,
                "recommendation": "可考虑进行复测以跟踪变化",
            }
        
        return {
            "has_warning": False,
            "days_since_update": days_since_crawl,
            "message": "数据较新，暂无需复测",
        }
    
    def _calculate_next_retest_date(self) -> str:
        """计算建议的下次复测日期"""
        from datetime import timedelta
        
        # 默认建议14天后复测
        next_date = datetime.now(timezone.utc) + timedelta(days=14)
        return next_date.strftime("%Y-%m-%d")
    
    # ========== GEO 体检报告生成 ==========
    
    async def generate_health_report(
        self,
        run_id: UUID,
        project_id: UUID,
        health_score: int,
        metrics_data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        生成 GEO 体检报告
        
        基于健康度评分和各项指标生成详细报告
        """
        project = await self._get_project(project_id)
        if not project:
            raise ValueError("Project not found")
        
        # 生成或使用提供的指标
        metrics = metrics_data or self._generate_health_metrics(health_score)
        
        # 生成优化建议
        recommendations = self._generate_health_recommendations(health_score, metrics)
        
        return {
            'report_type': 'health_check',
            'title': f'{project.name} - GEO 体检报告',
            'project_id': str(project_id),
            'project_name': project.name,
            'run_id': str(run_id),
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'health_score': health_score,
                'status': self._get_status(health_score),
                'status_text': self._get_status_text(health_score),
            },
            'metrics': metrics,
            'recommendations': recommendations,
            'comparison': {
                'industry_avg': 65,
                'vs_industry': health_score - 65,
                'percentile': self._calculate_percentile(health_score),
            },
        }
    
    def _generate_health_metrics(self, health_score: int) -> Dict[str, Any]:
        """基于健康度生成详细指标"""
        # 模拟各项指标 (实际实现需要真实数据)
        base = health_score / 100
        
        return {
            'visibility': {
                'score': round(min(100, health_score + 5)),
                'label': '可见性覆盖率',
                'description': 'AI 引擎中品牌内容被引用的覆盖率',
            },
            'position': {
                'score': round(min(100, health_score - 5)),
                'label': '平均引用位置',
                'description': '在 AI 回复中被引用的平均位置排名',
            },
            'authority': {
                'score': round(min(100, health_score + 10)),
                'label': '权威性信号',
                'description': '内容的专业性和可信度评估',
            },
            'technical': {
                'score': round(min(100, health_score - 10)),
                'label': '技术优化',
                'description': '结构化数据和技术 SEO 评估',
            },
        }
    
    def _generate_health_recommendations(
        self,
        health_score: int,
        metrics: Dict,
    ) -> List[Dict[str, Any]]:
        """生成体检报告的优化建议"""
        recommendations = []
        
        if health_score < 60:
            recommendations.append({
                'priority': 'high',
                'category': 'overall',
                'title': '全面优化 GEO 表现',
                'description': '您的整体健康度较低，需要系统性优化。',
                'actions': [
                    '审核并更新网站核心内容',
                    '添加结构化数据标记',
                    '优化页面加载速度',
                    '提升移动端体验',
                ],
            })
        
        # 基于各项指标的建议
        for key, metric in metrics.items():
            if metric['score'] < 60:
                recommendations.append({
                    'priority': 'medium',
                    'category': key,
                    'title': f'改进{metric["label"]}',
                    'description': metric['description'],
                    'actions': self._get_metric_actions(key),
                })
        
        return recommendations
    
    def _get_metric_actions(self, metric_key: str) -> List[str]:
        """获取各指标的具体行动建议"""
        actions_map = {
            'visibility': [
                '创建更多问答式内容',
                '优化长尾关键词覆盖',
                '增加内容更新频率',
            ],
            'position': [
                '提升内容深度和专业性',
                '获取更多权威外链',
                '优化页面标题和描述',
            ],
            'authority': [
                '展示作者专业背景',
                '添加可验证的数据来源',
                '获取行业认证或背书',
            ],
            'technical': [
                '实施 Schema.org 标记',
                '优化 Core Web Vitals',
                '确保 HTTPS 和安全性',
            ],
        }
        return actions_map.get(metric_key, ['请联系专业人员进行评估'])
    
    # ========== 辅助方法 ==========
    
    async def _get_project(self, project_id: UUID) -> Optional[Project]:
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_query_items(self, project_id: UUID) -> List[QueryItem]:
        result = await self.db.execute(
            select(QueryItem).where(QueryItem.project_id == project_id)
        )
        return list(result.scalars().all())
    
    async def _get_crawl_results(self, query_ids: List[UUID]) -> List[CrawlResult]:
        if not query_ids:
            return []
        result = await self.db.execute(
            select(CrawlResult).where(CrawlResult.query_item_id.in_(query_ids))
        )
        return list(result.scalars().all())
    
    def _extract_domain(self, url: str) -> str:
        try:
            return urlparse(url).netloc.lower()
        except:
            return ''
    
    def _domain_matches(self, domain: str, targets: List[str]) -> bool:
        domain_lower = domain.lower()
        for target in targets:
            target_lower = target.lower()
            if domain_lower == target_lower or domain_lower.endswith('.' + target_lower):
                return True
        return False
    
    def _get_status(self, score: int) -> str:
        if score >= 80:
            return 'excellent'
        if score >= 60:
            return 'good'
        if score >= 40:
            return 'fair'
        return 'poor'
    
    def _get_status_text(self, score: int) -> str:
        status_map = {
            'excellent': '优秀',
            'good': '良好',
            'fair': '一般',
            'poor': '需改进',
        }
        return status_map.get(self._get_status(score), '未知')
    
    def _interpret_avi(self, score: int) -> str:
        if score >= 80:
            return '您的品牌在 AI 引擎中具有极高的可见性，继续保持！'
        if score >= 60:
            return '品牌可见性良好，但仍有提升空间。'
        if score >= 40:
            return '品牌可见性一般，建议加强内容优化。'
        return '品牌在 AI 引擎中几乎不可见，需要紧急优化。'
    
    def _interpret_cqs(self, score: int) -> str:
        if score >= 80:
            return '引用质量优秀，品牌以专业形象出现。'
        if score >= 60:
            return '引用质量良好，部分引用可以优化。'
        return '引用质量较低，可能影响品牌形象。'
    
    def _interpret_cpi(self, score: int) -> str:
        if score >= 80:
            return '在竞争格局中处于领先地位。'
        if score >= 60:
            return '竞争地位稳固，但有提升空间。'
        return '竞争地位较弱，需要加强差异化。'
    
    def _get_brand_rank(self, domain_counts: Dict, targets: List[str]) -> int:
        sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)
        for idx, (domain, _) in enumerate(sorted_domains):
            if self._domain_matches(domain, targets):
                return idx + 1
        return len(sorted_domains) + 1
    
    def _identify_coverage_gaps(self, engine_scores: Dict) -> List[str]:
        gaps = []
        for engine, data in engine_scores.items():
            if data['coverage_rate'] < 20:
                gaps.append(engine)
        return gaps
    
    def _calculate_threat_level(self, data: Dict) -> str:
        score = data['count'] * 2 + len(data['engines']) * 10 + len(data['queries']) * 5
        if score > 50:
            return 'high'
        if score > 20:
            return 'medium'
        return 'low'
    
    def _get_analysis_period(self, results: List[CrawlResult]) -> Dict[str, str]:
        if not results:
            return {'start': '', 'end': ''}
        
        dates = [r.crawled_at for r in results if r.crawled_at]
        if not dates:
            return {'start': '', 'end': ''}
        
        return {
            'start': min(dates).isoformat(),
            'end': max(dates).isoformat(),
        }
    
    def _calculate_percentile(self, score: int) -> int:
        # 简化的百分位计算
        if score >= 90:
            return 95
        if score >= 80:
            return 85
        if score >= 70:
            return 70
        if score >= 60:
            return 55
        if score >= 50:
            return 40
        return 25
    
    def _empty_research_report(self, project: Project, title: Optional[str]) -> Dict[str, Any]:
        """生成空的研究报告"""
        return {
            'report_type': 'research',
            'title': title or f'{project.name} - AI 可见性研究报告',
            'project_id': str(project.id),
            'project_name': project.name,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'overall_score': 0,
                'status': 'no_data',
                'total_queries': 0,
                'total_results': 0,
                'target_domains': project.target_domains or [],
            },
            'scores': {
                'avi': {'score': 0, 'breakdown': {}, 'interpretation': '暂无数据'},
                'cqs': {'score': 0, 'breakdown': {}, 'interpretation': '暂无数据'},
                'cpi': {'score': 0, 'breakdown': {}, 'interpretation': '暂无数据'},
            },
            'recommendations': [{
                'priority': 'critical',
                'category': 'data',
                'title': '运行研究任务',
                'description': '尚无爬虫数据，请先运行研究任务。',
                'actions': ['创建研究任务并选择 AI 引擎', '添加查询词进行测试'],
                'expected_impact': 'critical',
            }],
        }
