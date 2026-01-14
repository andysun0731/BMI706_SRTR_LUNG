# FastAPI + React Architecture Plan

This document outlines the architecture for upgrading the BMI706 Lung Transplant visualization from Streamlit to a FastAPI + React stack.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    AWS EC2 Instance                      │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Docker Compose                      │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────────────┐  │    │
│  │  │  NGINX  │  │ FastAPI │  │    Next.js      │  │    │
│  │  │  :80    │──│  :8000  │  │     :3000       │  │    │
│  │  │ (proxy) │  │ (API)   │  │   (Frontend)    │  │    │
│  │  └─────────┘  └────┬────┘  └─────────────────┘  │    │
│  │                    │                             │    │
│  │                    ▼                             │    │
│  │              ┌──────────┐                        │    │
│  │              │ CSV Data │                        │    │
│  │              └──────────┘                        │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
bmi706-lung-transplant/
├── backend/                     # FastAPI Backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── map.py           # /api/map/* endpoints
│   │   │   ├── survival.py      # /api/survival/* endpoints
│   │   │   └── utilization.py   # /api/utilization/* endpoints
│   │   └── services/
│   │       └── data_loader.py   # CSV loading & caching
│   ├── data/
│   │   ├── viz_map_data.csv
│   │   ├── viz_survival_curves.csv
│   │   ├── viz_survival_stats.csv
│   │   ├── viz_donor_utilization.csv
│   │   └── viz_lundon_summary.csv
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                    # Next.js Frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx       # Root layout
│   │   │   ├── page.tsx         # Map tab (home)
│   │   │   ├── survival/
│   │   │   │   └── page.tsx     # Survival tab
│   │   │   └── utilization/
│   │   │       └── page.tsx     # Utilization tab
│   │   ├── components/
│   │   │   ├── Map/
│   │   │   │   └── OPOMap.tsx   # Interactive map
│   │   │   ├── Charts/
│   │   │   │   ├── SurvivalChart.tsx
│   │   │   │   └── UtilizationChart.tsx
│   │   │   └── Navigation.tsx
│   │   └── lib/
│   │       └── api.ts           # API client functions
│   ├── package.json
│   ├── tailwind.config.js
│   └── Dockerfile
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
└── README.md
```

---

## API Endpoints

### Map Data
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/map/connections` | OPO-Center connections with filters |
| GET | `/api/map/opos` | OPO summary (location, transplants, DCU rate) |

**Query Parameters:**
```
/api/map/connections?start_year=2018&end_year=2024&start_month=1&end_month=12
```

### Survival Data
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/survival/curves` | Kaplan-Meier survival curves |
| GET | `/api/survival/stats` | Log-rank test p-values |

**Query Parameters:**
```
/api/survival/curves?opos=CAGS,NYRT&include_nationwide=true
```

### Utilization Data
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/utilization/summary` | Utilization rates by OPO |
| GET | `/api/utilization/compare` | DCD vs DBD comparison |

**Query Parameters:**
```
/api/utilization/summary?cas_period=Post-CAS&donor_type=DBD
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Backend** | FastAPI | REST API, async, auto-docs |
| **Frontend** | Next.js 14 | React framework, SSR |
| **Charts** | Recharts | D3-based React charts |
| **Maps** | Mapbox GL JS | Professional interactive maps |
| **Styling** | Tailwind CSS | Utility-first CSS |
| **State** | React Query | Data fetching & caching |
| **Container** | Docker Compose | Multi-container orchestration |
| **Proxy** | NGINX | Reverse proxy, SSL |

---

## Docker Configuration

### docker-compose.yml
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: bmi706-api
    ports:
      - "8000:8000"
    volumes:
      - ./backend/data:/app/data:ro
    environment:
      - DATA_PATH=/app/data
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: bmi706-web
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: bmi706-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - backend
      - frontend
    restart: unless-stopped
```

---

## Backend Example (FastAPI)

### main.py
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import map, survival, utilization

app = FastAPI(title="BMI706 Lung Transplant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(map.router, prefix="/api/map", tags=["map"])
app.include_router(survival.router, prefix="/api/survival", tags=["survival"])
app.include_router(utilization.router, prefix="/api/utilization", tags=["utilization"])

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
```

### routers/map.py
```python
from fastapi import APIRouter, Query
from typing import Optional
import pandas as pd

router = APIRouter()

# Load data at startup
MAP_DATA = pd.read_csv("/app/data/viz_map_data.csv")

@router.get("/connections")
async def get_connections(
    start_year: int = Query(2018),
    end_year: int = Query(2024),
    start_month: int = Query(1),
    end_month: int = Query(12)
):
    filtered = MAP_DATA[
        (MAP_DATA['Year'] >= start_year) & 
        (MAP_DATA['Year'] <= end_year)
    ]
    return filtered.to_dict(orient="records")
```

---

## Frontend Example (React + Recharts)

### SurvivalChart.tsx
```tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, Area } from 'recharts';

interface SurvivalChartProps {
  data: Array<{
    GraftTime: number;
    survival_prob: number;
    ci_lower: number;
    ci_upper: number;
    Group: string;
  }>;
}

export function SurvivalChart({ data }: SurvivalChartProps) {
  return (
    <LineChart width={800} height={400} data={data}>
      <XAxis dataKey="GraftTime" label="Days Since Transplant" />
      <YAxis domain={[0, 1]} label="Survival Probability" />
      <Tooltip />
      <Legend />
      <Area dataKey="ci_lower" stroke="none" fill="#8884d8" fillOpacity={0.2} />
      <Area dataKey="ci_upper" stroke="none" fill="#8884d8" fillOpacity={0.2} />
      <Line type="stepAfter" dataKey="survival_prob" stroke="#8884d8" />
    </LineChart>
  );
}
```

---

## Migration Plan

| Phase | Duration | Tasks |
|-------|----------|-------|
| **1. Backend** | 2-3 days | Create FastAPI with all endpoints |
| **2. Frontend Core** | 3-4 days | Next.js setup, routing, API client |
| **3. Map Component** | 2-3 days | Mapbox GL integration |
| **4. Charts** | 2-3 days | Survival & utilization with Recharts |
| **5. Styling** | 1-2 days | Tailwind polish |
| **6. Docker** | 1 day | Multi-container setup |
| **Total** | ~2 weeks | |

---

## Deployment Commands

```bash
# On EC2 instance
cd ~/bmi706-lung-transplant

# Build and start all services
docker-compose up -d --build

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Restart after code changes
docker-compose down
docker-compose up -d --build
```

---

## Access URLs

| Service | Development | Production |
|---------|-------------|------------|
| Frontend | http://localhost:3000 | http://your-ip |
| API Docs | http://localhost:8000/docs | http://your-ip/api/docs |
| Health Check | http://localhost:8000/api/health | http://your-ip/api/health |
