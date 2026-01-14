from fastapi import APIRouter, Query
from typing import Optional, Literal
import pandas as pd
import os

router = APIRouter()

# Load data at startup
DATA_PATH = os.environ.get("DATA_PATH", os.path.join(os.path.dirname(__file__), "../../data"))
UTIL_DATA = pd.read_csv(os.path.join(DATA_PATH, "viz_donor_utilization.csv"))
LUNDON_DATA = pd.read_csv(os.path.join(DATA_PATH, "viz_lundon_summary.csv"))

@router.get("/summary")
async def get_utilization_summary(
    cas_period: Optional[Literal["All", "Pre-CAS", "Post-CAS"]] = Query("All"),
    donor_type: Optional[Literal["All", "DBD", "DCD"]] = Query("All"),
    opos: Optional[str] = Query(None, description="Comma-separated list of OPOs")
):
    """
    Get donor utilization summary by OPO.
    """
    df = UTIL_DATA.copy()
    
    # Apply CAS filter
    if cas_period and cas_period != "All":
        df = df[df['CAS_Period'] == cas_period]
    
    # Apply donor type filter
    if donor_type and donor_type != "All":
        dcd_val = 1 if donor_type == "DCD" else 0
        df = df[df['DCD'] == dcd_val]
    
    # Apply OPO filter
    if opos:
        opo_list = [o.strip() for o in opos.split(",")]
        df = df[df['DON_OPO'].isin(opo_list)]
    
    # Aggregate by OPO
    summary = df.groupby('DON_OPO').agg({
        'Total_Donors': 'sum',
        'Used_Donors': 'sum',
        'DCU_Rate': 'mean'
    }).reset_index()
    
    summary['Utilization_Rate'] = summary['Used_Donors'] / summary['Total_Donors']
    
    return summary.to_dict(orient="records")

@router.get("/national")
async def get_national_utilization(
    cas_period: Optional[Literal["All", "Pre-CAS", "Post-CAS"]] = Query("All"),
    donor_type: Optional[Literal["All", "DBD", "DCD"]] = Query("All")
):
    """
    Get national utilization rate.
    """
    df = UTIL_DATA.copy()
    
    if cas_period and cas_period != "All":
        df = df[df['CAS_Period'] == cas_period]
    
    if donor_type and donor_type != "All":
        dcd_val = 1 if donor_type == "DCD" else 0
        df = df[df['DCD'] == dcd_val]
    
    total_donors = df['Total_Donors'].sum()
    used_donors = df['Used_Donors'].sum()
    
    return {
        "national_utilization": used_donors / total_donors if total_donors > 0 else 0,
        "total_donors": int(total_donors),
        "used_donors": int(used_donors)
    }

@router.get("/compare")
async def get_dcd_dbd_comparison(
    cas_period: Optional[Literal["All", "Pre-CAS", "Post-CAS"]] = Query("All"),
    opos: Optional[str] = Query(None)
):
    """
    Compare DCD vs DBD utilization rates.
    """
    df = UTIL_DATA.copy()
    
    if cas_period and cas_period != "All":
        df = df[df['CAS_Period'] == cas_period]
    
    if opos:
        opo_list = [o.strip() for o in opos.split(",")]
        df = df[df['DON_OPO'].isin(opo_list)]
    
    # Aggregate by OPO and DCD status
    comparison = df.groupby(['DON_OPO', 'DCD']).agg({
        'Total_Donors': 'sum',
        'Used_Donors': 'sum'
    }).reset_index()
    
    comparison['Utilization_Rate'] = comparison['Used_Donors'] / comparison['Total_Donors']
    comparison['Donor_Type'] = comparison['DCD'].map({0: 'DBD', 1: 'DCD'})
    
    return comparison.to_dict(orient="records")

@router.get("/lundon")
async def get_lundon_scores(
    opos: Optional[str] = Query(None)
):
    """
    Get mean LUNDON scores by OPO (DBD donors only).
    """
    df = LUNDON_DATA.copy()
    
    if opos:
        opo_list = [o.strip() for o in opos.split(",")]
        df = df[df['DON_OPO'].isin(opo_list)]
    
    return df.to_dict(orient="records")

@router.get("/opos")
async def get_available_opos():
    """Get list of all OPOs with utilization data."""
    opos = UTIL_DATA['DON_OPO'].unique().tolist()
    return {"opos": sorted(opos)}
