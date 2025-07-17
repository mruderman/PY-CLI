# Phase 1: Environment Setup & Dependencies

## Overview
Set up the local development environment by adding required dependencies and configuring the self-hosted Letta ADE server connection.

## Prerequisites
- Existing virtual environment in `sanctum-letta-mcp/venv/`
- Self-hosted Letta server: `https://cyansociety.a.pinggy.link/`
- Letta API password: `TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JT`

## Tasks

### 1.1 Update Dependencies
**File**: `sanctum-letta-mcp/requirements.txt`

Add the following dependencies:
```
letta-client>=0.4.0
sqlalchemy>=2.0.0
apscheduler>=3.10.0
croniter>=1.4.0
```

**Validation**: Check that all packages can be imported after installation.

### 1.2 Create Environment Configuration
**File**: `sanctum-letta-mcp/.env`

Create with the following content:
```bash
# Letta Self-Hosted Server Configuration
LETTA_BASE_URL=https://cyansociety.a.pinggy.link/
LETTA_API_KEY=TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JT

# Promptyoself Plugin Configuration
PROMPTYOSELF_DB_PATH=./promptyoself.db
PROMPTYOSELF_INTERVAL=60

# MCP Server Configuration
MCP_PLUGINS_DIR=smcp/plugins
```

### 1.3 Install Dependencies
**Commands**:
```bash
cd sanctum-letta-mcp
source venv/bin/activate
pip install -r requirements.txt
```

### 1.4 Test Letta Server Connection
**File**: `sanctum-letta-mcp/test_letta_connection.py` (temporary)

Create a simple test script:
```python
import os
from dotenv import load_dotenv
from letta import create_client

load_dotenv()

def test_connection():
    try:
        client = create_client(
            base_url=os.getenv("LETTA_BASE_URL"),
            token=os.getenv("LETTA_API_KEY")
        )
        
        # Test basic API call
        agents = client.list_agents()
        print(f"✅ Connection successful! Found {len(agents)} agents.")
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
```

**Validation**: Script should connect successfully and list available agents.

### 1.5 Git Commit
After completing all tasks:
```bash
git add .
git commit -m "Phase 1: Environment setup and dependencies

- Add letta-client, sqlalchemy, apscheduler, croniter dependencies
- Configure self-hosted Letta server connection
- Test Letta API connectivity

🤖 Generated with Claude Code"
git push origin main
```

## Success Criteria
- [ ] All dependencies installed without conflicts
- [ ] Environment variables configured correctly
- [ ] Letta server connection test passes
- [ ] Changes committed and pushed to GitHub

## Next Phase
Proceed to Phase 2: Plugin Structure Creation