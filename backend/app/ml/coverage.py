"""C1 - Coverage gap map (H3 hexagons).

For every hexagon we compare
    DEMAND  = how much mobile-money activity the area could generate (census-population potential surface, see app/data/bd_towns.py), with
    SUPPLY  = how much our agents there actually handle (observed volume of the last 28 days).

Gap types (checked in this order):
    CAPACITY_GAP  agents exist but lose much more demand to stockouts than the network median (OBSERVED)
    NO_COVERAGE   real demand, but no agent in the hexagon or its neighbours    (needs the demand assumption)
    UNDER_SERVED  agents nearby, but they handle less than half of the demand   (needs the demand assumption)
    OVER_SUPPLIED agents handle more than twice the demand
    LOW_DEMAND    too little demand to matter
    BALANCED      everything else

HONEST NOTE: the demand surface is a documented assumption (see app/data/bd_towns.py).
It is scaled so that areas where we already have agents are "in balance" on average,
so the map shows RELATIVE gaps, not absolute truth.
"""
import math
import statistics

import h3

from app.ml.rebalance import haversine_km

H3_RESOLUTION = 5            # about 250 km2 per hexagon
SEARCH_RINGS = 3             # hexagons considered around every town centre
MIN_DEMAND_INDEX = 0.03      # drop hexagons with almost no demand potential

CENTER_SHARE = 0.5           # an agent's volume: 50% in its own hexagon ...
# ... and the other 50% spread over the 6 neighbouring hexagons (customers travel a few km)

CAPACITY_GAP_MIN_SHARE = 0.04       # never flag below 4% unserved demand
CAPACITY_GAP_VS_MEDIAN = 2.0        # flag hexagons that lose at least 2x the network's median share
# (relative on purpose: the whole network loses more around Eid, so a fixed limit would flag everything)
UNDER_SERVED_RATIO = 0.5
OVER_SUPPLIED_RATIO = 2.0
LOW_DEMAND_SHARE = 0.25      # below 25% of the typical covered hexagon's demand = LOW_DEMAND
MAX_AGENTS_RECOMMENDED = 8


# ---------------------------------------------------------------- demand surface
def demand_at_point(lat, lon, towns):
    """Sum of bell-shaped demand from every town. Returns (demand_index, nearest_town_name)."""
    total = 0.0
    nearest_name = ""
    nearest_distance = 1e9
    for town in towns:
        distance = haversine_km(lat, lon, town["lat"], town["lon"])
        spread = town["spread_km"]
        total = total + town["weight"] * math.exp(-0.5 * (distance / spread) ** 2)
        if distance < nearest_distance:
            nearest_distance = distance
            nearest_name = town["name"]
    return total, nearest_name


def build_cells(towns, agent_cells):
    """One entry per hexagon near a town (plus any hexagon that holds an agent)."""
    cell_ids = set()
    for town in towns:
        center = h3.latlng_to_cell(town["lat"], town["lon"], H3_RESOLUTION)
        for cell_id in h3.grid_disk(center, SEARCH_RINGS):
            cell_ids.add(cell_id)
    for cell_id in agent_cells:
        cell_ids.add(cell_id)

    cells = {}
    for cell_id in cell_ids:
        lat, lon = h3.cell_to_latlng(cell_id)
        demand_index, nearest_town = demand_at_point(lat, lon, towns)
        if demand_index < MIN_DEMAND_INDEX and cell_id not in agent_cells:
            continue
        cells[cell_id] = {
            "h3": cell_id,
            "lat": lat,
            "lon": lon,
            "nearest_town": nearest_town,
            "demand_index": demand_index,
            "supply_bdt": 0.0,
            "own_volume_bdt": 0.0,
            "unserved_bdt": 0.0,
            "agents_in_cell": [],
            "agents_nearby": [],
        }
    return cells


# ---------------------------------------------------------------- supply
def agent_cell_id(lat, lon):
    return h3.latlng_to_cell(lat, lon, H3_RESOLUTION)


def add_supply(cells, agent_rows):
    """agent_rows: list of dicts with agent_code, lat, lon, monthly_volume_bdt, unserved_bdt."""
    for agent in agent_rows:
        own_cell = agent_cell_id(agent["lat"], agent["lon"])
        neighbours = []
        for cell_id in h3.grid_disk(own_cell, 1):
            if cell_id != own_cell:
                neighbours.append(cell_id)

        volume = agent["monthly_volume_bdt"]
        if own_cell in cells:
            cells[own_cell]["supply_bdt"] = cells[own_cell]["supply_bdt"] + CENTER_SHARE * volume
            cells[own_cell]["own_volume_bdt"] = cells[own_cell]["own_volume_bdt"] + volume
            cells[own_cell]["unserved_bdt"] = cells[own_cell]["unserved_bdt"] + agent["unserved_bdt"]
            cells[own_cell]["agents_in_cell"].append(agent["agent_code"])
            cells[own_cell]["agents_nearby"].append(agent["agent_code"])

        share_each = (1.0 - CENTER_SHARE) * volume / len(neighbours)
        for cell_id in neighbours:
            if cell_id in cells:
                cells[cell_id]["supply_bdt"] = cells[cell_id]["supply_bdt"] + share_each
                cells[cell_id]["agents_nearby"].append(agent["agent_code"])
    return cells


# ---------------------------------------------------------------- calibration and classification
def calibrate_scale(cells):
    """BDT per demand-index point, chosen so that hexagons that already contain agents are in balance
    on average (median supply / demand = 1). Returns (scale, median_demand_of_covered_cells_in_bdt)."""
    ratios = []
    for cell in cells.values():
        if len(cell["agents_in_cell"]) > 0 and cell["demand_index"] > 0:
            ratios.append(cell["supply_bdt"] / cell["demand_index"])
    if len(ratios) == 0:
        return 1.0
    return statistics.median(ratios)


def classify_cells(cells, scale):
    covered_demands = []
    for cell in cells.values():
        cell["demand_bdt"] = cell["demand_index"] * scale
        if len(cell["agents_in_cell"]) > 0:
            covered_demands.append(cell["demand_bdt"])

    low_demand_limit = 0.0
    if len(covered_demands) > 0:
        low_demand_limit = LOW_DEMAND_SHARE * statistics.median(covered_demands)

    # capacity-gap limit: twice the median unserved share of hexagons that contain agents (but at least 4%)
    unserved_shares = []
    for cell in cells.values():
        if cell["own_volume_bdt"] > 0:
            unserved_shares.append(cell["unserved_bdt"] / cell["own_volume_bdt"])
    capacity_limit = CAPACITY_GAP_MIN_SHARE
    if len(unserved_shares) > 0:
        relative_limit = CAPACITY_GAP_VS_MEDIAN * statistics.median(unserved_shares)
        if relative_limit > capacity_limit:
            capacity_limit = relative_limit

    for cell in cells.values():
        demand = cell["demand_bdt"]
        supply = cell["supply_bdt"]
        cell["coverage_ratio"] = 0.0
        if demand > 0:
            cell["coverage_ratio"] = supply / demand
        cell["untapped_bdt"] = max(demand - supply, 0.0)

        unserved_share = 0.0
        if cell["own_volume_bdt"] > 0:
            unserved_share = cell["unserved_bdt"] / cell["own_volume_bdt"]
        cell["unserved_share"] = unserved_share

        has_agents_inside = len(cell["agents_in_cell"]) > 0
        has_agents_nearby = len(cell["agents_nearby"]) > 0

        if has_agents_inside and unserved_share >= capacity_limit:
            gap_type = "CAPACITY_GAP"
        elif demand < low_demand_limit and not has_agents_inside:
            gap_type = "LOW_DEMAND"
        elif not has_agents_nearby:
            gap_type = "NO_COVERAGE"
        elif cell["coverage_ratio"] < UNDER_SERVED_RATIO:
            gap_type = "UNDER_SERVED"
        elif cell["coverage_ratio"] > OVER_SUPPLIED_RATIO:
            gap_type = "OVER_SUPPLIED"
        else:
            gap_type = "BALANCED"
        cell["gap_type"] = gap_type
    return cells


# ---------------------------------------------------------------- recommendation (plain business rules)
def recommend(cell, typical_agent_volume, commission_rate):
    gap_type = cell["gap_type"]
    town = cell["nearest_town"]

    if gap_type in ("NO_COVERAGE", "UNDER_SERVED"):
        needed = 1
        if typical_agent_volume > 0:
            needed = math.ceil(cell["untapped_bdt"] / typical_agent_volume)
        if needed < 1:
            needed = 1
        if needed > MAX_AGENTS_RECOMMENDED:
            needed = MAX_AGENTS_RECOMMENDED
        cell["agents_needed"] = needed
        cell["opportunity_commission_bdt"] = cell["untapped_bdt"] * commission_rate
        if gap_type == "NO_COVERAGE":
            return f"Recruit about {needed} agent(s) near {town}: demand exists but no agent is within reach."
        return f"Recruit about {needed} more agent(s) near {town}: nearby agents cover less than half of the demand."

    cell["agents_needed"] = 0
    cell["opportunity_commission_bdt"] = cell["unserved_bdt"] * commission_rate
    if gap_type == "CAPACITY_GAP":
        return (f"Agents near {town} lose about ৳{cell['unserved_bdt']:,.0f} a month to stockouts. "
                f"Improve cash / e-float supply there before recruiting more agents.")
    if gap_type == "OVER_SUPPLIED":
        return f"Enough agents near {town}. Do not recruit more here."
    return "No action needed."


# ---------------------------------------------------------------- output helpers
def cell_polygon(cell_id):
    """GeoJSON ring in [longitude, latitude] order, closed."""
    ring = []
    for lat, lon in h3.cell_to_boundary(cell_id):
        ring.append([round(lon, 5), round(lat, 5)])
    ring.append(ring[0])
    return ring