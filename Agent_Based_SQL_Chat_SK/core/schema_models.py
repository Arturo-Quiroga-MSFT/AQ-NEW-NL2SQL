from __future__ import annotations

from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator


VALID_TYPES = {
    # Simplified whitelist; extend later.
    "INT", "BIGINT", "SMALLINT", "TINYINT", "DECIMAL(18,2)", "DECIMAL(19,4)",
    "DATE", "DATETIME", "DATETIME2", "VARCHAR(20)", "VARCHAR(40)", "VARCHAR(50)",
    "VARCHAR(60)", "VARCHAR(100)", "VARCHAR(200)", "BIT", "FLOAT", "REAL"
}


class Column(BaseModel):
    name: str
    type: str
    nullable: bool = True
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def snake_case(cls, v: str) -> str:
        if v.lower() != v or " " in v:
            raise ValueError(f"Column name '{v}' must be snake_case and lower.")
        return v

    @field_validator("type")
    @classmethod
    def known_type(cls, v: str) -> str:
        if v.upper() not in VALID_TYPES:
            raise ValueError(f"Type '{v}' not in whitelist (extend VALID_TYPES to allow).")
        return v.upper()


class Index(BaseModel):
    name: str
    columns: List[str]
    unique: bool = False


class ForeignKey(BaseModel):
    column: str
    references: str  # format: table(column)


class Dimension(BaseModel):
    name: str
    surrogate_key: Optional[str] = None
    natural_key: Optional[str] = None
    columns: List[Column]
    indexes: List[Index] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def prefix_dim(cls, v: str) -> str:
        if not v.startswith("dim_"):
            raise ValueError("Dimension tables must start with 'dim_'.")
        return v


class Fact(BaseModel):
    name: str
    grain: Optional[str] = None
    foreign_keys: List[ForeignKey] = Field(default_factory=list)
    measures: List[Column] = Field(default_factory=list)
    columns: List[Column] = Field(default_factory=list)
    indexes: List[Index] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def prefix_fact(cls, v: str) -> str:
        if not v.startswith("fact_"):
            raise ValueError("Fact tables must start with 'fact_'.")
        return v


class Entities(BaseModel):
    dimensions: List[Dimension] = Field(default_factory=list)
    facts: List[Fact] = Field(default_factory=list)


class SchemaSpec(BaseModel):
    version: int
    warehouse: Optional[str] = None
    entities: Entities

    def table_dict(self) -> Dict[str, object]:
        d: Dict[str, object] = {}
        for dim in self.entities.dimensions:
            d[dim.name] = dim
        for fact in self.entities.facts:
            d[fact.name] = fact
        return d
