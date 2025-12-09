# precompute.py
import pandas as pd
import pyreadstat
import numpy as np
import pgeocode
from lifelines import KaplanMeierFitter
from lifelines.statistics import logrank_test
import os

# --- PATH CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# UPDATE THIS IF NEEDED
SOURCE_FILE = os.path.join(
    "/Users/lanrr/Downloads/706_Data_Visualization/drive-download-20251208T024017Z-1-001",
    "LU_REC_MAP.sav"
)


def get_geocoder():
    return pgeocode.Nominatim('us')

def get_coords(zip_code, geocoder):
    if pd.isna(zip_code) or str(zip_code).strip() == '':
        return None, None
    zip_str = str(zip_code).strip()[:5].zfill(5)
    try:
        loc = geocoder.query_postal_code(zip_str)
        if not pd.isna(loc['latitude']):
            return loc['latitude'], loc['longitude']
    except:
        pass
    return None, None

def main():
    print(f"Running script in: {SCRIPT_DIR}")
    
    # 1. Load Data
    try:
        print("1. Loading raw data...")
        df, meta = pyreadstat.read_sav(SOURCE_FILE)

        # Load donor-level data
        DONOR_FILE = os.path.join(
            "/Users/lanrr/Downloads/706_Data_Visualization/drive-download-20251208T024017Z-1-001",
            "LU_DON_MAP.sav"
        )
        donor_df, donor_meta = pyreadstat.read_sav(DONOR_FILE)

        # Clean donor dates
        donor_df["DON_RECOV_DT"] = pd.to_datetime(donor_df["DON_RECOV_DT"], errors="coerce")
        donor_df["Year"] = donor_df["DON_RECOV_DT"].dt.year
        donor_df["Month"] = donor_df["DON_RECOV_DT"].dt.month

    except FileNotFoundError:
        print(f"ERROR: Could not find file at {SOURCE_FILE}")
        return



    except FileNotFoundError:
        print(f"ERROR: Could not find file at {SOURCE_FILE}")
        return

    if 'REC_TX_DT' in df.columns:
        df['REC_TX_DT'] = pd.to_datetime(df['REC_TX_DT'], errors='coerce')
        df['Year'] = df['REC_TX_DT'].dt.year
        df['Month'] = df['REC_TX_DT'].dt.month
    
    df_dcd0 = df[df['DCD'] == 0].copy()


    # 2. Map Data
    print("2. Processing Map Data...")
    nomi = get_geocoder()
    map_data = []
    zip_cache = {}
    
    # Group by Year, Month, OPO, Center, and ZIP codes
    grouped = df_dcd0.groupby(['Year', 'Month', 'DON_OPO', 'REC_CTR_CD', 'OPO_ZIP', 'TXP_CTR_ZIP']).size().reset_index(name='Count')
    
    for i, row in grouped.iterrows():
        # Quick check for DCU rate
        subset = df_dcd0[(df_dcd0['Year'] == row['Year']) & 
                         (df_dcd0['Month'] == row['Month']) &
                         (df_dcd0['DON_OPO'] == row['DON_OPO']) & 
                         (df_dcd0['REC_CTR_CD'] == row['REC_CTR_CD'])]
        dcu_rate = subset['any_DCU'].mean() if 'any_DCU' in subset.columns else 0
        
        opo_zip = str(row['OPO_ZIP'])[:5]
        if opo_zip not in zip_cache: zip_cache[opo_zip] = get_coords(opo_zip, nomi)
        
        ctr_zip = str(row['TXP_CTR_ZIP'])[:5]
        if ctr_zip not in zip_cache: zip_cache[ctr_zip] = get_coords(ctr_zip, nomi)
        
        if zip_cache[opo_zip][0] and zip_cache[ctr_zip][0]:
            map_data.append({
                'Year': int(row['Year']),
                'Month': int(row['Month']),
                'OPO': row['DON_OPO'],
                'OPO_Zip': opo_zip,
                'OPO_Lat': zip_cache[opo_zip][0],
                'OPO_Lon': zip_cache[opo_zip][1],
                'Center': row['REC_CTR_CD'],
                'Center_Zip': ctr_zip,
                'Center_Lat': zip_cache[ctr_zip][0],
                'Center_Lon': zip_cache[ctr_zip][1],
                'Count': row['Count'],
                'DCU_Rate': dcu_rate
            })

    pd.DataFrame(map_data).to_csv(os.path.join(SCRIPT_DIR, 'viz_map_data.csv'), index=False)

    # 3. Survival Data (THE FIX IS HERE)
    print("3. Calculating Survival Curves...")
    s_df = df_dcd0[(df_dcd0['REC_TX_DT'] >= '2018-01-01') & (df_dcd0['REC_TX_DT'] <= '2024-12-31')].copy()
    s_df['GraftTime'] = pd.to_numeric(s_df['GraftTime'], errors='coerce')
    s_df['GraftDeath'] = pd.to_numeric(s_df['GraftDeath'], errors='coerce')
    s_df = s_df.dropna(subset=['GraftTime', 'GraftDeath'])
    s_df = s_df[(s_df['GraftTime'] >= 0)]

    # Convert to boolean: 1 (event/death) → True, 0 (censored/survive) → False
    # Per lifelines docs: True = event observed, False = censored
    s_df['EventObserved'] = s_df['GraftDeath'] == 1
    
    # Censor patients at 1825 days instead of removing them
    # If GraftTime > 1825 and they survived, censor them at 1825
    s_df.loc[(s_df['GraftTime'] > 1825) & (s_df['EventObserved'] == False), 'GraftTime'] = 1825
    # If GraftTime > 1825 and they died (after 5 years), exclude them (event outside our window)
    s_df = s_df[~((s_df['GraftTime'] > 1825) & (s_df['EventObserved'] == True))]


    kmf = KaplanMeierFitter()
    curve_export = []
    p_values = []
    
    # Helper to standardise dataframe columns
    def process_km(fitter, label_name):
        d = fitter.survival_function_
        # RENAME column to standard 'survival_prob'
        d.columns = ['survival_prob'] 
        d['ci_lower'] = fitter.confidence_interval_.iloc[:, 0]
        d['ci_upper'] = fitter.confidence_interval_.iloc[:, 1]
        d['Group'] = label_name
        d['GraftTime'] = d.index
        return d

    # Nationwide
    kmf.fit(s_df['GraftTime'], s_df['GraftDeath'], label='Nationwide')
    curve_export.append(process_km(kmf, 'Nationwide'))
    
    # OPOs
    opos = s_df['DON_OPO'].unique()
    print(f"   - Processing {len(opos)} OPOs...")
    
    for opo in opos:
        subset = s_df[s_df['DON_OPO'] == opo]
        rest = s_df[s_df['DON_OPO'] != opo]
        if len(subset) > 10:
            kmf.fit(subset['GraftTime'], subset['GraftDeath'], label=str(opo))
            curve_export.append(process_km(kmf, str(opo)))
            
            # P-Values
            try:
                res = logrank_test(subset['GraftTime'], rest['GraftTime'], 
                                   event_observed_A=subset['GraftDeath'], 
                                   event_observed_B=rest['GraftDeath'])
                p_values.append({'OPO': opo, 'P_Value': res.p_value})
            except:
                p_values.append({'OPO': opo, 'P_Value': np.nan})

    pd.concat(curve_export).to_csv(os.path.join(SCRIPT_DIR, 'viz_survival_curves.csv'), index=False)
    pd.DataFrame(p_values).to_csv(os.path.join(SCRIPT_DIR, 'viz_survival_stats.csv'), index=False)


   
    # ----------------------------------------------------------
    # 4. DONOR UTILIZATION DATA 
    # ----------------------------------------------------------
    print("4. Computing Donor Utilization & CAS Period Classification...")

    # CAS date
    CAS_DATE = pd.to_datetime("2023-03-09")

    # Pre/Post CAS classification
    donor_df["CAS_Period"] = donor_df["DON_RECOV_DT"].apply(
        lambda d: "Pre-CAS" if d < CAS_DATE else "Post-CAS"
    )
    
    lundon_df = donor_df[
        (donor_df["DCD"] == 0) &
        (~donor_df["LUNDON"].isna())
    ].copy()
    
        # Monthly OPO-level donor utilization summary, including LUNDON (DBD will have non-missing)
    donor_util = (
        donor_df.groupby(["Year", "Month", "DON_OPO", "CAS_Period", "DCD"])
        .agg(
            Total_Donors=("Transplanted", "count"),
            Used_Donors=("Transplanted", "sum"),
            Utilization_Rate=("Transplanted", "mean"),
            DCU_Rate=("DCU_any", "mean"),
            Mean_LUNDON=("LUNDON", "mean"),
            Median_LUNDON=("LUNDON", "median"),
            N_LUNDON=("LUNDON", "count"),
        )
        .reset_index()
    )

    donor_util.to_csv(os.path.join(SCRIPT_DIR, "viz_donor_utilization.csv"), index=False)

    # CAS summary (OPO-level, not monthly)
    donor_cas_summary = (
        donor_df.groupby(["DON_OPO", "CAS_Period"])
        .agg(
            Total=("Transplanted", "count"),
            Used=("Transplanted", "sum"),
            Utilization=("Transplanted", "mean")
        )
        .reset_index()
    )

    donor_lundon_summary = (
        lundon_df
        .groupby(["DON_OPO", "CAS_Period"])
        .agg(
            Mean_LUNDON=("LUNDON", "mean"),
            Median_LUNDON=("LUNDON", "median"),
            N=("LUNDON", "count")
        )
        .reset_index()
    )

    donor_lundon_summary.to_csv(
        os.path.join(SCRIPT_DIR, "viz_lundon_summary.csv"),
        index=False
    )





    print("DONE! CSVs regenerated with correct column names.")

if __name__ == "__main__":
    main()
