"""
Get Schema MCP Tool
Retrieves Elasticsearch index schema and metadata
"""

from typing import Dict, Any, Optional, List
from elasticsearch import Elasticsearch
import logging
from .base import MCPTool
from . import tool_registry

logger = logging.getLogger(__name__)

class GetSchemaTool(MCPTool):
    """Tool to get Elasticsearch schema and metadata"""

    name = "get_schema"
    description = "Get Elasticsearch schema and metadata for an index pattern"

    def __init__(self):
        # Avoid circular import by getting ES config at runtime
        import os
        es_url = os.getenv("ES_URL", "http://elasticsearch:9200")
        es_username = os.getenv("ES_USERNAME", "")
        es_password = os.getenv("ES_PASSWORD", "")
        
        self.es = Elasticsearch(
            es_url,
            basic_auth=(es_username, es_password) if es_username else None,
            verify_certs=False
        )

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get schema and metadata for an index pattern"""
        self.validate_input(args, ['index_pattern'])
        index_pattern = args['index_pattern']

        self.validate_index_pattern(index_pattern)

        try:
            # Try to get data streams first
            data_streams = self._get_matching_data_streams(index_pattern)
            if data_streams:
                schema = self._extract_schema_from_data_streams(data_streams, index_pattern)
            else:
                # Fall back to regular indices
                mapping_response = self.es.indices.get_mapping(index=index_pattern)
                schema = self._extract_schema_with_meta(mapping_response, index_pattern)

            self.log_execution(self.name, args, schema)
            return schema

        except Exception as e:
            logger.error(f"Error getting schema for {index_pattern}: {e}")
            raise

    def _get_matching_data_streams(self, index_pattern: str) -> List[Dict[str, Any]]:
        """Get data streams that match the pattern"""
        try:
            # Get all data streams
            data_streams_response = self.es.indices.get_data_stream()
            all_data_streams = data_streams_response.get('data_streams', [])
            
            # Filter by pattern
            matching_streams = []
            for ds in all_data_streams:
                ds_name = ds['name']
                if self._matches_pattern(ds_name, index_pattern):
                    matching_streams.append(ds)
            
            return matching_streams
        except Exception:
            return []

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Simple pattern matching for data stream names"""
        import fnmatch
        return fnmatch.fnmatch(name, pattern)

    def _extract_schema_from_data_streams(self, data_streams: List[Dict[str, Any]], index_pattern: str) -> Dict[str, Any]:
        """Extract schema from data streams"""
        schema = {
            "index_pattern": index_pattern,
            "fields": {},
            "meta": {
                "default_time_field": "@timestamp",
                "primary_facets": ["event.outcome", "event.action", "app.channel"],
                "examples": ["failed login on mobile"]
            }
        }

        # Get mapping from the first data stream's backing index
        if data_streams:
            ds_name = data_streams[0]['name']
            backing_indices = data_streams[0].get('indices', [])
            if backing_indices:
                index_name = backing_indices[0]['index_name']
                try:
                    mapping_response = self.es.indices.get_mapping(index=index_name)
                    # Extract fields from mapping
                    for index_name, index_data in mapping_response.items():
                        mappings = index_data.get('mappings', {})
                        properties = mappings.get('properties', {})
                        for field_name, field_info in properties.items():
                            if field_name not in ['message']:  # Exclude PII fields
                                schema['fields'][field_name] = {
                                    "type": field_info.get("type", "unknown"),
                                    "description": field_info.get("description", ""),
                                    "examples": field_info.get("examples", [])
                                }
                except Exception as e:
                    logger.warning(f"Could not get mapping for {index_name}: {e}")

        return schema

    def _extract_schema_with_meta(self, mapping_response: Dict[str, Any], index_pattern: str) -> Dict[str, Any]:
        """Extract curated schema with _meta information"""
        schema = {
            "index_pattern": index_pattern,
            "fields": {},
            "meta": {}
        }

        # Process each index in the pattern
        for index_name, index_data in mapping_response.items():
            mappings = index_data.get('mappings', {})

            # Extract _meta information
            if '_meta' in mappings:
                schema['meta'] = mappings['_meta']

            # Extract field mappings
            properties = mappings.get('properties', {})
            for field_name, field_info in properties.items():
                if field_name not in ['message']:  # Exclude PII fields
                    schema['fields'][field_name] = {
                        "type": field_info.get("type", "unknown"),
                        "description": field_info.get("description", ""),
                        "examples": field_info.get("examples", [])
                    }

        return schema