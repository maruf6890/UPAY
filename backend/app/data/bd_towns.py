"""Town centres used to build the demand-potential surface for the coverage map.

How a town's weight is set (one source, one formula):

    weight = DHAKA_WEIGHT * (town population / Dhaka population) ** WEIGHT_EXPONENT

  * population: urban population from the Bangladesh Bureau of Statistics, Population and Housing Census 2022
    (the national report's table of the 46 "cities" with more than 100,000 people, pp. 388-394).
  * exponent 0.5 (square root): a district town also serves rural customers that an urban head-count leaves out,
    so demand grows more slowly than population. Tested from 0.3 to 1.0: the map keeps its character up to about 0.5,
    and above 0.7 Dhaka itself becomes the biggest gap. The exponent is the ONE assumption in the formula.
  * DHAKA_WEIGHT = 3.0 only fixes the scale. The coverage module rescales demand to money, but its cut-offs
    (MIN_DEMAND_INDEX) are written in these units, so keep it at 3.0 unless you change them too.
  * 10 of the 38 towns are under the 100,000 "city" line and have no figure in that table. They get
    PLACEHOLDER_POPULATION. Replace them with the pourashava figures from the census report when you have them.

  spread_km = how far a town's demand reaches around its centre. This is still an ASSUMPTION (bigger towns reach further)
  and it moves the map more than the weights do; see the sensitivity notes in the coverage brief.

Do NOT add a weight component built from our own agents' volume: the coverage calibration already ties demand to supply,
so it would be circular.
"""
from __future__ import annotations

WEIGHT_EXPONENT = 0.5
DHAKA_WEIGHT = 3.0
PLACEHOLDER_POPULATION = 50_000      # half the 100,000 "city" threshold; used only where the census table has no figure

# BBS Population and Housing Census 2022, urban population of cities (> 100,000)
CENSUS_2022_URBAN_POPULATION = {
    'Dhaka': 10_295_786,
    'Chattogram': 3_230_507,
    'Gazipur': 2_677_715,
    'Narayanganj': 967_951,
    'Khulna': 719_557,
    'Rangpur': 708_570,
    'Mymensingh': 577_000,
    'Rajshahi': 553_288,
    'Sylhet': 532_839,
    'Bogura': 486_016,
    'Cumilla': 440_233,
    'Barishal': 419_484,
    'Brahmanbaria': 264_341,
    'Faridpur': 237_266,
    'Feni': 234_356,
    'Kushtia': 221_806,
    'Tangail': 212_887,
    'Dinajpur': 212_288,
    'Jashore': 209_352,
    "Cox's Bazar": 196_385,
    'Narsingdi': 180_711,
    'Pabna': 176_005,
    'Jamalpur': 158_889,
    'Satkhira': 138_411,
    'Kishoreganj': 138_063,
    'Noakhali': 132_198,
    'Netrokona': 122_299,
    'Thakurgaon': 100_462,
}

_BASE = [
    {"name": 'Dhaka', "division": 'Dhaka', "lat": 23.81, "lon": 90.41, "spread_km": 20},
    {"name": 'Gazipur', "division": 'Dhaka', "lat": 24.0, "lon": 90.42, "spread_km": 15},
    {"name": 'Narayanganj', "division": 'Dhaka', "lat": 23.62, "lon": 90.5, "spread_km": 12},
    {"name": 'Tangail', "division": 'Dhaka', "lat": 24.25, "lon": 89.92, "spread_km": 12},
    {"name": 'Faridpur', "division": 'Dhaka', "lat": 23.6, "lon": 89.84, "spread_km": 11},
    {"name": 'Narsingdi', "division": 'Dhaka', "lat": 23.92, "lon": 90.72, "spread_km": 11},
    {"name": 'Manikganj', "division": 'Dhaka', "lat": 23.86, "lon": 90.0, "spread_km": 10},
    {"name": 'Kishoreganj', "division": 'Dhaka', "lat": 24.43, "lon": 90.78, "spread_km": 11},
    {"name": 'Madaripur', "division": 'Dhaka', "lat": 23.17, "lon": 90.2, "spread_km": 10},
    {"name": 'Chattogram', "division": 'Chattogram', "lat": 22.36, "lon": 91.78, "spread_km": 18},
    {"name": 'Cumilla', "division": 'Chattogram', "lat": 23.46, "lon": 91.18, "spread_km": 13},
    {"name": "Cox's Bazar", "division": 'Chattogram', "lat": 21.43, "lon": 91.98, "spread_km": 11},
    {"name": 'Noakhali', "division": 'Chattogram', "lat": 22.82, "lon": 91.1, "spread_km": 11},
    {"name": 'Feni', "division": 'Chattogram', "lat": 23.02, "lon": 91.4, "spread_km": 10},
    {"name": 'Brahmanbaria', "division": 'Chattogram', "lat": 23.96, "lon": 91.11, "spread_km": 11},
    {"name": 'Rajshahi', "division": 'Rajshahi', "lat": 24.37, "lon": 88.6, "spread_km": 13},
    {"name": 'Bogura', "division": 'Rajshahi', "lat": 24.85, "lon": 89.37, "spread_km": 12},
    {"name": 'Pabna', "division": 'Rajshahi', "lat": 24.0, "lon": 89.23, "spread_km": 11},
    {"name": 'Natore', "division": 'Rajshahi', "lat": 24.41, "lon": 88.99, "spread_km": 10},
    {"name": 'Khulna', "division": 'Khulna', "lat": 22.82, "lon": 89.55, "spread_km": 14},
    {"name": 'Jashore', "division": 'Khulna', "lat": 23.17, "lon": 89.21, "spread_km": 12},
    {"name": 'Kushtia', "division": 'Khulna', "lat": 23.9, "lon": 89.12, "spread_km": 11},
    {"name": 'Satkhira', "division": 'Khulna', "lat": 22.72, "lon": 89.07, "spread_km": 10},
    {"name": 'Barishal', "division": 'Barishal', "lat": 22.7, "lon": 90.37, "spread_km": 12},
    {"name": 'Patuakhali', "division": 'Barishal', "lat": 22.36, "lon": 90.33, "spread_km": 10},
    {"name": 'Bhola', "division": 'Barishal', "lat": 22.69, "lon": 90.65, "spread_km": 10},
    {"name": 'Sylhet', "division": 'Sylhet', "lat": 24.9, "lon": 91.87, "spread_km": 14},
    {"name": 'Sunamganj', "division": 'Sylhet', "lat": 25.07, "lon": 91.4, "spread_km": 11},
    {"name": 'Moulvibazar', "division": 'Sylhet', "lat": 24.48, "lon": 91.77, "spread_km": 10},
    {"name": 'Habiganj', "division": 'Sylhet', "lat": 24.38, "lon": 91.42, "spread_km": 10},
    {"name": 'Rangpur', "division": 'Rangpur', "lat": 25.75, "lon": 89.25, "spread_km": 13},
    {"name": 'Dinajpur', "division": 'Rangpur', "lat": 25.63, "lon": 88.64, "spread_km": 11},
    {"name": 'Kurigram', "division": 'Rangpur', "lat": 25.81, "lon": 89.64, "spread_km": 10},
    {"name": 'Gaibandha', "division": 'Rangpur', "lat": 25.33, "lon": 89.54, "spread_km": 10},
    {"name": 'Thakurgaon', "division": 'Rangpur', "lat": 26.03, "lon": 88.46, "spread_km": 10},
    {"name": 'Mymensingh', "division": 'Mymensingh', "lat": 24.75, "lon": 90.41, "spread_km": 13},
    {"name": 'Jamalpur', "division": 'Mymensingh', "lat": 24.92, "lon": 89.94, "spread_km": 11},
    {"name": 'Netrokona', "division": 'Mymensingh', "lat": 24.87, "lon": 90.73, "spread_km": 10},
]


def _weight(population: int) -> float:
    return DHAKA_WEIGHT * (population / CENSUS_2022_URBAN_POPULATION["Dhaka"]) ** WEIGHT_EXPONENT


TOWNS = []
for _t in _BASE:
    _census = _t["name"] in CENSUS_2022_URBAN_POPULATION
    _pop = CENSUS_2022_URBAN_POPULATION.get(_t["name"], PLACEHOLDER_POPULATION)
    TOWNS.append({**_t, "weight": round(_weight(_pop), 3), "population": _pop,
                  "population_source": "census_2022" if _census else "placeholder"})