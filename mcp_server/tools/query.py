"""
Execute ES Query MCP Tool
Executes Elasticsearch DSL queries with safety validations
"""

from typing import Dict, Any, Optional
from elasticsearch import Elasticsearch, NotFoundError, RequestError
from fastapi import HTTPException
import logging
from .base import MCPTool
from . import tool_registry

logger = logging.getLogger(__name__)

class ExecuteESQueryTool(MCPTool):
    """Tool to execute Elasticsearch DSL queries"""

    name = "execute_es_query"
    description = "Execute Elasticsearch DSL query with safety validations"

    def __init__(self):
        from ..main import ES_URL, ES_USERNAME, ES_PASSWORD, MAX_RESULT_SIZE
        self.es = Elasticsearch(
            ES_URL,
            basic_auth=(ES_USERNAME, ES_PASSWORD) if ES_USERNAME else None,
            verify_certs=False
        )
        self.max_result_size = MAX_RESULT_SIZE

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Elasticsearch DSL query"""
        self.validate_input(args, ['index', 'dsl'])
        index = args['index']
        dsl = args['dsl']

        self.validate_index_pattern(index)
        self._validate_query_safety(dsl)

        try:
            # Extract size from DSL or use default
            query_size = dsl.pop('size', self.max_result_size)
            query_size = min(query_size, self.max_result_size)
            
            # Execute the query
            response = self.es.search(
                index=index,
                body=dsl,
                size=query_size
            )

            # Process and sanitize response
            result = self._process_query_response(response)

            self.log_execution(self.name, args, result)
            return result

        except NotFoundError:
            raise HTTPException(status_code=404, detail=f"Index '{index}' not found")
        except RequestError as e:
            logger.error(f"Invalid DSL query: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid query structure: {str(e)}")
        except Exception as e:
            logger.error(f"Error executing ES query: {e}")
            raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")

    def _validate_query_safety(self, dsl: Dict[str, Any]) -> None:
        """Validate query for safety and compliance"""
        # Check for forbidden operations
        if 'script' in str(dsl).lower():
            raise ValueError("Script operations not allowed")

        # Check for overly broad queries
        query = dsl.get('query', {})
        if not query or query == {"match_all": {}}:
            # Allow match_all only with size limits
            if dsl.get('size', 0) > 10:
                raise ValueError("Broad queries limited to 10 results")
            
        # Ensure time ranges are consistent
        self._normalize_time_range(dsl)

        # Validate aggregations don't exceed limits
        aggs = dsl.get('aggs', {})
        if len(aggs) > 5:
            raise ValueError("Maximum 5 aggregations per query")

    def _normalize_time_range(self, dsl: Dict[str, Any]) -> None:
        """Normalize time ranges to be consistent"""
        query = dsl.get('query', {})
        if isinstance(query, dict):
            # Handle bool queries
            if 'bool' in query:
                must_clauses = query['bool'].get('must', [])
                for clause in must_clauses:
                    if isinstance(clause, dict) and 'range' in clause:
                        self._convert_relative_time(clause['range'])
            # Handle direct range queries
            elif 'range' in query:
                self._convert_relative_time(query['range'])

    def _convert_relative_time(self, range_query: Dict[str, Any]) -> None:
        """Convert relative time ranges to absolute for consistency"""
        if '@timestamp' in range_query:
            timestamp_range = range_query['@timestamp']
            if isinstance(timestamp_range, dict):
                for key in ['gte', 'gt', 'lte', 'lt']:
                    if key in timestamp_range and str(timestamp_range[key]).startswith('now'):
                        # Convert 'now' ranges to explicit dates for consistency
                        from datetime import datetime, timedelta
                        now = datetime.now()
                        if timestamp_range[key] == 'now-1h':
                            timestamp_range[key] = (now - timedelta(hours=1)).isoformat()
                        elif timestamp_range[key] == 'now':
                            timestamp_range[key] = now.isoformat()
                        elif timestamp_range[key] == 'now/d':
                            timestamp_range[key] = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    def _process_query_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process and sanitize Elasticsearch response"""
        result = {
            "took": response.get("took", 0),
            "timed_out": response.get("timed_out", False),
            "total": response["hits"]["total"]["value"] if "hits" in response else 0,
            "hits": [],
            "aggregations": {}
        }

        # Process hits (with PII filtering)
        if "hits" in response:
            for hit in response["hits"]["hits"][:self.max_result_size]:
                # Remove sensitive fields
                source = hit.get("_source", {})
                safe_source = {k: v for k, v in source.items() if k != "message"}
                result["hits"].append({
                    "_index": hit["_index"],
                    "_id": hit["_id"],
                    "_score": hit.get("_score"),
                    "_source": safe_source
                })

        # Include aggregations if present
        if "aggregations" in response:
            result["aggregations"] = response["aggregations"]
            # For count queries, use total_count aggregation
            if "total_count" in response["aggregations"]:
                result["count"] = response["aggregations"]["total_count"]["value"]
            # Backward compatibility for older count aggregation
            elif "count" in response["aggregations"]:
                result["count"] = response["aggregations"]["count"]["value"]
            
            # Use hits total if no specific count aggregation
            if "count" not in result:
                result["count"] = result["total"]

        return result