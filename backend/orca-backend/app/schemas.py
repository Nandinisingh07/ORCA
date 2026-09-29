from typing import Literal

from pydantic import BaseModel, Field


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    session_id: str | None = None
    language: str | None = None  # "en"/"hi"/"gu"/"ta" or a display name like "हिन्दी (Hindi)"; None = auto
    mode: Literal["simple", "technical"] = "simple"
    place: str | None = None  # current UI selection, e.g. "Veraval, Gujarat"
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    scenario: Literal["calm", "rough", "storm"] | None = None  # demo only (forces labelled mock data)


class RouteIn(BaseModel):
    origin: str
    distance_km: float = Field(default=20, gt=0, le=200)
    bearing_deg: float | None = Field(default=None, ge=0, lt=360)
    day: str = "today"
    scenario: Literal["calm", "rough", "storm"] | None = None


class PointIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
