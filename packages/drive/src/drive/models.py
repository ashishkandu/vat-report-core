from datetime import datetime

from pydantic import BaseModel, Field


class GoogleDriveFile(BaseModel):
    kind: str | None = None
    mime_type: str | None = Field(None, alias="mimeType")
    id: str
    name: str
    modified_time: datetime | None = Field(None, alias="modifiedTime")

    class Config:
        populate_by_name = True


class GoogleDriveFileList(BaseModel):
    kind: str
    next_page_token: str | None = Field(None, alias="nextPageToken")
    incomplete_search: bool | None = Field(None, alias="incompleteSearch")
    files: list[GoogleDriveFile]

    class Config:
        populate_by_name = True
