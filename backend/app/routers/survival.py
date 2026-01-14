from fastapi import APIRouter, Query
from typing import Optional, List
import pandas as pd
import os

router = APIRouter()

# Load data at startup
DATA_PATH = os.environ.get("DATA_PATH", os.path.join(os.path.dirname(__file__), "../../data"))
SURVIVAL_CURVES = pd.read_csv(os.path.join(DATA_PATH, "viz_survival_curves.csv"))
SURVIVAL_STATS = pd.read_csv(os.path.join(DATA_PATH, "viz_survival_stats.csv"))

@router.get("/curves")
async def get_survival_curves(
    opos: Optional[str] = Query(None, description="Comma-separated list of OPOs"),
    include_nationwide: bool = Query(True, description="Include nationwide reference curve")
):
    """
    Get Kaplan-Meier survival curves for selected OPOs.
    Returns survival probability over time with confidence intervals.
    """
    df = SURVIVAL_CURVES.copy()
    
    groups_to_include = []
    
    if include_nationwide:
        groups_to_include.append("Nationwide")
    
    if opos:
        opo_list = [o.strip() for o in opos.split(",")]
        groups_to_include.extend(opo_list)
    
    if groups_to_include:
        df = df[df['Group'].isin(groups_to_include)]
    
    return df.to_dict(orient="records")

@router.get("/stats")
async def get_survival_stats(
    opos: Optional[str] = Query(None, description="Comma-separated list of OPOs")
):
    """
    Get log-rank test statistics (p-values) comparing OPOs vs nationwide.
    """
    df = SURVIVAL_STATS.copy()
    
    if opos:
        opo_list = [o.strip() for o in opos.split(",")]
        df = df[df['OPO'].isin(opo_list)]
    
    return df.to_dict(orient="records")

@router.get("/opos")
async def get_available_opos():
    """Get list of all available OPOs with survival data."""
    opos = SURVIVAL_CURVES[SURVIVAL_CURVES['Group'] != 'Nationwide']['Group'].unique().tolist()
    return {"opos": sorted(opos)}
