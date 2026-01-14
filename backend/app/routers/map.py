from fastapi import APIRouter, Query
from typing import Optional, List
import pandas as pd
import os

router = APIRouter()

# Load data at startup
DATA_PATH = os.environ.get("DATA_PATH", os.path.join(os.path.dirname(__file__), "../../data"))
MAP_DATA = pd.read_csv(os.path.join(DATA_PATH, "viz_map_data.csv"))

# Ensure Month column exists
if 'Month' not in MAP_DATA.columns:
    MAP_DATA['Month'] = 1

# Create YearMonth column
MAP_DATA['YearMonth'] = MAP_DATA['Year'] * 100 + MAP_DATA['Month']

@router.get("/connections")
async def get_connections(
    start_year: int = Query(2018, description="Start year filter"),
    end_year: int = Query(2024, description="End year filter"),
    start_month: int = Query(1, ge=1, le=12, description="Start month filter"),
    end_month: int = Query(12, ge=1, le=12, description="End month filter"),
    opo: Optional[str] = Query(None, description="Filter by specific OPO")
):
    """
    Get OPO-Center connections with optional filters.
    Returns aggregated transplant data between OPOs and transplant centers.
    """
    df = MAP_DATA.copy()
    
    # Create YearMonth for filtering
    start_ym = start_year * 100 + start_month
    end_ym = end_year * 100 + end_month
    
    # Apply filters
    df = df[(df['YearMonth'] >= start_ym) & (df['YearMonth'] <= end_ym)]
    
    if opo:
        df = df[df['OPO'] == opo]
    
    # Aggregate connections
    conn_agg = df.groupby(['OPO', 'Center', 'OPO_Lat', 'OPO_Lon', 'Center_Lat', 'Center_Lon']).agg({
        'Count': 'sum',
        'DCU_Rate': 'mean',
        'OPO_Zip': 'first',
        'Center_Zip': 'first'
    }).reset_index()
    conn_agg = conn_agg.rename(columns={'Count': 'Transplants'})
    
    return conn_agg.to_dict(orient="records")

@router.get("/opos")
async def get_opos(
    start_year: int = Query(2018),
    end_year: int = Query(2024),
    start_month: int = Query(1, ge=1, le=12),
    end_month: int = Query(12, ge=1, le=12)
):
    """
    Get OPO summary data (location, total transplants, DCU rate).
    """
    df = MAP_DATA.copy()
    
    # Create YearMonth for filtering
    start_ym = start_year * 100 + start_month
    end_ym = end_year * 100 + end_month
    
    df = df[(df['YearMonth'] >= start_ym) & (df['YearMonth'] <= end_ym)]
    
    # Aggregate by OPO
    opo_agg = df.groupby('OPO').agg({
        'Count': 'sum',
        'DCU_Rate': 'mean',
        'OPO_Lat': 'first',
        'OPO_Lon': 'first'
    }).reset_index()
    opo_agg = opo_agg.rename(columns={'Count': 'Transplants'})
    
    return opo_agg.to_dict(orient="records")

@router.get("/date-range")
async def get_date_range():
    """Get available date range in the data."""
    min_ym = int(MAP_DATA['YearMonth'].min())
    max_ym = int(MAP_DATA['YearMonth'].max())
    return {
        "min_year_month": min_ym,
        "max_year_month": max_ym,
        "cas_implementation": {"year": 2023, "month": 3, "year_month": 202303}
    }

