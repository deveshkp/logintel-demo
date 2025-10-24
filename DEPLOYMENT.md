# Deployment and Hosting Guide

## Architecture Overview

### Components
1. **Frontend (UI)**
   - Technology: React
   - Hosting: Firebase Hosting
   - URL: https://your-project-id.web.app
   - Directory: `/ui`

2. **Backend (MCP Server)**
   - Technology: FastAPI
   - Hosting: Firebase Cloud Functions
   - URL: https://your-project-id.web.app/api
   - Directory: `/mcp_server`

3. **Database (Elasticsearch & Kibana)**
   - Hosting: Elastic Cloud (recommended) or self-hosted
   - Access: Secure VPC connection
   - Configuration: Via environment variables

## Deployment Steps

### 1. Elasticsearch & Kibana Setup
```bash
# Option 1: Elastic Cloud (Recommended)
1. Sign up for Elastic Cloud
2. Create a deployment
3. Note down the connection details:
   - Elasticsearch URL
   - Kibana URL
   - API keys

# Option 2: Self-hosted
1. Set up VMs on your preferred cloud provider
2. Deploy using provided docker-compose.prod.yml
3. Configure security and networking
```

### 2. Firebase Project Setup
```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login to Firebase
firebase login

# Initialize Firebase project
firebase init

# Configure environment variables
firebase functions:config:set \
  elasticsearch.url="YOUR_ES_URL" \
  kibana.url="YOUR_KIBANA_URL" \
  gemini.api_key="YOUR_GEMINI_KEY"
```

### 3. Frontend Deployment
```bash
# Build the React app
cd ui
npm run build

# Deploy to Firebase Hosting
firebase deploy --only hosting
```

### 4. Backend Deployment
```bash
# Deploy the MCP server as Firebase Function
firebase deploy --only functions
```

## Production Environment Variables

Create a `.env.production` file in the UI directory:
```env
REACT_APP_MCP_SERVER_URL=https://your-project-id.web.app/api
```

Set Firebase Functions configuration:
```bash
firebase functions:config:set \
  elasticsearch.url="https://your-es-cluster.cloud.es.io" \
  kibana.url="https://your-kibana.cloud.es.io" \
  gemini.api_key="your-api-key" \
  allowed_index_patterns="logs-*"
```

## Security Considerations

1. **Firebase Security Rules**
   - Configure proper authentication rules
   - Restrict function access to authenticated users

2. **Elasticsearch Security**
   - Use API keys for authentication
   - Configure IP allowlisting
   - Enable SSL/TLS encryption

3. **CORS Configuration**
   - Configure allowed origins in MCP server
   - Set up proper Firebase security headers

## Monitoring and Maintenance

1. **Firebase Monitoring**
   - Use Firebase Console for hosting metrics
   - Monitor Cloud Functions performance
   - Set up error alerting

2. **Elasticsearch Monitoring**
   - Monitor cluster health
   - Set up index lifecycle management
   - Configure alerting for capacity issues

3. **Application Monitoring**
   - Implement application logging
   - Set up error tracking
   - Monitor API performance

## Scaling Considerations

1. **Frontend**
   - Firebase Hosting scales automatically
   - Implement caching strategies
   - Use CDN for static assets

2. **Backend**
   - Firebase Functions auto-scale
   - Implement proper connection pooling
   - Cache frequently used queries

3. **Elasticsearch**
   - Monitor resource usage
   - Scale cluster as needed
   - Implement proper index management

## Backup and Disaster Recovery

1. **Elasticsearch Data**
   - Configure automated snapshots
   - Store snapshots in secure location
   - Test recovery procedures

2. **Application Code**
   - Maintain version control
   - Store secrets securely
   - Document deployment procedures