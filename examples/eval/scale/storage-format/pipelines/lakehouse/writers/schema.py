from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T

_PRIMITIVES: dict[str, T.DataType] = {
    "string": T.StringType(),
    "int": T.IntegerType(),
    "bigint": T.LongType(),
    "double": T.DoubleType(),
    "decimal(18,2)": T.DecimalType(18, 2),
    "decimal(38,9)": T.DecimalType(38, 9),
    "boolean": T.BooleanType(),
    "date": T.DateType(),
    "timestamp": T.TimestampType(),
}


def resolve_type(type_name: str) -> T.DataType:
    key = type_name.strip().lower()
    if key not in _PRIMITIVES:
        raise ValueError(f"unknown column type: {type_name}")
    return _PRIMITIVES[key]


def build_struct(columns: list[dict]) -> T.StructType:
    fields = []
    for col in columns:
        nullable = col.get("nullable", True)
        fields.append(T.StructField(col["name"], resolve_type(col["type"]), nullable))
    return T.StructType(fields)


def coerce_to_schema(df: DataFrame, schema: T.StructType) -> DataFrame:
    projected = []
    for field in schema.fields:
        if field.name not in df.columns:
            raise ValueError(f"source frame missing column: {field.name}")
        projected.append(F.col(field.name).cast(field.dataType).alias(field.name))
    return df.select(*projected)
