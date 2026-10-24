import heapq
import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models import Location, RoadEdge
from app.traffic_service import traffic_service

logger = logging.getLogger(__name__)

class RouteResult:
    def __init__(
        self,
        found: bool,
        message: str = "",
        origin: str = "",
        destination: str = "",
        criteria: str = "time",
        path: List[str] = None,
        total_distance_km: float = 0.0,
        total_time_minutes: float = 0.0,
        free_flow_time_minutes: float = 0.0,
        traffic_delay_minutes: float = 0.0,
        directions: List[Dict[str, Any]] = None,
        is_emergency: bool = False,
        emergency_type: Optional[str] = None
    ):
        self.found = found
        self.message = message
        self.origin = origin
        self.destination = destination
        self.criteria = criteria
        self.path = path or []
        self.total_distance_km = round(total_distance_km, 2)
        self.total_time_minutes = round(total_time_minutes, 2)
        self.free_flow_time_minutes = round(free_flow_time_minutes, 2)
        self.traffic_delay_minutes = round(traffic_delay_minutes, 2)
        self.directions = directions or []
        self.is_emergency = is_emergency
        self.emergency_type = emergency_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "found": self.found,
            "message": self.message,
            "origin": self.origin,
            "destination": self.destination,
            "criteria": self.criteria,
            "path": self.path,
            "total_distance_km": self.total_distance_km,
            "total_time_minutes": self.total_time_minutes,
            "free_flow_time_minutes": self.free_flow_time_minutes,
            "traffic_delay_minutes": self.traffic_delay_minutes,
            "directions": self.directions,
            "is_emergency": self.is_emergency,
            "emergency_type": self.emergency_type
        }

class RoutingEngine:
    def __init__(self, db: Session):
        self.db = db
        self.locations: Dict[int, Location] = {}
        self.name_to_id: Dict[str, int] = {}
        self.graph: Dict[int, List[Dict[str, Any]]] = {}
        self._build_graph()

    def _build_graph(self):
        locs = self.db.query(Location).all()
        for loc in locs:
            self.locations[loc.id] = loc
            self.name_to_id[loc.name.strip().lower()] = loc.id
            self.graph[loc.id] = []

        edges = self.db.query(RoadEdge).filter(RoadEdge.is_closed == False).all()
        for e in edges:
            if e.from_location_id in self.graph and e.to_location_id in self.graph:
                self.graph[e.from_location_id].append({
                    "edge_id": e.id,
                    "to_id": e.to_location_id,
                    "road_name": e.road_name,
                    "distance_km": float(e.distance_km),
                    "base_time_minutes": float(e.base_time_minutes)
                })

    def find_route(self, origin_name: str, destination_name: str, criteria: str = "time") -> RouteResult:
        orig_key = origin_name.strip().lower()
        dest_key = destination_name.strip().lower()

        if orig_key not in self.name_to_id:
            return RouteResult(
                found=False,
                message=f"Starting location '{origin_name}' not found in database.",
                origin=origin_name,
                destination=destination_name,
                criteria=criteria
            )

        if dest_key not in self.name_to_id:
            return RouteResult(
                found=False,
                message=f"Destination location '{destination_name}' not found in database.",
                origin=origin_name,
                destination=destination_name,
                criteria=criteria
            )

        start_id = self.name_to_id[orig_key]
        dest_id = self.name_to_id[dest_key]

        if start_id == dest_id:
            loc = self.locations[start_id]
            return RouteResult(
                found=True,
                message="Origin and destination are identical.",
                origin=loc.name,
                destination=loc.name,
                criteria=criteria,
                path=[loc.name],
                total_distance_km=0.0,
                total_time_minutes=0.0
            )

        # Dijkstra algorithm
        # Priority queue item: (cost, current_node_id)
        pq = [(0.0, start_id)]
        costs = {start_id: 0.0}
        prev_nodes: Dict[int, Optional[int]] = {start_id: None}
        prev_edges: Dict[int, Dict[str, Any]] = {}

        while pq:
            curr_cost, curr_id = heapq.heappop(pq)

            if curr_cost > costs.get(curr_id, float("inf")):
                continue

            if curr_id == dest_id:
                break

            curr_name = self.locations[curr_id].name

            for edge in self.graph.get(curr_id, []):
                next_id = edge["to_id"]
                next_name = self.locations[next_id].name

                # Query traffic delay
                traffic_info = traffic_service.get_edge_traffic(curr_name, next_name, edge["road_name"])
                delay = traffic_info.get("delay_minutes", 0.0)
                factor = traffic_info.get("traffic_factor", 1.0)

                base_time = edge["base_time_minutes"]
                dist = edge["distance_km"]

                # Weight calculation
                if criteria.lower() == "distance":
                    weight = dist
                else:  # 'time'
                    weight = (base_time * factor) + delay

                new_cost = curr_cost + weight

                if new_cost < costs.get(next_id, float("inf")):
                    costs[next_id] = new_cost
                    prev_nodes[next_id] = curr_id
                    prev_edges[next_id] = {
                        "edge": edge,
                        "delay": delay,
                        "factor": factor,
                        "effective_time": (base_time * factor) + delay,
                        "condition": traffic_info.get("condition", "Normal")
                    }
                    heapq.heappush(pq, (new_cost, next_id))

        if dest_id not in prev_nodes:
            # Unreachable
            return RouteResult(
                found=False,
                message=f"No route found between '{origin_name}' and '{destination_name}'. The path is disconnected or road closures prevent access.",
                origin=self.locations[start_id].name,
                destination=self.locations[dest_id].name,
                criteria=criteria
            )

        # Reconstruct path
        path_ids = []
        curr = dest_id
        while curr is not None:
            path_ids.append(curr)
            curr = prev_nodes[curr]
        path_ids.reverse()

        path_names = [self.locations[node_id].name for node_id in path_ids]

        # Compute totals & turn-by-turn directions
        total_dist = 0.0
        total_time = 0.0
        free_flow_time = 0.0
        traffic_delay = 0.0
        directions = []

        for step, i in enumerate(range(len(path_ids) - 1), start=1):
            u_id = path_ids[i]
            v_id = path_ids[i + 1]
            u_name = self.locations[u_id].name
            v_name = self.locations[v_id].name

            edge_data = prev_edges[v_id]
            edge_info = edge_data["edge"]

            dist = edge_info["distance_km"]
            base_t = edge_info["base_time_minutes"]
            eff_t = edge_data["effective_time"]
            delay_t = edge_data["delay"]
            condition = edge_data["condition"]

            total_dist += dist
            total_time += eff_t
            free_flow_time += base_t
            traffic_delay += (eff_t - base_t)

            directions.append({
                "step": step,
                "from_node": u_name,
                "to_node": v_name,
                "road_name": edge_info["road_name"],
                "distance_km": round(dist, 2),
                "time_minutes": round(eff_t, 1),
                "delay_minutes": round(delay_t, 1),
                "condition": condition
            })

        return RouteResult(
            found=True,
            message="Optimal route successfully calculated.",
            origin=self.locations[start_id].name,
            destination=self.locations[dest_id].name,
            criteria=criteria,
            path=path_names,
            total_distance_km=total_dist,
            total_time_minutes=total_time,
            free_flow_time_minutes=free_flow_time,
            traffic_delay_minutes=traffic_delay,
            directions=directions,
            is_emergency=False
        )

    def find_nearest_emergency(self, current_location_name: str, service_type: str = "hospital") -> RouteResult:
        """
        Calculates shortest path to the closest hospital or police station from current location.
        """
        curr_key = current_location_name.strip().lower()
        if curr_key not in self.name_to_id:
            return RouteResult(
                found=False,
                message=f"Current location '{current_location_name}' not found in database.",
                origin=current_location_name,
                criteria="time",
                is_emergency=True,
                emergency_type=service_type
            )

        # Get all emergency locations of the requested category
        target_locs = [
            loc for loc in self.locations.values()
            if loc.category.lower() == service_type.strip().lower()
        ]

        if not target_locs:
            return RouteResult(
                found=False,
                message=f"No facilities registered for emergency type '{service_type}'.",
                origin=current_location_name,
                criteria="time",
                is_emergency=True,
                emergency_type=service_type
            )

        # Run routing to each target facility and pick the best (fastest ETA)
        best_result: Optional[RouteResult] = None
        min_time = float("inf")

        for target in target_locs:
            res = self.find_route(current_location_name, target.name, criteria="time")
            if res.found:
                if res.total_time_minutes < min_time:
                    min_time = res.total_time_minutes
                    best_result = res

        if not best_result:
            return RouteResult(
                found=False,
                message=f"No accessible {service_type.replace('_', ' ')} found from {current_location_name}.",
                origin=current_location_name,
                criteria="time",
                is_emergency=True,
                emergency_type=service_type
            )

        best_result.is_emergency = True
        best_result.emergency_type = service_type
        best_result.message = f"EMERGENCY DISPATCH: Closest {service_type.replace('_', ' ')} is '{best_result.destination}' ({best_result.total_distance_km} km, ~{best_result.total_time_minutes} min)."
        return best_result
