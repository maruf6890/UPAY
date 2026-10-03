OPEN_HOURS = list(range(7, 23))      # agents trade 07:00-22:59 -> 16 rows per agent-day
N_OPEN = len(OPEN_HOURS)
Z90 = 1.2815515655446004             # standard-normal 90th percentile
QUANTILES = {"q10": 0.1, "q50": 0.5, "q90": 0.9}

ARCH_CODES = {"urban_market": 0, "garment_zone": 1, "rural_remittance": 2, "transit_hub": 3}
AREA_CODES = {"urban": 0, "semi_urban": 1, "rural": 2}

REPORTING_THRESHOLD_BDT = 50_000     # ASSUMPTION: illustrative single-transaction reporting threshold


def agent_code(agent_id: int) -> str:
    return f"AG{int(agent_id):04d}"


def parse_agent_code(code: str) -> int:
    code = str(code).upper().strip()
    return int(code[2:]) if code.startswith("AG") else int(code)
