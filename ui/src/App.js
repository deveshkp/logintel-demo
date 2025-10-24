import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Send, ExternalLink, Database } from 'lucide-react';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      // Process query using MCP server tools
      const response = await processQuery(inputMessage);

      const assistantMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: response.answer,
        kibanaLink: response.kibanaLink,
        dsl: response.dsl,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: 'Sorry, I encountered an error processing your query. Please try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Process query using MCP server tools
  const processQuery = async (query) => {
    const mcpServerUrl = process.env.REACT_APP_MCP_SERVER_URL || 'http://localhost:8000';

    // Helper function to parse time range from query
    const parseTimeRange = (query) => {
      const queryLower = query.toLowerCase();
      
      // Check if this is a "total" query that shouldn't have time filtering
      if (queryLower.includes('total') || queryLower.includes('all') || queryLower.includes('overall')) {
        return null; // No time filter for total queries
      }
      
      // Parse time ranges
      if (queryLower.includes('24 hour') || queryLower.includes('last 24') || queryLower.includes('24h') || queryLower.includes('24 hr')) {
        return 'last_24h';
      } else if (queryLower.includes('last hour') || queryLower.includes('1 hour') || queryLower.includes('hour')) {
        return 'last_hour';
      } else if (queryLower.includes('today')) {
        return 'today';
      } else {
        return 'last_hour'; // default for time-filtered queries
      }
    };

    // Helper function to get date range for DSL queries
    const getDateRangeForDSL = (timeRange) => {
      const now = new Date();
      switch (timeRange) {
        case 'today':
          const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
          const endOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
          return { gte: startOfDay.toISOString(), lt: endOfDay.toISOString() };
        case 'last_hour':
          const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
          return { gte: oneHourAgo.toISOString(), lte: now.toISOString() };
        case 'last_24h':
          const twentyFourHoursAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
          return { gte: twentyFourHoursAgo.toISOString(), lte: now.toISOString() };
        default:
          return { gte: new Date(now.getTime() - 60 * 60 * 1000).toISOString(), lte: now.toISOString() };
      }
    };

    try {
      // Use Gemini AI for natural language query interpretation
      const geminiResponse = await axios.post(`${mcpServerUrl}/tools/interpret_query`, {
        query: query
      });

      const structuredQuery = geminiResponse.data.result.structured_query;
      const timeRange = structuredQuery.time_range;
      const filters = structuredQuery.filters || {};
      const queryType = structuredQuery.query_type || 'count';
      const description = structuredQuery.description || query;

      // Build DSL query from structured parameters
      let dslQuery = {};
      let kibanaLink = null;
      let answer = '';
      let kqlQuery = '';

      // Build must clauses from filters
      const mustClauses = [];
      for (const [field, value] of Object.entries(filters)) {
        if (field === '@timestamp' && typeof value === 'object') {
          mustClauses.push({"range": {"@timestamp": value}});
        } else {
          mustClauses.push({"term": {[field]: value}});
        }
      }

      // Add time range filter if specified
      if (timeRange && timeRange !== 'null') {
        mustClauses.push({"range": {"@timestamp": getDateRangeForDSL(timeRange)}});
      }

      // Determine index pattern based on query content
      let indexPattern = 'logs-*'; // Default
      if (query.toLowerCase().includes('auth') || query.toLowerCase().includes('login')) {
        indexPattern = 'logs-auth-*';
      } else if (query.toLowerCase().includes('payment')) {
        indexPattern = 'logs-payment-*';
      } else if (query.toLowerCase().includes('mobile')) {
        indexPattern = 'logs-mobile-*';
      }

      if (queryType === 'greeting') {
        // Handle greetings
        answer = `Hello! 👋 I'm LogWell, your log analytics assistant. I can help you analyze your banking system logs.\n\nTry asking me questions like:\n\n• "How many failed logins were there today?"\n• "Show me mobile authentication failures in the last 24 hours"\n• "What are the payment processing errors?"\n\nWhat would you like to know about your logs?`;
        kibanaLink = null;
        dslQuery = null;

      } else if (queryType === 'help') {
        // Handle help requests
        answer = `I'm here to help you analyze your banking system logs! 📊\n\nI can answer questions about:\n\n🔐 **Authentication & Logins**\n• Failed/successful login attempts\n• Mobile, online, and IVR channels\n• Time-based analysis (today, yesterday, last 24 hours, etc.)\n\n💳 **Payment Processing**\n• Transaction successes and failures\n• Payment methods and channels\n• Error analysis and trends\n\n📱 **App Channels**\n• Mobile app activity\n• Online banking usage\n• IVR system interactions\n\n💡 **Example Queries:**\n• "failed logins on mobile today"\n• "total payment failures yesterday"\n• "authentication errors in last 24 hours"\n• "successful transactions by channel"\n\nWhat would you like to explore?`;
        kibanaLink = null;
        dslQuery = null;

      } else if (queryType === 'count') {
        // Count query with aggregations
        dslQuery = {
          "query": {
            "bool": {
              "must": mustClauses
            }
          },
          "size": 0,
          "aggs": {
            "total_count": {"value_count": {"field": "event.action"}},
            "by_channel": {"terms": {"field": "app.channel"}},
            "by_outcome": {"terms": {"field": "event.outcome"}}
          }
        };

        // Execute the query
        const queryResponse = await axios.post(`${mcpServerUrl}/tools/execute_es_query`, {
          index: indexPattern,
          dsl: dslQuery
        });

        const totalCount = queryResponse.data.result.aggregations?.total_count?.value || 0;
        const channels = queryResponse.data.result.aggregations?.by_channel?.buckets || [];
        const outcomes = queryResponse.data.result.aggregations?.by_outcome?.buckets || [];

        // Build human-readable answer
        const timeDesc = timeRange === 'today' ? 'today' :
                        timeRange === 'last_24h' ? 'last 24 hours' :
                        timeRange === 'last_hour' ? 'last hour' :
                        timeRange === 'yesterday' ? 'yesterday' :
                        timeRange === 'last_week' ? 'last week' : 'all time';

        answer = `${description}\n\n**${totalCount}** events found in the ${timeDesc}.`;

        if (channels.length > 0) {
          answer += `\n\nBreakdown by channel:\n${channels.map(c => `- ${c.key}: ${c.doc_count}`).join('\n')}`;
        }

        if (outcomes.length > 0) {
          answer += `\n\nBreakdown by outcome:\n${outcomes.map(c => `- ${c.key}: ${c.doc_count}`).join('\n')}`;
        }

        // Generate Kibana link
        kqlQuery = Object.entries(filters).map(([field, value]) => `${field}:"${value}"`).join(' AND ');
        if (!kqlQuery) {
          kqlQuery = '*'; // Match all if no specific filters
        }

        const kibanaResponse = await axios.post(`${mcpServerUrl}/tools/create_kibana_link`, {
          index_pattern: indexPattern,
          time_range: timeRange || 'all_time',
          kql_query: kqlQuery
        });
        kibanaLink = kibanaResponse.data.result.kibana_link;

      } else {
        // Default response for unsupported query types
        answer = `I understood your query as: "${description}"\n\nHowever, I can currently only handle count queries. Try asking about:\n\n• Failed logins (mobile, online, ivr)\n• Authentication events\n• Payment processing\n• App channel activity\n\nFor example: "how many failed logins today" or "show me authentication failures in last 24 hours"`;
      }

      return {
        answer,
        kibanaLink,
        dsl: JSON.stringify(dslQuery, null, 2),
        interpreted_query: structuredQuery
      };

    } catch (error) {
      console.error('MCP Server error:', error);
      throw new Error(`Failed to process query: ${error.response?.data?.detail || error.message}`);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <Database className="header-icon" />
          <h1>LogWell</h1>
          <p>Ask questions about your banking system logs</p>
        </div>
      </header>

      <div className="chat-container">
        <div className="messages-container">
          {messages.length === 0 && (
            <div className="welcome-message">
              <h2>Welcome to LogWell</h2>
              <p>Try asking questions like:</p>
              <ul>
                <li>"How many failed logins were there on mobile today?"</li>
                <li>"Show me payment failures from iOS devices"</li>
                <li>"What were the most common errors last hour?"</li>
              </ul>
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id} className={`message ${message.type}`}>
              <div className="message-content">
                <div className="message-text" dangerouslySetInnerHTML={{ __html: message.content }} />

                {message.kibanaLink && (
                  <div className="message-actions">
                    <a
                      href={message.kibanaLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="kibana-button"
                    >
                      <ExternalLink size={16} />
                      Open in Kibana
                    </a>
                  </div>
                )}

                {message.dsl && (
                  <details className="dsl-details">
                    <summary>View DSL Query</summary>
                    <pre className="dsl-code">{message.dsl}</pre>
                  </details>
                )}
              </div>
              <div className="message-timestamp">
                {message.timestamp.toLocaleTimeString()}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="message assistant loading">
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={sendMessage} className="input-form">
          <div className="input-container">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask about banking logs..."
              disabled={isLoading}
              className="message-input"
            />
            <button
              type="submit"
              disabled={!inputMessage.trim() || isLoading}
              className="send-button"
            >
              <Send size={20} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default App;