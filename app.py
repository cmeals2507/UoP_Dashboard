import streamlit as st
import pandas as pd
import altair as alt

# ——— Page config ———
st.set_page_config(
    page_title="University of the Pacific Conservatory of Music Programming Database",
    layout="wide"
)

# ——— Custom CSS for Tighter Layout ———
st.markdown("""
    <style>
    /* Reduce header margins and font sizes */
    h1 { font-size: 2rem; margin-bottom: 0.25rem; }
    h2 { font-size: 1.5rem; margin-top: 0.5rem; margin-bottom: 0.25rem; }
    h3 { font-size: 1rem; margin-top: 0.25rem; margin-bottom: 0.25rem; }

    /* Tighter metric spacing */
    div[data-testid="metric-container"] {
        padding: 0.25rem 0.5rem;
    }
    div[data-testid="metric-container"] > div {
        gap: 0.25rem;
    }
    /* Narrow Composer Demographics Distribution column */
    .element-container:nth-of-type(5) .stMarkdown h3 {
        font-size: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# ——— Frozen Top Banner ———
st.markdown(
    "<h1 style='text-align:left;'>University of the Pacific Conservatory of Music<br>Programming Database</h1>",
    unsafe_allow_html=True
)
st.markdown("---")

@st.cache_data
def load_data():
    df = pd.read_excel("LongForm.xlsx", sheet_name="LongForm")
    # Drop unwanted columns if present
    for col in ["Year", "Composer dates"]:
        if col in df.columns:
            df = df.drop(columns=[col])
    # Normalize column names: strip and lowercase
    df.columns = df.columns.str.strip().str.lower()
    return df

df = load_data()


# ——— Detect actual column names ———
cols = df.columns.tolist()

def detect_column(keywords):
    for col in cols:
        if all(k in col for k in keywords):
            return col
    return None

col_semester = detect_column(['semester'])

# Detect Academic Year column
col_academic_year = detect_column(['academic', 'year'])

col_concert = detect_column(['concert'])
col_index = detect_column(['index'])
col_performer = detect_column(['performer'])           # name of the musician
col_perf_type = detect_column(['performance type'])    # type of performance
# Performer Cohort (from Performer Type column)
col_kind = detect_column(['performer type'])
col_instrument = detect_column(['instrument'])
# Composer name, excluding category/status/gen
col_composer_name = next(
    (c for c in cols if 'composer' in c and all(x not in c for x in ['category','status','gen'])),
    None
)
col_piece = detect_column(['piece'])
col_date_time = detect_column(['date'])
col_date = None
if col_date_time:
    # Format date as e.g. Jan. 1, 2025, leave blank if missing
    df['date_clean'] = pd.to_datetime(df[col_date_time], errors='coerce').apply(
        lambda dt: dt.strftime('%b. ') + str(dt.day) + ', ' + dt.strftime('%Y') if pd.notna(dt) else ""
    )
    col_date = 'date_clean'

# Detect composer demographics columns
col_comp_gen = detect_column(['composer category'])
col_comp_status = detect_column(['composer status'])

    # Sidebar filters
# ——— Sidebar Logo ———
st.sidebar.image("UoP_Logo.svg", use_container_width=True)

filters = {}
if col_academic_year:
    opts = sorted(df[col_academic_year].dropna().unique())
    filters['Academic Year'] = st.sidebar.multiselect("Academic Year", opts, default=opts)
else:
    st.sidebar.warning("Column not found: 'Academic Year'")

if col_semester:
    opts = sorted(df[col_semester].dropna().unique())
    filters['Semester'] = st.sidebar.multiselect("Semester", opts, default=opts)
else:
    st.sidebar.warning("Column not found: 'Semester'")

if col_perf_type:
    opts = sorted(df[col_perf_type].dropna().unique())
    filters['Performance Type'] = st.sidebar.multiselect("Performance Type", opts, default=opts)
else:
    st.sidebar.warning("Column not found: 'Performance Type'")




# Composer autocomplete dropdown
composer_opts = sorted(df[col_composer_name].dropna().unique()) if col_composer_name else []
composer_opts = ["All"] + composer_opts
composer_select = st.sidebar.selectbox("Composer", composer_opts)

# Performer autocomplete dropdown
performer_opts = sorted(df[col_performer].dropna().unique()) if col_performer else []
performer_opts = ["All"] + performer_opts
performer_select = st.sidebar.selectbox("Performer", performer_opts)


# Apply filters: Academic Year OR Semester, AND Performance Type
# Academic Year mask
if col_academic_year:
    ay_selected = filters.get('Academic Year', [])
    mask_ay = df[col_academic_year].isin(ay_selected)
else:
    mask_ay = pd.Series(True, index=df.index)

# Semester mask
if col_semester:
    sem_selected = filters.get('Semester', [])
    mask_sem = df[col_semester].isin(sem_selected)
else:
    mask_sem = pd.Series(True, index=df.index)

# Combine AY and Semester with OR
mask_as = mask_ay | mask_sem

# Performance Type mask (empty selection → no filter)
if col_perf_type:
    pt_selected = filters.get('Performance Type', [])
    if pt_selected:
        mask_pt = df[col_perf_type].isin(pt_selected)
    else:
        mask_pt = pd.Series(True, index=df.index)
else:
    mask_pt = pd.Series(True, index=df.index)

# Apply combined mask
filtered = df[mask_as & mask_pt]

# Apply composer dropdown filter
if composer_select != "All" and col_composer_name:
    filtered = filtered[filtered[col_composer_name] == composer_select]

# Apply performer dropdown filter
if performer_select != "All" and col_performer:
    filtered = filtered[filtered[col_performer] == performer_select]

# ——— Sort by Academic Year, Semester (Fall, Spring), then Index ———
if col_academic_year and col_semester and col_index:
    filtered = filtered.copy()
    # Convert Semester to ordered categorical for custom sort order
    filtered[col_semester] = pd.Categorical(
        filtered[col_semester],
        categories=['Fall', 'Spring'],
        ordered=True
    )
    # Convert Index to numeric for correct ordering
    try:
        filtered[col_index] = pd.to_numeric(filtered[col_index])
    except:
        pass
    # Sort by Academic Year, Semester, then Index
    filtered = filtered.sort_values(
        by=[col_academic_year, col_semester, col_index]
    )
# Fallback: original date, concert, index sorting
elif col_date and col_concert and col_index:
    filtered = filtered.copy()
    try:
        filtered[col_concert] = pd.to_numeric(filtered[col_concert])
        filtered[col_index] = pd.to_numeric(filtered[col_index])
    except:
        pass
    filtered = filtered.sort_values(
        by=[col_date, col_concert, col_index]
    )
elif col_date:
    filtered = filtered.sort_values(by=[col_date])

# ——— Composer Demographics Gauges ———
total = len(filtered)

# Series for category and status
comp_cat_series = filtered[col_comp_gen].dropna().astype(int) if col_comp_gen else pd.Series(dtype=int)
comp_status_series = filtered[col_comp_status].dropna().astype(int) if col_comp_status else pd.Series(dtype=int)

# Gender: Male codes 1 & 3, Female codes 2 & 4
male = comp_cat_series.isin([1,3]).sum()
female = comp_cat_series.isin([2,4]).sum()
nb = total - male - female
gender_counts = {'Male': male, 'Female': female, 'NB': nb}

# Ethnicity: White codes 1 & 2, BBIA codes 3 & 4
white = comp_cat_series.isin([1,2]).sum()
bbia = comp_cat_series.isin([3,4]).sum()
eth_counts = {'White': white, 'BBIA': bbia}

# Demographic groups
dem_counts = {
    'White Men': (comp_cat_series==1).sum(),
    'White Women': (comp_cat_series==2).sum(),
    'BBIA Men': (comp_cat_series==3).sum(),
    'BBIA Women': (comp_cat_series==4).sum()
}

# Vital status
living = (comp_status_series==1).sum()
deceased = (comp_status_series==2).sum()
stat_counts = {'Living': living, 'Deceased': deceased}

# ——— Composer Demographics Distribution Section ———
dem_section_cols = st.columns([1, 1])
with dem_section_cols[0]:
    st.subheader("Composer Demographics Distribution")
    st.caption("Metrics reflect the currently filtered results.")

    # Gender gauges
    g1, g2, g3 = st.columns(3)
    g1.metric("Male", f"{gender_counts['Male']/total:.0%}" if total else "N/A")
    g2.metric("Female", f"{gender_counts['Female']/total:.0%}" if total else "N/A")
    g3.metric("NB", f"{gender_counts['NB']/total:.0%}" if total else "N/A")

    # Ethnicity gauges
    e1, e2 = st.columns(2)
    e1.metric("White", f"{eth_counts['White']/total:.0%}" if total else "N/A")
    e2.metric("BBIA", f"{eth_counts['BBIA']/total:.0%}" if total else "N/A")

    # Demographic group gauges
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("White Men", f"{dem_counts['White Men']/total:.0%}" if total else "N/A")
    d2.metric("White Women", f"{dem_counts['White Women']/total:.0%}" if total else "N/A")
    d3.metric("BBIA Men", f"{dem_counts['BBIA Men']/total:.0%}" if total else "N/A")
    d4.metric("BBIA Women", f"{dem_counts['BBIA Women']/total:.0%}" if total else "N/A")

    # Vital status gauges
    s1, s2 = st.columns(2)
    s1.metric("Living", f"{stat_counts['Living']/total:.0%}" if total else "N/A")
    s2.metric("Deceased", f"{stat_counts['Deceased']/total:.0%}" if total else "N/A")

with dem_section_cols[1]:
    # Prepare and render the stacked Demographic Groups chart (narrow, left-justified)
    st.subheader("Demographic Groups (by Vital Status)")
    st.caption("Chart reflects the currently filtered results.")

    records = []
    group_map = {'White Men': 1, 'White Women': 2, 'BBIA Men': 3, 'BBIA Women': 4}
    for grp, code in group_map.items():
        for status, status_code in [('Living', 1), ('Deceased', 2)]:
            gen_series = pd.to_numeric(filtered[col_comp_gen], errors='coerce').fillna(0).astype(int)
            stat_series = pd.to_numeric(filtered[col_comp_status], errors='coerce').fillna(0).astype(int)
            count = ((gen_series == code) & (stat_series == status_code)).sum()
            records.append({'Group': grp, 'Status': status, 'Count': count})
    dem_status_df = pd.DataFrame(records)
    dem_status_df['GroupStatus'] = dem_status_df['Group'] + "_" + dem_status_df['Status']

    chart_narrow = alt.Chart(dem_status_df).mark_bar().encode(
        y=alt.Y("Group:N", sort=list(group_map.keys()), title=None),
        x=alt.X("Count:Q", title="Count"),
        color=alt.Color(
            "GroupStatus:N",
            scale=alt.Scale(
                domain=[
                    "White Men_Living", "White Men_Deceased",
                    "White Women_Living", "White Women_Deceased",
                    "BBIA Men_Living",   "BBIA Men_Deceased",
                    "BBIA Women_Living", "BBIA Women_Deceased"
                ],
                range=[
                    "#ADD8E6", "#00008B",
                    "#B0C4DE", "#4682B4",
                    "#D8BFD8", "#800080",
                    "#E6E6FA", "#EE82EE"
                ]
            ),
            legend=None
        )
    ).properties(height=200)
    st.altair_chart(chart_narrow, use_container_width=True)

# ——— Inline Distribution Charts ———
st.caption("Distribution charts reflect the currently filtered data.")
cols_dist = st.columns(2)
with cols_dist[0]:
    st.subheader("Gender Distribution")
    gender_df = pd.DataFrame(list(gender_counts.items()), columns=["Gender","Count"])
    chart_gender = alt.Chart(gender_df).mark_bar().encode(
        x=alt.X("Count:Q", title="Count"),
        y=alt.Y("Gender:N", sort=list(gender_df["Gender"]), title=None),
        color=alt.Color("Gender:N", legend=None)
    ).properties(height=150)
    st.altair_chart(chart_gender, use_container_width=True)
with cols_dist[1]:
    st.subheader("Ethnicity Distribution")
    eth_df = pd.DataFrame(list(eth_counts.items()), columns=["Ethnicity","Count"])
    chart_eth = alt.Chart(eth_df).mark_bar().encode(
        x=alt.X("Count:Q", title="Count"),
        y=alt.Y("Ethnicity:N", sort=list(eth_df["Ethnicity"]), title=None),
        color=alt.Color("Ethnicity:N", legend=None)
    ).properties(height=150)
    st.altair_chart(chart_eth, use_container_width=True)

# ——— Toggle Main Distribution View ———
view_option = st.selectbox(
    "Select distribution view",
    ["Demographic Groups", "Vital Status"]
)
if view_option == "Demographic Groups":
    cols_dem = st.columns([1, 1])
    with cols_dem[0]:
        st.subheader("Demographic Groups Distribution (stacked by Vital Status)")

        # Prepare a DataFrame with counts of Living vs Deceased for each demographic group
        records = []
        group_map = {'White Men': 1, 'White Women': 2, 'BBIA Men': 3, 'BBIA Women': 4}
        for grp, code in group_map.items():
            for status, status_code in [('Living', 1), ('Deceased', 2)]:
                gen_series = pd.to_numeric(filtered[col_comp_gen], errors='coerce').fillna(0).astype(int)
                stat_series = pd.to_numeric(filtered[col_comp_status], errors='coerce').fillna(0).astype(int)
                count = ((gen_series == code) & (stat_series == status_code)).sum()
                records.append({'Group': grp, 'Status': status, 'Count': count})
        dem_status_df = pd.DataFrame(records)
        dem_status_df['GroupStatus'] = dem_status_df['Group'] + "_" + dem_status_df['Status']

        chart_dem = alt.Chart(dem_status_df).mark_bar().encode(
            y=alt.Y("Group:N", sort=list(group_map.keys()), title=None),
            x=alt.X("Count:Q", title="Count"),
            color=alt.Color(
                "GroupStatus:N",
                scale=alt.Scale(
                    domain=[
                        "White Men_Living", "White Men_Deceased",
                        "White Women_Living", "White Women_Deceased",
                        "BBIA Men_Living",   "BBIA Men_Deceased",
                        "BBIA Women_Living", "BBIA Women_Deceased"
                    ],
                    range=[
                        "#ADD8E6", "#00008B",  # White Men: lightblue/darkblue
                        "#B0C4DE", "#4682B4",  # White Women: lightsteelblue/steelblue
                        "#D8BFD8", "#800080",  # BBIA Men: thistle/purple
                        "#E6E6FA", "#EE82EE"   # BBIA Women: lavender/violet
                    ]
                ),
                legend=alt.Legend(title="Group & Status")
            )
        ).properties(height=200)

        st.altair_chart(chart_dem, use_container_width=True)
    # cols_dem[1] remains empty, keeping the chart narrow & left-aligned
else:
    st.subheader("Vital Status Distribution")
    stat_df = pd.DataFrame(list(stat_counts.items()), columns=["Status","Count"])
    chart_stat = alt.Chart(stat_df).mark_bar().encode(
        x=alt.X("Count:Q", title="Count"),
        y=alt.Y("Status:N", sort=list(stat_df["Status"]), title=None),
        color=alt.Color("Status:N", legend=None)
    ).properties(height=200)
    st.altair_chart(chart_stat, use_container_width=True)

# ——— Main UI ———
st.header("Music Performance Dashboard")

# Summary metrics
col1, col2, col3 = st.columns(3)
col1.metric("Total Performances", len(filtered))

# Distinct Works metric: count unique composer+piece combinations
if col_piece and col_composer_name:
    unique_works = filtered[[col_composer_name, col_piece]].drop_duplicates().shape[0]
    col2.metric("Distinct Works", unique_works)
elif col_piece:
    col2.metric("Distinct Works", filtered[col_piece].nunique())
else:
    col2.metric("Distinct Works", "N/A")

# Distinct Performers metric
if col_performer:
    col3.metric("Distinct Performers", filtered[col_performer].nunique())
else:
    col3.metric("Distinct Performers", "N/A")

# Performance Details table
st.subheader("Performance Details")
st.caption("Table shows records matching current filters.")
display_cols = []
rename_map = {}
if col_semester:      display_cols.append(col_semester);      rename_map[col_semester] = "Semester"
if col_date:          display_cols.append(col_date);          rename_map[col_date] = "Date"
if col_performer:     display_cols.append(col_performer);     rename_map[col_performer] = "Performer"
if col_instrument:    display_cols.append(col_instrument);    rename_map[col_instrument] = "Instrument"
if col_composer_name: display_cols.append(col_composer_name); rename_map[col_composer_name] = "Composer"
if col_piece:         display_cols.append(col_piece);         rename_map[col_piece] = "Piece"

df_display = filtered[display_cols].rename(columns=rename_map)

# Download filtered results
# import io
# towrite = io.BytesIO()
# df_display.to_excel(towrite, index=False, sheet_name='Data')
# towrite.seek(0)
# st.download_button(
#     label="Download data as Excel (.xlsx)",
#     data=towrite,
#     file_name="filtered_data.xlsx",
#     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
# )

# ——— Sidebar ICD Logo ———
st.sidebar.markdown("<br><br><br>", unsafe_allow_html=True)
st.sidebar.image("powered by.png", use_container_width=True)

# Display filtered results table
st.write(f"Displaying {len(df_display)} records:")
st.dataframe(df_display, use_container_width=True)
