"""
Gemini NLP Tool
Uses Google Gemini AI for natural language query interpretation
"""

import json
import logging
import os
from typing import Dict, Any, Optional
import google.generativeai as genai
from .base import MCPTool
from . import tool_registry

logger = logging.getLogger(__name__)

class GeminiNLPQueryTool(MCPTool):
    """Tool to interpret natural language queries using Google Gemini AI"""

    name = "interpret_query"
    description = "Interpret natural language banking log queries and convert to structured search parameters"

    def __init__(self):
        from ..main import GEMINI_API_KEY
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        genai.configure(api_key=GEMINI_API_KEY)

        preferred_models = []
        if os.getenv("GEMINI_MODEL_NAME"):
            preferred_models.append(os.getenv("GEMINI_MODEL_NAME"))
        preferred_models.extend([
            "gemini-2.0-flash-exp",  # Gemini 2.5 Pro
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-pro"
        ])

        selected_model = None
        try:
            available_models = list(genai.list_models())
            generate_capable = {
                model.name.replace("models/", ""): model.name
                for model in available_models
                if hasattr(model, "supported_generation_methods") and "generateContent" in model.supported_generation_methods
            }

            for candidate in preferred_models:
                if candidate in generate_capable:
                    selected_model = generate_capable[candidate]
                    break

            if not selected_model and generate_capable:
                selected_model = next(iter(generate_capable.values()))

        except Exception as list_error:
            logger.warning(f"Unable to list Gemini models: {list_error}")

        if not selected_model:
            selected_model = preferred_models[0]

        logger.info(f"Initializing Gemini model '{selected_model}'")
        self.model = genai.GenerativeModel(selected_model)

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Interpret natural language query using Gemini AI with fallback"""
        user_query = args.get('query', '').strip()
        if not user_query:
            raise ValueError("Query is required")

        try:
            # Try Gemini AI first
            structured_query = await self._try_gemini_interpretation(user_query)
            return {
                "original_query": user_query,
                "structured_query": structured_query,
                "interpreted_by": "gemini_ai",
                "confidence": structured_query.get('confidence', 0.5)
            }
        except Exception as e:
            logger.warning(f"Gemini AI failed: {e}, falling back to basic parsing")
            # Fallback to basic string matching
            fallback_query = self._basic_query_parsing(user_query)
            return {
                "original_query": user_query,
                "structured_query": fallback_query,
                "interpreted_by": "basic_fallback",
                "confidence": 0.3,
                "error": str(e)
            }

    async def _try_gemini_interpretation(self, user_query: str) -> Dict[str, Any]:
        """Try to interpret query with Gemini AI"""
        # Get schema information for context
        from .schema import GetSchemaTool
        schema_tool = GetSchemaTool()
        schema_result = await schema_tool.execute({"index_pattern": "logs-*"})
        available_fields = schema_result.get('schema', {})

        # Get dictionary for field synonyms
        from .dictionary import GetDictionaryTool
        dict_tool = GetDictionaryTool()
        dict_result = await dict_tool.execute({"index_pattern": "logs-*"})
        field_synonyms = dict_result.get('dictionary', {})

        # Create context for Gemini
        context = self._build_context(available_fields, field_synonyms)

        # Generate structured query using Gemini
        return await self._interpret_query_with_gemini(user_query, context)

    def _basic_query_parsing(self, query: str) -> Dict[str, Any]:
        """Fallback basic string matching for query interpretation"""
        query_lower = query.lower().strip()
        
        # Check for greetings and non-query inputs
        greetings = ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening', 'howdy', 'sup', 'yo']
        if query_lower in greetings or len(query_lower.split()) <= 2 and any(word in greetings for word in query_lower.split()):
            return {
                "time_range": None,
                "query_type": "greeting",
                "filters": {},
                "description": f"Greeting: {query}",
                "confidence": 0.9
            }
        
        # Check for other non-query inputs
        if len(query_lower) < 3 or query_lower in ['?', 'help', 'what', 'how', 'can you']:
            return {
                "time_range": None,
                "query_type": "help",
                "filters": {},
                "description": f"Help request: {query}",
                "confidence": 0.8
            }

        # Determine time range
        time_range = None
        if 'today' in query_lower:
            time_range = 'today'
        elif 'yesterday' in query_lower:
            time_range = 'yesterday'
        elif '24 hour' in query_lower or '24 hr' in query_lower or 'last 24' in query_lower:
            time_range = 'last_24h'
        elif 'hour' in query_lower:
            time_range = 'last_hour'
        elif 'week' in query_lower:
            time_range = 'last_week'
        # If no time mentioned, assume "total" (all time)

        # Determine filters based on keywords - only use fields that exist
        filters = {}
        if 'failed' in query_lower or 'failure' in query_lower:
            filters['event.outcome'] = 'failure'
        if 'success' in query_lower or 'successful' in query_lower:
            filters['event.outcome'] = 'success'
        if 'mobile' in query_lower:
            filters['app.channel'] = 'mobile'
        if 'online' in query_lower:
            filters['app.channel'] = 'online'
        if 'ivr' in query_lower:
            filters['app.channel'] = 'ivr'
        
        # Add specific event action filters for login-related queries
        if 'login' in query_lower:
            filters['event.action'] = 'user_login'

        # Determine query type
        query_type = 'count'  # Default to count

        # Create description
        time_desc = "all time" if time_range is None else time_range.replace('_', ' ')
        filter_desc = ', '.join([f"{k}={v}" for k, v in filters.items()])
        description = f"Count of events with {filter_desc} in {time_desc}" if filter_desc else f"Count of all events in {time_desc}"

        return {
            "time_range": time_range,
            "query_type": query_type,
            "filters": filters,
            "description": description,
            "confidence": 0.3
        }

    def _build_context(self, available_fields: Dict, field_synonyms: Dict) -> str:
        """Build context string for Gemini with available fields and examples"""
        context_parts = []

        # Add available fields
        context_parts.append("Available Elasticsearch fields:")
        for field, info in available_fields.items():
            field_type = info.get('type', 'unknown')
            description = info.get('description', '')
            context_parts.append(f"- {field} ({field_type}): {description}")

        # Add field synonyms
        if field_synonyms:
            context_parts.append("\nField synonyms/aliases:")
            for field, synonyms in field_synonyms.items():
                if synonyms:
                    context_parts.append(f"- {field}: {', '.join(synonyms)}")

        # Add query examples
        context_parts.append("""
Common query patterns:
- "failed logins today" → time_range: "today", filters: {"event.outcome": "failure", "event.action": "user_login"}
- "mobile login failures in last 24 hours" → time_range: "last_24h", filters: {"event.outcome": "failure", "app.channel": "mobile", "event.action": "user_login"}
- "total failed payments" → time_range: null (all time), filters: {"event.outcome": "failure", "event.action": "payment"}
- "successful logins on ivr yesterday" → time_range: "yesterday", filters: {"event.outcome": "success", "app.channel": "ivr", "event.action": "user_login"}
""")

        return "\n".join(context_parts)

    async def _interpret_query_with_gemini(self, query: str, context: str) -> Dict[str, Any]:
        """Use Gemini to interpret the natural language query"""

        prompt = f"""
You are an expert at interpreting banking system log queries. Convert natural language queries into structured search parameters for Elasticsearch.

Context:
{context}

Instructions:
1. Identify the time range (today, yesterday, last_hour, last_24h, last_week, or null for all time)
2. Identify the main event/action being queried
3. Identify any filters (channel, outcome, category, etc.)
4. Determine if this is a count query or data retrieval query
5. Return a JSON object with the structured parameters

Query: "{query}"

Return ONLY a valid JSON object with this structure:
{{
  "time_range": "today|last_hour|last_24h|yesterday|last_week|null",
  "query_type": "count|search",
  "filters": {{"field": "value", ...}},
  "description": "human readable description",
  "confidence": 0.0-1.0
}}

Examples:
Input: "failed logins today"
Output: {{"time_range": "today", "query_type": "count", "filters": {{"event.outcome": "failure", "event.action": "user_login"}}, "description": "Count of failed login events today", "confidence": 0.95}}

Input: "mobile login failures in last 24 hours"
Output: {{"time_range": "last_24h", "query_type": "count", "filters": {{"event.outcome": "failure", "app.channel": "mobile", "event.action": "user_login"}}, "description": "Count of failed mobile login events in last 24 hours", "confidence": 0.9}}

Input: "total failed payments"
Output: {{"time_range": null, "query_type": "count", "filters": {{"event.outcome": "failure", "event.action": "payment"}}, "description": "Total count of failed payment events", "confidence": 0.85}}
"""

        try:
            response = await self.model.generate_content_async(prompt)
            response_text = response.text.strip()

            # Clean up response (remove markdown code blocks if present)
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            # Parse JSON response
            structured_query = json.loads(response_text)

            # Validate required fields
            required_fields = ['time_range', 'query_type', 'filters', 'description', 'confidence']
            for field in required_fields:
                if field not in structured_query:
                    raise ValueError(f"Missing required field: {field}")

            return structured_query

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {response_text}")
            raise ValueError(f"Invalid JSON response from Gemini: {e}")
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

@tool_registry.register
class InterpretQueryTool(GeminiNLPQueryTool):
    """Registered Gemini NLP query interpretation tool"""
    pass