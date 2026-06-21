# ZaminSaathi — Agent Constitution

## What This Project Is
ZaminSaathi is a three-agent AI system that helps rural Karnataka 
families understand their land documents (RTC, Mutation Extract, 
Survey Sketch) and know what to do next.

## Tech Stack
- Agent Framework: Google ADK (Agent Development Kit)
- MCP Server: Python (serves synthetic land records database)
- Backend: Python / Flask
- Database: PostgreSQL
- Frontend: React
- Deployment: Docker Compose
- Build Environment: Antigravity IDE

## Project Structure
zaminsaathi/
├── agents/          # Three ADK agents
├── mcp_server/      # MCP server + synthetic database
├── skills/          # Agent Skills (RTC, Mutation, Survey)
├── security/        # Permission checks + audit logs
├── frontend/        # React UI
├── sample_docs/     # Synthetic land documents for demo
└── docker/          # Docker Compose config

## Three Agents — Their Jobs
- Agent 1 (Parser): Reads a document, explains every field in 
  plain English
- Agent 2 (Detector): Cross-checks documents against each other 
  AND the MCP database, flags discrepancies
- Agent 3 (Planner): Generates next steps — which office, 
  which portal, what to file

## Hard Rules — Never Break These
1. Never give legal advice. Always say "consult a lawyer for 
   final decisions"
2. Never store real user documents. Demo uses synthetic data only
3. Security has TWO separate layers — never mix them:
   - Permission check = BEFORE Agent 2 acts (access control)
   - Audit log = AFTER Agent 2 acts (append-only record)
4. Never hardcode API keys or passwords anywhere
5. Agent Skills load on demand only — never preload all three
6. Kannada output only if manually verified — default is English

## What "Done" Means For Each Feature
- Multi-agent: Agents actually pass state to each other
- MCP Server: Agent 2 actually queries it to cross-check
- Security: Permission check actually gates Agent 2's actions
- Skills: Each skill loads ONLY when that document type detected
- Docker: One command starts everything