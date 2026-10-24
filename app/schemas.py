from typing import List, Optional
from pydantic import BaseModel, Field

class LocationResponse(BaseModel):
    id: int
    name: str
    category: str
    latitude: float
    longitude: float
    address: Optional[str] = None

    class Config:
        from_attributes = True

class RouteRequest(BaseModel):
    origin: str = Field(..., description="Starting location name (e.g., 'Majestic')")
    destination: str = Field(..., description="Destination location name (e.g., 'Whitefield')")
    criteria: str = Field("time", description="Optimization criteria: 'time' or 'distance'")

class SOSRequest(BaseModel):
    current_location: str = Field(..., description="User's current location (e.g., 'Indiranagar')")
    service_type: str = Field("hospital", description="Emergency type: 'hospital' or 'police_station'")

class TurnDirection(BaseModel):
    step: int
    from_node: str
    to_node: str
    road_name: str
    distance_km: float
    time_minutes: float
    delay_minutes: float
    condition: str

class RouteResponse(BaseModel):
    found: bool
    message: str
    origin: str
    destination: str
    criteria: str
    path: List[str] = []
    total_distance_km: float = 0.0
    total_time_minutes: float = 0.0
    free_flow_time_minutes: float = 0.0
    traffic_delay_minutes: float = 0.0
    directions: List[TurnDirection] = []
    is_emergency: bool = False
    emergency_type: Optional[str] = None

class HistoryItem(BaseModel):
    id: int
    origin_name: str
    destination_name: str
    criteria: str
    path_nodes: str
    total_distance_km: float
    total_time_minutes: float
    is_emergency: bool
    emergency_type: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True

class TrafficDelayItem(BaseModel):
    road_name: str
    from_location: str
    to_location: str
    delay_minutes: float
    traffic_factor: float
    condition: str
    notes: Optional[str] = ""
