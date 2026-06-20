# 🤖 GitHub Forensics API

An automated workflow agent built with **FastAPI** and **Pydantic** that leverages the **Model Context Protocol (MCP)** to perform deep forensics and profile analysis on GitHub.

This backend connects a **Mistral Large LLM** to live GitHub data via a secure, containerized MCP server. This setup allows the AI to autonomously execute searches, read commits, analyze pull requests, and audit user activity in real-time.

---

## ⚡ Features

- **Profile Analyzer Agent**: Audits a GitHub user's entire public ecosystem (event streams, pinned repositories, and contribution habits).
- **Forensics Investigator Agent**: Isolates actions performed by a specific user within a single target repository (Commits, PRs, Issues, Reviews, and Admin actions).
- **Autonomous Tool Calling**: Implements a customizable `max_tool_rounds` loop for iterative searching, reading, and data refinement before final output.
- **Human-Readable Output**: Bypasses standard JSON serialization to return raw `PlainTextResponse` text for instant markdown readability in Swagger UI.

---

## 🏗️ Architecture & Tech Stack

- **Framework**: FastAPI & Pydantic
- **AI Model**: Mistral AI (`mistral-large-latest`)
- **Tooling Protocol**: Model Context Protocol (MCP) via `stdio_client`
- **Data Source**: `ghcr.io/github/github-mcp-server` (Executed via Docker)

---

## 📋 Prerequisites

Before starting the server, ensure your local environment meets these requirements:

- **Python 3.10+** installed.
- **Docker Daemon** running: The application spawns a lightweight Docker container to securely communicate with GitHub's API.
- **API Keys**:
  - A Mistral API Key.
  - A GitHub Personal Access Token (Classic) with at least `repo` and `read:user` scopes.

---

## 🚀 Local Setup & Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd <your-repo-directory>
```

### 2. Set Up Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Ensure you have `fastapi`, `uvicorn`, `mistralai`, `mcp`, and `python-dotenv` listed in your requirements.

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory (same level as `main.py`):

```env
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_classic_token_here
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_MODEL=mistral-large-latest
```

### 5. Start the FastAPI Server

```bash
python -m uvicorn main:app --reload
```

- **API URL**: `http://127.0.0.1:8000`
- **Interactive Swagger UI Docs**: `http://127.0.0.1:8000/docs`

---

## 🔌 API Endpoints

### 1. Health Check

- **Method / Route**: `GET /health`
- **Description**: Verifies the API is online.
- **Response**:
  ```json
  { "status": "ok" }
  ```

### 2. Profile Analyzer

- **Method / Route**: `POST /profile/chat`
- **Description**: Analyzes a specific GitHub username's overall activity, repositories, and recent events.
- **Payload**:
  ```json
  {
    "username": "octocat",
    "query": "Summarize this user's recent open-source activity.",
    "max_tool_rounds": 5
  }
  ```

### 3. User-Repository Forensics

- **Method / Route**: `POST /user-repo/chat`
- **Description**: Investigates the exact operations (code changes, PRs, issue comments) performed by a specific user within a targeted repository.
- **Payload**:
  ```json
  {
    "username": "octocat",
    "repository": "facebook/react",
    "query": "What pull requests has this user reviewed or authored?",
    "max_tool_rounds": 5
  }
  ```

> 💡 **Note on `max_tool_rounds`**: This parameter (default: 5, max: 10) controls how many consecutive API requests the AI can make to GitHub before compiling a final answer. Higher values allow deeper analysis but increase response times.

---

## 🛠️ Troubleshooting

- **`500 Internal Server Error`**: The `.env` file is missing, misnamed, or not in the exact directory where the script execution takes place.
- **`401 Bad Credentials` (in logs)**: The `GITHUB_PERSONAL_ACCESS_TOKEN` is expired, formatted incorrectly (remove any quotes), or lacks required permissions.
- **Server hangs / Connection refused**: Docker is not running. The MCP client requires an active Docker daemon to spawn the GitHub server image.
