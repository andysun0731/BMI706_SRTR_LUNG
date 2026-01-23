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

    # Initialize session state
    if 'selected_opo_map' not in st.session_state:
        st.session_state.selected_opo_map = None


    # Data preparation
    if 'Month' in map_data.columns:
        map_data_local = map_data.copy()
    else:
        map_data_local = map_data.copy()
        map_data_local['Month'] = 1
    
    map_data_local['YearMonthNum'] = map_data_local['Year'] * 100 + map_data_local['Month']
    all_ym_nums = sorted(map_data_local['YearMonthNum'].unique())
    
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    def ym_to_label(ym_num):
        year = ym_num // 100
        month = ym_num % 100
        return f"{month_names[month-1]} {year}"
    
    min_ym = min(all_ym_nums)
    max_ym = max(all_ym_nums)
    
    # CAS Implementation marker
    cas_ym = 202303
    if min_ym <= cas_ym <= max_ym:
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
    
    # Date range selector
    selected_range = st.select_slider(
        "Select Date Range",
        options=all_ym_nums,
        value=(min_ym, max_ym),
        format_func=ym_to_label
    )
    start_ym_num, end_ym_num = selected_range
    
    # Filter data
    filtered = map_data_local[(map_data_local['YearMonthNum'] >= start_ym_num) & 
                               (map_data_local['YearMonthNum'] <= end_ym_num)]
    
    # Aggregate data
    conn_agg = filtered.groupby(['OPO', 'Center', 'OPO_Lat', 'OPO_Lon', 'Center_Lat', 'Center_Lon']).agg({
        'Count': 'sum',
        'DCU_Rate': 'mean',
        'OPO_Zip': 'first',
        'Center_Zip': 'first'
    }).reset_index().rename(columns={'Count': 'Transplants'})

    opo_agg = conn_agg.groupby('OPO').agg({
        'Transplants': 'sum', 
        'DCU_Rate': 'mean', 
        'OPO_Lat': 'first', 
        'OPO_Lon': 'first'
    }).reset_index()
    
    center_agg = conn_agg.groupby(['OPO', 'Center']).agg({
        'Transplants': 'sum',
        'Center_Lat': 'first',
        'Center_Lon': 'first',
        'Center_Zip': 'first'
    }).reset_index().rename(columns={'Transplants': 'Center_Transplants'})
    
    # Instructions and controls
    col_inst, col_reset = st.columns([5, 1])
    with col_inst:
        if st.session_state.selected_opo_map:
            st.info(f"**Selected OPO:** {st.session_state.selected_opo_map} — Click Clear or click again to deselect, or click another OPO to switch.")
        else:
            st.info("**Click on an OPO** to see its connections to transplant centers.")
    with col_reset:
        if st.button("🔄 Clear", key="reset_map_btn"):
            st.session_state.selected_opo_map = None
            st.rerun(scope="fragment")
    
    # Create placeholder for map
    map_placeholder = st.empty()
    
    # Build the map
    def create_map(opo_data, conn_data, center_data, selected_opo):
        """Create Plotly map with OPO points, connections, and centers"""
        fig = go.Figure()
        
        # Color mapping for DCU_Rate
        def get_dcu_color(dcu_rate):
            if dcu_rate <= 0.5:
                t = dcu_rate / 0.5
                r = int(33 + (153 - 33) * t)
                g = int(102 + (112 - 102) * t)
                b = int(172 + (171 - 172) * t)
            else:
                t = (dcu_rate - 0.5) / 0.5
                r = int(153 + (178 - 153) * t)
                g = int(112 + (24 - 112) * t)
                b = int(171 + (43 - 171) * t)
            return f'rgb({r},{g},{b})'
        
        # Prepare OPO display data
        opo_display = opo_data.copy()
        opo_display['Size'] = opo_display['Transplants'].apply(
            lambda x: max(10, min(50, 10 + (x / 1000) * 40))
        )
        opo_display['Color'] = opo_display['DCU_Rate'].apply(get_dcu_color)
        
        # Set opacity: dim non-selected OPOs if one is selected
        if selected_opo:
            opo_display['Opacity'] = opo_display['OPO'].apply(
                lambda x: 0.9 if x == selected_opo else 0.3
            )
        else:
            opo_display['Opacity'] = 0.9
        
        # TRACE 0: OPO markers
        fig.add_trace(go.Scattergeo(
            lon=opo_display['OPO_Lon'],
            lat=opo_display['OPO_Lat'],
            text=opo_display['OPO'],
            customdata=opo_display[['OPO', 'Transplants', 'DCU_Rate']].values,
            hovertemplate='<b>%{customdata[0]}</b><br>Total Transplants: %{customdata[1]}<br>DCU-era donor: %{customdata[2]:.2%}<extra></extra>',
            mode='markers',
            marker=dict(
                size=opo_display['Size'],
                color=opo_display['Color'],
                line=dict(width=1.5, color='white'),
                opacity=opo_display['Opacity'].tolist()
            ),
            showlegend=False
        ))
        
        # TRACE 1: Connection lines (Always calculate, but empty if no selection)
        lons = []
        lats = []
        
        if selected_opo:
            selected_conn = conn_data[conn_data['OPO'] == selected_opo]
            
            # Helper function to adjust Hawaii coordinates for Albers USA projection
            def adjust_coords_for_projection(lat, lon):
                if lat >= 19 and lat <= 23 and lon >= -161 and lon <= -154:
                    return 27.27, -107.45
                return lat, lon
            
            for _, row in selected_conn.iterrows():
                opo_lat, opo_lon = adjust_coords_for_projection(row['OPO_Lat'], row['OPO_Lon'])
                center_lat, center_lon = adjust_coords_for_projection(row['Center_Lat'], row['Center_Lon'])
                lons.extend([opo_lon, center_lon, None])
                lats.extend([opo_lat, center_lat, None])
                
        fig.add_trace(go.Scattergeo(
            lon=lons,
            lat=lats,
            mode='lines',
            line=dict(width=2, color='orange'),
            opacity=0.6,
            showlegend=False,
            hoverinfo='skip'
        ))
            
        # TRACE 2: Transplant centers (Always calculate, but empty if no selection)
        center_lons = []
        center_lats = []
        center_texts = []
        center_customdata = []
        center_sizes = []
        
        if selected_opo:
            selected_centers = center_data[center_data['OPO'] == selected_opo].copy()
            if not selected_centers.empty:
                selected_centers['Size'] = selected_centers['Center_Transplants'].apply(
                    lambda x: max(8, min(35, 8 + (x / 120) ** 0.8 * 27))
                )
                center_lons = selected_centers['Center_Lon']
                center_lats = selected_centers['Center_Lat']
                center_texts = selected_centers['Center']
                center_customdata = selected_centers[['Center', 'Center_Zip', 'Center_Transplants', 'OPO']].values
                center_sizes = selected_centers['Size']

        fig.add_trace(go.Scattergeo(
            lon=center_lons,
            lat=center_lats,
            text=center_texts,
            customdata=center_customdata,
            hovertemplate='<b>%{customdata[0]}</b><br>ZIP: %{customdata[1]}<br>Transplants from OPO: %{customdata[2]}<br>OPO: %{customdata[3]}<extra></extra>' if len(center_lons) > 0 else '',
            mode='markers',
            marker=dict(
                symbol='triangle-up',
                size=center_sizes,
                color='gold',
                line=dict(width=1, color='darkorange')
            ),
            showlegend=False,
            hoverinfo='text' if len(center_lons) > 0 else 'skip',
            selected=dict(marker=dict(opacity=1)),
            unselected=dict(marker=dict(opacity=1))
        ))
        
        # TRACE 3: Colorbar (Always present)
        fig.add_trace(go.Scattergeo(
            lon=[None], lat=[None],
            mode='markers',
            marker=dict(
                colorscale=[[0, '#2166ac'], [0.5, '#9970ab'], [1, '#b2182b']],
                cmin=0, cmax=1,
                colorbar=dict(
                    title="DCU Available Time",
                    tickformat='.0%',
                    tick0=0,
                    dtick=0.2,
                    x=1.02,
                    y=0.5,
                    len=0.5
                ),
                showscale=True
            ),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Configure map layout
        fig.update_geos(
            scope='usa',
            showland=True, landcolor='lightgray',
            showlakes=True, lakecolor='white',
            showcountries=False,
            showcoastlines=True, coastlinecolor='white',
            projection_type='albers usa'
        )
        
        fig.update_layout(
            height=500,
            margin=dict(l=0, r=0, t=0, b=0),
            geo=dict(bgcolor='rgba(0,0,0,0)'),
            dragmode=False,
            hovermode='closest',
            uirevision='constant' # Vital for smooth updates
        )
        
        return fig
    
    # Create and display the map
    map_fig = create_map(opo_agg, conn_agg, center_agg, st.session_state.selected_opo_map)
    
    config = {
        'displayModeBar': False,
        'scrollZoom': False,
        'doubleClick': False,
        'staticPlot': False,
        'editable': False
    }
    
    # Remove st.empty placeholder usage, just render directly
    event = st.plotly_chart(map_fig, use_container_width=True, on_select="rerun", key="opo_map_interactive", config=config)
    
    # Handle click events - only process clicks on OPO markers (trace 0)
    if event and 'selection' in event and 'points' in event['selection']:
        points = event['selection']['points']
        if points and len(points) > 0:
            # Get trace index and point index
            trace_idx = points[0].get('curve_number', None)
            clicked_idx = points[0].get('point_index', None)
            
            # If clicked on OPO markers (trace 0)
            if trace_idx == 0 and clicked_idx is not None and clicked_idx < len(opo_agg):
                clicked_opo = opo_agg.iloc[clicked_idx]['OPO']
                
                # Toggle: if clicking the same OPO, deselect it; otherwise select the new one
                if st.session_state.selected_opo_map == clicked_opo:
                    st.session_state.selected_opo_map = None
                else:
                    st.session_state.selected_opo_map = clicked_opo
                
                st.rerun(scope="fragment")
            
            # If clicked on transplant center (trace 2), check if it overlaps with an OPO
            elif trace_idx == 2 and st.session_state.selected_opo_map:
                # Get the clicked point's coordinates
                clicked_point = points[0]
                clicked_lon = clicked_point.get('lon', None)
                clicked_lat = clicked_point.get('lat', None)
                
                if clicked_lon is not None and clicked_lat is not None:
                    # Check if this location matches any OPO location (with small tolerance)
                    tolerance = 0.5  # degrees of lat/lon
                    for idx, opo_row in opo_agg.iterrows():
                        opo_lon = opo_row['OPO_Lon']
                        opo_lat = opo_row['OPO_Lat']
                        
                        # Check if within tolerance (overlapping)
                        if abs(clicked_lon - opo_lon) < tolerance and abs(clicked_lat - opo_lat) < tolerance:
                            # Found overlapping OPO, toggle it
                            clicked_opo = opo_row['OPO']
                            if st.session_state.selected_opo_map == clicked_opo:
                                st.session_state.selected_opo_map = None
                            else:
                                st.session_state.selected_opo_map = clicked_opo
                            st.rerun(scope="fragment")
                            break
                    # If no OPO found nearby, do nothing (triangle click ignored)
    
    # Summary statistics
    st.markdown("---")
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
    
    if 'selected_opos_survival' not in st.session_state:
        st.session_state.selected_opos_survival = []
        
    st.subheader("Select OPOs for Survival Analysis")
    st.write("**Click on OPO dots on the map to select/deselect. Green = selected, Blue = unselected.**")
    
    if not map_data.empty:
        opo_locations = map_data.groupby('OPO').agg({
            'OPO_Lat': 'first',
            'OPO_Lon': 'first',
            'Count': 'sum',
            'DCU_Rate': 'mean'
        }).reset_index().rename(columns={'Count': 'Transplants'})
        
        opo_locations = opo_locations[opo_locations['OPO'].isin(all_opos)]
        
        if len(opo_locations) > 0:
            
            # Add selection status
            opo_locations['Selected'] = opo_locations['OPO'].isin(st.session_state.selected_opos_survival)
            opo_locations['Status'] = opo_locations['Selected'].apply(lambda x: 'Selected' if x else 'Click to select')
            
            # Create Plotly figure
            fig = go.Figure()
            
            # Add scatter geo points
            fig.add_trace(go.Scattergeo(
                lon=opo_locations['OPO_Lon'],
                lat=opo_locations['OPO_Lat'],
                text=opo_locations['OPO'],
                customdata=opo_locations[['OPO', 'Transplants', 'DCU_Rate', 'Status']].values,
                hovertemplate='<b>%{customdata[0]}</b><br>Transplants: %{customdata[1]}<br>DCU Available Time: %{customdata[2]:.1%}<br>%{customdata[3]}<extra></extra>',
                mode='markers',
                marker=dict(
                    size=opo_locations['Transplants'] / opo_locations['Transplants'].max() * 30 + 8,
                    color=opo_locations['DCU_Rate'].fillna(0),
                    colorscale=[[0, '#2166ac'], [0.5, '#9970ab'], [1, '#b2182b']],
                    cmin=0,
                    cmax=1,
                    colorbar=dict(title="DCU Available Time", tickformat=".0%", tick0=0, dtick=0.2),
                    line=dict(
                        width=opo_locations['Selected'].map(lambda x: 3 if x else 1),
                        color=opo_locations['Selected'].map(lambda x: 'yellow' if x else 'white'),
                    ),
                    opacity=opo_locations['Selected'].map(lambda x: 1.0 if x else 0.8),
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
        stats = stats.rename(columns={"P_Value": "P-value"})

        surv_lookup = survival_data[survival_data['Group'].isin(selected + ['Nationwide'])].copy()
        surv_lookup = surv_lookup[surv_lookup['GraftTime'] <= 1825]
        surv_5yr = (
            surv_lookup.sort_values('GraftTime')
            .groupby('Group', as_index=False)
            .tail(1)
            .set_index('Group')
        )
        stats['5-year Graft Survival (95% CI)'] = stats['OPO'].map(
            lambda opo: (
                f"{surv_5yr.loc[opo, 'survival_prob']:.1%} "
                f"({surv_5yr.loc[opo, 'ci_lower']:.1%}–{surv_5yr.loc[opo, 'ci_upper']:.1%})"
                if opo in surv_5yr.index else "—"
            )
        )
        national_5yr = "—"
        if "Nationwide" in surv_5yr.index:
            national_5yr = (
                f"{surv_5yr.loc['Nationwide', 'survival_prob']:.1%} "
                f"({surv_5yr.loc['Nationwide', 'ci_lower']:.1%}–{surv_5yr.loc['Nationwide', 'ci_upper']:.1%})"
            )
        stats = pd.concat(
            [
                pd.DataFrame([{"OPO": "Nationwide", "P-value": pd.NA, "5-year Graft Survival (95% CI)": national_5yr}]),
                stats,
            ],
            ignore_index=True,
        )
        stats['Significant'] = stats['P-value'].apply(lambda x: '✓' if x < 0.05 else '')
        st.dataframe(
            stats.style.map(lambda x: 'color: red; font-weight: bold' if isinstance(x, float) and x < 0.05 else '', subset=['P-value']),
            use_container_width=True
        )


# --- TAB 3: Utilization ---
@st.fragment
def run_utilization_tab():
    st.header("Donor Lung Utilization")

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
        #st.write("LUNDON file:", lundon_file)
        #st.write("Mean_LUNDON max:", float(lundon_df["Mean_LUNDON"].max()))
        #st.write(lundon_df.head(5))

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

    # ---- Session state for selected OPOs ----
    if "selected_opos_util" not in st.session_state:
        st.session_state.selected_opos_util = []

    # ------------------------------------------------------------------
    # 1) Controls row (filters & options)
    # ------------------------------------------------------------------
    col_f1, col_f2 = st.columns([1.4, 1.6])

    with col_f1:
        cas_filter = st.radio(
            "CAS Period",
            ["All", "Pre-CAS", "Post-CAS"],
            horizontal=True
        )
    with col_f2:
        pass

    # Merge basic utilization info (overall) to drive map coloring/size
    map_util_df = util_df.copy()
    if cas_filter != "All":
        map_util_df = map_util_df[map_util_df["CAS_Period"] == cas_filter]

    overall_util = (
        map_util_df.groupby("DON_OPO")
        .agg(
            Overall_Utilization=("Utilization_Rate", "mean"),
            Overall_DCU=("DCU_Rate", "mean"),
            Overall_Donors=("Total_Donors", "sum")
        )
        .reset_index()
    )

    all_overall_util = (
        util_df.groupby("DON_OPO")
        .agg(Overall_Donors=("Total_Donors", "sum"))
        .reset_index()
    )
    all_donor_max = max(all_overall_util["Overall_Donors"].max(), 1)

    opo_map_df = opo_locations.merge(
        overall_util, on="DON_OPO", how="left"
    )
    opo_map_df["Overall_Donors"] = opo_map_df["Overall_Donors"].fillna(0)
    opo_map_df["Overall_DCU"] = opo_map_df["Overall_DCU"].fillna(0)

        



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
    size_scale = 30
    if cas_filter != "All":
        size_scale = 45

    fig_map.add_trace(
        go.Scattergeo(
            lon=opo_map_df["OPO_Lon"],
            lat=opo_map_df["OPO_Lat"],
            text=opo_map_df["DON_OPO"],
            customdata=opo_map_df[["DON_OPO", "Overall_DCU", "Overall_Donors", "Status"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "DCU Available Time: %{customdata[1]:.1%}<br>"
                "Total donors: %{customdata[2]}<br>"
                "%{customdata[3]}<extra></extra>"
            ),
            mode="markers",
            marker=dict(
            size=(
                opo_map_df["Overall_Donors"]
                / all_donor_max
                * size_scale + 8
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

            colorbar=dict(
                title="DCU Available Time",
                tickformat=".0%",
                tick0=0,
                dtick=0.2
            ),
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

    # ------------------------------------------------------------------
    # 5) Build utilization bar chart
    # ------------------------------------------------------------------
    st.subheader("Utilization Rates")

    # Helper: list of OPOs to display (always include National)
    if selected_opos:
        opos_for_chart = selected_opos
    else:
        opos_for_chart = []  # just national baseline
    # ------------------------------------------------------------------
    # Build utilization dataframe (always DCD vs DBD)
    # ------------------------------------------------------------------
    comp_df = df.groupby(["DON_OPO", "DCD"]).agg(
        Used=("Used_Donors", "sum"),
        Total=("Total_Donors", "sum")
    ).reset_index()

    comp_df["Utilization_Rate"] = comp_df["Used"] / comp_df["Total"]
    comp_df["Donor_Type"] = comp_df["DCD"].map({0: "DBD", 1: "DCD"})

    # National rows (per DCD status)
    nat_rows = []
    for dcd_val in [0, 1]:
        sub = df[df["DCD"] == dcd_val]
        if len(sub) > 0 and sub["Total_Donors"].sum() > 0:
            nat_rows.append({
                "DON_OPO": "National",
                "DCD": dcd_val,
                "Utilization_Rate": sub["Used_Donors"].sum() / sub["Total_Donors"].sum(),
                "Donor_Type": "DCD" if dcd_val == 1 else "DBD",
            })

    util_plot_df = pd.concat([pd.DataFrame(nat_rows), comp_df], ignore_index=True) if nat_rows else comp_df.copy()

    # Filter to selected OPOs plus National
    if selected_opos:
        util_plot_df = util_plot_df[
            (util_plot_df["DON_OPO"] == "National")
            | (util_plot_df["DON_OPO"].isin(selected_opos))
        ]
    else:
        util_plot_df = util_plot_df[util_plot_df["DON_OPO"] == "National"]

    # ==========================
    # Draw utilization + LUNDON
    # ==========================
    col1, col2 = st.columns(2)

    # ---- LEFT: Utilization (DCD vs DBD only) ----
    with col1:
        rest = [o for o in util_plot_df["DON_OPO"].unique() if o != "National"]
        opo_order = ["National"] + sorted(rest)

        fig_util = px.bar(
            util_plot_df,
            x="DON_OPO",
            y="Utilization_Rate",
            color="Donor_Type",
            barmode="group",
            title="Utilization Rate (DCD vs DBD)",
            category_orders={"DON_OPO": opo_order},
        )
        fig_util.update_layout(legend_title_text="Donor Type")
        fig_util.update_yaxes(title="Utilization Rate", tickformat=".0%", rangemode="tozero")
        fig_util.update_xaxes(title="OPO")
        st.plotly_chart(fig_util, use_container_width=True)

    # ---- RIGHT: LUNDON (Overall vs Transplanted) ----
    with col2:
        if lundon_df is None or lundon_df.empty:
            st.info("LUNDON summary not available.")
        else:
            ldf = lundon_df.copy()

            if cas_filter != "All" and "CAS_Period" in ldf.columns:
                ldf = ldf[ldf["CAS_Period"] == cas_filter]

            if selected_opos:
                ldf = ldf[
                    (ldf["DON_OPO"] == "National")
                    | (ldf["DON_OPO"].isin(selected_opos))
                ]
            else:
                ldf = ldf[ldf["DON_OPO"] == "National"]

            ldf = ldf.rename(columns={"DON_OPO": "OPO"})


            ldf = (
                ldf
                .groupby(["OPO", "LUNDON_Group"], as_index=False)
                .agg(Mean_LUNDON=("Mean_LUNDON", "mean"))
            )

            ldf["Value"] = ldf["Mean_LUNDON"]
                    # TEMP DEBUG: inspect LUNDON values being plotted
            #st.dataframe(
            #    ldf[["OPO", "LUNDON_Group", "Mean_LUNDON"]]
            #    .sort_values(["OPO", "LUNDON_Group"]),
            #    use_container_width=True
            #)


            rest = [o for o in ldf["OPO"].unique() if o != "National"]
            opo_order = ["National"] + sorted(rest)

            fig_lundon = px.bar(
                ldf,
                x="OPO",
                y="Value",
                color="LUNDON_Group",
                barmode="group",
                title="Mean LUNDON Score (DBD only)",
                category_orders={"OPO": opo_order},
            )
            fig_lundon.update_layout(legend_title_text="")
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
