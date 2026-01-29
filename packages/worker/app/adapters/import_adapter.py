"""Import adapter for CSV, JSON, and paste data."""
import csv
import json
from io import StringIO
from typing import Any, Dict, List


class ImportAdapter:
    """Adapter for importing data from various formats."""
    
    async def ingest(self, raw_data: str, format: str) -> List[Dict[str, Any]]:
        """Ingest data from the specified format."""
        if format == "csv":
            return self._parse_csv(raw_data)
        elif format == "json":
            return self._parse_json(raw_data)
        else:
            return self._parse_paste(raw_data)
    
    def _parse_csv(self, data: str) -> List[Dict[str, Any]]:
        """Parse CSV data."""
        reader = csv.DictReader(StringIO(data))
        items = []
        
        for i, row in enumerate(reader):
            query = row.get("query") or row.get("question") or row.get("q") or ""
            response = row.get("response") or row.get("answer") or row.get("a") or ""
            
            items.append({
                "query_id": f"q_{i}",
                "query_text": query.strip(),
                "response_text": response.strip(),
                "citations": [],
                "metadata": {k: v for k, v in row.items() 
                            if k.lower() not in ("query", "question", "q", "response", "answer", "a")},
            })
        
        return items
    
    def _parse_json(self, data: str) -> List[Dict[str, Any]]:
        """Parse JSON data."""
        parsed = json.loads(data)
        
        if isinstance(parsed, list):
            items = parsed
        elif isinstance(parsed, dict):
            if "items" in parsed:
                items = parsed["items"]
            elif "data" in parsed:
                items = parsed["data"]
            else:
                items = [parsed]
        else:
            items = [{"response_text": str(parsed)}]
        
        # Normalize items
        normalized = []
        for i, item in enumerate(items):
            if isinstance(item, str):
                item = {"response_text": item}
            
            normalized.append({
                "query_id": item.get("query_id", f"q_{i}"),
                "query_text": item.get("query", item.get("question", "")),
                "response_text": item.get("response", item.get("answer", item.get("text", ""))),
                "citations": item.get("citations", []),
                "metadata": item.get("metadata", {}),
            })
        
        return normalized
    
    def _parse_paste(self, data: str) -> List[Dict[str, Any]]:
        """Parse pasted text data."""
        items = []
        blocks = data.strip().split("\n\n")
        
        current_query = None
        current_response_lines = []
        
        for block in blocks:
            lines = block.strip().split("\n")
            if not lines:
                continue
            
            first_line = lines[0].strip()
            
            # Check if this starts a new Q&A pair
            is_query = False
            query_prefixes = ["Q:", "Query:", "问:", "Question:", "查询:"]
            
            for prefix in query_prefixes:
                if first_line.lower().startswith(prefix.lower()):
                    is_query = True
                    query_text = first_line[len(prefix):].strip()
                    break
            
            if is_query:
                # Save previous item
                if current_query:
                    items.append({
                        "query_id": f"q_{len(items)}",
                        "query_text": current_query,
                        "response_text": "\n".join(current_response_lines),
                        "citations": [],
                        "metadata": {},
                    })
                
                current_query = query_text
                current_response_lines = lines[1:] if len(lines) > 1 else []
            else:
                # Add to current response
                current_response_lines.extend(lines)
        
        # Save last item
        if current_query:
            items.append({
                "query_id": f"q_{len(items)}",
                "query_text": current_query,
                "response_text": "\n".join(current_response_lines),
                "citations": [],
                "metadata": {},
            })
        elif current_response_lines:
            # No structured Q&A, treat as single response
            items.append({
                "query_id": "q_0",
                "query_text": "",
                "response_text": "\n".join(current_response_lines),
                "citations": [],
                "metadata": {},
            })
        
        return items
