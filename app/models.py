from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def utc_now():
    return datetime.now(timezone.utc)

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(120), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=False, default="hub")  # 'hub', 'hospital', 'police_station'
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    outgoing_edges = relationship(
        "RoadEdge",
        foreign_keys="RoadEdge.from_location_id",
        back_populates="from_location",
        cascade="all, delete-orphan"
    )
    incoming_edges = relationship(
        "RoadEdge",
        foreign_keys="RoadEdge.to_location_id",
        back_populates="to_location",
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "address": self.address
        }


class RoadEdge(Base):
    __tablename__ = "road_edges"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    from_location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    to_location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    road_name = Column(String(150), nullable=False)
    distance_km = Column(Float, nullable=False)
    base_time_minutes = Column(Float, nullable=False)
    is_closed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    from_location = relationship("Location", foreign_keys=[from_location_id], back_populates="outgoing_edges")
    to_location = relationship("Location", foreign_keys=[to_location_id], back_populates="incoming_edges")

    def to_dict(self):
        return {
            "id": self.id,
            "from_location_id": self.from_location_id,
            "to_location_id": self.to_location_id,
            "from_location": self.from_location.name if self.from_location else None,
            "to_location": self.to_location.name if self.to_location else None,
            "road_name": self.road_name,
            "distance_km": self.distance_km,
            "base_time_minutes": self.base_time_minutes,
            "is_closed": self.is_closed
        }


class RouteHistory(Base):
    __tablename__ = "route_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    origin_name = Column(String(120), nullable=False)
    destination_name = Column(String(120), nullable=False)
    criteria = Column(String(30), nullable=False)  # 'distance' or 'time'
    path_nodes = Column(Text, nullable=False)  # JSON formatted list of node names
    total_distance_km = Column(Float, nullable=False)
    total_time_minutes = Column(Float, nullable=False)
    is_emergency = Column(Boolean, default=False)
    emergency_type = Column(String(50), nullable=True)  # 'hospital' or 'police_station'
    created_at = Column(DateTime, default=utc_now)

    def to_dict(self):
        return {
            "id": self.id,
            "origin_name": self.origin_name,
            "destination_name": self.destination_name,
            "criteria": self.criteria,
            "path_nodes": self.path_nodes,
            "total_distance_km": self.total_distance_km,
            "total_time_minutes": self.total_time_minutes,
            "is_emergency": self.is_emergency,
            "emergency_type": self.emergency_type,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }
