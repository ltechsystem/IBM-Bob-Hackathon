# IBM Hackathon GitHub Project Template

This GitHub project template is for IBM Hackathon projects. It includes pre-configured security files to help prevent accidental credential commits and potential account suspension during the hackathon.

## 🚀 Quick Start

1. **Use this template to create your project:**
   - Click "Use this template" button above and select "Create a new repository"
   - Name your repository
   - Click "Create repository"

2. **Clone your new repository:**

   ```bash
   git clone https://github.com/HACKATHON-ORG/your-repo-name.git
   cd your-repo-name
   ```

3. **Set up environment variables:**

   ```bash
   # Copy the example file
   cp .env.example .env

   # Edit .env with your actual credentials
   # Use your preferred editor (nano, vim, code, etc.)
   nano .env
   ```

4. **Verify .gitignore is working:**

   ```bash
   # This should NOT show .env file
   git status

   # This should confirm .env is ignored
   git check-ignore -v .env
   ```

5. **Start developing!**

## 🔒 Security Features

This template includes:

- **`.gitignore`** - Prevents committing credentials and live session files
- **`.bobignore`** - Prevents AI assistants from logging credentials
- **`.env.example`** - Template for your environment variables

## 📋 Before Every Commit

Always run this checklist:

- [ ] Reviewed `git diff` for sensitive data
- [ ] No hardcoded API keys or passwords
- [ ] `.env` file is NOT in staged changes
- [ ] No files with "credential" or "secret" in name
- [ ] Used environment variables for all credentials

## 🆘 Need Help?

- Read [SECURITY.md](SECURITY.MD) for detailed guidelines
- Contact hackathon support through mentor channel
- Ask in the hackathon Slack workspace

---

**Remember:** Security is everyone's responsibility. When in doubt, ask for help!

---

## 🤖 Sentinel — Continuous Test Maintenance for IBM i RPG

Sentinel is a Python agent that watches IBM i source members, runs RPGUnit tests after each compile, and uses watsonx.ai (Bob) to classify failures as stale tests, genuine regressions, or gaps in coverage. See [`sentinel-plan.md`](sentinel-plan.md) for the full architecture.

### Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | `python --version` |
| IBM i partition with XMLSERVICE | HTTP server must be running on the partition |
| RPGUnit installed on IBM i | Required for Sub-Tasks 3+ |
| watsonx.ai API key | Required for Sub-Task 4 (classifier) |

### Installation

```bash
# 1. Clone the repo and enter it
git clone <repo-url>
cd <repo>

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows

# 3. Install Sentinel and its dependencies
pip install -e .

# 4. Copy the example env file and fill in your credentials
cp .env.example .env
# Edit .env — set IBMI_HOST, IBMI_USER, IBMI_PASSWORD at minimum
```

### IBM i Connection Setup

Sentinel connects to IBM i via **XMLSERVICE** over HTTP.  Before running:

1. Ensure XMLSERVICE is installed on the partition (`CHKOBJ OBJ(QXMLSERV/XMLSTOREDP) OBJTYPE(*PGM)`).
2. Start the IBM i HTTP server: `STRTCPSVR SERVER(*HTTP) HTTPSVR(ZSVR)`
3. Confirm the CGI endpoint is reachable: `http://<IBMI_HOST>:<IBMI_PORT>/cgi-bin/xmlcgi.pgm`

### Verify the Connection

```bash
python scripts/smoke_test_connection.py
# Expected: IBM i connection OK
```

### Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `IBMI_HOST` | IBM i hostname or IP | — |
| `IBMI_USER` | IBM i user profile | — |
| `IBMI_PASSWORD` | IBM i password | — |
| `IBMI_PORT` | XMLSERVICE HTTP port | `80` |
| `WATSONX_API_KEY` | watsonx.ai API key | — |
| `WATSONX_PROJECT_ID` | watsonx.ai project ID | — |
| `WATSONX_URL` | watsonx.ai service URL | — |
| `WATSONX_MODEL_ID` | Model for classification | `ibm/granite-13b-instruct-v2` |
| `SENTINEL_POLL_INTERVAL_SECS` | Watcher poll interval | `5` |
| `SENTINEL_CONFIDENCE_THRESHOLD` | Min confidence for auto-verdict | `0.75` |
| `SENTINEL_BOB_STUB` | Skip real watsonx call (dev mode) | `false` |
