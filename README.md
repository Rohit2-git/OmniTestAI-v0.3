# OmniTestAI

OmniTest AI is a centralized API server designed to execute autonomous testing workflows across multiple domains: Web, API, Performance, Accessibility, Security (Pentesting), and Mobile. The system utilizes Large Language Models (LLMs) to act as "Reasoning Agents" that interpret user intent, generate test strategies, and execute code via specialized "Executor Frameworks." 

---

## Tech Stack

- **FastAPI** — REST API framework (auto-generates Swagger UI at `/docs`)
- **Prisma** — ORM and database client
- **SQLite** — local database (`dev.db`)
- **Google Gemini** — LLM for generating test cases
- **Stagehand AI** — browser automation using natural language
- **Python 3.11+**

---

## Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/Rohit2-git/OmniTestAI-v0.3
cd OmniTestAI
```

### 2. Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright browsers (required by Stagehand)

```bash
playwright install
```

### 5. Set up environment variables

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_gemini_api_key_here
CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
```

> **CHROME_PATH** — update this to your Chrome installation path if different.
> On macOS it is typically `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`

### 6. Set up the database

```bash
# Apply all migrations and create the database
prisma migrate deploy

# Generate the Prisma Python client
prisma generate
```

> If you are running this for the first time and `migrate deploy` gives an error, use this instead:
> ```bash
> prisma migrate dev --name init
> prisma generate
> ```

### 7. Start the server

```bash
uvicorn app.main:app --reload
```

The server will start at `http://127.0.0.1:8000`

Open `http://127.0.0.1:8000/docs` in your browser to access the Swagger UI.

---

## API Endpoints

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check if server is running |

### Generate Test Cases
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/tests/generate` | Upload a requirements document to generate test cases using Gemini. Optionally upload a context file to generate app-specific test cases with real values instead of placeholders. |

**Supported file formats:** `.txt`, `.pdf`, `.docx`, `.md`

### Results
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/results/` | List all test runs |
| GET | `/results/{run_id}` | Get all generated test cases for a run |
| GET | `/results/{run_id}/execution` | Get full execution history for a run |
| GET | `/results/{run_id}/execution/latest` | Get the most recent execution for a run |
| DELETE | `/results/{run_id}` | Delete a run and all its data |

### Execute
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/execute/` | Execute all generated test cases for a run against a live website. Stops on first failure. Saves results to DB. |
| POST | `/execute/single` | Execute only the first test case — quick sanity check |
| POST | `/execute/nl` | Send plain English steps directly without a saved run. Stagehand AI executes them against the given URL. |

---

## Typical Workflow

```
1. POST /tests/generate      — upload requirements doc → get run_id
2. GET  /results/{run_id}    — review generated test cases
3. POST /execute/            — run all test cases against your live site
4. GET  /results/{run_id}/execution/latest  — view execution results
```

---

## Project Structure

```
OmniTestAI/
├── app/
│   ├── agents/
│   │   └── reasoning_agent.py      # LLM reasoning agent (Observe → Plan → Act)
│   ├── executors/
│   │   ├── base.py                 # Abstract base class for all executors
│   │   ├── web.py                  # Web executor using Stagehand AI
│   │   ├── nl_executor.py          # Natural language executor (raw steps)
│   │   ├── api.py                  # API executor (stub — in progress)
│   │   └── performance.py          # Performance executor (stub — in progress)
│   ├── routers/
│   │   ├── execute.py              # Execution endpoints
│   │   ├── generate.py             # Test case generation endpoints
│   │   ├── health.py               # Health check
│   │   ├── results.py              # Results and history endpoints
│   │   └── tests.py                # Agent-based test runner
│   ├── schemas/
│   │   ├── generate.py             # Pydantic models for generation
│   │   └── test.py                 # Pydantic models for test runs
│   ├── services/
│   │   ├── file_service.py         # File parsing (.txt, .pdf, .docx)
│   │   └── llm_service.py          # Gemini API integration
│   ├── database.py                 # Prisma client
│   └── main.py                     # FastAPI app entry point
├── migrations/                     # Prisma migration history
├── schema.prisma                   # Database schema
├── requirements.txt
├── .env                            # Environment variables (not committed)
└── README.md
```

---

## Notes

- The `.env` file is not committed to GitHub. Each developer must create their own.
- `dev.db` (the SQLite database file) is also not committed — it is created locally when you run migrations.
- Stagehand runs a local Chromium server in the background when executing tests. You will see a terminal process start automatically.
- The `/execute/nl` and `/execute/single` endpoints do not save results to the database — they are intended for quick one-off checks only.
