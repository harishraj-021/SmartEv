# SmartEV — EV Trip Energy & Range Planner

SmartEV is a machine-learning-assisted EV trip planner. It predicts a vehicle's base energy efficiency from the supplied EV Energy Efficiency Dataset and then applies transparent trip-condition factors for terrain, weather and driving style to estimate energy demand and trip feasibility.

## Stack

- Frontend: React 19 + TypeScript + Vite + Tailwind CSS v4
- UI direction: Watermelon UI / Agndex-inspired dashboard, with a shadcn-compatible registry configuration
- Charts: Recharts
- Maps: React-Leaflet + OpenStreetMap tiles
- Backend: FastAPI
- ML: scikit-learn Random Forest + OneHotEncoder
- Routing: OpenRouteService / HeiGIT
- Weather & geocoding fallback: Open-Meteo

Watermelon UI is a copy-pasteable React registry built around React, Tailwind, Radix and Framer Motion. This project configures the `@watermelon` registry in `frontend/components.json` so official components can be added with the shadcn CLI when network access is available. See the official registry documentation: https://github.com/WatermelonCorp/watermellon-registry

## Project structure

```text
SmartEv/
├── backend/
│   ├── app/main.py
│   ├── data/EV Energy Efficiency Dataset.csv
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── lib/api.ts
│   │   └── App.tsx
│   ├── components.json
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## 1. Backend setup

From `backend/`:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env
```

Put your **new** OpenRouteService key into `backend/.env`:

```env
OPENROUTE_API_KEY=your_key_here
ORS_BASE_URL=https://api.heigit.org/openrouteservice
CORS_ORIGINS=http://localhost:5173
```

Never commit `.env`.

Run:

```bash
uvicorn app.main:app --reload --port 8000
```

Health check: `http://localhost:8000/api/health`

## 2. Frontend setup

From `frontend/`:

```bash
npm install
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`.

If the backend is not on port 8000, create `frontend/.env.local`:

```env
VITE_API_URL=http://localhost:8000
```

## 3. Add official Watermelon components

Watermelon UI supports shadcn-compatible registry installation. The project already has the registry configured as `@watermelon`.

For example, when online:

```bash
npx shadcn@latest add https://registry.watermelon.sh/button.json
```

You can then replace local UI primitives with the installed Watermelon components as desired.

## Security

The OpenRouteService key belongs in the backend environment only. Do not place it in React, `.env` files committed to GitHub, or source code.

Because a real API key was previously exposed during development, rotate/revoke that key and use a fresh key before publishing this repository.

## ML scope

The supplied dataset contains vehicle specifications and `Energy Efficiency (km/kWh)`. It does not contain battery capacity or route-level telemetry. Therefore battery capacity is entered by the user and terrain/weather/driving effects are transparent heuristic factors rather than claims of being learned from driving telemetry.
