# app.py
import streamlit as st
import pandas as pd
import altair as alt
import os
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Lung Transplant Data Visualization", page_icon="🫁", layout="wide")

@st.cache_data
def load_data():
    # Use relative path to look in the same folder as app.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        map_df = pd.read_csv(os.path.join(script_dir, 'viz_map_data.csv'))
        surv_df = pd.read_csv(os.path.join(script_dir, 'viz_survival_curves.csv'))
        stats_df = pd.read_csv(os.path.join(script_dir, 'viz_survival_stats.csv'))
        return map_df, surv_df, stats_df
    except FileNotFoundError:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

map_data, survival_data, survival_stats = load_data()

# --- TAB 1: Viz Map ---
@st.fragment
def run_viz_tab():
    st.header("OPO & Transplant Center Connections")
    if map_data.empty:
        st.error("Map data not found. Run precompute.py first.")
        return

    # Handle both old format (Year only) and new format (Year + Month)
    if 'Month' in map_data.columns:
        map_data_local = map_data.copy()
    else:
        # Fallback for old data without Month
        map_data_local = map_data.copy()
        map_data_local['Month'] = 1
    
    # Create YearMonth numeric and label columns
    map_data_local['YearMonthNum'] = map_data_local['Year'] * 100 + map_data_local['Month']
    
    # Get all unique YearMonth values sorted
    all_ym_nums = sorted(map_data_local['YearMonthNum'].unique())
    
    # Create label mapping (e.g., 202303 -> "Mar 2023")
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    def ym_to_label(ym_num):
        year = ym_num // 100
        month = ym_num % 100
        return f"{month_names[month-1]} {year}"
    
    # Create slider with YearMonth range
    min_ym = min(all_ym_nums)
    max_ym = max(all_ym_nums)
    
    # CAS Implementation marker ABOVE slider (March 2023 = 202303)
    cas_ym = 202303
    if min_ym <= cas_ym <= max_ym:
        # Calculate relative position for the marker
        total_range = len(all_ym_nums)
        cas_index = all_ym_nums.index(cas_ym) if cas_ym in all_ym_nums else -1
        if cas_index >= 0:
            position_pct = cas_index / (total_range - 1) * 100
            st.markdown(
                f"""
                <div style="position: relative; width: 100%; height: 35px; margin-bottom: -35px; margin-top: 10px;">
                    <div style="position: absolute; left: calc(4% + {position_pct * 0.94}%); transform: translateX(-50%); text-align: center;">
                        <div style="font-size: 14px; color: #d62728; font-weight: bold; white-space: nowrap;">CAS Implementation</div>
                        <div style="font-size: 16px; color: #d62728; margin-top: -3px;">▼</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    # Range slider
    selected_range = st.select_slider(
        "Select Date Range",
        options=all_ym_nums,
        value=(min_ym, max_ym),
        format_func=ym_to_label
    )
    start_ym_num, end_ym_num = selected_range
    
    st.write("Dot size represents the number of transplants. **Click on an OPO** to see its connections to transplant centers.")
    
    # Filter data by year-month range
    filtered = map_data_local[(map_data_local['YearMonthNum'] >= start_ym_num) & (map_data_local['YearMonthNum'] <= end_ym_num)]
    
    # Aggregate OPO-to-Center connections (for lines and center points)
    conn_agg = filtered.groupby(['OPO', 'Center', 'OPO_Lat', 'OPO_Lon', 'Center_Lat', 'Center_Lon']).agg({
        'Count': 'sum',
        'DCU_Rate': 'mean',
        'OPO_Zip': 'first',
        'Center_Zip': 'first'
    }).reset_index().rename(columns={'Count': 'Transplants'})

    # Aggregate OPO data (for OPO points)
    opo_agg = conn_agg.groupby('OPO').agg({
        'Transplants': 'sum', 
        'DCU_Rate': 'mean', 
        'OPO_Lat': 'first', 
        'OPO_Lon': 'first'
    }).reset_index()
    
    # Aggregate Center data (for center triangle points)
    center_agg = conn_agg.groupby(['OPO', 'Center']).agg({
        'Transplants': 'sum',
        'Center_Lat': 'first',
        'Center_Lon': 'first',
        'Center_Zip': 'first'
    }).reset_index()
    # Rename to avoid scale conflict with OPO Transplants
    center_agg = center_agg.rename(columns={'Transplants': 'Center_Transplants'})

    us_states = alt.topo_feature('https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json', 'states')
    background = alt.Chart(us_states).mark_geoshape(
        fill='lightgray', 
        stroke='white'
    ).project('albersUsa').properties(
        width=900,
        height=500
    )
    
    # Selection for OPO dots visibility (empty='all' -> all visible by default)
    # clear='dblclick' means single-click on empty space won't deselect, double-click will
    select_opo = alt.selection_point(
        fields=['OPO'], 
        on='click', 
        empty='all',
        clear='dblclick',
        name='SelectOPO'
    )
    
    # Selection for lines and centers visibility
    # IMPORTANT: Use value=[{'OPO': '__NONE__'}] instead of empty='none' 
    # because empty='none' doesn't work on Streamlit Cloud
    # The initial value '__NONE__' won't match any real OPO, so lines are hidden by default
    # toggle='true' means clicking same OPO again deselects (but value stays as list, not empty)
    select_lines = alt.selection_point(
        fields=['OPO'], 
        on='click', 
        toggle='true',
        name='SelectLines',
        value=[{'OPO': '__NONE__'}]
    )
    
    # OPO Points Layer
    opo_points = alt.Chart(opo_agg).mark_circle(
        strokeWidth=1.5,
        stroke='white'
    ).encode(
        longitude='OPO_Lon:Q',
        latitude='OPO_Lat:Q',
        size=alt.Size('Transplants:Q', 
                      scale=alt.Scale(type='linear', domain=[0, 1000], range=[100, 2000]),
                      legend=None),
        color=alt.Color('DCU_Rate:Q',
                        scale=alt.Scale(domain=[0, 0.5, 1], range=['#2166ac', '#9970ab', '#b2182b']),
                        legend=alt.Legend(title='DCU-era donor', format='.0%', orient='right', direction='vertical', offset=10, legendY=200)),
        opacity=alt.condition(select_opo, alt.value(1), alt.value(0)),
        tooltip=[
            alt.Tooltip('OPO:N', title='OPO'),
            alt.Tooltip('Transplants:Q', title='Total Transplants'),
            alt.Tooltip('DCU_Rate:Q', title='DCU-era donor', format='.2%')
        ]
    ).add_params(
        select_opo, select_lines
    )
    
    # Connection lines from OPO to Centers - Hidden by default
    # transform_filter with select_lines: filters to matching OPOs
    # Initial value '__NONE__' doesn't match any real OPO, so nothing shows initially
    # When an OPO is clicked, it replaces __NONE__ with the real OPO name
    # When cleared (dblclick), the store becomes empty and filter passes nothing
    lines = alt.Chart(conn_agg).mark_rule(
        color='orange', 
        strokeWidth=2,
        opacity=0.6
    ).encode(
        longitude='OPO_Lon:Q',
        latitude='OPO_Lat:Q',
        longitude2='Center_Lon:Q',
        latitude2='Center_Lat:Q',
        detail='OPO:N'
    ).transform_filter(
        select_lines
    )
    
    # Transplant center points (triangles) - Hidden by default
    center_points = alt.Chart(center_agg).mark_point(
        shape='triangle',
        filled=True,
        color='gold',
        strokeWidth=1,
        stroke='darkorange'
    ).encode(
        longitude='Center_Lon:Q',
        latitude='Center_Lat:Q',
        size=alt.Size('Center_Transplants:Q', 
                      scale=alt.Scale(
                          type='pow',  # Power scale
                          exponent=0.8,
                          domain=[0, 120],
                          range=[10, 700]
                      ), 
                      legend=None),
        detail='OPO:N',
        tooltip=[
            alt.Tooltip('Center:N', title='Transplant Center'),
            alt.Tooltip('Center_Zip:N', title='ZIP Code'),
            alt.Tooltip('Center_Transplants:Q', title='Transplants from OPO'),
            alt.Tooltip('OPO:N', title='OPO')
        ]
    ).transform_filter(
        select_lines
    )
    
    # Combine and RESOLVE SCALE independently
    # This prevents OPO size settings from affecting Center size settings
    map_chart = (background + opo_points + lines + center_points).resolve_scale(size='independent')
    
    st.altair_chart(map_chart, use_container_width=True)
    
    # Summary statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Number of OPOs", len(opo_agg))
    with col2:
        total_transplants = int(opo_agg['Transplants'].sum())
        st.metric("Total Transplants (DBD)", total_transplants)
    with col3:
        avg_dcu = opo_agg['DCU_Rate'].mean()
        st.metric("Donor at OPO with effective DCU", f"{avg_dcu:.1%}")

# --- TAB 2: Survival ---
@st.fragment
def run_survival_tab():
    st.header("Survival Analysis")
    if survival_data.empty:
        st.error("Survival data not found. Run precompute.py first.")
        return

    all_opos = sorted(survival_data[survival_data['Group'] != 'Nationwide']['Group'].unique())
    
    # Initialize session state for selected OPOs
    if 'selected_opos_survival' not in st.session_state:
        st.session_state.selected_opos_survival = []
    
    # --- OPO Selection Map using Plotly ---
    st.subheader("Select OPOs for Survival Analysis")
    st.write("**Click on OPO dots on the map to select/deselect. Green = selected, Blue = unselected.**")
    
    # Get OPO coordinates from map_data (from Tab1)
    if not map_data.empty:
        # Aggregate unique OPO locations from map_data
        opo_locations = map_data.groupby('OPO').agg({
            'OPO_Lat': 'first',
            'OPO_Lon': 'first',
            'Count': 'sum'
        }).reset_index().rename(columns={'Count': 'Transplants'})
        
        # Filter to only OPOs that exist in survival data
        opo_locations = opo_locations[opo_locations['OPO'].isin(all_opos)]
        
        if len(opo_locations) > 0:
            
            # Add selection status and colors
            opo_locations['Selected'] = opo_locations['OPO'].isin(st.session_state.selected_opos_survival)
            opo_locations['Color'] = opo_locations['Selected'].apply(lambda x: '#2ca02c' if x else '#1f77b4')
            opo_locations['Status'] = opo_locations['Selected'].apply(lambda x: 'Selected' if x else 'Click to select')
            
            # Create Plotly figure
            fig = go.Figure()
            
            # Add scatter geo points
            fig.add_trace(go.Scattergeo(
                lon=opo_locations['OPO_Lon'],
                lat=opo_locations['OPO_Lat'],
                text=opo_locations['OPO'],
                customdata=opo_locations[['OPO', 'Transplants', 'Status']].values,
                hovertemplate='<b>%{customdata[0]}</b><br>Transplants: %{customdata[1]}<br>%{customdata[2]}<extra></extra>',
                mode='markers',
                marker=dict(
                    size=opo_locations['Transplants'] / opo_locations['Transplants'].max() * 30 + 8,
                    color=opo_locations['Color'],
                    line=dict(width=1, color='white'),
                    opacity=0.8
                )
            ))
            
            # Configure the map
            fig.update_geos(
                scope='usa',
                showland=True,
                landcolor='lightgray',
                showlakes=True,
                lakecolor='white',
                showcoastlines=True,
                coastlinecolor='white'
            )
            
            fig.update_layout(
                height=400,
                margin=dict(l=0, r=0, t=0, b=0),
                geo=dict(bgcolor='rgba(0,0,0,0)'),
                dragmode=False  # Disable drag/pan
            )
            
            # Display the map with click event handling (zoom/pan disabled)
            config = {'scrollZoom': False, 'displayModeBar': False}
            event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="survival_plotly_map", config=config)
            
            # Handle click events
            if event and 'selection' in event and 'points' in event['selection']:
                points = event['selection']['points']
                if points and len(points) > 0:
                    # Get clicked OPO name from the first point
                    clicked_idx = points[0].get('point_index', None)
                    if clicked_idx is not None:
                        clicked_opo = opo_locations.iloc[clicked_idx]['OPO']
                        # Toggle selection
                        if clicked_opo in st.session_state.selected_opos_survival:
                            st.session_state.selected_opos_survival.remove(clicked_opo)
                        else:
                            st.session_state.selected_opos_survival.append(clicked_opo)
                        st.rerun()
    
    # Display selected OPOs bar
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.session_state.selected_opos_survival:
            st.write("**Selected OPOs:**", ", ".join(sorted(st.session_state.selected_opos_survival)))
        else:
            st.write("**Selected OPOs:** None (click on OPOs on the map to select)")
    with col2:
        if st.button("Clear All", key="clear_opo_selection"):
            st.session_state.selected_opos_survival = []
            st.rerun()
    
    selected = st.session_state.selected_opos_survival
    
    # Show Nationwide checkbox
    show_nationwide = st.checkbox("Show Nationwide Reference", True)
    groups = selected + ["Nationwide"] if show_nationwide else selected
    plot_df = survival_data[survival_data['Group'].isin(groups)].copy()
    
    if plot_df.empty:
        st.warning("No data to display. Please select at least one OPO or enable Nationwide reference.")
        return

    # Build custom color scale: gray for Nationwide, colors for OPOs
    domain = sorted(plot_df['Group'].unique())
    palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    color_range = []
    opo_idx = 0
    for group in domain:
        if group == 'Nationwide':
            color_range.append('gray')
        else:
            color_range.append(palette[opo_idx % len(palette)])
            opo_idx += 1
            
    color_scale = alt.Scale(domain=domain, range=color_range)
    group_color_map = dict(zip(domain, color_range))
    
    # Build p-value text annotations
    stats_annotation = []
    y_pos = 0.05
    for opo in selected:
        opo_stats = survival_stats[survival_stats['OPO'] == opo]
        if not opo_stats.empty:
            p_value = opo_stats['P_Value'].values[0]
            color = group_color_map.get(opo, 'black')
            stats_annotation.append({
                'x': 50,
                'y': y_pos,
                'text': f"{opo}: p={p_value:.4f}",
                'color': color
            })
            y_pos += 0.05
    
    # Base chart
    base = alt.Chart(plot_df).encode(
        x=alt.X('GraftTime:Q', title='Time (Days)', scale=alt.Scale(domain=[0, 1825])),
        color=alt.Color('Group:N', scale=color_scale, legend=alt.Legend(title="Group", symbolType='stroke'))
    )
    
    # Lines with dashed style for Nationwide
    lines = base.mark_line(interpolate='step-after').encode(
        y=alt.Y('survival_prob:Q', title='Survival Probability', scale=alt.Scale(domain=[0, 1])),
        strokeDash=alt.condition(
            alt.datum.Group == 'Nationwide',
            alt.value([5, 5]),  # Dashed for Nationwide
            alt.value([0])      # Solid for others
        ),
        tooltip=[
            alt.Tooltip('Group:N', title='Group'),
            alt.Tooltip('GraftTime:Q', title='Days'),
            alt.Tooltip('survival_prob:Q', title='Survival Probability', format='.3f'),
            alt.Tooltip('ci_lower:Q', title='CI Lower', format='.3f'),
            alt.Tooltip('ci_upper:Q', title='CI Upper', format='.3f')
        ]
    )
    
    # Confidence intervals
    ci = base.mark_area(opacity=0.2, interpolate='step-after').encode(
        y='ci_lower:Q',
        y2='ci_upper:Q'
    )
    
    # Text layer for p-value annotations
    if stats_annotation:
        stats_df = pd.DataFrame(stats_annotation)
        text_layer = alt.Chart(stats_df).mark_text(
            align='left', 
            baseline='bottom', 
            fontSize=12, 
            fontWeight='bold'
        ).encode(
            x=alt.X('x:Q', scale=alt.Scale(domain=[0, 1825])),
            y=alt.Y('y:Q', scale=alt.Scale(domain=[0, 1])),
            text='text:N',
            color=alt.Color('color:N', scale=None)
        )
        chart = ci + lines + text_layer
    else:
        chart = ci + lines
    
    st.altair_chart(chart, use_container_width=True)
    
    # Summary statistics table
    if selected:
        st.subheader("Log-Rank Test Results")
        st.caption("P-values for each OPO compared against the rest of the nation (p < 0.05 highlighted in red)")
        stats = survival_stats[survival_stats['OPO'].isin(selected)].copy()
        stats['Significant'] = stats['P_Value'].apply(lambda x: '✓' if x < 0.05 else '')
        st.dataframe(
            stats.style.map(lambda x: 'color: red; font-weight: bold' if isinstance(x, float) and x < 0.05 else '', subset=['P_Value']),
            use_container_width=True
        )


# --- TAB 3: Utilization ---
@st.fragment
def run_utilization_tab():
    st.header("Donor Transplant Utilization")

    # ---- Load donor utilization dataset ----
    script_dir = os.path.dirname(os.path.abspath(__file__))
    util_file = os.path.join(script_dir, "viz_donor_utilization.csv")

    if not os.path.exists(util_file):
        st.error("Utilization data not found. Run precompute.py first.")
        return

    util_df = pd.read_csv(util_file)
    # ---- Load LUNDON summary (DBD only) ----
    lundon_file = os.path.join(script_dir, "viz_lundon_summary.csv")

    lundon_df = None
    if os.path.exists(lundon_file):
        lundon_df = pd.read_csv(lundon_file)
    # Expect columns: ['DON_OPO', 'Mean_LUNDON']

    

    # Expect columns:
    # ['Year', 'Month', 'DON_OPO', 'CAS_Period',
    #  'Total_Donors', 'Used_Donors', 'Utilization_Rate',
    #  'DCU_Rate', 'DCD']   # DCD: 0 = DBD, 1 = DCD

    # ---- OPO locations from map_data (global, loaded at top of app) ----
    if map_data.empty or not {"OPO_Lat", "OPO_Lon"}.issubset(map_data.columns):
        st.error("OPO location data not available from map_data.")
        return

    opo_locations = (
        map_data.groupby("OPO")
        .agg(
            OPO_Lat=("OPO_Lat", "first"),
            OPO_Lon=("OPO_Lon", "first"),
            Total_Transplants=("Count", "sum")
        )
        .reset_index()
        .rename(columns={"OPO": "DON_OPO"})
    )

    # Merge basic utilization info (overall) to drive map coloring/size

    overall_util = (
        util_df.groupby("DON_OPO")
        .agg(
            Overall_Utilization=("Utilization_Rate", "mean"),
            Overall_DCU=("DCU_Rate", "mean"),
            Overall_Donors=("Total_Donors", "sum")
        )
        .reset_index()
    )


    opo_map_df = opo_locations.merge(
        overall_util, on="DON_OPO", how="left"
    )

    # ---- Session state for selected OPOs ----
    if "selected_opos_util" not in st.session_state:
        st.session_state.selected_opos_util = []

    # ------------------------------------------------------------------
    # 1) Controls row (filters & options)
    # ------------------------------------------------------------------
    col_f1, col_f2, col_f3 = st.columns([1.4, 1.4, 1.2])

    with col_f1:
        cas_filter = st.radio(
            "CAS Period",
            ["All", "Pre-CAS", "Post-CAS"],
            horizontal=True
        )

    with col_f2:
        donor_type_filter = st.radio(
        "Donor Type",
        ["All donors", "Compare DCD vs DBD"],
        horizontal=True
    )

        

    with col_f3:
        show_reference_line = st.checkbox(
            "Show National Reference Line",
            value=True
        )

    st.markdown("---")

    # ------------------------------------------------------------------
    # 2) Plotly OPO selection map (independent of Survival tab)
    # ------------------------------------------------------------------
    st.subheader("Select OPOs on the Map")

    # color by overall utilization (fallback to donors if missing)
    color_column = "Overall_Utilization"
    if opo_map_df[color_column].isna().all():
        color_column = "Overall_Donors"

    # mark selected vs unselected
    opo_map_df["Selected"] = opo_map_df["DON_OPO"].isin(
        st.session_state.selected_opos_util
    )
    opo_map_df["Status"] = opo_map_df["Selected"].apply(
        lambda x: "Selected" if x else "Click to select"
    )
    fig_map = go.Figure()
    fig_map.add_trace(
        go.Scattergeo(
            lon=opo_map_df["OPO_Lon"],
            lat=opo_map_df["OPO_Lat"],
            text=opo_map_df["DON_OPO"],
            customdata=opo_map_df[["DON_OPO", "Overall_DCU", "Overall_Donors", "Status"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "DCU rate: %{customdata[1]:.1%}<br>"
                "Total donors: %{customdata[2]}<br>"
                "%{customdata[3]}<extra></extra>"
            ),
            mode="markers",
            marker=dict(
            size=(
                opo_map_df["Overall_Donors"]
                / max(opo_map_df["Overall_Donors"].max(), 1)
                * 30 + 8
            ),
            color=opo_map_df["Overall_DCU"],
            colorscale=[
                [0.0, "#2166ac"],
                [0.5, "#9970ab"],
                [1.0, "#b2182b"],
            ],
            cmin=0,
            cmax=1,

            # 🔥 VISUAL FEEDBACK
            line=dict(
                width=opo_map_df["Selected"].map(lambda x: 3 if x else 1),
                color=opo_map_df["Selected"].map(lambda x: "yellow" if x else "white"),
            ),
            opacity=opo_map_df["Selected"].map(lambda x: 1.0 if x else 0.6),

            colorbar=dict(title="DCU-era donor"),
            ),
        )
    )


    fig_map.update_geos(
        scope="usa",
        showland=True,
        landcolor="lightgray",
        showlakes=True,
        lakecolor="white",
        showcoastlines=True,
        coastlinecolor="white",
    )

    fig_map.update_layout(
        height=420,
        margin=dict(l=0, r=0, t=0, b=0),
        geo=dict(bgcolor="rgba(0,0,0,0)"),
        dragmode=False,
        title=None,
    )

    config = {"scrollZoom": False, "displayModeBar": False}
    event = st.plotly_chart(
        fig_map,
        use_container_width=True,
        on_select="rerun",
        key="utilization_plotly_map",
        config=config,
    )

    # Handle click events (same logic pattern as Survival tab)
    if event and "selection" in event and "points" in event["selection"]:
        points = event["selection"]["points"]
        if points:
            idx = points[0].get("point_index", None)
            if idx is not None and 0 <= idx < len(opo_map_df):
                clicked_opo = opo_map_df.iloc[idx]["DON_OPO"]
                # toggle
                if clicked_opo in st.session_state.selected_opos_util:
                    st.session_state.selected_opos_util.remove(clicked_opo)
                else:
                    st.session_state.selected_opos_util.append(clicked_opo)
                st.rerun()

    # Selected OPOs summary + clear button
    col_sel1, col_sel2 = st.columns([3, 1])
    with col_sel1:
        if st.session_state.selected_opos_util:
            st.write(
                "**Selected OPOs:** "
                + ", ".join(sorted(st.session_state.selected_opos_util))
            )
        else:
            st.write("**Selected OPOs:** None (click OPOs on the map to select)")

    with col_sel2:
        if st.button("Clear Selection", key="clear_opo_selection_util"):
            st.session_state.selected_opos_util = []
            st.rerun()

    selected_opos = st.session_state.selected_opos_util

    st.markdown("---")

    # ------------------------------------------------------------------
    # 3) Apply CAS & donor-type filters to utilization data
    # ------------------------------------------------------------------
    df = util_df.copy()

    # CAS filter
    if cas_filter != "All":
        df = df[df["CAS_Period"] == cas_filter]

    # "Compare" handled separately later

    # ------------------------------------------------------------------
    # 4) Compute national metrics & insight cards
    # ------------------------------------------------------------------
    # For national utilization, use the currently filtered df
    if len(df) == 0:
        st.warning("No donor records for the chosen filters.")
        return

    # National Utilization = Total Used / Total Donors (not mean of rates)
    national_util = df["Used_Donors"].sum() / df["Total_Donors"].sum() if df["Total_Donors"].sum() > 0 else 0
    
    # DCD/DBD national utilization
    dcd_df = df[df["DCD"] == 1]
    dbd_df = df[df["DCD"] == 0]
    national_dcd_util = dcd_df["Used_Donors"].sum() / dcd_df["Total_Donors"].sum() \
        if len(dcd_df) > 0 and dcd_df["Total_Donors"].sum() > 0 else None
    national_dbd_util = dbd_df["Used_Donors"].sum() / dbd_df["Total_Donors"].sum() \
        if len(dbd_df) > 0 and dbd_df["Total_Donors"].sum() > 0 else None

    if selected_opos:
        selected_df = df[df["DON_OPO"].isin(selected_opos)]
        selected_util = selected_df["Used_Donors"].sum() / selected_df["Total_Donors"].sum() \
            if selected_df["Total_Donors"].sum() > 0 else 0
        delta_util = selected_util - national_util
        selected_donors = int(selected_df["Total_Donors"].sum())
    else:
        selected_util = None
        delta_util = None
        selected_donors = 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            "National Utilization",
            f"{national_util:.1%}",
        )
    with c2:
        if selected_util is not None:
            st.metric(
                "Selected OPOs Utilization",
                f"{selected_util:.1%}",
                f"{delta_util:+.1%} vs national",
            )
        else:
            st.metric("Selected OPOs Utilization", "—")

    with c3:
        st.metric("Donors (Selected OPOs)", f"{selected_donors:,}")

    st.markdown("---")

    # ------------------------------------------------------------------
    # 5) Build utilization bar chart
    # ------------------------------------------------------------------
    st.subheader("Utilization Rates")

    # Helper: list of OPOs to display (always include National)
    if selected_opos:
        opos_for_chart = selected_opos
    else:
        opos_for_chart = []  # just national baseline

    # --- Simple mode: All / DBD / DCD ---
    if donor_type_filter != "Compare DCD vs DBD":
        # Calculate utilization as sum(Used) / sum(Total) per OPO
        opo_util_df = df[df["DON_OPO"].isin(opos_for_chart)].groupby("DON_OPO").agg(
            Used=("Used_Donors", "sum"),
            Total=("Total_Donors", "sum")
        ).reset_index()

        opo_util_df["Utilization"] = opo_util_df["Used"] / opo_util_df["Total"]
        opo_util_df = opo_util_df.rename(columns={"DON_OPO": "OPO"})

    # ---- Base chart dataframe (Utilization) ----
        chart_df = pd.concat(
            [
                pd.DataFrame(
                    {"OPO": ["National"], "Utilization": [national_util]}
                ),
                opo_util_df[["OPO", "Utilization"]],
            ],
            ignore_index=True,
        )   

    # ---- Merge LUNDON (DBD only) ----
        if lundon_df is not None:
            chart_df = chart_df.merge(
                lundon_df.rename(columns={"DON_OPO": "OPO"}),
                on="OPO",
                how="left"
            )
        # --- ADD THIS: Ensure no duplicate OPOs before melting ---
        chart_df = chart_df.groupby("OPO", as_index=False).agg({
            "Utilization": "mean",
            "Mean_LUNDON": "mean"
        })

    # ---- Reshape for grouped bars (Utilization vs LUNDON) ----
        plot_df = chart_df.melt(
            id_vars="OPO",
            value_vars=["Utilization", "Mean_LUNDON"],
            var_name="Metric",
            value_name="Value"
        ).dropna()

        util_df = plot_df[plot_df["Metric"] == "Utilization"]
        lundon_df_plot = plot_df[plot_df["Metric"] == "Mean_LUNDON"]

        lundon_df_plot = (
            lundon_df_plot
            .groupby("OPO", as_index=False)
            .agg(Value=("Value", "mean"))
        )



    
        util_plot_df = util_df
        lundon_plot_df = lundon_df_plot


    

    # --- Compare mode: grouped bars DCD vs DBD ---
    else:
        # Calculate utilization as sum(Used) / sum(Total) per OPO and DCD
        comp_df = df.groupby(["DON_OPO", "DCD"]).agg(
            Used=("Used_Donors", "sum"),
            Total=("Total_Donors", "sum")
        ).reset_index()
        comp_df["Utilization_Rate"] = comp_df["Used"] / comp_df["Total"]

        # National rows (per DCD status)
        nat_rows = []
        for dcd_val in [0, 1]:
            sub = df[df["DCD"] == dcd_val]
            if len(sub) > 0 and sub["Total_Donors"].sum() > 0:
                nat_rows.append(
                    {
                        "DON_OPO": "National",
                        "DCD": dcd_val,
                        "Utilization_Rate": sub["Used_Donors"].sum() / sub["Total_Donors"].sum(),
                    }
                )
        if nat_rows:
            comp_df = pd.concat(
                [pd.DataFrame(nat_rows), comp_df], ignore_index=True
            )

        # Filter to selected OPOs + National
        if opos_for_chart:
            comp_df = comp_df[
                (comp_df["DON_OPO"] == "National")
                | (comp_df["DON_OPO"].isin(opos_for_chart))
            ]
        else:
            comp_df = comp_df[comp_df["DON_OPO"] == "National"]

        comp_df["Donor_Type"] = comp_df["DCD"].map(
            {0: "DBD", 1: "DCD"}
        )

        
        # ---- Add LUNDON as reference (DBD only) ----
        if lundon_df is not None:
            lundon_plot = lundon_df.rename(columns={"DON_OPO": "OPO"})

            lundon_plot = (
                lundon_plot
                .groupby("OPO", as_index=False)
                .agg(Value=("Mean_LUNDON", "mean"))
            )

            # Keep National + selected OPOs
            if opos_for_chart:
                lundon_plot = lundon_plot[
                    (lundon_plot["OPO"] == "National")
                    | (lundon_plot["OPO"].isin(opos_for_chart))
                ]

        util_plot_df = comp_df.copy()
        lundon_plot_df = lundon_plot.copy()


    # ------------------------------------------------------------------
    # 6) Optional: data table for export / inspection
    # ------------------------------------------------------------------
    with st.expander("Show underlying data table (filtered)"):
        table_df = df.copy()
        if opos_for_chart:
            table_df = table_df[table_df["DON_OPO"].isin(opos_for_chart)]
        st.dataframe(
            table_df[
                [
                    "Year",
                    "Month",
                    "DON_OPO",
                    "CAS_Period",
                    "DCD",
                    "Total_Donors",
                    "Used_Donors",
                    "Utilization_Rate",
                    "DCU_Rate",
                ]
            ].rename(columns={"DCD": "DCD(1) vs DBD(0)"}),
            use_container_width=True,
        )
    # ==========================
    # Draw utilization + LUNDON
    # ==========================
    col1, col2 = st.columns(2)

    # ---- LEFT: Utilization ----
    with col1:
        if donor_type_filter == "Compare DCD vs DBD":
            fig_util = px.bar(
                util_plot_df,
                x="DON_OPO",
                y="Utilization_Rate",
                color="Donor_Type",
                barmode="group",
                title="Utilization Rate (DCD vs DBD)",
            )
        else:
          
            rest = [opo for opo in util_plot_df["OPO"].unique() if opo != "National"]
            #

            opo_order = ['National'] + rest

            util_plot_df["OPO"] = pd.Categorical(util_plot_df["OPO"], categories=opo_order, ordered=True)
            fig_util = px.bar(
                util_plot_df,
                x="OPO",
                y="Value",
                title="Utilization Rate",
                text_auto=False,
                category_orders={"OPO": opo_order},
            )
        fig_util.update_traces(text=None, texttemplate="%{y:.1%}", textposition="outside", cliponaxis=False)


        fig_util.update_yaxes(tickformat=".0%", rangemode="tozero")



        st.plotly_chart(fig_util, use_container_width=True)

    # ---- RIGHT: LUNDON ----
    with col2:
        fig_lundon = px.bar(
            lundon_plot_df,
            x="OPO",
            y="Value",
            title="Mean LUNDON Score (DBD only)",
            text=lundon_plot_df["Value"].map(lambda x: f"{x:.1f}"),
        )

        fig_lundon.update_traces(
            marker_color="#2ca02c",
            textposition="outside"
        )

        fig_lundon.update_yaxes(rangemode="tozero")

        fig_lundon.add_annotation(
            text="LUNDON calculated from DBD donors only",
            xref="paper",
            yref="paper",
            x=0,
            y=1.08,
            showarrow=False,
            font=dict(size=11, color="gray"),
        )

        st.plotly_chart(fig_lundon, use_container_width=True)

       


# --- MAIN APP LAYOUT ---
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Map"

# 2. Create a horizontal navigation menu that persists across reruns
# We use a horizontal radio button to simulate tabs. 
# This guarantees that even if the app fully reruns, it remembers where you were.
st.markdown(
    """
    <style>
    /* Optional: CSS to make the radio button look more like a navigation bar */
    div[role="radiogroup"] {
        flex-direction: row;
        width: 100%;
        justify-content: left;
    }
    div[data-testid="stRadio"] > label {
        display: none; /* Hide the label "Navigate to:" */
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# The Radio button automatically syncs with st.session_state.active_tab
selected_tab = st.radio(
    "Navigate to:",
    ["Map", "Survival", "Utilization"],
    horizontal=True,
    key="active_tab" 
)

st.markdown("---")

if selected_tab == "Map":
    run_viz_tab()

if selected_tab == "Survival":
    run_survival_tab()

if selected_tab == "Utilization":
    run_utilization_tab()
