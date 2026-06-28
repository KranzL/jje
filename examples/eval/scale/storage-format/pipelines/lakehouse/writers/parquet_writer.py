from __future__ import annotations

from dataclasses import dataclass, field

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import types as T

from pipelines.lakehouse.writers.schema import build_struct, coerce_to_schema

_DEFAULT_COMPRESSION = "zstd"

_FORMAT_WRITERS = {
    "parquet": "parquet",
    "orc": "orc",
    "json": "json",
    "csv": "csv",
}


@dataclass(frozen=True)
class TableWriteConfig:
    name: str
    path: str
    file_format: str
    columns: list[dict]
    partition_by: list[str] = field(default_factory=list)
    sort_by: list[str] = field(default_factory=list)
    compression: str | None = None
    write_mode: str = "overwrite"
    target_file_mb: int = 256
    options: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict) -> "TableWriteConfig":
        return cls(
            name=raw["name"],
            path=raw["path"],
            file_format=raw["file_format"].lower(),
            columns=raw["columns"],
            partition_by=raw.get("partition_by", []),
            sort_by=raw.get("sort_by", []),
            compression=raw.get("compression"),
            write_mode=raw.get("write_mode", "overwrite"),
            target_file_mb=raw.get("target_file_mb", 256),
            options=raw.get("options", {}),
        )

    @property
    def schema(self) -> T.StructType:
        return build_struct(self.columns)


def _resolve_compression(config: TableWriteConfig) -> str:
    if config.compression is not None:
        return config.compression
    if config.file_format in ("parquet", "orc"):
        return _DEFAULT_COMPRESSION
    return "none"


def _repartition(df: DataFrame, config: TableWriteConfig) -> DataFrame:
    if config.sort_by:
        ordered = df.sortWithinPartitions(*config.sort_by)
    else:
        ordered = df
    return ordered


def write_table(spark: SparkSession, df: DataFrame, config: TableWriteConfig) -> None:
    if config.file_format not in _FORMAT_WRITERS:
        raise ValueError(f"unsupported file_format: {config.file_format}")

    typed = coerce_to_schema(df, config.schema)
    laid_out = _repartition(typed, config)

    writer = laid_out.write.mode(config.write_mode)
    writer = writer.option("compression", _resolve_compression(config))

    for key, value in config.options.items():
        writer = writer.option(key, str(value))

    if config.partition_by:
        writer = writer.partitionBy(*config.partition_by)

    writer.format(_FORMAT_WRITERS[config.file_format]).save(config.path)
