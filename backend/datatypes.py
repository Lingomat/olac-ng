from typing import TypedDict, NotRequired
from datetime import datetime
from bson import ObjectId

# *** Archive collection - comes from XML file (in dev)

class XMLArchive(TypedDict):
    _id: NotRequired[ObjectId]
    id: str
    baseURL: str
    dateApproved: datetime

class ValidationErrors(TypedDict):
    baseURL: str
    error: str


class FetchStatus(TypedDict):
    id: str
    type: str
    pages: int | None  # Pages of records (XML files in the filestore)
    status: str
    lastFetch: datetime | None
    lastError: str | None
    retryAttempt: int
    # True if all pre-reqs for validation are met (custom schemas)
    validatorPreReqs: bool
    validated: bool
    validateErrors: list[ValidationErrors]

# Static archive collection


class CustomSchemaLoc(TypedDict):
    namespace: str
    schema: str


class OLACArchive(TypedDict):
    _id: NotRequired[ObjectId]
    id: str
    type: str
    baseURL: str
    identify: dict                  # XML2Dict parsed identify
    lastModified: datetime
    customSchemas: list[CustomSchemaLoc]

# Custom schema store collection


class CustomSchemaStore(TypedDict):
    _id: NotRequired[ObjectId]
    namespace: str
    schema: bytes
    date: datetime

# Records collection


class OLACRecord(TypedDict):
    _id: NotRequired[ObjectId]
    languages: NotRequired[list[str]]
    countries: NotRequired[list[str]]
    id: str
    identifier: str
    datestamp: datetime
    metadata: dict  # XML2Dict parsed metadata

# Countries collection


class CountryDB(TypedDict):
    code: str
    name: str
    area: str

# Regional areas collection


class AreaDB(TypedDict):
    area: str
    countries: list[str]
    languages: list[str]

# Languages collection


class LanguageDB(TypedDict):
    code: str
    name: str
    country: str | None
    area: str | None
    altNames: list[str]
    dialects: list[str]
