# HotelMind Backend

FastAPI backend for the HotelMind AI platform.

## Quick Start

```bash
# 1. Start infrastructure
cd .. && docker compose up -d

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements-dev.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your values

# 5. Run migrations
alembic upgrade head

# 6. Start server
uvicorn app.main:app --reload
```

API docs available at http://localhost:8000/docs
