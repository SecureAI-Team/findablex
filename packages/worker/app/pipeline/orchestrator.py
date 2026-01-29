"""Pipeline orchestrator for running complete workflows."""
from typing import Any, Dict

from app.pipeline.stages import (
    DiagnoseInput,
    DiagnoseStage,
    ExtractInput,
    ExtractStage,
    IngestInput,
    IngestStage,
    PipelineContext,
    ReportInput,
    ReportOutput,
    ReportStage,
    ScoreInput,
    ScoreStage,
    TrackInput,
    TrackStage,
)


class CheckupPipeline:
    """Complete checkup pipeline orchestrator."""
    
    def __init__(self):
        self.ingest = IngestStage()
        self.extract = ExtractStage()
        self.score = ScoreStage()
        self.diagnose = DiagnoseStage()
        self.track = TrackStage()
        self.report = ReportStage()
    
    async def run(
        self,
        raw_data: str,
        input_format: str,
        ctx: PipelineContext,
        target_domains: list = None,
        baseline_run_id: str = None,
    ) -> ReportOutput:
        """Run the complete checkup pipeline."""
        target_domains = target_domains or []
        
        # Stage 1: Ingest
        ingest_input = IngestInput(
            raw_data=raw_data,
            format=input_format,
            source="import",
        )
        ingest_output = await self.ingest(ingest_input, ctx)
        
        # Stage 2: Extract
        extract_input = ExtractInput(items=ingest_output.items)
        extract_output = await self.extract(extract_input, ctx)
        
        # Stage 3: Score
        score_input = ScoreInput(
            responses=extract_output.responses,
            target_domains=target_domains,
        )
        score_output = await self.score(score_input, ctx)
        
        # Stage 4: Diagnose
        diagnose_input = DiagnoseInput(
            query_metrics=score_output.query_metrics,
            project_metrics=score_output.project_metrics,
        )
        diagnose_output = await self.diagnose(diagnose_input, ctx)
        
        # Stage 5: Track
        track_input = TrackInput(
            current_metrics=score_output.project_metrics,
            baseline_run_id=baseline_run_id,
        )
        track_output = await self.track(track_input, ctx)
        
        # Stage 6: Report
        report_input = ReportInput(
            project_metrics=score_output.project_metrics,
            query_metrics=score_output.query_metrics,
            issues=diagnose_output.issues,
            recommendations=diagnose_output.recommendations,
            drift_events=track_output.drift_events,
            health_score=diagnose_output.health_score,
        )
        report_output = await self.report(report_input, ctx)
        
        return report_output
