"""AI #1 - Service understanding.

Turns a free-text (or dictated) customer sentence into a structured job
requirement: service, problem, required skills, worker count, urgency and
preferred time.

Two engines, in this order:

1. ``llm``        - an optional hosted model, used only when AI_API_KEY is set.
2. ``rule_based`` - a deterministic keyword / pattern engine that ships with the
                    product and needs no network access.

The rule-based engine is not a stub: it is the guaranteed path, and the LLM is
an optional accelerator. Whatever the LLM returns is validated against the
canonical taxonomy before it is trusted, and any failure silently degrades to
the rule engine so the demo never breaks. The ``method`` field on the result
always states which engine actually produced the answer, so the UI can be
honest about it.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, time, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.models.enums import Urgency
from app.services.taxonomy import SERVICE_BY_SLUG, SKILL_BY_SLUG, ServiceDef

logger = logging.getLogger(__name__)

METHOD_LLM = "llm"
METHOD_RULES = "rule_based"
METHOD_LLM_FALLBACK = "rule_based_llm_unavailable"


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class Understanding:
    """Structured interpretation of a customer request."""

    service_slug: str
    service_name: str
    problem: str
    skill_slugs: list[str]
    skill_names: list[str]
    workers_required: int
    urgency: str
    preferred_time_label: str
    scheduled_for: datetime | None
    confidence: float
    method: str
    matched_terms: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["scheduled_for"] = (
            self.scheduled_for.isoformat() if self.scheduled_for else None
        )
        return payload


# ---------------------------------------------------------------------------
# Keyword tables
# ---------------------------------------------------------------------------

#: term -> weight, per service. Multi-word terms are matched as phrases.
SERVICE_KEYWORDS: dict[str, dict[str, int]] = {
    "plumbing": {
        "plumber": 5, "plumbing": 5, "sink": 4, "washbasin": 4, "basin": 3,
        "tap": 4, "faucet": 4, "pipe": 4, "pipeline": 4, "leak": 4, "leaking": 4,
        "leakage": 4, "drip": 3, "dripping": 3, "drain": 4, "drainage": 4,
        "clog": 4, "clogged": 4, "blocked": 3, "blockage": 4, "toilet": 4,
        "commode": 4, "flush": 3, "bathroom": 2, "shower": 3, "overflow": 3,
        "seepage": 3, "water tank": 4, "sump": 4, "borewell": 4, "water supply": 4,
        "water motor": 4, "nal": 3, "paani": 2, "water purifier": 4, "ro": 2,
    },
    "electrical": {
        "electrician": 5, "electrical": 5, "electric": 4, "wiring": 5, "wire": 3,
        "short circuit": 6, "shortcircuit": 5, "fuse": 4, "mcb": 5, "switch": 4,
        "socket": 4, "plug point": 4, "power": 2, "current": 2, "sparking": 5,
        "spark": 4, "shock": 4, "inverter": 4, "meter": 3, "switchboard": 5,
        "tube light": 4, "bulb": 3, "light": 2, "fan": 3, "ceiling fan": 5,
        "solar": 5, "solar panel": 6, "ev charger": 6, "bijli": 3, "no power": 5,
    },
    "carpentry": {
        "carpenter": 5, "carpentry": 5, "wood": 3, "wooden": 3, "furniture": 4,
        "door": 4, "window": 3, "cupboard": 4, "wardrobe": 4, "cabinet": 4,
        "drawer": 4, "hinge": 4, "table": 3, "chair": 3, "bed": 3, "shelf": 3,
        "lock": 3, "frame": 2, "polish": 3, "modular kitchen": 5, "almirah": 4,
    },
    "painting": {
        "painter": 5, "painting": 5, "paint": 4, "repaint": 5, "whitewash": 5,
        "putty": 4, "primer": 4, "emulsion": 4, "distemper": 4, "texture": 3,
        "wall": 2, "walls": 2, "ceiling": 2, "waterproofing": 4, "coating": 3,
    },
    "cleaning": {
        "cleaning": 5, "clean": 4, "cleaner": 4, "housekeeping": 5, "sweep": 3,
        "mop": 3, "dust": 3, "deep clean": 6, "deep cleaning": 6, "sanitise": 4,
        "sanitize": 4, "sanitisation": 4, "disinfect": 4, "sofa cleaning": 6,
        "upholstery": 4, "maid": 4, "safai": 4, "vacuum": 3, "scrub": 3,
    },
    "gardening": {
        "gardener": 5, "gardening": 5, "garden": 4, "lawn": 5, "grass": 4,
        "plant": 3, "plants": 3, "tree": 4, "pruning": 5, "prune": 4,
        "trimming": 4, "hedge": 4, "weeds": 4, "soil": 3, "manure": 3,
        "landscaping": 5, "terrace garden": 5, "irrigation": 4, "mali": 4,
    },
    "appliance-repair": {
        "appliance": 5, "ac": 4, "air conditioner": 6, "air-conditioner": 6,
        "refrigerator": 5, "fridge": 5, "washing machine": 6, "microwave": 5,
        "oven": 4, "geyser": 4, "water heater": 5, "chimney": 4, "dishwasher": 5,
        "television": 4, "cooler": 3, "servicing": 3, "gas stove": 5,
        "not cooling": 5, "compressor": 4,
    },
}


@dataclass(frozen=True)
class ProblemRule:
    """A recognisable problem.

    ``groups`` is a list of alternation sets: every group must contribute at
    least one matching term for the rule to fire. That keeps "sink" plus "leak"
    from matching a request that merely mentions a sink.
    """

    service_slug: str
    label: str
    groups: tuple[tuple[str, ...], ...]
    skills: tuple[str, ...]
    urgency: Urgency | None = None
    workers_required: int | None = None

    @property
    def specificity(self) -> int:
        return len(self.groups)


LEAK_TERMS = ("leak", "leaking", "leakage", "drip", "dripping", "seepage", "water coming")
BROKEN_TERMS = ("not working", "broken", "damaged", "repair", "faulty", "stopped", "jam", "stuck")

PROBLEM_RULES: tuple[ProblemRule, ...] = (
    # --- plumbing ----------------------------------------------------------
    ProblemRule(
        "plumbing", "Kitchen Sink Leakage",
        (("kitchen",), ("sink", "washbasin", "basin"), LEAK_TERMS),
        ("plumbing", "pipe-repair"),
    ),
    ProblemRule(
        "plumbing", "Sink Leakage",
        (("sink", "washbasin", "basin"), LEAK_TERMS),
        ("plumbing", "pipe-repair"),
    ),
    ProblemRule(
        "plumbing", "Water Pipe Burst",
        (("pipe", "pipeline", "water line"), ("burst", "cracked", "broken", "split")),
        ("plumbing", "pipe-repair", "water-systems"),
        urgency=Urgency.EMERGENCY,
    ),
    ProblemRule(
        "plumbing", "Tap Leakage",
        (("tap", "faucet", "nal"), LEAK_TERMS),
        ("plumbing", "sanitary-fitting"),
    ),
    ProblemRule(
        "plumbing", "Drain Blockage",
        (("drain", "drainage", "sewage", "gutter"), ("block", "blocked", "blockage", "clog", "clogged", "choked", "overflow")),
        ("plumbing", "drainage-systems"),
    ),
    ProblemRule(
        "plumbing", "Toilet Repair",
        (("toilet", "commode", "flush"), BROKEN_TERMS + ("block", "blocked", "clogged") + LEAK_TERMS),
        ("plumbing", "sanitary-fitting"),
    ),
    ProblemRule(
        "plumbing", "Water Tank & Motor Repair",
        (("water tank", "sump", "motor", "borewell", "pump"), BROKEN_TERMS + ("not filling", "no water")),
        ("plumbing", "water-systems"),
    ),
    ProblemRule(
        "plumbing", "Water Purifier Servicing",
        (("water purifier", "ro", "purifier"),),
        ("water-purifier-servicing", "plumbing"),
    ),
    # --- electrical --------------------------------------------------------
    ProblemRule(
        "electrical", "Short Circuit",
        (("short circuit", "shortcircuit", "sparking", "spark", "burning smell"),),
        ("circuit-repair", "electrical-wiring"),
        urgency=Urgency.EMERGENCY,
    ),
    ProblemRule(
        "electrical", "Power Failure",
        (("no power", "power gone", "no current", "power cut", "tripping", "trip"),),
        ("circuit-repair", "electrical-wiring"),
        urgency=Urgency.HIGH,
    ),
    ProblemRule(
        "electrical", "Ceiling Fan Repair",
        (("fan", "ceiling fan"), BROKEN_TERMS + ("slow", "noise", "noisy")),
        ("lighting-installation", "circuit-repair"),
    ),
    ProblemRule(
        "electrical", "Light Fitting Repair",
        (("light", "bulb", "tube light", "lamp"), BROKEN_TERMS + ("flicker", "flickering", "fused")),
        ("lighting-installation",),
    ),
    ProblemRule(
        "electrical", "Switch & Socket Repair",
        (("switch", "socket", "plug point", "switchboard"), BROKEN_TERMS),
        ("electrical-wiring", "circuit-repair"),
    ),
    ProblemRule(
        "electrical", "House Wiring Work",
        (("wiring", "rewiring", "new wiring"),),
        ("electrical-wiring",),
    ),
    ProblemRule(
        "electrical", "Solar Panel Installation",
        (("solar", "solar panel", "rooftop solar"),),
        ("solar-installation", "electrical-wiring"),
        workers_required=2,
    ),
    ProblemRule(
        "electrical", "EV Charger Installation",
        (("ev charger", "car charger", "charging point"),),
        ("ev-charger-installation", "electrical-wiring"),
    ),
    ProblemRule(
        "electrical", "Inverter & Battery Service",
        (("inverter", "battery", "ups"),),
        ("inverter-battery",),
    ),
    # --- carpentry ---------------------------------------------------------
    ProblemRule(
        "carpentry", "Door & Hinge Repair",
        (("door", "hinge", "window"), BROKEN_TERMS + ("not closing", "not opening", "sagging")),
        ("carpentry", "door-window-fitting"),
    ),
    ProblemRule(
        "carpentry", "Furniture Repair",
        (("furniture", "cupboard", "wardrobe", "almirah", "drawer", "table", "chair", "bed", "shelf", "cabinet"), BROKEN_TERMS),
        ("carpentry", "furniture-repair"),
    ),
    ProblemRule(
        "carpentry", "Modular Kitchen Fitting",
        (("modular kitchen", "modular"),),
        ("modular-fitting", "carpentry"),
        workers_required=2,
    ),
    ProblemRule(
        "carpentry", "Wood Polishing",
        (("polish", "polishing", "varnish"),),
        ("wood-polishing", "carpentry"),
    ),
    # --- painting ----------------------------------------------------------
    ProblemRule(
        "painting", "Waterproof Coating",
        (("waterproofing", "waterproof", "damp", "seepage"), ("wall", "terrace", "ceiling", "roof")),
        ("waterproof-coating", "painting"),
    ),
    ProblemRule(
        "painting", "Wall Painting",
        (("paint", "painting", "repaint", "whitewash", "distemper", "emulsion"),),
        ("painting", "wall-putty-primer"),
        workers_required=2,
    ),
    ProblemRule(
        "painting", "Texture Wall Finish",
        (("texture", "designer wall", "accent wall"),),
        ("texture-painting", "painting"),
    ),
    # --- cleaning ----------------------------------------------------------
    ProblemRule(
        "cleaning", "Sofa & Upholstery Cleaning",
        (("sofa", "upholstery", "carpet", "mattress"),),
        ("upholstery-cleaning", "deep-cleaning"),
    ),
    ProblemRule(
        "cleaning", "Bathroom Deep Cleaning",
        (("bathroom", "toilet", "washroom"), ("clean", "cleaning", "deep clean", "scrub")),
        ("deep-cleaning", "sanitisation"),
    ),
    ProblemRule(
        "cleaning", "Home Deep Cleaning",
        (("deep clean", "deep cleaning", "full house", "whole house", "complete cleaning"),),
        ("deep-cleaning", "housekeeping"),
        workers_required=2,
    ),
    ProblemRule(
        "cleaning", "Housekeeping Service",
        (("clean", "cleaning", "housekeeping", "safai", "maid"),),
        ("housekeeping",),
    ),
    # --- gardening ---------------------------------------------------------
    ProblemRule(
        "gardening", "Tree Pruning",
        (("tree", "branch", "hedge"), ("pruning", "prune", "trim", "trimming", "cut", "cutting")),
        ("tree-pruning", "gardening"),
    ),
    ProblemRule(
        "gardening", "Lawn Maintenance",
        (("lawn", "grass"),),
        ("lawn-maintenance", "gardening"),
    ),
    ProblemRule(
        "gardening", "Drip Irrigation Setup",
        (("irrigation", "drip", "watering system"),),
        ("drip-irrigation", "gardening"),
    ),
    ProblemRule(
        "gardening", "Garden Landscaping",
        (("landscaping", "garden design", "terrace garden"),),
        ("landscaping", "gardening"),
        workers_required=2,
    ),
    # --- appliance repair --------------------------------------------------
    ProblemRule(
        "appliance-repair", "AC Not Cooling",
        (("ac", "air conditioner", "air-conditioner"), ("not cooling", "no cooling", "not working", "servicing", "service", "repair", "leaking", "noise")),
        ("refrigeration-ac", "appliance-diagnostics"),
    ),
    ProblemRule(
        "appliance-repair", "Refrigerator Repair",
        (("refrigerator", "fridge"), BROKEN_TERMS + ("not cooling", "noise")),
        ("refrigeration-ac", "appliance-diagnostics"),
    ),
    ProblemRule(
        "appliance-repair", "Washing Machine Repair",
        (("washing machine", "washer"),),
        ("washing-machine-repair", "appliance-diagnostics"),
    ),
    ProblemRule(
        "appliance-repair", "Microwave & Oven Repair",
        (("microwave", "oven", "otg"),),
        ("microwave-oven-repair", "appliance-diagnostics"),
    ),
    ProblemRule(
        "appliance-repair", "Geyser Repair",
        (("geyser", "water heater"),),
        ("appliance-diagnostics", "electrical-wiring"),
    ),
    ProblemRule(
        "appliance-repair", "Chimney & Stove Service",
        (("chimney", "gas stove", "hob"),),
        ("appliance-diagnostics",),
    ),
)


EMERGENCY_TERMS = (
    "emergency", "urgent", "urgently", "immediately", "right now", "asap",
    "burst", "flooding", "flooded", "overflowing", "sparking", "shock",
    "gas leak", "burning smell", "danger", "dangerous", "fire",
)
HIGH_URGENCY_TERMS = ("today", "tonight", "as soon as possible", "quickly", "same day", "no water", "no power")
LOW_URGENCY_TERMS = ("next week", "sometime", "whenever", "no hurry", "not urgent", "next month")

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "ek": 1, "do": 2, "teen": 3,
}


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def _normalise(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"[^\w\s:'-]", " ", lowered)
    return re.sub(r"\s+", " ", lowered)


def _contains(haystack: str, term: str) -> bool:
    """Whole-word (or whole-phrase) containment, tolerant of simple plurals.

    "trees" matches the term "tree", "switches" matches "switch". This is a
    deliberately small amount of morphology: enough for real requests, without
    dragging in a stemming dependency.
    """
    return (
        re.search(rf"(?<!\w){re.escape(term)}(?:es|s)?(?!\w)", haystack) is not None
    )


# ---------------------------------------------------------------------------
# Time parsing
# ---------------------------------------------------------------------------

MORNING = time(10, 0)
AFTERNOON = time(14, 0)
EVENING = time(17, 30)
NIGHT = time(20, 0)


def _at(base: datetime, day_offset: int, clock: time) -> datetime:
    target = (base + timedelta(days=day_offset)).replace(
        hour=clock.hour, minute=clock.minute, second=0, microsecond=0
    )
    return target


def parse_preferred_time(text: str, now: datetime) -> tuple[str, datetime]:
    """Return a human label and a concrete slot for the request."""
    part_of_day: tuple[str, time] | None = None
    if _contains(text, "morning"):
        part_of_day = ("Morning", MORNING)
    elif _contains(text, "afternoon"):
        part_of_day = ("Afternoon", AFTERNOON)
    elif _contains(text, "evening"):
        part_of_day = ("Evening", EVENING)
    elif _contains(text, "night") or _contains(text, "tonight"):
        part_of_day = ("Night", NIGHT)

    explicit = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text)
    explicit_clock: time | None = None
    if explicit:
        hour = int(explicit.group(1)) % 12
        minute = int(explicit.group(2) or 0)
        if explicit.group(3) == "pm":
            hour += 12
        explicit_clock = time(hour, minute)

    if any(_contains(text, term) for term in ("now", "immediately", "right now", "asap", "emergency")):
        slot = now + timedelta(minutes=45)
        return "As soon as possible", slot.replace(second=0, microsecond=0)

    if _contains(text, "tomorrow"):
        clock = explicit_clock or (part_of_day[1] if part_of_day else MORNING)
        label = f"Tomorrow {part_of_day[0]}" if part_of_day else "Tomorrow"
        if explicit_clock and not part_of_day:
            label = f"Tomorrow {explicit_clock.strftime('%I:%M %p').lstrip('0')}"
        return label, _at(now, 1, clock)

    if _contains(text, "day after tomorrow"):
        clock = explicit_clock or (part_of_day[1] if part_of_day else MORNING)
        return "Day after tomorrow", _at(now, 2, clock)

    if _contains(text, "weekend"):
        # Next Saturday (weekday 5).
        days_ahead = (5 - now.weekday()) % 7 or 7
        clock = explicit_clock or (part_of_day[1] if part_of_day else MORNING)
        return "This weekend", _at(now, days_ahead, clock)

    if _contains(text, "next week"):
        clock = explicit_clock or (part_of_day[1] if part_of_day else MORNING)
        return "Next week", _at(now, 7, clock)

    if _contains(text, "today") or _contains(text, "tonight"):
        clock = explicit_clock or (part_of_day[1] if part_of_day else EVENING)
        candidate = _at(now, 0, clock)
        if candidate <= now:
            candidate = now + timedelta(hours=3)
        label = f"Today {part_of_day[0]}" if part_of_day else "Today"
        return label, candidate.replace(second=0, microsecond=0)

    if part_of_day or explicit_clock:
        clock = explicit_clock or part_of_day[1]  # type: ignore[index]
        candidate = _at(now, 0, clock)
        offset = 0 if candidate > now else 1
        label = part_of_day[0] if part_of_day else clock.strftime("%I:%M %p").lstrip("0")
        prefix = "Today" if offset == 0 else "Tomorrow"
        return f"{prefix} {label}", _at(now, offset, clock)

    return "Tomorrow Morning", _at(now, 1, MORNING)


# ---------------------------------------------------------------------------
# Rule-based engine
# ---------------------------------------------------------------------------


def _score_services(text: str) -> tuple[dict[str, int], list[str]]:
    scores: dict[str, int] = {slug: 0 for slug in SERVICE_KEYWORDS}
    matched: list[str] = []
    for slug, keywords in SERVICE_KEYWORDS.items():
        for term, weight in keywords.items():
            if _contains(text, term):
                scores[slug] += weight
                matched.append(term)
    return scores, matched


def _matching_rules(text: str) -> list[ProblemRule]:
    hits: list[ProblemRule] = []
    for rule in PROBLEM_RULES:
        if all(any(_contains(text, term) for term in group) for group in rule.groups):
            hits.append(rule)
    return sorted(hits, key=lambda rule: rule.specificity, reverse=True)


def _detect_urgency(text: str, rule: ProblemRule | None) -> Urgency:
    if any(_contains(text, term) for term in EMERGENCY_TERMS):
        return Urgency.EMERGENCY
    if rule is not None and rule.urgency is not None:
        return rule.urgency
    if any(_contains(text, term) for term in HIGH_URGENCY_TERMS):
        return Urgency.HIGH
    if any(_contains(text, term) for term in LOW_URGENCY_TERMS):
        return Urgency.LOW
    return Urgency.NORMAL


def _detect_worker_count(text: str, rule: ProblemRule | None) -> int:
    match = re.search(r"\b(\d+)\s+(?:workers?|people|persons?|men|staff)\b", text)
    if match:
        return max(1, min(6, int(match.group(1))))
    for word, value in NUMBER_WORDS.items():
        if re.search(rf"(?<!\w){word}\s+(?:workers?|people|persons?|men|staff)(?!\w)", text):
            return max(1, min(6, value))
    if rule is not None and rule.workers_required:
        return rule.workers_required
    return 1


def _resolve_skills(slugs: tuple[str, ...], service: ServiceDef) -> tuple[list[str], list[str]]:
    valid = [slug for slug in slugs if slug in SKILL_BY_SLUG]
    if not valid:
        valid = [slug for slug in service.primary_skill_slugs if slug in SKILL_BY_SLUG]
    # Preserve order, drop duplicates.
    seen: set[str] = set()
    ordered = [slug for slug in valid if not (slug in seen or seen.add(slug))]
    return ordered, [SKILL_BY_SLUG[slug].name for slug in ordered]


def understand_with_rules(text: str, now: datetime | None = None) -> Understanding:
    """Deterministic engine. Always returns a usable interpretation."""
    now = now or datetime.now(timezone.utc)
    normalised = _normalise(text)

    scores, matched_terms = _score_services(normalised)
    rules = _matching_rules(normalised)

    # A matched problem pattern is stronger evidence than a loose keyword.
    for rule in rules:
        scores[rule.service_slug] = scores.get(rule.service_slug, 0) + 4 * rule.specificity

    best_slug, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score == 0:
        # Nothing recognised. Say so rather than guessing a service.
        service = SERVICE_BY_SLUG["cleaning"]
        skill_slugs, skill_names = _resolve_skills((), service)
        label, slot = parse_preferred_time(normalised, now)
        return Understanding(
            service_slug=service.slug,
            service_name=service.name,
            problem="General Service Request",
            skill_slugs=skill_slugs,
            skill_names=skill_names,
            workers_required=1,
            urgency=str(_detect_urgency(normalised, None)),
            preferred_time_label=label,
            scheduled_for=slot,
            confidence=0.2,
            method=METHOD_RULES,
            matched_terms=[],
            notes=(
                "No service keywords were recognised in this request. "
                "Please pick a service manually or add more detail."
            ),
        )

    service = SERVICE_BY_SLUG[best_slug]
    rule = next((r for r in rules if r.service_slug == best_slug), None)

    if rule is not None:
        problem = rule.label
        skill_slugs, skill_names = _resolve_skills(rule.skills, service)
    else:
        problem = f"{service.name} Service Request"
        skill_slugs, skill_names = _resolve_skills(tuple(service.primary_skill_slugs), service)

    urgency = _detect_urgency(normalised, rule)
    label, slot = parse_preferred_time(normalised, now)
    if urgency is Urgency.EMERGENCY:
        label = "As soon as possible"
        slot = (now + timedelta(minutes=45)).replace(second=0, microsecond=0)

    # Confidence: how decisively the winning service beat the runner-up, and
    # whether a specific problem pattern fired.
    runner_up = max((s for slug, s in scores.items() if slug != best_slug), default=0)
    margin = (best_score - runner_up) / best_score if best_score else 0
    confidence = 0.45 + 0.3 * margin + (0.2 if rule is not None else 0.0)
    confidence = round(min(0.97, max(0.3, confidence)), 2)

    return Understanding(
        service_slug=service.slug,
        service_name=service.name,
        problem=problem,
        skill_slugs=skill_slugs,
        skill_names=skill_names,
        workers_required=_detect_worker_count(normalised, rule),
        urgency=str(urgency),
        preferred_time_label=label,
        scheduled_for=slot,
        confidence=confidence,
        method=METHOD_RULES,
        matched_terms=sorted(set(matched_terms))[:10],
        notes="",
    )


# ---------------------------------------------------------------------------
# Optional LLM engine
# ---------------------------------------------------------------------------

LLM_SYSTEM_PROMPT = """You classify household service requests for an Indian labour cooperative.
Reply with a single JSON object and nothing else, using exactly these keys:
  service_slug: one of {services}
  problem: a short Title Case problem name, at most 5 words
  skill_slugs: array of 1-3 slugs chosen from {skills}
  workers_required: integer 1-6
  urgency: one of LOW, NORMAL, HIGH, EMERGENCY
  preferred_time_label: short phrase such as "Tomorrow Morning" or "As soon as possible"
Never invent slugs that are not in the lists."""


async def understand_with_llm(text: str, now: datetime) -> Understanding | None:
    """Call the configured model. Returns None on any problem."""
    if not settings.llm_enabled:
        return None

    import httpx

    prompt = LLM_SYSTEM_PROMPT.format(
        services=", ".join(SERVICE_BY_SLUG),
        skills=", ".join(SKILL_BY_SLUG),
    )
    try:
        async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
            response = await client.post(
                f"{settings.ai_base_url.rstrip('/')}/v1/messages",
                headers={
                    "x-api-key": settings.ai_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": settings.ai_model,
                    "max_tokens": 512,
                    "system": prompt,
                    "messages": [{"role": "user", "content": text}],
                },
            )
            response.raise_for_status()
            body = response.json()
        raw = "".join(
            block.get("text", "")
            for block in body.get("content", [])
            if block.get("type") == "text"
        )
        payload = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))  # type: ignore[union-attr]
    except Exception as exc:  # noqa: BLE001 - any failure must degrade gracefully
        logger.warning("LLM understanding unavailable, using rule engine: %s", exc)
        return None

    return _validate_llm_payload(payload, text, now)


def _validate_llm_payload(
    payload: dict[str, Any], text: str, now: datetime
) -> Understanding | None:
    """Trust nothing: every field is checked against the taxonomy."""
    slug = str(payload.get("service_slug", "")).strip()
    service = SERVICE_BY_SLUG.get(slug)
    if service is None:
        logger.warning("LLM returned unknown service %r; using rule engine.", slug)
        return None

    raw_skills = payload.get("skill_slugs") or []
    if not isinstance(raw_skills, list):
        raw_skills = []
    skill_slugs, skill_names = _resolve_skills(
        tuple(str(s).strip() for s in raw_skills), service
    )

    urgency_raw = str(payload.get("urgency", "NORMAL")).upper()
    urgency = urgency_raw if urgency_raw in set(Urgency) else str(Urgency.NORMAL)

    try:
        workers = max(1, min(6, int(payload.get("workers_required", 1))))
    except (TypeError, ValueError):
        workers = 1

    problem = str(payload.get("problem") or f"{service.name} Service Request").strip()[:80]
    label_from_llm = str(payload.get("preferred_time_label") or "").strip()[:64]

    # Scheduling stays deterministic: the rule parser owns the calendar so the
    # slot is always a real, sane datetime.
    label, slot = parse_preferred_time(_normalise(text), now)
    if label_from_llm:
        label = label_from_llm

    return Understanding(
        service_slug=service.slug,
        service_name=service.name,
        problem=problem,
        skill_slugs=skill_slugs,
        skill_names=skill_names,
        workers_required=workers,
        urgency=urgency,
        preferred_time_label=label,
        scheduled_for=slot,
        confidence=0.92,
        method=METHOD_LLM,
        matched_terms=[],
        notes="",
    )


async def understand_request(text: str, now: datetime | None = None) -> Understanding:
    """Public entry point: LLM when configured, rule engine otherwise."""
    now = now or datetime.now(timezone.utc)
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("Describe the problem in a sentence so we can help.")

    if settings.llm_enabled:
        result = await understand_with_llm(cleaned, now)
        if result is not None:
            return result
        fallback = understand_with_rules(cleaned, now)
        fallback.method = METHOD_LLM_FALLBACK
        fallback.notes = (
            "The language model was unavailable, so the built-in rule engine "
            "interpreted this request."
        )
        return fallback

    return understand_with_rules(cleaned, now)
