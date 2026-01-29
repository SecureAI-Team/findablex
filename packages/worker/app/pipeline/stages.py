"""Pipeline stage implementations."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

T_IN = TypeVar("T_IN")
T_OUT = TypeVar("T_OUT")


@dataclass
class PipelineContext:
    """Context passed through all pipeline stages."""
    run_id: str
    project_id: str
    workspace_id: str
    user_id: str
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class PipelineStage(ABC, Generic[T_IN, T_OUT]):
    """Base class for pipeline stages."""
    
    @abstractmethod
    async def process(self, input_data: T_IN, ctx: PipelineContext) -> T_OUT:
        """Process input and return output."""
        pass
    
    def validate_input(self, input_data: T_IN) -> bool:
        """Validate input data. Override in subclasses."""
        return True
    
    async def __call__(self, input_data: T_IN, ctx: PipelineContext) -> T_OUT:
        """Execute the stage."""
        if not self.validate_input(input_data):
            raise ValueError(f"Invalid input for {self.__class__.__name__}")
        return await self.process(input_data, ctx)


@dataclass
class IngestInput:
    """Input for ingest stage."""
    raw_data: str
    format: str  # csv, json, paste
    source: str  # import, qwen, crawl


@dataclass
class IngestOutput:
    """Output from ingest stage."""
    items: List[Dict[str, Any]]
    total_count: int
    parse_errors: List[Dict[str, Any]] = field(default_factory=list)


class IngestStage(PipelineStage[IngestInput, IngestOutput]):
    """Stage for ingesting and parsing input data."""
    
    async def process(self, input_data: IngestInput, ctx: PipelineContext) -> IngestOutput:
        from app.adapters.import_adapter import ImportAdapter
        
        adapter = ImportAdapter()
        items = await adapter.ingest(input_data.raw_data, input_data.format)
        
        return IngestOutput(
            items=items,
            total_count=len(items),
        )


@dataclass
class ExtractInput:
    """Input for extract stage."""
    items: List[Dict[str, Any]]


@dataclass
class ExtractOutput:
    """Output from extract stage."""
    responses: List[Dict[str, Any]]
    extraction_stats: Dict[str, Any] = field(default_factory=dict)


class ExtractStage(PipelineStage[ExtractInput, ExtractOutput]):
    """Stage for extracting citations from responses."""
    
    async def process(self, input_data: ExtractInput, ctx: PipelineContext) -> ExtractOutput:
        from app.agents.citation_extractor import CitationExtractor
        
        extractor = CitationExtractor()
        responses = []
        
        for item in input_data.items:
            citations = await extractor.extract(item.get("response_text", ""))
            responses.append({
                **item,
                "citations": citations,
            })
        
        return ExtractOutput(
            responses=responses,
            extraction_stats={"total": len(responses)},
        )


@dataclass
class ScoreInput:
    """Input for score stage."""
    responses: List[Dict[str, Any]]
    target_domains: List[str] = field(default_factory=list)


@dataclass
class ScoreOutput:
    """Output from score stage."""
    query_metrics: List[Dict[str, Any]]
    project_metrics: Dict[str, Any]


class ScoreStage(PipelineStage[ScoreInput, ScoreOutput]):
    """Stage for calculating metrics."""
    
    async def process(self, input_data: ScoreInput, ctx: PipelineContext) -> ScoreOutput:
        from app.tasks.score import calculate_all_metrics
        
        all_citations = []
        for response in input_data.responses:
            for citation in response.get("citations", []):
                citation["query_id"] = response.get("query_id")
                all_citations.append(citation)
        
        project_metrics = calculate_all_metrics(all_citations, input_data.target_domains)
        
        return ScoreOutput(
            query_metrics=[],  # TODO: Per-query metrics
            project_metrics=project_metrics,
        )


@dataclass
class DiagnoseInput:
    """Input for diagnose stage."""
    query_metrics: List[Dict[str, Any]]
    project_metrics: Dict[str, Any]
    historical_runs: Optional[List[Dict[str, Any]]] = None


@dataclass
class DiagnoseOutput:
    """Output from diagnose stage."""
    issues: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    health_score: float


class DiagnoseStage(PipelineStage[DiagnoseInput, DiagnoseOutput]):
    """Stage for diagnosing issues and generating recommendations."""
    
    async def process(self, input_data: DiagnoseInput, ctx: PipelineContext) -> DiagnoseOutput:
        from app.tasks.report import generate_recommendations
        
        health_score = input_data.project_metrics.get("health_score", 0)
        recommendations = generate_recommendations(input_data.project_metrics)
        
        issues = []
        if health_score < 60:
            issues.append({
                "type": "low_health_score",
                "severity": "warning" if health_score >= 40 else "critical",
                "message": "Overall GEO health score is below target",
            })
        
        return DiagnoseOutput(
            issues=issues,
            recommendations=recommendations,
            health_score=health_score,
        )


@dataclass
class TrackInput:
    """Input for track stage."""
    current_metrics: Dict[str, Any]
    baseline_run_id: Optional[str] = None


@dataclass
class TrackOutput:
    """Output from track stage."""
    drift_events: List[Dict[str, Any]]
    trend_analysis: Dict[str, Any]
    alerts: List[Dict[str, Any]]


class TrackStage(PipelineStage[TrackInput, TrackOutput]):
    """Stage for tracking changes and detecting drift."""
    
    async def process(self, input_data: TrackInput, ctx: PipelineContext) -> TrackOutput:
        drift_events = []
        alerts = []
        
        # TODO: Load baseline metrics and compare
        
        return TrackOutput(
            drift_events=drift_events,
            trend_analysis={},
            alerts=alerts,
        )


@dataclass
class ReportInput:
    """Input for report stage."""
    project_metrics: Dict[str, Any]
    query_metrics: List[Dict[str, Any]]
    issues: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    drift_events: List[Dict[str, Any]]
    health_score: float


@dataclass
class ReportOutput:
    """Output from report stage."""
    report_id: str
    report_html: str
    report_json: Dict[str, Any]
    summary: str


class ReportStage(PipelineStage[ReportInput, ReportOutput]):
    """Stage for generating reports."""
    
    async def process(self, input_data: ReportInput, ctx: PipelineContext) -> ReportOutput:
        from app.tasks.report import generate_checkup_report
        
        report = generate_checkup_report(ctx.run_id, input_data.project_metrics)
        
        return ReportOutput(
            report_id="",  # Will be set after DB save
            report_html=report.get("content_html", ""),
            report_json=report.get("content_json", {}),
            summary=f"Health Score: {input_data.health_score}",
        )
