

"""Statutory versioning and date-sensitive provision lookup."""



from datetime import date, datetime, timezone



from fastapi import APIRouter, Depends, HTTPException, Query

from pydantic import BaseModel, Field, field_validator

from sqlalchemy import select, or_

from sqlalchemy.orm import Session



from app.db.session import get_db

from app.models.statutory import (

    StatutoryInstrument,

    StatutoryProvision,

    StatutoryVersion,

    StatutoryEvent,

)

from app.models.ingestion import IngestionJob, IngestionChunk

from app.models.evidence import EvidenceVerification

from app.models.tenant import TenantMembership

from app.security.auth import get_current_user





router = APIRouter(

    prefix="/research/statutes",

    tags=["statutory-versioning-temporal-law"],

)





INSTRUMENT_TYPES = {

    "act",

    "central_act",

    "state_act",

    "rules",

    "regulations",

    "notification",

    "ordinance",

    "other",

}



EVENT_TYPES = {

    "enacted",

    "published",

    "commenced",

    "amended",

    "inserted",

    "substituted",

    "omitted",

    "repealed",

    "expired",

    "repeal_savings",

    "corrected",

}





# ---------------------------------------------------------------------

# Request schemas

# ---------------------------------------------------------------------



class InstrumentCreate(BaseModel):

    title: str = Field(min_length=2, max_length=500)

    canonical_identifier: str = Field(min_length=2, max_length=250)

    instrument_type: str

    jurisdiction: str = Field(default="India", min_length=2, max_length=150)

    enactment_date: date | None = None

    publication_date: date | None = None



    @field_validator("instrument_type")

    @classmethod

    def valid_type(cls, value):

        value = value.strip().lower()

        if value not in INSTRUMENT_TYPES:

            raise ValueError(

                f"instrument_type must be one of {sorted(INSTRUMENT_TYPES)}"

            )

        return value





class ProvisionCreate(BaseModel):

    provision_ref: str = Field(min_length=1, max_length=120)

    heading: str | None = Field(default=None, max_length=500)





class VersionCreate(BaseModel):

    version_label: str | None = Field(default=None, max_length=120)

    text: str = Field(min_length=1, max_length=100000)

    effective_from: date

    effective_to: date | None = None

    commencement_date: date | None = None

    publication_date: date | None = None

    source_job_id: str = Field(min_length=1, max_length=36)

    source_chunk_id: str = Field(min_length=1, max_length=36)

    evidence_verification_id: str | None = Field(default=None, max_length=36)





class EventCreate(BaseModel):

    event_type: str

    event_date: date

    description: str = Field(min_length=5, max_length=5000)

    amending_instrument: str | None = Field(default=None, max_length=500)

    source_job_id: str = Field(min_length=1, max_length=36)

    source_chunk_id: str = Field(min_length=1, max_length=36)

    evidence_verification_id: str | None = Field(default=None, max_length=36)



    @field_validator("event_type")

    @classmethod

    def valid_event(cls, value):

        value = value.strip().lower()

        if value not in EVENT_TYPES:

            raise ValueError(

                f"event_type must be one of {sorted(EVENT_TYPES)}"

            )

        return value







class VersionUpdate(BaseModel):
    version_label: str | None = Field(default=None, max_length=120)
    text: str | None = Field(default=None, min_length=1, max_length=100000)
    effective_from: date | None = None
    effective_to: date | None = None
    commencement_date: date | None = None
    publication_date: date | None = None
    source_job_id: str | None = Field(default=None, min_length=1, max_length=36)
    source_chunk_id: str | None = Field(default=None, min_length=1, max_length=36)
    evidence_verification_id: str | None = Field(default=None, max_length=36)


class VersionClose(BaseModel):

    effective_to: date





# ---------------------------------------------------------------------

# Identity and evidence helpers

# ---------------------------------------------------------------------



def _identity(db: Session, claims: dict, write: bool = False):

    user_id = claims.get("app_user_id")



    if not user_id:

        raise HTTPException(

            status_code=403,

            detail="Workspace identity is unavailable.",

        )



    memberships = db.scalars(

        select(TenantMembership).where(

            TenantMembership.user_id == user_id

        )

    ).all()



    if not memberships:

        raise HTTPException(

            status_code=403,

            detail="Workspace membership required.",

        )



    if write and not any(

        membership.role in {"owner", "admin"}

        for membership in memberships

    ):

        raise HTTPException(

            status_code=403,

            detail=(

                "Only workspace owners or admins can modify "

                "the shared statutory corpus."

            ),

        )



    return user_id





def _source(

    db: Session,

    job_id: str,

    chunk_id: str,

    verification_id: str | None,

):

    job = db.scalar(

        select(IngestionJob).where(IngestionJob.id == job_id)

    )



    chunk = db.scalar(

        select(IngestionChunk).where(IngestionChunk.id == chunk_id)

    )



    if not job or not chunk or chunk.job_id != job.id:

        raise HTTPException(

            status_code=422,

            detail=(

                "Source chunk must belong to the supplied "

                "ingestion job."

            ),

        )



    verification = None



    if verification_id:

        verification = db.scalar(

            select(EvidenceVerification).where(

                EvidenceVerification.id == verification_id,

                EvidenceVerification.job_id == job_id,

                EvidenceVerification.chunk_id == chunk_id,

            )

        )



        if not verification:

            raise HTTPException(

                status_code=422,

                detail=(

                    "Evidence verification must match the supplied "

                    "source job and chunk."

                ),

            )



    return job, chunk, verification





def _instrument_dict(item):

    return {

        "instrument_id": item.id,

        "title": item.title,

        "canonical_identifier": item.canonical_identifier,

        "instrument_type": item.instrument_type,

        "jurisdiction": item.jurisdiction,

        "enactment_date": (

            item.enactment_date.isoformat()

            if item.enactment_date else None

        ),

        "publication_date": (

            item.publication_date.isoformat()

            if item.publication_date else None

        ),

    }





# ---------------------------------------------------------------------

# Statutory instrument endpoints

# ---------------------------------------------------------------------



@router.post("/instruments", status_code=201)

def create_instrument(

    payload: InstrumentCreate,

    db: Session = Depends(get_db),

    claims: dict = Depends(get_current_user),

):

    user_id = _identity(db, claims, write=True)



    item = StatutoryInstrument(

        **payload.model_dump(),

        created_by=user_id,

    )



    db.add(item)



    try:

        db.flush()

    except Exception:

        db.rollback()

        raise HTTPException(

            status_code=409,

            detail=(

                "An instrument with this canonical_identifier "

                "may already exist."

            ),

        )



    result = _instrument_dict(item)

    db.commit()



    return result





@router.get("/instruments")

def list_instruments(

    q: str | None = Query(default=None, max_length=250),

    db: Session = Depends(get_db),

    claims: dict = Depends(get_current_user),

):

    _identity(db, claims)



    stmt = select(StatutoryInstrument).order_by(

        StatutoryInstrument.title

    ).limit(100)



    if q:

        stmt = stmt.where(

            or_(

                StatutoryInstrument.title.ilike(f"%{q}%"),

                StatutoryInstrument.canonical_identifier.ilike(

                    f"%{q}%"

                ),

            )

        )



    items = db.scalars(stmt).all()



    return {

        "count": len(items),

        "instruments": [

            _instrument_dict(item) for item in items

        ],

    }





# ---------------------------------------------------------------------

# Statutory provision endpoints

# ---------------------------------------------------------------------



@router.post(

    "/instruments/{instrument_id}/provisions",

    status_code=201,

)

def create_provision(

    instrument_id: str,

    payload: ProvisionCreate,

    db: Session = Depends(get_db),

    claims: dict = Depends(get_current_user),

):

    user_id = _identity(db, claims, write=True)



    if not db.get(StatutoryInstrument, instrument_id):

        raise HTTPException(

            status_code=404,

            detail="Statutory instrument not found.",

        )



    item = StatutoryProvision(

        instrument_id=instrument_id,

        created_by=user_id,

        **payload.model_dump(),

    )



    db.add(item)



    try:

        db.flush()

    except Exception:

        db.rollback()

        raise HTTPException(

            status_code=409,

            detail=(

                "This provision reference already exists "

                "for the instrument."

            ),

        )



    result = {

        "provision_id": item.id,

        "instrument_id": item.instrument_id,

        "provision_ref": item.provision_ref,

        "heading": item.heading,

    }



    db.commit()

    return result





@router.get("/instruments/{instrument_id}/provisions")

def list_provisions(

    instrument_id: str,

    db: Session = Depends(get_db),

    claims: dict = Depends(get_current_user),

):

    _identity(db, claims)



    instrument = db.get(StatutoryInstrument, instrument_id)



    if not instrument:

        raise HTTPException(

            status_code=404,

            detail="Statutory instrument not found.",

        )



    items = db.scalars(

        select(StatutoryProvision)

        .where(

            StatutoryProvision.instrument_id == instrument_id

        )

        .order_by(StatutoryProvision.provision_ref)

    ).all()



    return {

        "instrument_id": instrument_id,

        "count": len(items),

        "provisions": [

            {

                "provision_id": item.id,

                "provision_ref": item.provision_ref,

                "heading": item.heading,

                "created_at": (

                    item.created_at.isoformat()

                    if item.created_at else None

                ),

            }

            for item in items

        ],

    }





# ---------------------------------------------------------------------

# Statutory version endpoints

# ---------------------------------------------------------------------



@router.post(

    "/provisions/{provision_id}/versions",

    status_code=201,

)

def create_version(

    provision_id: str,

    payload: VersionCreate,

    db: Session = Depends(get_db),

    claims: dict = Depends(get_current_user),

):

    user_id = _identity(db, claims, write=True)



    if not db.get(StatutoryProvision, provision_id):

        raise HTTPException(

            status_code=404,

            detail="Statutory provision not found.",

        )



    if (

        payload.effective_to

        and payload.effective_to <= payload.effective_from

    ):

        raise HTTPException(

            status_code=422,

            detail=(

                "effective_to must be later than effective_from; "

                "intervals are half-open."

            ),

        )



    _, _, verification = _source(

        db,

        payload.source_job_id,

        payload.source_chunk_id,

        payload.evidence_verification_id,

    )



    # Intervals use [effective_from, effective_to).

    # Overlapping versions are rejected.

    overlap_filters = [

        StatutoryVersion.provision_id == provision_id,

        or_(

            StatutoryVersion.effective_to.is_(None),

            StatutoryVersion.effective_to > payload.effective_from,

        ),

    ]



    if payload.effective_to is not None:

        overlap_filters.append(

            StatutoryVersion.effective_from < payload.effective_to

        )



    overlap = db.scalar(

        select(StatutoryVersion)

        .where(*overlap_filters)

        .limit(1)

    )



    if overlap:

        raise HTTPException(

            status_code=409,

            detail=(

                "This effective interval overlaps an existing version. "

                "Close the earlier interval before adding another."

            ),

        )



    item = StatutoryVersion(

        provision_id=provision_id,

        created_by=user_id,

        verification_status=(

            "verified_integrity"

            if verification

            and verification.integrity_status == "matched"

            else "unverified"

        ),

        **payload.model_dump(),

    )



    db.add(item)

    db.flush()



    result = {

        "version_id": item.id,

        "provision_id": item.provision_id,

        "version_label": item.version_label,

        "effective_from": item.effective_from.isoformat(),

        "effective_to": (

            item.effective_to.isoformat()

            if item.effective_to else None

        ),

        "commencement_date": (

            item.commencement_date.isoformat()

            if item.commencement_date else None

        ),

        "publication_date": (

            item.publication_date.isoformat()

            if item.publication_date else None

        ),

        "verification_status": item.verification_status,

        "source_job_id": item.source_job_id,

        "source_chunk_id": item.source_chunk_id,

        "evidence_verification_id": item.evidence_verification_id,

    }



    db.commit()

    return result







@router.patch("/versions/{version_id}")
def update_version(
    version_id: str,
    payload: VersionUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user),
):
    """Correct an existing captured statutory version without changing its ID."""
    _identity(db, claims, write=True)

    item = db.get(StatutoryVersion, version_id)
    if not item:
        raise HTTPException(
            status_code=404,
            detail="Statutory version not found.",
        )

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one field to update.",
        )

    # A source reference is an inseparable job/chunk pair.
    new_job_id = changes.get("source_job_id", item.source_job_id)
    new_chunk_id = changes.get("source_chunk_id", item.source_chunk_id)
    source_changed = (
        "source_job_id" in changes or "source_chunk_id" in changes
        or "evidence_verification_id" in changes
    )
    verification = None
    if source_changed:
        if not new_job_id or not new_chunk_id:
            raise HTTPException(
                status_code=422,
                detail="Both source_job_id and source_chunk_id are required.",
            )
        verification_id = changes.get(
            "evidence_verification_id",
            item.evidence_verification_id,
        )
        _, _, verification = _source(
            db, new_job_id, new_chunk_id, verification_id
        )

    new_from = changes.get("effective_from", item.effective_from)
    new_to = changes.get("effective_to", item.effective_to)
    if new_from is None:
        raise HTTPException(
            status_code=422,
            detail="effective_from cannot be null.",
        )
    if new_to is not None and new_to <= new_from:
        raise HTTPException(
            status_code=422,
            detail="effective_to must be later than effective_from; intervals are half-open.",
        )

    # Exclude this record while checking the revised [from, to) interval.
    overlap_filters = [
        StatutoryVersion.provision_id == item.provision_id,
        StatutoryVersion.id != item.id,
        or_(
            StatutoryVersion.effective_to.is_(None),
            StatutoryVersion.effective_to > new_from,
        ),
    ]
    if new_to is not None:
        overlap_filters.append(
            StatutoryVersion.effective_from < new_to
        )
    overlap = db.scalar(
        select(StatutoryVersion).where(*overlap_filters).limit(1)
    )
    if overlap:
        raise HTTPException(
            status_code=409,
            detail="The revised effective interval overlaps another version.",
        )

    # Apply only explicitly supplied fields. Null is allowed for optional dates
    # and for clearing an evidence verification reference.
    for field, value in changes.items():
        setattr(item, field, value)

    if source_changed:
        item.verification_status = (
            "verified_integrity"
            if verification
            and verification.integrity_status == "matched"
            else "unverified"
        )

    db.flush()
    result = {
        "version_id": item.id,
        "provision_id": item.provision_id,
        "version_label": item.version_label,
        "effective_from": item.effective_from.isoformat(),
        "effective_to": item.effective_to.isoformat() if item.effective_to else None,
        "commencement_date": (
            item.commencement_date.isoformat()
            if item.commencement_date else None
        ),
        "publication_date": (
            item.publication_date.isoformat()
            if item.publication_date else None
        ),
        "verification_status": item.verification_status,
        "source_job_id": item.source_job_id,
        "source_chunk_id": item.source_chunk_id,
        "evidence_verification_id": item.evidence_verification_id,
        "notice": "Existing version updated; version_id and provision_id were preserved.",
    }
    db.commit()
    return result


@router.post("/versions/{version_id}/close")

def close_version(

    version_id: str,

    payload: VersionClose,

    db: Session = Depends(get_db),

    claims: dict = Depends(get_current_user),

):

    user_id = _identity(db, claims, write=True)



    item = db.get(StatutoryVersion, version_id)



    if not item:

        raise HTTPException(

            status_code=404,

            detail="Statutory version not found.",

        )



    if item.effective_to is not None:

        raise HTTPException(

            status_code=409,

            detail=(

                "This version already has an effective_to date "

                "and cannot be closed again."

            ),

        )



    if payload.effective_to <= item.effective_from:

        raise HTTPException(

            status_code=422,

            detail="effective_to must be later than effective_from.",

        )



    successor = db.scalar(

        select(StatutoryVersion).where(

            StatutoryVersion.provision_id == item.provision_id,

            StatutoryVersion.id != item.id,

            StatutoryVersion.effective_from < payload.effective_to,

            or_(

                StatutoryVersion.effective_to.is_(None),

                StatutoryVersion.effective_to > item.effective_from,

            ),

        ).limit(1)

    )



    if successor:

        raise HTTPException(

            status_code=409,

            detail="The proposed closing date overlaps another version.",

        )



    item.effective_to = payload.effective_to

    item.closed_by = user_id

    item.closed_at = datetime.now(timezone.utc)



    db.flush()



    result = {

        "version_id": item.id,

        "effective_from": item.effective_from.isoformat(),

        "effective_to": item.effective_to.isoformat(),

        "closed_by": item.closed_by,

        "closed_at": item.closed_at.isoformat(),

        "notice": (

            "Only the temporal boundary was closed; "

            "the captured statutory text was not changed."

        ),

    }



    db.commit()

    return result





# ---------------------------------------------------------------------

# Statutory amendment and event endpoints

# ---------------------------------------------------------------------



@router.post(

    "/provisions/{provision_id}/events",

    status_code=201,

)

def create_event(

    provision_id: str,

    payload: EventCreate,

    db: Session = Depends(get_db),

    claims: dict = Depends(get_current_user),

):

    user_id = _identity(db, claims, write=True)



    if not db.get(StatutoryProvision, provision_id):

        raise HTTPException(

            status_code=404,

            detail="Statutory provision not found.",

        )



    _source(

        db,

        payload.source_job_id,

        payload.source_chunk_id,

        payload.evidence_verification_id,

    )



    item = StatutoryEvent(

        provision_id=provision_id,

        created_by=user_id,

        **payload.model_dump(),

    )



    db.add(item)

    db.flush()



    result = {

        "event_id": item.id,

        "provision_id": item.provision_id,

        "event_type": item.event_type,

        "event_date": item.event_date.isoformat(),

        "description": item.description,

        "amending_instrument": item.amending_instrument,

        "source_job_id": item.source_job_id,

        "source_chunk_id": item.source_chunk_id,

        "evidence_verification_id": item.evidence_verification_id,

    }



    db.commit()

    return result





# ---------------------------------------------------------------------

# Historical provision lookup

# ---------------------------------------------------------------------



@router.get("/provisions/{provision_id}/as-of")

def provision_as_of(

    provision_id: str,

    on_date: date = Query(alias="date"),

    db: Session = Depends(get_db),

    claims: dict = Depends(get_current_user),

):

    _identity(db, claims)



    provision = db.get(StatutoryProvision, provision_id)



    if not provision:

        raise HTTPException(

            status_code=404,

            detail="Statutory provision not found.",

        )



    instrument = db.get(

        StatutoryInstrument,

        provision.instrument_id,

    )



    versions = db.scalars(

        select(StatutoryVersion).where(

            StatutoryVersion.provision_id == provision_id,

            StatutoryVersion.effective_from <= on_date,

            or_(

                StatutoryVersion.effective_to.is_(None),

                StatutoryVersion.effective_to > on_date,

            ),

        ).order_by(

            StatutoryVersion.effective_from.desc()

        )

    ).all()



    events = db.scalars(

        select(StatutoryEvent).where(

            StatutoryEvent.provision_id == provision_id,

            StatutoryEvent.event_date <= on_date,

        ).order_by(

            StatutoryEvent.event_date

        )

    ).all()



    if len(versions) == 1:

        status = (

            "complete"

            if versions[0].verification_status == "verified_integrity"

            else "partial"

        )

        selected = versions[0]

    elif len(versions) == 0:

        status = "unresolved"

        selected = None

    else:

        status = "unresolved"

        selected = None



    return {

        "instrument": _instrument_dict(instrument),

        "provision": {

            "provision_id": provision.id,

            "provision_ref": provision.provision_ref,

            "heading": provision.heading,

        },

        "requested_date": on_date.isoformat(),

        "historical_status": status,

        "applicable_version": (

            {

                "version_id": selected.id,

                "version_label": selected.version_label,

                "text": selected.text,

                "effective_from": selected.effective_from.isoformat(),

                "effective_to": (

                    selected.effective_to.isoformat()

                    if selected.effective_to else None

                ),

                "commencement_date": (

                    selected.commencement_date.isoformat()

                    if selected.commencement_date else None

                ),

                "publication_date": (

                    selected.publication_date.isoformat()

                    if selected.publication_date else None

                ),

                "verification_status": selected.verification_status,

                "source_job_id": selected.source_job_id,

                "source_chunk_id": selected.source_chunk_id,

                "evidence_verification_id": (

                    selected.evidence_verification_id

                ),

            }

            if selected else None

        ),

        "events": [

            {

                "event_type": event.event_type,

                "event_date": event.event_date.isoformat(),

                "description": event.description,

                "amending_instrument": event.amending_instrument,

                "source_job_id": event.source_job_id,

                "source_chunk_id": event.source_chunk_id,

            }

            for event in events

        ],

        "notice": (

            "Temporal lookup is limited to versions recorded in this "

            "repository. A partial or unresolved result is not a "

            "statement that no law existed on the requested date."

        ),

    }
