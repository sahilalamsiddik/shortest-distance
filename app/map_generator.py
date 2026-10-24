import io
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless rendering
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Location, RoadEdge
from app.traffic_service import traffic_service

def generate_route_map(
    db: Session,
    path_node_names: Optional[List[str]] = None,
    is_emergency: bool = False,
    emergency_type: Optional[str] = None,
    unreachable_origin: Optional[str] = None,
    unreachable_destination: Optional[str] = None
) -> bytes:
    """
    Renders a crisp, light-themed vector map image of Bengaluru with road network
    and highlighted delivery/emergency route, returning PNG bytes.
    """
    locations = db.query(Location).all()
    loc_by_name = {loc.name: loc for loc in locations}
    loc_by_id = {loc.id: loc for loc in locations}
    edges = db.query(RoadEdge).filter(RoadEdge.is_closed == False).all()

    # Create figure with high DPI and clean light background
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
    fig.patch.set_facecolor("#FAFAFA")
    ax.set_facecolor("#FFFFFF")

    # Draw all roads (background graph)
    drawn_pairs = set()
    for e in edges:
        u = loc_by_id.get(e.from_location_id)
        v = loc_by_id.get(e.to_location_id)
        if not u or not v:
            continue
        pair = tuple(sorted([u.name, v.name]))
        if pair in drawn_pairs:
            continue
        drawn_pairs.add(pair)

        # Base road styling
        ax.plot(
            [u.longitude, v.longitude],
            [u.latitude, v.latitude],
            color="#E2E8F0",
            linewidth=2.5,
            zorder=2,
            linestyle="-"
        )

    # Highlight active route if provided
    path = path_node_names or []
    if len(path) > 1:
        route_color = "#DC2626" if is_emergency else "#2563EB"
        # Draw glowing halo under route
        for i in range(len(path) - 1):
            u = loc_by_name.get(path[i])
            v = loc_by_name.get(path[i + 1])
            if u and v:
                ax.plot(
                    [u.longitude, v.longitude],
                    [u.latitude, v.latitude],
                    color=route_color,
                    alpha=0.3,
                    linewidth=9.0,
                    zorder=4,
                    solid_capstyle="round"
                )
                ax.plot(
                    [u.longitude, v.longitude],
                    [u.latitude, v.latitude],
                    color=route_color,
                    linewidth=4.0,
                    zorder=5,
                    solid_capstyle="round"
                )

    # Plot Nodes
    path_set = set(path)
    for loc in locations:
        x, y = loc.longitude, loc.latitude
        is_in_path = loc.name in path_set
        is_start = path and loc.name == path[0]
        is_end = path and loc.name == path[-1]

        if is_start:
            # Green Start Pin
            ax.scatter(x, y, s=260, color="#16A34A", edgecolors="#FFFFFF", linewidth=2.5, zorder=10)
            ax.text(x, y + 0.005, f"START: {loc.name}", fontsize=8.5, fontweight="bold",
                    color="#14532D", ha="center", va="bottom", zorder=12,
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="#DCFCE7", edgecolor="#86EFAC", alpha=0.9))
        elif is_end:
            # Red/Orange Dest Pin
            pin_color = "#DC2626" if is_emergency else "#EA580C"
            ax.scatter(x, y, s=260, color=pin_color, edgecolors="#FFFFFF", linewidth=2.5, zorder=10)
            label_prefix = f"EMERGENCY ({emergency_type.upper()})" if is_emergency else "DEST"
            ax.text(x, y + 0.005, f"{label_prefix}: {loc.name}", fontsize=8.5, fontweight="bold",
                    color="#7F1D1D" if is_emergency else "#7C2D12", ha="center", va="bottom", zorder=12,
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="#FEE2E2", edgecolor="#FCA5A5", alpha=0.9))
        elif is_in_path:
            # Waypoint
            ax.scatter(x, y, s=140, color="#2563EB", edgecolors="#FFFFFF", linewidth=2, zorder=9)
            ax.text(x, y + 0.004, loc.name, fontsize=7.5, fontweight="semibold", color="#1E3A8A",
                    ha="center", va="bottom", zorder=11,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#EFF6FF", edgecolor="#BFDBFE", alpha=0.85))
        else:
            # Normal Nodes
            if loc.category == "hospital":
                ax.scatter(x, y, s=90, color="#EF4444", marker="P", edgecolors="#B91C1C", linewidth=1, zorder=7)
                ax.text(x, y - 0.004, loc.name, fontsize=6.5, color="#991B1B", ha="center", va="top", zorder=8)
            elif loc.category == "police_station":
                ax.scatter(x, y, s=90, color="#4F46E5", marker="s", edgecolors="#3730A3", linewidth=1, zorder=7)
                ax.text(x, y - 0.004, loc.name, fontsize=6.5, color="#3730A3", ha="center", va="top", zorder=8)
            else:
                ax.scatter(x, y, s=70, color="#64748B", edgecolors="#FFFFFF", linewidth=1.5, zorder=6)
                ax.text(x, y - 0.004, loc.name, fontsize=6.5, color="#475569", ha="center", va="top", zorder=8)

    # If unreachable error message requested
    if unreachable_origin and unreachable_destination:
        ax.text(
            0.5, 0.5,
            f"NO ROUTE FOUND\nBetween '{unreachable_origin}' and '{unreachable_destination}'\nDisconnected road network or closures",
            transform=ax.transAxes,
            ha="center", va="center",
            fontsize=12, fontweight="bold", color="#B91C1C",
            bbox=dict(boxstyle="round,pad=0.8", facecolor="#FEF2F2", edgecolor="#EF4444", alpha=0.95),
            zorder=20
        )

    # Title & Legend formatting
    title_text = "Bengaluru Delivery Route Map"
    if is_emergency:
        title_text = f"SOS EMERGENCY ROUTE -> Nearest {emergency_type.title() if emergency_type else 'Facility'}"
    elif path:
        title_text = f"Route: {path[0]} -> {path[-1]}"

    ax.set_title(title_text, fontsize=12, fontweight="bold", pad=14, color="#0F172A")
    ax.set_xlabel("Longitude (°E)", fontsize=8, color="#64748B")
    ax.set_ylabel("Latitude (°N)", fontsize=8, color="#64748B")
    ax.tick_params(colors="#64748B", labelsize=7.5)

    # Gridlines
    ax.grid(True, linestyle=":", color="#E2E8F0", alpha=0.8)

    # Spines
    for spine in ax.spines.values():
        spine.set_color("#CBD5E1")
        spine.set_linewidth(1.0)

    # Legend elements
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', label='Delivery Hub', markerfacecolor='#64748B', markersize=7),
        plt.Line2D([0], [0], marker='P', color='w', label='Hospital (SOS)', markerfacecolor='#EF4444', markersize=7),
        plt.Line2D([0], [0], marker='s', color='w', label='Police Station (SOS)', markerfacecolor='#4F46E5', markersize=7),
        plt.Line2D([0], [0], color='#2563EB', lw=3, label='Active Route'),
    ]
    ax.legend(handles=legend_elements, loc="lower left", fontsize=7.5, framealpha=0.9, facecolor="#FFFFFF", edgecolor="#E2E8F0")

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
