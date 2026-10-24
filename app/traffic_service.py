import os
import csv
import logging
from typing import Dict, Any, List, Tuple
from app.config import settings

logger = logging.getLogger(__name__)

class TrafficService:
    def __init__(self, csv_path=None):
        self.csv_path = csv_path or settings.TRAFFIC_CSV_PATH
        self._last_mtime = 0.0
        self._pair_delays: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._road_delays: Dict[str, Dict[str, Any]] = {}
        self._all_records: List[Dict[str, Any]] = []
        self._ensure_loaded()

    def _ensure_loaded(self, force=False):
        """Check file modification time and reload if changed or forced."""
        if not os.path.exists(self.csv_path):
            logger.warning(f"Traffic CSV file not found at: {self.csv_path}")
            return

        try:
            current_mtime = os.path.getmtime(self.csv_path)
            if force or current_mtime > self._last_mtime:
                self._load_csv()
                self._last_mtime = current_mtime
                logger.info(f"Loaded {len(self._all_records)} traffic delay records from CSV (mtime: {current_mtime})")
        except Exception as e:
            logger.error(f"Error checking traffic CSV mtime: {e}")

    def _load_csv(self):
        pair_delays = {}
        road_delays = {}
        all_records = []

        with open(self.csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                road_name = row.get("road_name", "").strip()
                from_loc = row.get("from_location", "").strip().lower()
                to_loc = row.get("to_location", "").strip().lower()
                
                try:
                    delay_min = float(row.get("delay_minutes", 0.0))
                except ValueError:
                    delay_min = 0.0

                try:
                    factor = float(row.get("traffic_factor", 1.0))
                except ValueError:
                    factor = 1.0

                condition = row.get("condition", "Normal flow").strip()
                notes = row.get("notes", "").strip()

                record = {
                    "road_name": road_name,
                    "from_location": row.get("from_location", "").strip(),
                    "to_location": row.get("to_location", "").strip(),
                    "delay_minutes": delay_min,
                    "traffic_factor": factor,
                    "condition": condition,
                    "notes": notes
                }
                all_records.append(record)

                # Store by bidirectional location pair
                if from_loc and to_loc:
                    pair_delays[(from_loc, to_loc)] = record
                    pair_delays[(to_loc, from_loc)] = record

                # Store by road name
                if road_name:
                    road_delays[road_name.lower()] = record

        self._pair_delays = pair_delays
        self._road_delays = road_delays
        self._all_records = all_records

    def get_edge_traffic(self, from_name: str, to_name: str, road_name: str = "") -> Dict[str, Any]:
        """
        Get traffic delay and factor for a given segment.
        Automatically checks if the CSV file was modified.
        """
        self._ensure_loaded()

        f_lower = from_name.strip().lower()
        t_lower = to_name.strip().lower()

        # Check by pair
        if (f_lower, t_lower) in self._pair_delays:
            return self._pair_delays[(f_lower, t_lower)]

        # Check by road name
        if road_name:
            r_lower = road_name.strip().lower()
            if r_lower in self._road_delays:
                return self._road_delays[r_lower]

        # Default fallback
        return {
            "road_name": road_name,
            "from_location": from_name,
            "to_location": to_name,
            "delay_minutes": 0.0,
            "traffic_factor": 1.0,
            "condition": "Normal Flow",
            "notes": ""
        }

    def get_all_delays(self) -> List[Dict[str, Any]]:
        self._ensure_loaded()
        return self._all_records

    def force_reload(self) -> int:
        self._ensure_loaded(force=True)
        return len(self._all_records)

traffic_service = TrafficService()
