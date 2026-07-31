from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


DateMode = Literal["claimed_period", "latest_available"]
PeriodName = Literal["before", "during", "after", "latest"]


class SearchRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    date_mode: DateMode = "claimed_period"
    start_date: date | None = None
    end_date: date | None = None
    reference_date: date | None = None
    radius_km: float = Field(default=5, gt=0, le=25)
    cloud_cover: float = Field(default=30, ge=0, le=100)
    window_days: int = Field(default=30, ge=5, le=365)

    @model_validator(mode="after")
    def validate_dates(self) -> "SearchRequest":
        if self.date_mode == "claimed_period":
            if self.start_date is None:
                raise ValueError("start_date is required for claimed_period mode")
            if self.end_date is None:
                self.end_date = self.start_date
            if self.end_date < self.start_date:
                raise ValueError("end_date must be on or after start_date")
        elif self.reference_date is None:
            self.reference_date = date.today()
        return self


class SceneResult(BaseModel):
    period: PeriodName
    item_id: str
    datetime: str
    cloud_cover: float | None = None
    platform: str | None = None
    coverage_fraction: float = Field(ge=0, le=1)
    item_url: str
    preview_url: str
    target_date: str
    date_distance_days: int
    selection_reason: str


class PeriodResult(BaseModel):
    period: PeriodName
    search_start: str
    search_end: str
    target_date: str
    scene: SceneResult | None = None
    message: str | None = None
    recency_explanation: str | None = None
    latest_catalogued_datetime: str | None = None
    closer_or_newer_cloudy_count: int = 0
    closest_or_newest_cloudy_datetime: str | None = None
    closest_or_newest_cloud_cover: float | None = None


class SearchResponse(BaseModel):
    collection: str
    date_mode: DateMode
    reference_date: str
    bbox: list[float]
    cloud_threshold: float
    resolution_notice: str
    cloud_notice: str
    periods: list[PeriodResult]
