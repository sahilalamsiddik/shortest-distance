# Bengaluru Local Delivery Route Planner

A full-stack logistics route planning and emergency dispatch system specifically built for Bengaluru's road network (Majestic, MG Road, Indiranagar, Whitefield, Koramangala, Electronic City, and more).

## Highlights & Features

- **Optimal Route Engine**:
  - **Shortest Distance**: Computes minimal physical travel distance in kilometers using Dijkstra's algorithm.
  - **Fastest Travel Time**: Factors in real-world Bengaluru bottlenecks, traffic factor multipliers, and road delays in minutes.
- **Dynamic Traffic Delays via CSV**:
  - Delays are loaded from `data/traffic_delays.csv`.
  - The application automatically tracks the CSV file's modified time (`os.path.getmtime`), dynamically applying updated road conditions on the next route calculation **without restarting the app**.
  - A manual reload button and `/api/traffic/reload` endpoint are also provided.
- **🚨 Emergency SOS Dispatch**:
  - High-priority dispatch modal finding the closest emergency responder from the user's location.
  - Routes directly to the nearest **Medical Trauma Hospital** (e.g. Manipal Hospital, Victoria Hospital, Apollo Hospital, Columbia Asia, Sakra World) or **Police Station** (Upparpet, Cubbon Park, Indiranagar, Whitefield, Madiwala, Electronic City).
- **Cartographic Map Image Generator**:
  - Generates high-resolution PNG vector maps (`/api/route/map-image`) using Matplotlib and Pillow, with highlighted paths, starting pins, destination badges, and hospital/police markers.
  - Includes an interactive Leaflet/OpenStreetMap view on the frontend for smooth panning and zooming.
- **Database Architecture (MySQL + Graceful Fallback)**:
  - Supports MySQL (`mysql+pymysql`) with dedicated `schema.sql` schema.
  - If MySQL credentials are not yet configured in `.env`, it automatically falls back to local SQLite (`bengaluru_routing.db`) with an active indicator badge in the UI.
  - Persists past search history with full turn-by-turn routes and one-click replay.
- **Clean Light-Themed UI**:
  - Professional, human-designed logistics dashboard (no dark neon AI aesthetics).
  - Handles unreachable routes gracefully with clear error banners and diagnostics.
- **FastAPI Backend & Interactive Swagger Docs**:
  - Full OpenAPI documentation accessible at `http://localhost:8000/docs`.

---

## Project Structure

```
├── app/
│   ├── __init__.py
│   ├── config.py             # Database settings, paths, environment configuration
│   ├── database.py           # Engine initialization (MySQL with SQLite fallback)
│   ├── models.py             # SQLAlchemy models: Location, RoadEdge, RouteHistory
│   ├── schemas.py            # Pydantic schemas for API requests & responses
│   ├── router_engine.py      # Dijkstra algorithm (Distance vs Traffic-adjusted Time)
│   ├── traffic_service.py    # Dynamic CSV loader with mtime watcher & reload API
│   ├── map_generator.py      # Matplotlib PNG map image generator
│   ├── seed_data.py          # Bengaluru hubs, hospitals, police stations, roads
│   └── main.py               # FastAPI application with CORS and static files
├── data/
│   └── traffic_delays.csv    # Live editable traffic delay factors
├── static/
│   ├── css/
│   │   └── styles.css        # Clean light enterprise stylesheet
│   ├── js/
│   │   └── app.js            # Frontend JavaScript application
│   └── index.html            # Logistics dashboard UI
├── tests/
│   └── test_routing.py       # Automated test suite
├── schema.sql                # Pure MySQL DDL schema script
├── requirements.txt          # Python dependencies
├── run.py                    # Server startup script
└── README.md
```

---

## Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Database (Optional MySQL)
To use MySQL, copy `.env.example` to `.env` and configure your credentials:
```env
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=bengaluru_routing
```
*Note: If no MySQL credentials are provided, the app will automatically use a local SQLite database (`bengaluru_routing.db`).*

### 3. Launch the Application
```bash
python run.py
```
- **Web Interface**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Run Automated Tests
```bash
python -m pytest -v tests/test_routing.py
```

---

## Live Traffic Delays (CSV)
You can open `data/traffic_delays.csv` in any text editor or spreadsheet app and adjust delays or add new corridors:
```csv
road_name,from_location,to_location,delay_minutes,traffic_factor,condition,notes
Silk Board Junction,Koramangala,HSR Layout,25.0,1.8,Heavy Congestion,Peak hour bottleneck
Marathahalli ORR,Indiranagar,Whitefield,35.0,2.2,Severe Gridlock,Road repair and tech corridor traffic
```
Once saved, any new route calculation immediately incorporates the updated delay without restarting the server!
