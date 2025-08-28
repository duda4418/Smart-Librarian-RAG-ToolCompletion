# Smart-Librarian-RAG-ToolCompletion
A full-stack project with a FastAPI backend and a Next.js frontend.
---

## Project Structure

```
/backend   # Python FastAPI backend
/frontend  # Next.js frontend 
```

---

## Backend (FastAPI)

### Prerequisites

- Python 3.9+
- (Recommended) Virtual environment tool (venv, virtualenv, etc.)

### Setup

```bash
cd backend
python -m venv .venv         # Create virtual environment
source .venv/bin/activate    # Activate virtual environment (Linux/Mac)
# For Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Run the Backend

```bash
uvicorn main:app --reload
```

- By default, FastAPI will run at [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## Frontend

### Prerequisites

- Node.js (v18+ recommended)
- npm (or yarn/pnpm)

### Setup

```bash
cd frontend
npm install
```

### Run the Frontend

```bash
npm run dev
```

- By default, Next.js runs at [http://localhost:3000](http://localhost:3000)
- The frontend may require API endpoint configuration—see `/frontend/.env.local` or similar.

---

## Requirements Files

- Backend Python dependencies: `/backend/requirements.txt`
- Frontend JS dependencies: `/frontend/package.json` (managed via `npm install`)

---

## Build Steps

### Backend

```bash
cd backend
pip install -r requirements.txt
# Run with uvicorn as above
```

### Frontend

```bash
cd frontend
npm install
npm run build     # For production build
npm run dev       # For development
```

