"""
GENERATED from contract/stock_coverage.yaml (contract stock_coverage, version 0.5.1)
by compiler/gen_schema.py. Do not edit: change the contract and run `python compiler/gen_schema.py`.
tests/test_generated.py regenerates this file and fails on any difference.

Column order is the load order. Types are Snowflake types; pandas columns are lower case and
write_pandas(quote_identifiers=False) maps them to upper-case Snowflake identifiers.
"""

from __future__ import annotations

__schema_version__ = '0.5.1'
CONTRACT_ID = 'stock_coverage'

TABLES: dict[str, dict[str, str]] = {
    'DIM_CALENDAR': {
        'month_start': 'DATE',
        'year': 'NUMBER(4,0)',
        'quarter': 'NUMBER(1,0)',
        'month_num': 'NUMBER(2,0)',
        'month_label': 'VARCHAR',
    },
    'DIM_GEO': {
        'country_id': 'NUMBER(6,0)',
        'country_code': 'VARCHAR',
        'country_name': 'VARCHAR',
        'region_code': 'VARCHAR',
        'region_name': 'VARCHAR',
    },
    'DIM_ITEM': {
        'item_id': 'NUMBER(6,0)',
        'sku_code': 'VARCHAR',
        'sku_name': 'VARCHAR',
        'family_code': 'VARCHAR',
        'family_name': 'VARCHAR',
        'range_code': 'VARCHAR',
        'range_name': 'VARCHAR',
        'item_type': 'VARCHAR',
        'lifecycle_status': 'VARCHAR',
        'raw_unit': 'VARCHAR',
        'qty_eq_factor': 'NUMBER(10,4)',
        'dimension': 'VARCHAR',
        'base_unit': 'VARCHAR',
        'std_cost_eur': 'NUMBER(12,4)',
        'cogs_eur': 'NUMBER(12,4)',
    },
    'DIM_WAREHOUSE': {
        'warehouse_id': 'NUMBER(6,0)',
        'warehouse_code': 'VARCHAR',
        'warehouse_type': 'VARCHAR',
        'country_id': 'NUMBER(6,0)',
    },
    'DIM_BATCH': {
        'batch_id': 'NUMBER(8,0)',
        'batch_code': 'VARCHAR',
        'item_id': 'NUMBER(6,0)',
        'batch_status': 'VARCHAR',
        'production_month': 'DATE',
        'expiry_date': 'DATE',
    },
    'FCT_STOCK_SNAPSHOT': {
        'snapshot_month': 'DATE',
        'batch_id': 'NUMBER(8,0)',
        'warehouse_id': 'NUMBER(6,0)',
        'item_id': 'NUMBER(6,0)',
        'country_id': 'NUMBER(6,0)',
        'expiry_bucket': 'VARCHAR',
        'stock_qty_raw': 'NUMBER(18,4)',
        'stock_qty_eq': 'NUMBER(18,4)',
        'stock_value_eur': 'NUMBER(18,4)',
    },
    'FCT_FORECAST': {
        'forecast_month': 'DATE',
        'item_id': 'NUMBER(6,0)',
        'country_id': 'NUMBER(6,0)',
        'forecast_qty_raw': 'NUMBER(18,4)',
        'forecast_qty_eq': 'NUMBER(18,4)',
        'forecast_value_eur': 'NUMBER(18,4)',
    },
}

# Declared grains. A declared grain is a promise checked by a quality expectation, not an assumption.
GRAINS: dict[str, tuple[str, ...]] = {
    'DIM_CALENDAR': ('month_start',),
    'DIM_GEO': ('country_id',),
    'DIM_ITEM': ('item_id',),
    'DIM_WAREHOUSE': ('warehouse_id',),
    'DIM_BATCH': ('batch_id',),
    'FCT_STOCK_SNAPSHOT': ('snapshot_month', 'batch_id', 'warehouse_id'),
    'FCT_FORECAST': ('forecast_month', 'item_id', 'country_id'),
}

# attribute -> (table, column, applicability class)
ATTRIBUTES: dict[str, tuple[str, str, str]] = {
    'sku_code': ('DIM_ITEM', 'sku_code', 'CONFORMED'),
    'family_code': ('DIM_ITEM', 'family_code', 'CONFORMED'),
    'range_code': ('DIM_ITEM', 'range_code', 'CONFORMED'),
    'lifecycle_status': ('DIM_ITEM', 'lifecycle_status', 'CONFORMED'),
    'dimension': ('DIM_ITEM', 'dimension', 'CONFORMED'),
    'country_code': ('DIM_GEO', 'country_code', 'CONFORMED'),
    'region_code': ('DIM_GEO', 'region_code', 'CONFORMED'),
    'batch_status': ('DIM_BATCH', 'batch_status', 'SNAPSHOT_ONLY'),
    'expiry_bucket': ('FCT_STOCK_SNAPSHOT', 'expiry_bucket', 'SNAPSHOT_ONLY'),
    'warehouse_code': ('DIM_WAREHOUSE', 'warehouse_code', 'SNAPSHOT_ONLY'),
    'warehouse_type': ('DIM_WAREHOUSE', 'warehouse_type', 'SNAPSHOT_ONLY'),
    'item_type': ('DIM_ITEM', 'item_type', 'SNAPSHOT_ONLY'),
}

# CONFORMED: groups and filters the snapshot and the flow alike.
# SNAPSHOT_ONLY (stock-only): groups and filters the snapshot; the flow stays at the parent conformed grain.
CONFORMED: tuple[str, ...] = ('sku_code', 'family_code', 'range_code', 'lifecycle_status', 'dimension', 'country_code', 'region_code')
SNAPSHOT_ONLY: tuple[str, ...] = ('batch_status', 'expiry_bucket', 'warehouse_code', 'warehouse_type', 'item_type')
NOT_APPLICABLE: tuple[str, ...] = ()

# measure basis -> (stock_on_hand column, demand_forecast column). The result of the metric is always in months;
# a basis is where stock and forecast are measured before the ratio.
BASES: dict[str, tuple[str, str]] = {
    'NATIVE': ('stock_qty_raw', 'forecast_qty_raw'),
    'QTY_EQ': ('stock_qty_eq', 'forecast_qty_eq'),
    'VALUE': ('stock_value_eur', 'forecast_value_eur'),
}
# measure basis -> where it is valid (the rows and totals the call returns)
BASIS_VALID_WHEN: dict[str, str] = {
    'NATIVE': 'ONE_ITEM_PER_ROW',
    'QTY_EQ': 'ONE_DIMENSION_PER_ROW',
    'VALUE': 'ALWAYS',
}
DEFAULT_BASIS = 'QTY_EQ'
# item dimension -> base unit; each item's dimension and base unit are columns of the item table
ITEM_DIMENSIONS: dict[str, str] = {
    'MASS': 'kg',
    'VOLUME': 'L',
}
ITEM_BASIS_COLUMNS = {'table': 'DIM_ITEM', 'key': 'item_id', 'dimension': 'dimension', 'base_unit': 'base_unit', 'native_unit': 'raw_unit', 'factor': 'qty_eq_factor'}

HORIZON_MONTHS = 24
