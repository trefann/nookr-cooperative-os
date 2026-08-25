"""Service catalogue, zones and skills. Readable without signing in so the
landing and registration screens can populate their pickers."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ServiceCategory, ServiceSkill, Skill, Zone

router = APIRouter(tags=["catalogue"])


@router.get("/services")
def list_services(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    links: dict[int, list[dict[str, Any]]] = {}
    for link, skill in db.execute(
        select(ServiceSkill, Skill).join(Skill, Skill.id == ServiceSkill.skill_id)
    ):
        links.setdefault(link.service_id, []).append(
            {
                "id": skill.id,
                "name": skill.name,
                "slug": skill.slug,
                "is_emerging": skill.is_emerging,
                "requires_certification": skill.requires_certification,
                "is_primary": link.is_primary,
            }
        )

    services = db.execute(select(ServiceCategory).order_by(ServiceCategory.name)).scalars()
    return [
        {
            "id": service.id,
            "name": service.name,
            "slug": service.slug,
            "description": service.description,
            "icon": service.icon,
            "base_price": service.base_price,
            "avg_duration_minutes": service.avg_duration_minutes,
            "emergency_supported": service.emergency_supported,
            "skills": sorted(
                links.get(service.id, []), key=lambda s: (not s["is_primary"], s["name"])
            ),
        }
        for service in services
    ]


@router.get("/zones")
def list_zones(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    zones = db.execute(select(Zone).order_by(Zone.code)).scalars()
    return [
        {
            "id": zone.id,
            "name": zone.name,
            "code": zone.code,
            "city": zone.city,
            "lat": zone.center_lat,
            "lng": zone.center_lng,
            "description": zone.description,
        }
        for zone in zones
    ]


@router.get("/skills")
def list_skills(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    skills = db.execute(select(Skill).order_by(Skill.name)).scalars()
    return [
        {
            "id": skill.id,
            "name": skill.name,
            "slug": skill.slug,
            "description": skill.description,
            "is_emerging": skill.is_emerging,
            "growth_factor": skill.growth_factor,
            "requires_certification": skill.requires_certification,
        }
        for skill in skills
    ]
