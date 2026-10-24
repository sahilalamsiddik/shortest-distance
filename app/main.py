import json
import logging
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, create_db_tables, get_db_status
from app.models import Location, RouteHistory
from app.schemas import (
    LocationResponse, RouteRequest, RouteResponse,
    SOSRequest, HistoryItem, TrafficDelayItem
)
from app.router_engine import RoutingEngine
from app.traffic_service import traffic_service
from app.map_generator import generate_route_map
from app.seed_data import seed_database

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database and tables...")
    create_db_tables()
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    logger.info("Bengaluru Delivery Route Planner ready.")
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Local Delivery Route Planner for Bengaluru with MySQL, real-time CSV traffic delays, and SOS emergency routing.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoints ---

@app.get("/api/status", tags=["System"])
def get_system_status():
    """Returns database connection status and live traffic configuration."""
    db_info = get_db_status()
    traffic_records = traffic_service.get_all_delays()
    return {
        "status": "online",
        "app_name": settings.APP_NAME,
        "database": db_info,
        "traffic_csv_path": str(settings.TRAFFIC_CSV_PATH),
        "traffic_active_bottlenecks": len(traffic_records)
    }

@app.get("/api/locations", response_model=List[LocationResponse], tags=["Locations"])
def list_locations(category: Optional[str] = None, db: Session = Depends(get_db)):
    """List Bengaluru delivery hubs and emergency locations."""
    query = db.query(Location)
    if category:
        query = query.filter(Location.category == category.lower())
    return query.order_by(Location.name).all()

@app.post("/api/route", response_model=RouteResponse, tags=["Routing"])
def calculate_route(req: RouteRequest, db: Session = Depends(get_db)):
    """
    Calculate optimal delivery route by shortest distance or fastest travel time.
    Factors in dynamic CSV traffic delays and saves search to history.
    """
    engine = RoutingEngine(db)
    result = engine.find_route(
        origin_name=req.origin,
        destination_name=req.destination,
        criteria=req.criteria
    )

    # Save to history if valid route
    if result.found and len(result.path) > 1:
        history_entry = RouteHistory(
            origin_name=result.origin,
            destination_name=result.destination,
            criteria=result.criteria,
            path_nodes=json.dumps(result.path),
            total_distance_km=result.total_distance_km,
            total_time_minutes=result.total_time_minutes,
            is_emergency=False,
            emergency_type=None
        )
        db.add(history_entry)
        db.commit()

    return result.to_dict()

@app.post("/api/sos", response_model=RouteResponse, tags=["Emergency SOS"])
def trigger_sos(req: SOSRequest, db: Session = Depends(get_db)):
    """
    Emergency SOS: Finds the closest hospital or police station from the user's
    current location and returns the fastest emergency route.
    """
    engine = RoutingEngine(db)
    result = engine.find_nearest_emergency(
        current_location_name=req.current_location,
        service_type=req.service_type
    )

    # Save emergency dispatch to history
    if result.found and len(result.path) > 1:
        history_entry = RouteHistory(
            origin_name=result.origin,
            destination_name=result.destination,
            criteria="time",
            path_nodes=json.dumps(result.path),
            total_distance_km=result.total_distance_km,
            total_time_minutes=result.total_time_minutes,
            is_emergency=True,
            emergency_type=req.service_type
        )
        db.add(history_entry)
        db.commit()

    return result.to_dict()

@app.get("/api/route/map-image", tags=["Map"])
def get_route_map_image(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    criteria: str = "time",
    is_emergency: bool = False,
    emergency_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Renders a high-resolution PNG map image showing the Bengaluru network and active route.
    """
    path_nodes = []
    unreachable_origin = None
    unreachable_destination = None

    if origin and destination:
        engine = RoutingEngine(db)
        if is_emergency:
            res = engine.find_nearest_emergency(origin, emergency_type or "hospital")
        else:
            res = engine.find_route(origin, destination, criteria)

        if res.found:
            path_nodes = res.path
        else:
            unreachable_origin = origin
            unreachable_destination = destination

    img_bytes = generate_route_map(
        db=db,
        path_node_names=path_nodes,
        is_emergency=is_emergency,
        emergency_type=emergency_type,
        unreachable_origin=unreachable_origin,
        unreachable_destination=unreachable_destination
    )

    return Response(content=img_bytes, media_type="image/png")

@app.get("/api/traffic", response_model=List[TrafficDelayItem], tags=["Traffic"])
def get_traffic_delays():
    """Retrieve all traffic delays loaded dynamically from CSV."""
    records = traffic_service.get_all_delays()
    return records

@app.post("/api/traffic/reload", tags=["Traffic"])
def reload_traffic():
    """Force re-reads the CSV file without restarting the server."""
    count = traffic_service.force_reload()
    return {"message": "Traffic delays reloaded successfully", "records_loaded": count}

@app.get("/api/history", response_model=List[HistoryItem], tags=["History"])
def get_route_history(limit: int = 50, db: Session = Depends(get_db)):
    """Fetch past route searches stored in MySQL / database."""
    items = db.query(RouteHistory).order_by(RouteHistory.created_at.desc()).limit(limit).all()
    return [item.to_dict() for item in items]

@app.post("/api/history/clear", tags=["History"])
def clear_history(db: Session = Depends(get_db)):
    """Clear past route history."""
    db.query(RouteHistory).delete()
    db.commit()
    return {"message": "History cleared"}

# Serve frontend
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

@app.get("/", include_in_schema=False)
def serve_index():
    index_file = settings.STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Bengaluru Route Planner API online. Access /docs for Swagger UI."}
