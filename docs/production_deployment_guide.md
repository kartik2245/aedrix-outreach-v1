# AEDRIX AI Cold Outreach System — Office Production Deployment Guide

## 1. System Overview
The **AEDRIX AI Cold Outreach System** is an enterprise B2B sales automation platform engineered specifically for UK commercial construction main contractors.

### Production Processing Stack
- **API Server & Orchestration Engine**: Python 3.12 + FastAPI + LangGraph
- **Primary Database**: Supabase PostgreSQL (via SQLAlchemy 2.0 & `psycopg3`)
- **Lead Discovery Engine**: Deepline V2 API (`DEEPLINE_LIVE=true`)
- **AI Personalization Engine**: AWS Bedrock DeepSeek V3.2 (`LLM_PROVIDER=aws_bedrock`)
- **Operator Web Dashboard**: React + TypeScript + Vite (`frontend/dist/`)
- **Safety Controls**: Human Approval Gate required before any lead staging (`SEND_EMAILS=false`, `SMARTLEAD_LIVE=false`).

---

## 2. Server Prerequisites
- **Operating System**: Windows Server 2019/2022, Windows 10/11 Pro, or Linux (Ubuntu 22.04 LTS+)
- **Python**: Version 3.12.x (with `pip` and `venv`)
- **Node.js**: Version 18.x or 20.x LTS (with `npm`)
- **Database**: Supabase PostgreSQL instance (or self-hosted PostgreSQL 15+)

---

## 3. Environment Configuration (`.env`)
Create or verify `.env` in the root project folder:

```ini
# Application Mode
APP_MODE=PRODUCTION

# Primary Production Database (Supabase PostgreSQL)
DATABASE_ENABLED=true
DATABASE_URL=postgresql+psycopg://postgres.[PROJECT-REF]:[PASSWORD]@[POOLER-HOST]:5432/postgres

# LLM Provider Configuration (AWS Bedrock / DeepSeek V3.2)
LLM_PROVIDER=aws_bedrock
LLM_MODEL=deepseek.v3.2
BEDROCK_MODEL_ID=deepseek.v3.2
AWS_REGION=ap-south-1
AWS_BEARER_TOKEN_BEDROCK=your_aws_bedrock_bearer_token

# Deepline Dynamic Discovery API Configuration
DEEPLINE_API_KEY=your_deepline_v2_api_key
DEEPLINE_BASE_URL=https://code.deepline.com/api/v2
DEEPLINE_LIVE=true
DEEPLINE_RUN_CONFIRMATION=true

# Smartlead Production API Configuration (Staging Only)
SMARTLEAD_API_KEY=
SMARTLEAD_BASE_URL=https://server.smartlead.ai/api/v1
SMARTLEAD_LIVE=false
SMARTLEAD_CAMPAIGN_ID=

# Batch Execution Settings
BATCH_SIZE=400
CLAUDE_BATCH_SIZE=25

# Safety Controls - DO NOT CHANGE
DRY_RUN=false
SEND_EMAILS=false
PRODUCTION_SEND_CONFIRMATION=false
```

---

## 4. Production Deployment Steps

### Step 1: Virtual Environment & Dependencies
```powershell
# Create virtual environment if missing
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install required Python packages
pip install -r requirements.txt
```

### Step 2: Database Migrations
```powershell
# Apply Alembic schema migrations to PostgreSQL
.\.venv\Scripts\alembic.exe upgrade head
```

### Step 3: Frontend Production Build
```powershell
# Build static React dashboard assets
cd frontend
npm install
npm run build
cd ..
```

### Step 4: Launch Production Server
On Windows:
```powershell
# Double click or run batch file
.\START_AEDRIX_PRODUCTION.bat
```
Or directly via Python:
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 5. Verification & Health Checks

### Check System Mode
```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/system/mode | ConvertTo-Json
```
Expected output:
- `mode`: `"PRODUCTION"`
- `demo_mode`: `false`
- `production_mode`: `true`
- `deepline_live`: `true`
- `smartlead_live`: `false`
- `real_emails_enabled`: `false`

### Check Database Connection
```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/system/database-health | ConvertTo-Json
```
Expected output:
- `database`: `"supabase_postgresql"`
- `connected`: `true`
- `status`: `"HEALTHY"`

---

## 6. Restart & Shutdown
- **Shutdown**: Press `Ctrl+C` in the terminal window running Uvicorn.
- **Restart**: Execute `START_AEDRIX_PRODUCTION.bat` or run the Uvicorn start command.
- **Log Location**: `data/logs/` and stdout terminal.
