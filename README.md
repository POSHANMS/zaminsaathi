# ZaminSaathi — AI Land Document Analysis

### *ನಿಮ್ಮ ಜಮೀನು, ನಿಮ್ಮ ಹಕ್ಕು (Your Land, Your Right)*
**Free AI-powered guidance for rural Karnataka families to understand their land documents and know their next steps.**

---

## 📌 Problem

In rural Karnataka, millions of families rely on land as their primary source of livelihood and wealth. However, the official land documents—such as the **RTC (Record of Rights, Tenancy and Crops)**, **Mutation Extracts**, and **Survey Sketches**—are written in complex legal Kannada or technical formats that are extremely difficult for laypeople to decipher. 

This information asymmetry leads to:
* **Exploitation:** Families are often forced to rely on middlemen, brokers, or corrupt local officials to explain their own records.
* **Land Disputes:** Mismatches between different records (e.g., a survey number typo in a mutation register vs. an RTC) go unnoticed for years, only to surface during sales or inheritance, resulting in decade-long court battles.
* **Personal Story Angle:** ZaminSaathi was born out of a real family land dispute in **Hassan, Karnataka**, where a simple survey number discrepancy between a mutation document and the official RTC remained unresolved for 12 years, freezing the family's assets and incurring massive legal expenses. ZaminSaathi aims to ensure no other family has to go through this.

---

## 💡 Solution

**ZaminSaathi** is a three-agent AI system built on the Google **Agent Development Kit (ADK)**. It empowers families to instantly upload their land documents and receive a comprehensive analysis that explains, detects, and plans:
1. **Parser Agent (Agent 1):** Reads the document, decodes complex legal jargon, and explains every field (e.g., land classification, owner details, encumbrances) in plain English.
2. **Detector Agent (Agent 2):** Performs permission-gated cross-checks across all uploaded documents and queries the official **MCP Land Records Database** to flag any inconsistencies or discrepancies.
3. **Planner Agent (Agent 3):** Generates a concrete, customized action plan guiding the family on exactly which government office to visit, which portal to check, what documents to bring, and even a draft script of what to say to the officer.

---

## 🏗️ Architecture

The multi-agent execution pipeline flows linearly from document parsing to report generation, backed by a secure data layer:

```
                                  +-----------------------+
                                  |  User Uploads JSON/   |
                                  |  Scan Land Document   |
                                  +-----------+-----------+
                                              |
                                              v
                                  +-----------+-----------+
                                  |    Agent 1: Parser    |
                                  | (Loads specific skill)|
                                  +-----------+-----------+
                                              |
                                              v
      +--------------------+      +-----------+-----------+      +--------------------+
      |  Permissions Gate  |      |   Agent 2: Detector   |      |  Append-Only Log   |
      |  (permissions.py)  +----->| (Queries MCP Server via|----->|   (audit_log.py)   |
      |  Checks BEFORE act |      |   FastMCP Database)   |      |  Records AFTER act |
      +--------------------+      +-----------+-----------+      +--------------------+
                                              |
                                              v
                                  +-----------+-----------+
                                  |    Agent 3: Planner   |
                                  | (Generates roadmap &  |
                                  |     officer script)   |
                                  +-----------+-----------+
                                              |
                                              v
                                  +-----------+-----------+
                                  |  Interactive HTML/JS  |
                                  |  Redesign Dashboard   |
                                  +-----------------------+
```

### 🔒 Security Design (Separation of Concerns)
Security is implemented using two entirely decoupled layers to ensure strict access control and auditing:
1. **Permission Check (Before Agent 2 Acts):** Governed by `security/permissions.py`. Before the Detector Agent is allowed to cross-reference records or query the database, it must query the permission gate. If authorization is not granted, the agent halts.
2. **Audit Logging (After Agent 2 Acts):** Governed by `security/permissions.py` (which handles the logging interface) and stored in `audit_log.jsonl`. This is an append-only transaction ledger that logs every cross-check, database query, and discrepancy flagged. The agent cannot modify or erase this file.

### 🧠 Agent Skills On-Demand Loading
To minimize token usage and optimize latency, specialized skills are not preloaded. Instead, they load dynamically only when the Parser Agent detects the specific document type:
* **`rtc-skill`:** Loaded when an RTC document is parsed.
* **`mutation-skill`:** Loaded when a Mutation Extract is parsed.
* **`survey-skill`:** Loaded when a Survey Sketch is parsed.

---

## 🤖 Agent Concepts Demonstrated

ZaminSaathi demonstrates six fundamental agentic software concepts:

1. **Multi-Agent Systems (ADK):** Shows how separate, highly specialized LLM agents can pass state, orchestrate tasks sequentially, and collaborate to solve a complex legal problem.
2. **Model Context Protocol (MCP) Server:** Integrates a Python FastMCP server representing a synthetic government land records database, showcasing how agents can securely query external state.
3. **Antigravity IDE Integration:** Developed, refined, and packaged inside the Antigravity IDE workspace, utilizing advanced agentic development workflows.
4. **Security Features (Separation of Concerns):** Employs distinct pre-action permission gating and post-action append-only auditing, simulating enterprise-grade zero-trust patterns.
5. **Deployability:** Includes a complete Docker Compose recipe to run the entire multi-service stack with a single command.
6. **Agent Skills (Dynamic Contexts):** Implements dynamic, demand-based context injection where specialized rules and legal frameworks are loaded only when a matching file type is identified.

---

## 💻 Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| **Agent Framework** | Google ADK (Agent Development Kit) | Multi-agent orchestration, state passing, and LLM communication. |
| **MCP Server** | FastMCP (Python) | Serves the synthetic government land records database over stdio. |
| **Security Layer** | Python (Zero-Trust design) | Houses permission checking logic and the append-only JSONL audit log. |
| **Frontend** | HTML5, CSS3, Vanilla JS | A highly responsive, split-layout dashboard designed with an earthy forest/gold palette, typewriter pipeline animations, and stamp-like disclaimer blocks. |
| **Deployment** | Docker & Docker Compose | Multi-container setup for the frontend and agent backend services. |

---

## 🚀 How to Run

Follow these step-by-step instructions to run the ZaminSaathi suite locally:

### 1. Clone the Repository
```bash
git clone https://github.com/POSHANMS/zaminsaathi.git
cd zaminsaathi
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables
Create a `.env` file in the root directory and add your Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Run the Agents/MCP Server Backend
Start the MCP server to make the synthetic database queries active:
```bash
python mcp_server/server.py
```
*(You can also run individual agents sequentially to test CLI output, e.g., `python agents/parser_agent.py`)*

### 5. Run the Frontend
Launch the lightweight Python HTTP server to host the ZaminSaathi dashboard:
```bash
python frontend/serve.py
```

### 6. Open the Dashboard
Navigate to **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 📊 Demo (Planted Discrepancy)

ZaminSaathi comes preloaded with a synthetic mismatch scenario to demonstrate its discrepancy-detecting capability:
* **The Setup:**
  - **`rtc_001.json`:** Represents the owner's RTC, showing that *Ramamurthy Gowda* owns 2.5 acres of dry land in **Survey Number 142/3**.
  - **`mutation_001.json`:** Represents a recent transaction record (Mutation Extract), but it incorrectly references **Survey Number 142/4** instead of 142/3.
* **The Analysis:**
  - When you click the **"Load Demo Mismatched Documents"** button on the dashboard and run the analysis:
    - **Agent 1** successfully parses the owner and details.
    - **Agent 2** queries the MCP server, compares the files, and flags a **HIGH severity survey mismatch** (142/3 vs. 142/4).
    - **Agent 3** compiles the findings and outputs a step-by-step resolution plan pointing the user to the *Tahsildar Office Hassan Taluk* and providing the exact script to say to the officer.

---

## 📁 Project Structure

```
zaminsaathi/
├── .env.example                 # Template for environment variables (Gemini API Key)
├── .gitignore                   # Standard git ignore file
├── AGENTS.md                    # ZaminSaathi Agent Constitution and rules
├── Dockerfile                   # Builds the Agents service docker container
├── README.md                    # Main project documentation (Kaggle submission details)
├── requirements.txt             # Python packages required to run the project
├── agents/                      # Google ADK Agents
│   ├── detector_agent.py        # Agent 2 - Cross-checks records and flags errors
│   ├── parser_agent.py          # Agent 1 - Decodes fields into plain English
│   └── planner_agent.py         # Agent 3 - Generates action roadmaps and scripts
├── docker/                      # Docker orchestration configs
│   └── docker-compose.yml       # Provisions frontend (port 3000) and backend (port 8000)
├── frontend/                    # Web UI
│   ├── index.html               # Earthy gold split-layout interactive dashboard
│   └── serve.py                 # Serves the frontend locally on port 3000
├── mcp_server/                  # Model Context Protocol Server
│   ├── server.py                # FastMCP server handling standard I/O database queries
│   └── data/
│       └── land_records.json    # Synthetic land registry database
├── sample_docs/                 # Demo files
│   ├── mutation_001.json        # Mismatched transaction document (survey 142/4)
│   ├── rtc_001.json             # Owner's base RTC record (survey 142/3)
│   ├── rtc_002.json             # Secondary clean record for validation
│   └── survey_001.json          # Synthetic survey sketch JSON file
├── security/                    # Zero-Trust security layers
│   ├── audit_log.py             # Appends transactions to JSONL file
│   └── permissions.py           # Handles permission gates before agent execution
└── skills/                      # Demand-driven agent capabilities
    ├── mutation-skill/          # Knowledge context for Mutation Extracts
    ├── rtc-skill/               # Knowledge context for RTCs
    └── survey-skill/            # Knowledge context for Survey Sketches
```

---

## ⚖️ Disclaimer

* **Guidance Only:** This tool is built to provide general guidance and explanation to help families understand official documents. It does not provide legal advice. Always consult a qualified lawyer before making final real estate decisions or taking legal action.
* **Synthetic Data:** All land records, owner names, transaction IDs, and documents provided in the demo folder are entirely synthetic and generated for demonstration purposes. Any resemblance to real individuals, survey numbers, or properties is purely coincidental.
