"""Static definitions used by the seed script.

Kept apart from the seeding logic so the cast of the demo (workers, zones,
customers) is easy to read and adjust without touching the generation code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The fictional cooperative that *uses* Nookr. "Sahakaar Nagar" is a
# locality name in the style of Sahakar Nagar in Bengaluru and Pune; it is
# the customer organisation, not the product.
COOPERATIVE_NAME = "Sahakaar Nagar Labour Cooperative"
COOPERATIVE_CODE = "SAHAKAAR-CBE"
COOPERATIVE_CITY = "Coimbatore"
COOPERATIVE_STATE = "Tamil Nadu"


@dataclass(frozen=True)
class ZoneDef:
    name: str
    code: str
    lat: float
    lng: float
    description: str


ZONES: tuple[ZoneDef, ...] = (
    ZoneDef("Zone 1 - Gandhipuram", "Z1", 11.0183, 76.9725, "Central commercial ward"),
    ZoneDef("Zone 2 - R.S. Puram", "Z2", 11.0080, 76.9490, "Dense residential ward"),
    ZoneDef("Zone 3 - Peelamedu", "Z3", 11.0270, 77.0030, "IT corridor and new housing"),
    ZoneDef("Zone 4 - Saibaba Colony", "Z4", 11.0290, 76.9450, "Established residential ward"),
    ZoneDef("Zone 5 - Singanallur", "Z5", 11.0000, 77.0300, "Industrial and suburban ward"),
)


@dataclass(frozen=True)
class WorkerDef:
    full_name: str
    email: str
    phone: str
    service_slug: str
    headline: str
    zone_code: str
    lat: float
    lng: float
    experience_years: int
    weekly_capacity: int
    #: Share of weekly capacity already committed. Drives the seeded bookings
    #: in the current rolling week, which is what workload is measured from.
    target_workload_pct: int
    target_rating: float
    skills: tuple[tuple[str, int], ...]          # (skill slug, proficiency 1-5)
    certifications: tuple[tuple[str, str, str], ...] = ()  # (name, body, skill slug)
    insurance_active: bool = True
    training_credits: int = 0
    availability_status: str = "AVAILABLE"
    days_off: tuple[int, ...] = (6,)             # 6 = Sunday
    bio: str = ""


#: The demo worker. Referenced by the SIH demo scenario.
DEMO_WORKER_EMAIL = "worker@demo.com"
DEMO_CUSTOMER_EMAIL = "customer@demo.com"
DEMO_ADMIN_EMAIL = "admin@demo.com"


WORKERS: tuple[WorkerDef, ...] = (
    # --- plumbing (8) ------------------------------------------------------
    WorkerDef(
        "Kumar Selvan", DEMO_WORKER_EMAIL, "+91 98430 11201", "plumbing", "Plumber",
        "Z2", 11.0080, 76.9490, 11, 12, 42, 4.7,
        (("plumbing", 5), ("pipe-repair", 5), ("water-systems", 4), ("drainage-systems", 3)),
        (("ITI Plumbing Certificate", "Tamil Nadu Skill Development Corporation", "plumbing"),
         ("Advanced Pipe Fitting", "National Skill Development Corporation", "pipe-repair")),
        insurance_active=True, training_credits=2,
        bio="Eleven years on domestic water systems across R.S. Puram and Saibaba Colony.",
    ),
    WorkerDef(
        "Rajesh Nair", "rajesh.nair@sahakaar.coop", "+91 98430 11202", "plumbing", "Senior Plumber",
        "Z2", 11.0123, 76.9490, 15, 12, 85, 4.9,
        (("plumbing", 5), ("pipe-repair", 4), ("sanitary-fitting", 5), ("water-systems", 4)),
        (("ITI Plumbing Certificate", "Tamil Nadu Skill Development Corporation", "plumbing"),),
        training_credits=3,
    ),
    WorkerDef(
        "Anitha Raman", "anitha.raman@sahakaar.coop", "+91 98430 11203", "plumbing", "Plumber",
        "Z2", 11.0030, 76.9530, 7, 12, 78, 4.5,
        (("plumbing", 4), ("drainage-systems", 5), ("sanitary-fitting", 3)),
        (("ITI Plumbing Certificate", "Tamil Nadu Skill Development Corporation", "plumbing"),),
    ),
    WorkerDef(
        "Suresh Babu", "suresh.babu@sahakaar.coop", "+91 98430 11204", "plumbing", "Plumber",
        "Z1", 11.0195, 76.9710, 9, 14, 31, 4.4,
        (("plumbing", 4), ("pipe-repair", 4), ("water-purifier-servicing", 4)),
        (("RO Systems Servicing", "Water Quality India Association", "water-purifier-servicing"),),
    ),
    WorkerDef(
        "Vimal Kannan", "vimal.kannan@sahakaar.coop", "+91 98430 11205", "plumbing", "Junior Plumber",
        "Z3", 11.0261, 77.0045, 3, 12, 24, 4.2,
        (("plumbing", 3), ("pipe-repair", 3)),
        insurance_active=False,
    ),
    WorkerDef(
        "Fathima Beevi", "fathima.beevi@sahakaar.coop", "+91 98430 11206", "plumbing", "Plumber",
        "Z4", 11.0301, 76.9438, 8, 10, 55, 4.6,
        (("plumbing", 4), ("sanitary-fitting", 4), ("water-systems", 3)),
        (("ITI Plumbing Certificate", "Tamil Nadu Skill Development Corporation", "plumbing"),),
        days_off=(4, 6),
    ),
    WorkerDef(
        "Gopal Krishnan", "gopal.krishnan@sahakaar.coop", "+91 98430 11207", "plumbing", "Plumber",
        "Z5", 11.0012, 77.0288, 12, 12, 63, 4.3,
        (("plumbing", 4), ("drainage-systems", 4), ("water-systems", 4)),
    ),
    WorkerDef(
        "Deepa Murugan", "deepa.murugan@sahakaar.coop", "+91 98430 11208", "plumbing", "Plumber",
        "Z1", 11.0170, 76.9741, 6, 12, 71, 4.8,
        (("plumbing", 4), ("pipe-repair", 5), ("sanitary-fitting", 3)),
        training_credits=1,
    ),
    # --- electrical (4) ----------------------------------------------------
    WorkerDef(
        "Arun Prakash", "arun.prakash@sahakaar.coop", "+91 98430 11209", "electrical", "Electrician",
        "Z3", 11.0282, 77.0018, 13, 12, 88, 4.8,
        (("electrical-wiring", 5), ("circuit-repair", 5), ("solar-installation", 4),
         ("lighting-installation", 4)),
        (("Suryamitra Solar PV Technician", "Ministry of New and Renewable Energy", "solar-installation"),
         ("Wireman Licence", "Tamil Nadu Electrical Licensing Board", "electrical-wiring")),
        training_credits=4,
        bio="Handles rooftop solar commissioning across the Peelamedu corridor.",
    ),
    WorkerDef(
        "Meena Lakshmi", "meena.lakshmi@sahakaar.coop", "+91 98430 11210", "electrical", "Electrician",
        "Z1", 11.0191, 76.9733, 9, 12, 82, 4.6,
        (("electrical-wiring", 4), ("circuit-repair", 4), ("lighting-installation", 5),
         ("solar-installation", 3)),
        (("Suryamitra Solar PV Technician", "Ministry of New and Renewable Energy", "solar-installation"),
         ("Wireman Licence", "Tamil Nadu Electrical Licensing Board", "electrical-wiring")),
    ),
    WorkerDef(
        "Ganesh Iyer", "ganesh.iyer@sahakaar.coop", "+91 98430 11211", "electrical", "Senior Electrician",
        "Z2", 11.0071, 76.9505, 17, 12, 90, 4.7,
        (("electrical-wiring", 5), ("circuit-repair", 5), ("inverter-battery", 5),
         ("solar-installation", 4)),
        (("Suryamitra Solar PV Technician", "Ministry of New and Renewable Energy", "solar-installation"),
         ("Wireman Licence", "Tamil Nadu Electrical Licensing Board", "electrical-wiring")),
        training_credits=2,
    ),
    WorkerDef(
        "Nasreen Banu", "nasreen.banu@sahakaar.coop", "+91 98430 11212", "electrical", "Electrician",
        "Z5", 11.0007, 77.0311, 5, 12, 76, 4.4,
        (("electrical-wiring", 4), ("lighting-installation", 4), ("smart-home-automation", 3)),
        (("Wireman Licence", "Tamil Nadu Electrical Licensing Board", "electrical-wiring"),),
    ),
    # --- cleaning (5) ------------------------------------------------------
    WorkerDef(
        "Lakshmi Devi", "lakshmi.devi@sahakaar.coop", "+91 98430 11213", "cleaning", "Cleaning Specialist",
        "Z2", 11.0092, 76.9478, 10, 12, 80, 4.7,
        (("deep-cleaning", 5), ("housekeeping", 5), ("sanitisation", 4)),
        (("Housekeeping Level 2", "Tamil Nadu Skill Development Corporation", "housekeeping"),),
        training_credits=2,
    ),
    WorkerDef(
        "Kavitha Rani", "kavitha.rani@sahakaar.coop", "+91 98430 11214", "cleaning", "Cleaning Specialist",
        "Z1", 11.0176, 76.9718, 6, 12, 74, 4.5,
        (("deep-cleaning", 4), ("upholstery-cleaning", 5), ("housekeeping", 4)),
    ),
    WorkerDef(
        "Shanthi Mohan", "shanthi.mohan@sahakaar.coop", "+91 98430 11215", "cleaning", "Housekeeper",
        "Z3", 11.0255, 77.0041, 4, 10, 68, 4.3,
        (("housekeeping", 4), ("sanitisation", 3)),
        insurance_active=False,
    ),
    WorkerDef(
        "Revathi Balu", "revathi.balu@sahakaar.coop", "+91 98430 11216", "cleaning", "Cleaning Specialist",
        "Z4", 11.0283, 76.9462, 8, 12, 66, 4.6,
        (("deep-cleaning", 5), ("sanitisation", 4), ("housekeeping", 3)),
        (("Housekeeping Level 2", "Tamil Nadu Skill Development Corporation", "housekeeping"),),
    ),
    WorkerDef(
        "Sarala Devi", "sarala.devi@sahakaar.coop", "+91 98430 11217", "cleaning", "Housekeeper",
        "Z5", 10.9988, 77.0294, 11, 12, 59, 4.4,
        (("housekeeping", 5), ("deep-cleaning", 3)),
        days_off=(2, 6),
    ),
    # --- carpentry (3) -----------------------------------------------------
    WorkerDef(
        "Murugan Pillai", "murugan.pillai@sahakaar.coop", "+91 98430 11218", "carpentry", "Carpenter",
        "Z1", 11.0188, 76.9702, 19, 12, 84, 4.8,
        (("carpentry", 5), ("furniture-repair", 5), ("door-window-fitting", 5),
         ("modular-fitting", 4)),
        (("ITI Carpentry Certificate", "Tamil Nadu Skill Development Corporation", "carpentry"),),
        training_credits=3,
    ),
    WorkerDef(
        "Ashok Varma", "ashok.varma@sahakaar.coop", "+91 98430 11219", "carpentry", "Carpenter",
        "Z3", 11.0264, 77.0012, 7, 12, 72, 4.5,
        (("carpentry", 4), ("furniture-repair", 4), ("wood-polishing", 4)),
    ),
    WorkerDef(
        "Selvi Natarajan", "selvi.natarajan@sahakaar.coop", "+91 98430 11220", "carpentry", "Carpenter",
        "Z4", 11.0296, 76.9471, 5, 12, 61, 4.3,
        (("carpentry", 4), ("modular-fitting", 3), ("door-window-fitting", 3)),
    ),
    # --- appliance repair (2) ----------------------------------------------
    WorkerDef(
        "Imran Sheikh", "imran.sheikh@sahakaar.coop", "+91 98430 11221", "appliance-repair",
        "Appliance Technician", "Z3", 11.0277, 77.0036, 10, 12, 92, 4.6,
        (("appliance-diagnostics", 5), ("refrigeration-ac", 5), ("washing-machine-repair", 4),
         ("solar-installation", 3)),
        (("RAC Technician Level 2", "National Skill Development Corporation", "refrigeration-ac"),
         ("Suryamitra Solar PV Technician", "Ministry of New and Renewable Energy", "solar-installation")),
        training_credits=1,
    ),
    WorkerDef(
        "Karthik Subramani", "karthik.subramani@sahakaar.coop", "+91 98430 11222",
        "appliance-repair", "Appliance Technician", "Z1", 11.0179, 76.9737, 6, 12, 86, 4.4,
        (("appliance-diagnostics", 4), ("refrigeration-ac", 4), ("microwave-oven-repair", 4)),
        (("RAC Technician Level 2", "National Skill Development Corporation", "refrigeration-ac"),),
    ),
    # --- painting (2) ------------------------------------------------------
    WorkerDef(
        "Bhaskar Rao", "bhaskar.rao@sahakaar.coop", "+91 98430 11223", "painting", "Painter",
        "Z5", 11.0018, 77.0281, 14, 12, 70, 4.5,
        (("painting", 5), ("wall-putty-primer", 5), ("texture-painting", 4),
         ("waterproof-coating", 4)),
        (("Painter Vocational Certificate", "Tamil Nadu Skill Development Corporation", "painting"),),
    ),
    WorkerDef(
        "Jyothi Prakash", "jyothi.prakash@sahakaar.coop", "+91 98430 11224", "painting", "Painter",
        "Z2", 11.0064, 76.9512, 8, 12, 64, 4.4,
        (("painting", 4), ("wall-putty-primer", 4), ("texture-painting", 3)),
    ),
    # --- gardening (2) -----------------------------------------------------
    WorkerDef(
        "Ravi Chandran", "ravi.chandran@sahakaar.coop", "+91 98430 11225", "gardening", "Gardener",
        "Z4", 11.0305, 76.9459, 16, 12, 58, 4.6,
        (("gardening", 5), ("tree-pruning", 5), ("lawn-maintenance", 4), ("landscaping", 4)),
        (("Horticulture Assistant", "Tamil Nadu Agricultural University", "gardening"),),
        training_credits=2,
    ),
    WorkerDef(
        "Malathi Sundar", "malathi.sundar@sahakaar.coop", "+91 98430 11226", "gardening", "Gardener",
        "Z5", 10.9994, 77.0307, 4, 12, 47, 4.2,
        (("gardening", 4), ("lawn-maintenance", 4), ("drip-irrigation", 3)),
        insurance_active=False,
    ),
)


@dataclass(frozen=True)
class CustomerDef:
    full_name: str
    email: str
    phone: str
    zone_code: str
    lat: float
    lng: float
    address: str


CUSTOMERS: tuple[CustomerDef, ...] = (
    CustomerDef(
        "Priya Sharma", DEMO_CUSTOMER_EMAIL, "+91 98940 20001", "Z2", 11.0253, 76.9490,
        "14 Bharathi Street, R.S. Puram, Coimbatore 641002",
    ),
    CustomerDef("Ramesh Iyer", "ramesh.iyer@example.com", "+91 98940 20002", "Z1",
                11.0190, 76.9718, "22 Cross Cut Road, Gandhipuram, Coimbatore 641012"),
    CustomerDef("Divya Menon", "divya.menon@example.com", "+91 98940 20003", "Z3",
                11.0266, 77.0022, "8 Avinashi Road, Peelamedu, Coimbatore 641004"),
    CustomerDef("Hari Prasad", "hari.prasad@example.com", "+91 98940 20004", "Z4",
                11.0294, 76.9448, "51 Mettupalayam Road, Saibaba Colony, Coimbatore 641011"),
    CustomerDef("Sneha Reddy", "sneha.reddy@example.com", "+91 98940 20005", "Z5",
                11.0004, 77.0296, "3 Trichy Road, Singanallur, Coimbatore 641005"),
    CustomerDef("Vignesh Kumar", "vignesh.kumar@example.com", "+91 98940 20006", "Z1",
                11.0175, 76.9736, "9 Sathy Road, Gandhipuram, Coimbatore 641012"),
    CustomerDef("Aishwarya Nair", "aishwarya.nair@example.com", "+91 98940 20007", "Z2",
                11.0068, 76.9503, "77 DB Road, R.S. Puram, Coimbatore 641002"),
    CustomerDef("Mohammed Rafi", "mohammed.rafi@example.com", "+91 98940 20008", "Z3",
                11.0259, 77.0047, "18 Hope College Road, Peelamedu, Coimbatore 641004"),
    CustomerDef("Geetha Raghavan", "geetha.raghavan@example.com", "+91 98940 20009", "Z4",
                11.0287, 76.9466, "6 Thadagam Road, Saibaba Colony, Coimbatore 641011"),
    CustomerDef("Naveen Balaji", "naveen.balaji@example.com", "+91 98940 20010", "Z5",
                10.9996, 77.0310, "44 Ondipudur Main Road, Singanallur, Coimbatore 641016"),
    CustomerDef("Sundari Ammal", "sundari.ammal@example.com", "+91 98940 20011", "Z2",
                11.0089, 76.9481, "12 Race Course Road, Coimbatore 641018"),
    CustomerDef("Prakash Jain", "prakash.jain@example.com", "+91 98940 20012", "Z1",
                11.0202, 76.9709, "31 100 Feet Road, Gandhipuram, Coimbatore 641012"),
    CustomerDef("Latha Venkat", "latha.venkat@example.com", "+91 98940 20013", "Z3",
                11.0273, 77.0009, "27 Nehru Nagar, Peelamedu, Coimbatore 641004"),
    CustomerDef("Joseph Antony", "joseph.antony@example.com", "+91 98940 20014", "Z4",
                11.0299, 76.9443, "5 NSR Road, Saibaba Colony, Coimbatore 641011"),
    CustomerDef("Bhavana Krishnan", "bhavana.krishnan@example.com", "+91 98940 20015", "Z5",
                11.0011, 77.0285, "63 Sungam Bypass, Coimbatore 641045"),
)


ADMIN_NAME = "Vasanthi Krishnamurthy"


@dataclass(frozen=True)
class ProblemDef:
    label: str
    skills: tuple[str, ...]
    weight: int = 1
    urgency: str = "NORMAL"


#: Realistic job mix per service. Weights control how often each problem shows
#: up in the seeded history, which in turn drives the skill-gap analysis.
PROBLEMS: dict[str, tuple[ProblemDef, ...]] = {
    "plumbing": (
        ProblemDef("Kitchen Sink Leakage", ("plumbing", "pipe-repair"), 5),
        ProblemDef("Tap Leakage", ("plumbing", "sanitary-fitting"), 4),
        ProblemDef("Drain Blockage", ("plumbing", "drainage-systems"), 4),
        ProblemDef("Toilet Repair", ("plumbing", "sanitary-fitting"), 3),
        ProblemDef("Water Tank & Motor Repair", ("plumbing", "water-systems"), 3),
        ProblemDef("Bathroom Pipe Leakage", ("plumbing", "pipe-repair"), 3),
        ProblemDef("Water Purifier Servicing", ("water-purifier-servicing", "plumbing"), 2),
        ProblemDef("Water Pipe Burst", ("plumbing", "pipe-repair", "water-systems"), 1, "EMERGENCY"),
    ),
    "electrical": (
        ProblemDef("Solar Panel Installation", ("solar-installation", "electrical-wiring"), 6),
        ProblemDef("Switch & Socket Repair", ("electrical-wiring", "circuit-repair"), 4),
        ProblemDef("Ceiling Fan Repair", ("lighting-installation", "circuit-repair"), 4),
        ProblemDef("Light Fitting Repair", ("lighting-installation",), 3),
        ProblemDef("House Wiring Work", ("electrical-wiring",), 3),
        ProblemDef("Inverter & Battery Service", ("inverter-battery",), 2),
        ProblemDef("Smart Switch Installation", ("smart-home-automation", "electrical-wiring"), 1),
        ProblemDef("Short Circuit", ("circuit-repair", "electrical-wiring"), 1, "EMERGENCY"),
    ),
    "cleaning": (
        ProblemDef("Home Deep Cleaning", ("deep-cleaning", "housekeeping"), 5),
        ProblemDef("Bathroom Deep Cleaning", ("deep-cleaning", "sanitisation"), 4),
        ProblemDef("Sofa & Upholstery Cleaning", ("upholstery-cleaning", "deep-cleaning"), 3),
        ProblemDef("Housekeeping Service", ("housekeeping",), 4),
        ProblemDef("Post-Renovation Cleaning", ("deep-cleaning", "sanitisation"), 2),
    ),
    "carpentry": (
        ProblemDef("Door & Hinge Repair", ("carpentry", "door-window-fitting"), 5),
        ProblemDef("Furniture Repair", ("carpentry", "furniture-repair"), 5),
        ProblemDef("Modular Kitchen Fitting", ("modular-fitting", "carpentry"), 2),
        ProblemDef("Wood Polishing", ("wood-polishing", "carpentry"), 3),
        ProblemDef("Wardrobe Installation", ("carpentry", "modular-fitting"), 2),
    ),
    "appliance-repair": (
        ProblemDef("AC Not Cooling", ("refrigeration-ac", "appliance-diagnostics"), 5),
        ProblemDef("Refrigerator Repair", ("refrigeration-ac", "appliance-diagnostics"), 4),
        ProblemDef("Washing Machine Repair", ("washing-machine-repair", "appliance-diagnostics"), 4),
        ProblemDef("Microwave & Oven Repair", ("microwave-oven-repair", "appliance-diagnostics"), 2),
        ProblemDef("Geyser Repair", ("appliance-diagnostics", "electrical-wiring"), 2),
    ),
    "painting": (
        ProblemDef("Wall Painting", ("painting", "wall-putty-primer"), 6),
        ProblemDef("Texture Wall Finish", ("texture-painting", "painting"), 2),
        ProblemDef("Waterproof Coating", ("waterproof-coating", "painting"), 2),
        ProblemDef("Exterior Repainting", ("painting", "wall-putty-primer"), 3),
    ),
    "gardening": (
        ProblemDef("Lawn Maintenance", ("lawn-maintenance", "gardening"), 5),
        ProblemDef("Tree Pruning", ("tree-pruning", "gardening"), 4),
        ProblemDef("Garden Landscaping", ("landscaping", "gardening"), 2),
        ProblemDef("Drip Irrigation Setup", ("drip-irrigation", "gardening"), 2),
    ),
}


#: Weekly job volume per service across the eight weeks of seeded history,
#: oldest week first. Electrical climbs steeply, which is what the demand
#: forecast and the workforce planner then pick up on their own.
WEEKLY_VOLUME: dict[str, tuple[int, ...]] = {
    "plumbing":         (50, 53, 49, 54, 51, 55, 52, 53),
    "electrical":       (24, 26, 30, 32, 32, 38, 48, 56),
    "cleaning":         (34, 36, 35, 38, 36, 37, 35, 36),
    "carpentry":        (25, 27, 26, 24, 27, 26, 28, 26),
    "appliance-repair": (20, 22, 21, 23, 22, 24, 23, 22),
    "painting":         (17, 18, 19, 17, 18, 20, 18, 18),
    "gardening":        (12, 14, 13, 12, 14, 13, 12, 13),
}


#: Zone bias per service (weights). Electrical demand concentrates in Zone 3,
#: which is why the planner recommends prioritising it.
ZONE_BIAS: dict[str, tuple[int, ...]] = {
    "plumbing":         (3, 4, 3, 3, 2),
    "electrical":       (2, 2, 6, 2, 2),
    "cleaning":         (3, 4, 3, 3, 2),
    "carpentry":        (3, 3, 3, 3, 2),
    "appliance-repair": (3, 2, 4, 2, 3),
    "painting":         (2, 3, 3, 3, 2),
    "gardening":        (2, 2, 2, 4, 3),
}


FEEDBACK_BY_STARS: dict[int, tuple[str, ...]] = {
    5: (
        "Arrived on time and fixed it properly. Very professional.",
        "Excellent work, explained the problem clearly.",
        "Neat, quick and courteous. Would book again.",
        "Solved something two other people could not.",
    ),
    4: (
        "Good work overall, arrived slightly late.",
        "Job done well, workspace could have been tidier.",
        "Solid service, fair price.",
    ),
    3: (
        "Work is acceptable but took longer than expected.",
        "Average job. Had to call back for a small adjustment.",
    ),
    2: (
        "The issue came back within a week.",
        "Reached very late and seemed rushed.",
    ),
    1: (
        "Did not resolve the problem at all.",
    ),
}
