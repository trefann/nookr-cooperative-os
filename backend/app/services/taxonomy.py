"""Canonical service and skill taxonomy.

Single source of truth shared by the database seed, the AI service-understanding
engine and the workforce planner, so the three can never drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SkillDef:
    name: str
    slug: str
    service_slug: str
    description: str = ""
    is_emerging: bool = False
    growth_factor: float = 1.0
    requires_certification: bool = False


@dataclass(frozen=True)
class ServiceDef:
    name: str
    slug: str
    description: str
    icon: str
    base_price: float
    avg_duration_minutes: int
    emergency_supported: bool = True
    primary_skill_slugs: tuple[str, ...] = field(default_factory=tuple)


SERVICES: tuple[ServiceDef, ...] = (
    ServiceDef(
        name="Plumbing",
        slug="plumbing",
        description="Leaks, blockages, sanitary fittings and water systems.",
        icon="droplet",
        base_price=650.0,
        avg_duration_minutes=75,
        primary_skill_slugs=("plumbing", "pipe-repair"),
    ),
    ServiceDef(
        name="Electrical",
        slug="electrical",
        description="Wiring, circuits, lighting and electrical safety work.",
        icon="zap",
        base_price=700.0,
        avg_duration_minutes=70,
        primary_skill_slugs=("electrical-wiring", "circuit-repair"),
    ),
    ServiceDef(
        name="Carpentry",
        slug="carpentry",
        description="Furniture, doors, windows and modular fittings.",
        icon="hammer",
        base_price=800.0,
        avg_duration_minutes=110,
        primary_skill_slugs=("carpentry", "furniture-repair"),
    ),
    ServiceDef(
        name="Painting",
        slug="painting",
        description="Interior and exterior painting, putty and coatings.",
        icon="brush",
        base_price=1200.0,
        avg_duration_minutes=240,
        emergency_supported=False,
        primary_skill_slugs=("painting", "wall-putty-primer"),
    ),
    ServiceDef(
        name="Cleaning",
        slug="cleaning",
        description="Deep cleaning, sanitisation and housekeeping.",
        icon="sparkles",
        base_price=900.0,
        avg_duration_minutes=180,
        emergency_supported=False,
        primary_skill_slugs=("deep-cleaning", "housekeeping"),
    ),
    ServiceDef(
        name="Gardening",
        slug="gardening",
        description="Lawn care, pruning, landscaping and irrigation.",
        icon="leaf",
        base_price=550.0,
        avg_duration_minutes=120,
        emergency_supported=False,
        primary_skill_slugs=("gardening", "lawn-maintenance"),
    ),
    ServiceDef(
        name="Appliance Repair",
        slug="appliance-repair",
        description="Air conditioners, refrigerators, washing machines and more.",
        icon="settings",
        base_price=750.0,
        avg_duration_minutes=90,
        primary_skill_slugs=("appliance-diagnostics", "refrigeration-ac"),
    ),
)


SKILLS: tuple[SkillDef, ...] = (
    # --- plumbing ----------------------------------------------------------
    SkillDef("Plumbing", "plumbing", "plumbing", "General plumbing work."),
    SkillDef("Pipe Repair", "pipe-repair", "plumbing", "Leak sealing and pipe replacement."),
    SkillDef("Drainage Systems", "drainage-systems", "plumbing", "Blockage clearing and drainage."),
    SkillDef("Water Systems", "water-systems", "plumbing", "Tanks, pumps and supply lines."),
    SkillDef("Sanitary Fitting", "sanitary-fitting", "plumbing", "Fixture installation."),
    SkillDef(
        "Water Purifier Servicing",
        "water-purifier-servicing",
        "plumbing",
        "RO and purifier maintenance.",
        is_emerging=True,
        growth_factor=1.22,
    ),
    # --- electrical --------------------------------------------------------
    SkillDef("Electrical Wiring", "electrical-wiring", "electrical", "Domestic wiring work."),
    SkillDef("Circuit Repair", "circuit-repair", "electrical", "Fuses, MCBs and short circuits."),
    SkillDef("Lighting Installation", "lighting-installation", "electrical", "Fixtures and fans."),
    SkillDef("Inverter & Battery", "inverter-battery", "electrical", "Backup power systems."),
    SkillDef(
        "Solar Installation",
        "solar-installation",
        "electrical",
        "Rooftop solar panels and inverters.",
        is_emerging=True,
        growth_factor=1.45,
        requires_certification=True,
    ),
    SkillDef(
        "EV Charger Installation",
        "ev-charger-installation",
        "electrical",
        "Home EV charging points.",
        is_emerging=True,
        growth_factor=1.38,
        requires_certification=True,
    ),
    SkillDef(
        "Smart Home Automation",
        "smart-home-automation",
        "electrical",
        "Connected switches, sensors and controllers.",
        is_emerging=True,
        growth_factor=1.30,
    ),
    # --- carpentry ---------------------------------------------------------
    SkillDef("Carpentry", "carpentry", "carpentry", "General woodwork."),
    SkillDef("Furniture Repair", "furniture-repair", "carpentry", "Repair and restoration."),
    SkillDef("Door & Window Fitting", "door-window-fitting", "carpentry", "Frames, hinges, locks."),
    SkillDef("Wood Polishing", "wood-polishing", "carpentry", "Finishing and polishing."),
    SkillDef("Modular Fitting", "modular-fitting", "carpentry", "Modular kitchens and wardrobes."),
    # --- painting ----------------------------------------------------------
    SkillDef("Painting", "painting", "painting", "Interior and exterior painting."),
    SkillDef("Wall Putty & Primer", "wall-putty-primer", "painting", "Surface preparation."),
    SkillDef("Texture Painting", "texture-painting", "painting", "Decorative finishes."),
    SkillDef(
        "Waterproof Coating",
        "waterproof-coating",
        "painting",
        "Terrace and wall waterproofing.",
        is_emerging=True,
        growth_factor=1.25,
    ),
    # --- cleaning ----------------------------------------------------------
    SkillDef("Deep Cleaning", "deep-cleaning", "cleaning", "Full-property deep cleaning."),
    SkillDef("Housekeeping", "housekeeping", "cleaning", "Routine household cleaning."),
    SkillDef("Sanitisation", "sanitisation", "cleaning", "Disinfection services."),
    SkillDef("Upholstery Cleaning", "upholstery-cleaning", "cleaning", "Sofa and carpet cleaning."),
    # --- gardening ---------------------------------------------------------
    SkillDef("Gardening", "gardening", "gardening", "General garden care."),
    SkillDef("Lawn Maintenance", "lawn-maintenance", "gardening", "Mowing and lawn health."),
    SkillDef("Tree Pruning", "tree-pruning", "gardening", "Pruning and hedge trimming."),
    SkillDef("Landscaping", "landscaping", "gardening", "Garden design and build."),
    SkillDef(
        "Drip Irrigation",
        "drip-irrigation",
        "gardening",
        "Water-efficient irrigation systems.",
        is_emerging=True,
        growth_factor=1.28,
    ),
    # --- appliance repair --------------------------------------------------
    SkillDef(
        "Appliance Diagnostics", "appliance-diagnostics", "appliance-repair", "Fault diagnosis."
    ),
    SkillDef(
        "Refrigeration & AC",
        "refrigeration-ac",
        "appliance-repair",
        "Air conditioners and refrigerators.",
        requires_certification=True,
    ),
    SkillDef(
        "Washing Machine Repair",
        "washing-machine-repair",
        "appliance-repair",
        "Front and top load machines.",
    ),
    SkillDef(
        "Microwave & Oven Repair",
        "microwave-oven-repair",
        "appliance-repair",
        "Kitchen appliance repair.",
    ),
)


SERVICE_BY_SLUG: dict[str, ServiceDef] = {service.slug: service for service in SERVICES}
SKILL_BY_SLUG: dict[str, SkillDef] = {skill.slug: skill for skill in SKILLS}


def skills_for_service(service_slug: str) -> tuple[SkillDef, ...]:
    return tuple(skill for skill in SKILLS if skill.service_slug == service_slug)
