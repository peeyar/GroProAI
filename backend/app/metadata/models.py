"""Typed views over model-map.json + TMDL. No schema names live in app code —
everything the app knows about the semantic model flows through these objects."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TmdlTable:
    name: str
    columns: tuple[str, ...]
    measures: tuple[str, ...]


@dataclass(frozen=True)
class TmdlModel:
    tables: dict[str, TmdlTable]

    @property
    def measures(self) -> frozenset[str]:
        return frozenset(m for t in self.tables.values() for m in t.measures)

    @property
    def columns(self) -> frozenset[tuple[str, str]]:
        return frozenset((t.name, c) for t in self.tables.values() for c in t.columns)


@dataclass(frozen=True)
class Bucket:
    key: str
    label: str
    yoy: str
    seq: str

    def measure(self, flavor: str) -> str:
        if flavor == "yoy":
            return self.yoy
        if flavor == "seq":
            return self.seq
        raise ValueError(f"Unknown flavor {flavor!r} (expected 'yoy' or 'seq')")


@dataclass(frozen=True)
class DrillLevel:
    level: str
    label: str
    table: str
    column: str


@dataclass(frozen=True)
class Periods:
    table: str
    column: str
    current: str
    prior_year: str
    prior_quarter: str


@dataclass(frozen=True)
class Allowlist:
    tables: frozenset[str]
    columns: frozenset[tuple[str, str]]
    measures: frozenset[str]


@dataclass(frozen=True)
class ModelContext:
    model_name: str
    total: Bucket
    buckets: tuple[Bucket, ...]
    drill_path: tuple[DrillLevel, ...]
    periods: Periods
    drill_row_cap: int
    tmdl: TmdlModel
    allowlist: Allowlist
    glossary: str

    def bridge_measures(self, flavor: str) -> list[tuple[str, str]]:
        """(label, measure name) for the six buckets followed by the total."""
        return [(b.label, b.measure(flavor)) for b in (*self.buckets, self.total)]
