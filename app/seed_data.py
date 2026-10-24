import logging
from sqlalchemy.orm import Session
from app.models import Location, RoadEdge

logger = logging.getLogger(__name__)

INITIAL_LOCATIONS = [
    # Primary Delivery Hubs
    {"name": "Majestic", "category": "hub", "latitude": 12.9767, "longitude": 77.5713, "address": "Kempegowda Bus Station & Railway Terminal, Central Bengaluru"},
    {"name": "MG Road", "category": "hub", "latitude": 12.9756, "longitude": 77.6066, "address": "Mahatma Gandhi Road, Central Business District"},
    {"name": "Indiranagar", "category": "hub", "latitude": 12.9784, "longitude": 77.6408, "address": "100ft Road / CMH Road Commercial Hub"},
    {"name": "Whitefield", "category": "hub", "latitude": 12.9698, "longitude": 77.7500, "address": "ITPL Main Road, East Bengaluru Tech Corridor"},
    {"name": "Koramangala", "category": "hub", "latitude": 12.9352, "longitude": 77.6245, "address": "Sony World Junction / 80ft Road Hub"},
    {"name": "HSR Layout", "category": "hub", "latitude": 12.9121, "longitude": 77.6446, "address": "Sector 1, Outer Ring Road Junction"},
    {"name": "Electronic City", "category": "hub", "latitude": 12.8452, "longitude": 77.6602, "address": "Phase 1 Toll Plaza, South Bengaluru"},
    {"name": "Jayanagar", "category": "hub", "latitude": 12.9299, "longitude": 77.5824, "address": "4th Block Shopping Complex & Hub"},
    {"name": "Hebbal", "category": "hub", "latitude": 13.0358, "longitude": 77.5970, "address": "Hebbal Flyover Junction, North Bengaluru"},
    {"name": "Marathahalli", "category": "hub", "latitude": 12.9591, "longitude": 77.6974, "address": "Marathahalli Bridge, Outer Ring Road"},
    {"name": "Yeshwanthpur", "category": "hub", "latitude": 13.0227, "longitude": 77.5510, "address": "Yeshwanthpur APMC Yard & Logistics Terminal"},
    {"name": "Bannerghatta Road", "category": "hub", "latitude": 12.8953, "longitude": 77.5980, "address": "IIMB / Hulimavu Gate, South Hub"},
    {"name": "Malleshwaram", "category": "hub", "latitude": 13.0031, "longitude": 77.5686, "address": "Sampige Road Market Hub"},
    # Unreachable / Isolated test hub
    {"name": "Nelamangala Isolated Depot", "category": "hub", "latitude": 13.0988, "longitude": 77.3912, "address": "Remote Outpost (Disconnected for route test)"},

    # Emergency: Hospitals
    {"name": "Victoria Hospital", "category": "hospital", "latitude": 12.9634, "longitude": 77.5746, "address": "Fort, Near City Market / Majestic"},
    {"name": "Manipal Hospital", "category": "hospital", "latitude": 12.9598, "longitude": 77.6481, "address": "HAL Old Airport Road, Kodihalli"},
    {"name": "Columbia Asia Hospital", "category": "hospital", "latitude": 13.0401, "longitude": 77.5890, "address": "Bellary Road, Hebbal"},
    {"name": "Narayana Health City", "category": "hospital", "latitude": 12.8021, "longitude": 77.6922, "address": "Bommasandra, Near Electronic City"},
    {"name": "Apollo Hospital", "category": "hospital", "latitude": 12.8925, "longitude": 77.5976, "address": "Bannerghatta Main Road, Krishnaraju Layout"},
    {"name": "Sakra World Hospital", "category": "hospital", "latitude": 12.9261, "longitude": 77.6833, "address": "Devarabeesanahalli, Outer Ring Road"},

    # Emergency: Police Stations
    {"name": "Upparpet Police Station", "category": "police_station", "latitude": 12.9772, "longitude": 77.5732, "address": "Subhash Nagar, Majestic"},
    {"name": "Cubbon Park Police Station", "category": "police_station", "latitude": 12.9763, "longitude": 77.5929, "address": "Kasturba Road, Near MG Road"},
    {"name": "Indiranagar Police Station", "category": "police_station", "latitude": 12.9712, "longitude": 77.6395, "address": "100 Feet Road, HAL 2nd Stage"},
    {"name": "Whitefield Police Station", "category": "police_station", "latitude": 12.9690, "longitude": 77.7490, "address": "Near Hope Farm, Whitefield"},
    {"name": "Madiwala Police Station", "category": "police_station", "latitude": 12.9220, "longitude": 77.6205, "address": "Hosur Main Road, Near Koramangala / Silk Board"},
    {"name": "Electronic City Police Station", "category": "police_station", "latitude": 12.8512, "longitude": 77.6650, "address": "Phase 1, Electronic City"},
]

# (From, To, Road Name, Distance km, Base Time minutes)
INITIAL_ROADS = [
    # Core Hub Connections
    ("Majestic", "MG Road", "MG Road Corridor via Richmond", 5.5, 15.0),
    ("Majestic", "Malleshwaram", "Sampige Road Link", 3.2, 10.0),
    ("Majestic", "Jayanagar", "KR Road via Lalbagh", 6.8, 18.0),
    ("Majestic", "Yeshwanthpur", "Subramanya Nagar Flyover", 7.0, 16.0),
    ("Malleshwaram", "Yeshwanthpur", "Platform Road Link", 4.1, 10.0),
    ("Malleshwaram", "Hebbal", "Mekhri Circle Expressway", 6.5, 14.0),
    ("Hebbal", "Majestic", "Bellary Road Flyover", 8.5, 20.0),

    ("MG Road", "Indiranagar", "Old Madras Road / 100ft Road", 4.8, 12.0),
    ("MG Road", "Koramangala", "Hosur Road via Richmond", 6.2, 16.0),
    ("MG Road", "Jayanagar", "Mission Road / Double Road", 5.9, 15.0),

    ("Indiranagar", "Marathahalli", "Old Airport Road Express", 7.5, 18.0),
    ("Indiranagar", "Koramangala", "Intermediate Ring Road (IRR)", 5.2, 14.0),

    ("Marathahalli", "Whitefield", "Varthur / ITPL Main Road", 8.0, 20.0),
    ("Indiranagar", "Whitefield", "Tin Factory / Old Madras Road", 14.0, 32.0),

    ("Koramangala", "HSR Layout", "Silk Board Flyover / ORR", 4.5, 12.0),
    ("Koramangala", "Jayanagar", "Sarjapur Road / Madiwala Link", 4.8, 13.0),

    ("HSR Layout", "Electronic City", "Hosur Elevated Tollway", 11.5, 18.0),
    ("HSR Layout", "Marathahalli", "Outer Ring Road (ORR) East", 8.2, 22.0),

    ("Jayanagar", "Bannerghatta Road", "Bannerghatta Main Road", 5.0, 14.0),
    ("Bannerghatta Road", "Electronic City", "NICE Ring Road South", 13.0, 20.0),

    ("Yeshwanthpur", "Hebbal", "Outer Ring Road North", 7.8, 16.0),

    # Emergency Connections: Hospitals
    ("Majestic", "Victoria Hospital", "Fort City Hospital Road", 1.8, 6.0),
    ("Jayanagar", "Victoria Hospital", "KR Market Link", 4.2, 11.0),
    ("Indiranagar", "Manipal Hospital", "HAL Airport Hospital Road", 2.1, 7.0),
    ("Marathahalli", "Manipal Hospital", "Old Airport Inbound", 5.6, 14.0),
    ("Hebbal", "Columbia Asia Hospital", "Hebbal Lake Road", 1.2, 4.0),
    ("Yeshwanthpur", "Columbia Asia Hospital", "ORR Hebbal Link", 7.2, 15.0),
    ("Electronic City", "Narayana Health City", "Bommasandra Link", 5.2, 10.0),
    ("Bannerghatta Road", "Apollo Hospital", "Krishnaraju Layout Road", 1.4, 4.0),
    ("Jayanagar", "Apollo Hospital", "Jayanagar 9th Block Link", 4.6, 12.0),
    ("Marathahalli", "Sakra World Hospital", "Bellandur ORR Link", 3.8, 9.0),
    ("HSR Layout", "Sakra World Hospital", "Outer Ring Road Bellandur", 4.9, 11.0),

    # Emergency Connections: Police Stations
    ("Majestic", "Upparpet Police Station", "Subhash Nagar Lane", 0.6, 3.0),
    ("MG Road", "Cubbon Park Police Station", "Kasturba Road Pass", 1.5, 5.0),
    ("Majestic", "Cubbon Park Police Station", "Ambedkar Veedhi", 3.4, 9.0),
    ("Indiranagar", "Indiranagar Police Station", "100ft Road Hub Link", 0.9, 3.0),
    ("Whitefield", "Whitefield Police Station", "Hope Farm Bypass", 1.1, 3.0),
    ("Marathahalli", "Whitefield Police Station", "Kundalahalli Link", 7.2, 17.0),
    ("Koramangala", "Madiwala Police Station", "Silk Board Police Lane", 2.2, 6.0),
    ("HSR Layout", "Madiwala Police Station", "Hosur Road Junction", 2.6, 7.0),
    ("Electronic City", "Electronic City Police Station", "Phase 1 Station Road", 1.2, 3.0),
]

def seed_database(db: Session):
    """Seed initial locations and road network if empty."""
    loc_count = db.query(Location).count()
    if loc_count > 0:
        logger.info(f"Database already has {loc_count} locations. Skipping seed.")
        return

    logger.info("Seeding database with Bengaluru hubs and roads...")

    loc_map = {}
    for item in INITIAL_LOCATIONS:
        loc = Location(
            name=item["name"],
            category=item["category"],
            latitude=item["latitude"],
            longitude=item["longitude"],
            address=item["address"]
        )
        db.add(loc)
        db.flush()
        loc_map[loc.name] = loc

    # Add bidirectional edges
    for from_name, to_name, road_name, dist_km, base_min in INITIAL_ROADS:
        if from_name in loc_map and to_name in loc_map:
            u = loc_map[from_name]
            v = loc_map[to_name]

            # Forward edge
            e1 = RoadEdge(
                from_location_id=u.id,
                to_location_id=v.id,
                road_name=road_name,
                distance_km=dist_km,
                base_time_minutes=base_min,
                is_closed=False
            )
            # Backward edge
            e2 = RoadEdge(
                from_location_id=v.id,
                to_location_id=u.id,
                road_name=road_name,
                distance_km=dist_km,
                base_time_minutes=base_min,
                is_closed=False
            )
            db.add_all([e1, e2])

    db.commit()
    logger.info("Database seeding complete!")
