"""Approximate town centres used to build the SYNTHETIC demand potential surface for the coverage map.

All numbers are rough assumptions for a hackathon prototype, NOT census data:
  weight    = relative market size (bigger city = bigger weight)
  spread_km = how far the town's demand reaches around its centre
Replace this file with real population / market data when it becomes available.
"""

TOWNS = [
    {"name": "Dhaka", "division": "Dhaka", "lat": 23.81, "lon": 90.41, "weight": 3.0, "spread_km": 20},
    {"name": "Gazipur", "division": "Dhaka", "lat": 24.00, "lon": 90.42, "weight": 1.6, "spread_km": 15},
    {"name": "Narayanganj", "division": "Dhaka", "lat": 23.62, "lon": 90.50, "weight": 1.5, "spread_km": 12},
    {"name": "Tangail", "division": "Dhaka", "lat": 24.25, "lon": 89.92, "weight": 0.7, "spread_km": 12},
    {"name": "Faridpur", "division": "Dhaka", "lat": 23.60, "lon": 89.84, "weight": 0.6, "spread_km": 11},
    {"name": "Narsingdi", "division": "Dhaka", "lat": 23.92, "lon": 90.72, "weight": 0.7, "spread_km": 11},
    {"name": "Manikganj", "division": "Dhaka", "lat": 23.86, "lon": 90.00, "weight": 0.5, "spread_km": 10},
    {"name": "Kishoreganj", "division": "Dhaka", "lat": 24.43, "lon": 90.78, "weight": 0.6, "spread_km": 11},
    {"name": "Madaripur", "division": "Dhaka", "lat": 23.17, "lon": 90.20, "weight": 0.5, "spread_km": 10},
    {"name": "Chattogram", "division": "Chattogram", "lat": 22.36, "lon": 91.78, "weight": 2.2, "spread_km": 18},
    {"name": "Cumilla", "division": "Chattogram", "lat": 23.46, "lon": 91.18, "weight": 1.1, "spread_km": 13},
    {"name": "Cox's Bazar", "division": "Chattogram", "lat": 21.43, "lon": 91.98, "weight": 0.8, "spread_km": 11},
    {"name": "Noakhali", "division": "Chattogram", "lat": 22.82, "lon": 91.10, "weight": 0.8, "spread_km": 11},
    {"name": "Feni", "division": "Chattogram", "lat": 23.02, "lon": 91.40, "weight": 0.6, "spread_km": 10},
    {"name": "Brahmanbaria", "division": "Chattogram", "lat": 23.96, "lon": 91.11, "weight": 0.7, "spread_km": 11},
    {"name": "Rajshahi", "division": "Rajshahi", "lat": 24.37, "lon": 88.60, "weight": 1.0, "spread_km": 13},
    {"name": "Bogura", "division": "Rajshahi", "lat": 24.85, "lon": 89.37, "weight": 0.9, "spread_km": 12},
    {"name": "Pabna", "division": "Rajshahi", "lat": 24.00, "lon": 89.23, "weight": 0.7, "spread_km": 11},
    {"name": "Natore", "division": "Rajshahi", "lat": 24.41, "lon": 88.99, "weight": 0.5, "spread_km": 10},
    {"name": "Khulna", "division": "Khulna", "lat": 22.82, "lon": 89.55, "weight": 1.2, "spread_km": 14},
    {"name": "Jashore", "division": "Khulna", "lat": 23.17, "lon": 89.21, "weight": 0.8, "spread_km": 12},
    {"name": "Kushtia", "division": "Khulna", "lat": 23.90, "lon": 89.12, "weight": 0.6, "spread_km": 11},
    {"name": "Satkhira", "division": "Khulna", "lat": 22.72, "lon": 89.07, "weight": 0.5, "spread_km": 10},
    {"name": "Barishal", "division": "Barishal", "lat": 22.70, "lon": 90.37, "weight": 0.9, "spread_km": 12},
    {"name": "Patuakhali", "division": "Barishal", "lat": 22.36, "lon": 90.33, "weight": 0.5, "spread_km": 10},
    {"name": "Bhola", "division": "Barishal", "lat": 22.69, "lon": 90.65, "weight": 0.4, "spread_km": 10},
    {"name": "Sylhet", "division": "Sylhet", "lat": 24.90, "lon": 91.87, "weight": 1.3, "spread_km": 14},
    {"name": "Sunamganj", "division": "Sylhet", "lat": 25.07, "lon": 91.40, "weight": 0.6, "spread_km": 11},
    {"name": "Moulvibazar", "division": "Sylhet", "lat": 24.48, "lon": 91.77, "weight": 0.6, "spread_km": 10},
    {"name": "Habiganj", "division": "Sylhet", "lat": 24.38, "lon": 91.42, "weight": 0.5, "spread_km": 10},
    {"name": "Rangpur", "division": "Rangpur", "lat": 25.75, "lon": 89.25, "weight": 1.0, "spread_km": 13},
    {"name": "Dinajpur", "division": "Rangpur", "lat": 25.63, "lon": 88.64, "weight": 0.8, "spread_km": 11},
    {"name": "Kurigram", "division": "Rangpur", "lat": 25.81, "lon": 89.64, "weight": 0.5, "spread_km": 10},
    {"name": "Gaibandha", "division": "Rangpur", "lat": 25.33, "lon": 89.54, "weight": 0.5, "spread_km": 10},
    {"name": "Thakurgaon", "division": "Rangpur", "lat": 26.03, "lon": 88.46, "weight": 0.4, "spread_km": 10},
    {"name": "Mymensingh", "division": "Mymensingh", "lat": 24.75, "lon": 90.41, "weight": 1.0, "spread_km": 13},
    {"name": "Jamalpur", "division": "Mymensingh", "lat": 24.92, "lon": 89.94, "weight": 0.6, "spread_km": 11},
    {"name": "Netrokona", "division": "Mymensingh", "lat": 24.87, "lon": 90.73, "weight": 0.5, "spread_km": 10},
]
