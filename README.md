# 🔀 Redirect Checker

A full-stack web app to trace URL redirect chains, inspect HTTP status codes, and measure response times — all in a clean, dark-themed UI.

Built with **FastAPI** (Python) + **nginx** + **Docker Compose**.

---

## ✨ Features

- **Single URL checker** — paste any URL and see every redirect hop with status codes, response times, content type, and server headers
- **Bulk checker** — check multiple URLs concurrently, results in a sortable table with expandable chains
- **History** — recent checks saved in your browser for quick re-runs
- **User-Agent switcher** — emulate Chrome, Googlebot, Facebook crawler, curl, and more
- **Loop detection** — flags infinite redirect loops automatically
- **Configurable** — set max redirects and timeout per request

## 🖥️ Screenshots

| Single URL | Bulk Check |
|---|---|
| Trace each hop with status badges and timing | Check dozens of URLs at once |

---

## 🚀 Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

### Run

```bash
git clone https://github.com/YOUR_USERNAME/redirect-checker.git
cd redirect-checker
docker compose up --build
```

Open **http://localhost:3000** in your browser.

To stop:
```bash
docker compose down
```

---

## 🏗️ Architecture

```
┌─────────────────────┐        ┌──────────────────────┐
│   nginx (port 3000) │──/api/→│  FastAPI (port 8000) │
│   Serves index.html │        │  Follows redirects   │
└─────────────────────┘        └──────────────────────┘
```

| Service    | Stack              | Port  |
|------------|--------------------|-------|
| `frontend` | nginx + HTML/JS/CSS | 3000 |
| `backend`  | Python + FastAPI    | internal only |

The frontend nginx container proxies all `/api/` calls to the FastAPI backend — no exposed backend port, no CORS issues.

## 📡 API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/health` | Health check |
| `POST` | `/api/check` | Check a single URL |
| `POST` | `/api/check/bulk` | Check multiple URLs concurrently |

### Example

```bash
curl -X POST http://localhost:3000/api/check \
  -H "Content-Type: application/json" \
  -d '{"url": "https://bit.ly/example", "max_redirects": 20, "timeout": 15}'
```

Response:
```json
{
  "original_url": "https://bit.ly/example",
  "final_url": "https://example.com/",
  "total_redirects": 2,
  "total_time_ms": 342.5,
  "hops": [
    {
      "step": 1,
      "url": "https://bit.ly/example",
      "status_code": 301,
      "status_text": "Moved Permanently",
      "response_time_ms": 120.3,
      "location": "https://example.com/"
    },
    ...
  ]
}
```

## 📁 Project Structure

```
redirect-checker/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    └── index.html
```

## 🛠️ Development

To run the backend locally without Docker:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

---

## 📄 License

MIT
