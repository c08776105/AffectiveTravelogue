from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Optional
from datetime import datetime

class WaypointBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    text_note: Optional[str] = Field(None, max_length=500)
    voice_blob_url: Optional[str] = None
    image_url: Optional[str] = None

class WaypointCreate(WaypointBase):
    route_id: str

class WaypointResponse(WaypointBase):
    id: str
    transcription: Optional[str] = None
    stored_at: datetime

    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)
