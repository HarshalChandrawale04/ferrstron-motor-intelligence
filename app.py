import io
import math
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

st.set_page_config(page_title="Ferrstron | Motor Test Intelligence", page_icon="⚙️", layout="wide")

st.markdown("""
<style>
.main {background:#f6f8fb;}
.block-container {padding-top:1.4rem; max-width:1450px;}
.hero {padding:24px 28px; border-radius:16px; color:white; background:linear-gradient(115deg,#10243a,#176b87);}
.hero h1 {margin:0; font-size:2rem;}
.hero p {margin:8px 0 0 0; opacity:.9;}
.small-note {color:#637083; font-size:.85rem;}
div[data-testid="stMetric"] {background:white; border:1px solid #e7edf3; padding:14px; border-radius:12px;}
</style>
<div class="hero">
<h1>⚙️ Motor Test Intelligence</h1>
<p>Engineering analytics prototype · motor performance, test comparison and report generation</p>
</div>
""", unsafe_allow_html=True)

st.caption("Independent demonstration prototype. Not affiliated with Ferrstron and not validated for production engineering decisions.")
st.sidebar.header("Workspace")
st.sidebar.write("Upload one or two motor test datasets, or start with the included illustrative sample files.")
st.sidebar.markdown("---")
st.sidebar.markdown("**Expected columns**")
st.sidebar.code("rpm, torque_nm, voltage_v, current_a, temperature_c", language="text")

ALIASES = {
    "rpm": ["rpm", "speed", "speed_rpm", "motor_rpm"],
    "torque_nm": ["torque_nm", "torque", "torque (nm)", "torque_nm "],
    "voltage_v": ["voltage_v", "voltage", "voltage (v)", "volt"],
    "current_a": ["current_a", "current", "current (a)", "amps"],
    "temperature_c": ["temperature_c", "temperature", "temp", "temp_c", "temperature (c)"],
}

def standardize(df):
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    rename = {}
    for target, choices in ALIASES.items():
        for c in df.columns:
            if c in choices or c.replace("_", " ") in choices:
                rename[c] = target
                break
    df = df.rename(columns=rename)
    required = ["rpm", "torque_nm", "voltage_v", "current_a"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    if "temperature_c" not in df.columns:
        df["temperature_c"] = np.nan
    for c in required + ["temperature_c"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=required).copy()
    df = df[(df["rpm"] >= 0) & (df["voltage_v"] >= 0) & (df["current_a"] >= 0)]
    df["mechanical_power_w"] = df["torque_nm"] * 2 * math.pi * df["rpm"] / 60
    df["electrical_input_w"] = df["voltage_v"] * df["current_a"]
    df["efficiency_pct"] = np.where(
        df["electrical_input_w"] > 0,
        100 * df["mechanical_power_w"] / df["electrical_input_w"],
        np.nan
    )
    # Efficiency above 100% is retained but visibly flagged; it can indicate bad units or measurements.
    for c in ["rpm", "torque_nm", "voltage_v", "current_a", "temperature_c",
              "mechanical_power_w", "electrical_input_w", "efficiency_pct"]:
        if c in df:
            df[c] = df[c].round(3)
    return df.reset_index(drop=True)

def load_file(file):
    if file.name.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(file)
    return pd.read_csv(file)

def metrics(df):
    valid = df["efficiency_pct"].dropna()
    return {
        "Rows": len(df),
        "Peak torque (Nm)": df["torque_nm"].max(),
        "Peak speed (RPM)": df["rpm"].max(),
        "Peak mechanical power (kW)": df["mechanical_power_w"].max()/1000,
        "Mean efficiency (%)": valid.mean() if len(valid) else np.nan,
        "Peak temperature (°C)": df["temperature_c"].max(),
    }

def flag_outliers(df):
    out = pd.Series(False, index=df.index)
    cols = ["torque_nm", "current_a", "temperature_c", "efficiency_pct"]
    for c in cols:
        vals = df[c].dropna()
        if len(vals) >= 4:
            q1, q3 = vals.quantile([.25, .75])
            iqr = q3-q1
            if iqr > 0:
                out |= (df[c] < q1-1.5*iqr) | (df[c] > q3+1.5*iqr)
    return out.fillna(False)

def make_pdf(title, df, summary, notes):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 8),
             Paragraph("Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M"), styles["Normal"]),
             Spacer(1, 12), Paragraph("Performance summary", styles["Heading2"])]
    data = [["Metric", "Value"]]
    for k, v in summary.items():
        data.append([str(k), "—" if pd.isna(v) else (f"{v:.2f}" if isinstance(v, (int,float,np.number)) else str(v))])
    t = Table(data, colWidths=[240, 220])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#163a52")),
                           ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                           ("GRID",(0,0),(-1,-1),.4,colors.HexColor("#cbd5df")),
                           ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f0f4f7")]),
                           ("PADDING",(0,0),(-1,-1),7)]))
    story += [t, Spacer(1, 14), Paragraph("Automated observations", styles["Heading2"])]
    for note in notes:
        story.append(Paragraph("• " + note, styles["BodyText"]))
        story.append(Spacer(1, 5))
    story += [Spacer(1, 12), Paragraph("Data preview", styles["Heading2"])]
    preview = df[["rpm","torque_nm","voltage_v","current_a","mechanical_power_w","efficiency_pct"]].head(12)
    table_data = [list(preview.columns)] + preview.fillna("").astype(str).values.tolist()
    pt = Table(table_data, repeatRows=1)
    pt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#163a52")),
                            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                            ("FONTSIZE",(0,0),(-1,-1),7),
                            ("GRID",(0,0),(-1,-1),.3,colors.grey),
                            ("PADDING",(0,0),(-1,-1),4)]))
    story.append(pt)
    story += [Spacer(1, 12), Paragraph("Important: This report is an analytical aid, not engineering certification. Validate measurements, units, test conditions and conclusions with qualified engineers.", styles["Italic"])]
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()

def observations(df, flags):
    notes = []
    if len(df) == 0:
        return ["No valid rows were found."]
    eff = df["efficiency_pct"].dropna()
    if len(eff):
        notes.append(f"Mean calculated efficiency is {eff.mean():.1f}%; verify that torque, RPM, voltage and current units and measurement boundaries are correct.")
        if (eff > 100).any():
            notes.append("Some calculated efficiency values exceed 100%. This is physically inconsistent for a conventional motor boundary and should trigger a units, sensor or measurement-boundary check.")
    if df["temperature_c"].notna().any():
        notes.append(f"Highest recorded temperature is {df['temperature_c'].max():.1f} °C. Compare it with the component-specific limit supplied by the engineering team.")
    notes.append(f"{int(flags.sum())} row(s) were flagged by a simple IQR statistical outlier screen. A flag is not proof of a fault.")
    return notes

sample_a = pd.DataFrame({
    "rpm":[500,750,1000,1250,1500,1750,2000,2250,2500,2750,3000],
    "torque_nm":[42,41,40,38,36,34,31,28,25,21,17],
    "voltage_v":[48]*11,
    "current_a":[18,20,22,24,26,28,29,30,31,30,28],
    "temperature_c":[31,33,35,38,41,44,47,50,54,58,61]
})
sample_b = pd.DataFrame({
    "rpm":[500,750,1000,1250,1500,1750,2000,2250,2500,2750,3000],
    "torque_nm":[40,39,38,37,35,33,30,27,24,20,16],
    "voltage_v":[48]*11,
    "current_a":[17,19,21,23,25,27,28,29,30,29,27],
    "temperature_c":[30,32,34,36,39,42,45,48,51,55,58]
})

st.subheader("1. Upload test data")
c1, c2 = st.columns(2)
with c1:
    file_a = st.file_uploader("Motor / configuration A (CSV or Excel)", type=["csv","xlsx","xls"], key="a")
with c2:
    file_b = st.file_uploader("Motor / configuration B (optional)", type=["csv","xlsx","xls"], key="b")

use_sample = st.toggle("Use included illustrative sample datasets", value=not bool(file_a))
raw_a = load_file(file_a) if file_a else (sample_a if use_sample else None)
raw_b = load_file(file_b) if file_b else (sample_b if use_sample else None)

if raw_a is None:
    st.info("Upload a CSV/Excel test file or enable the sample datasets to begin.")
    st.stop()

try:
    a = standardize(raw_a)
    b = standardize(raw_b) if raw_b is not None else None
except Exception as e:
    st.error(f"Could not process the file: {e}")
    st.stop()

st.success(f"Configuration A: {len(a)} valid rows" + (f" · Configuration B: {len(b)} valid rows" if b is not None else ""))
st.caption("Calculations assume torque in Nm, speed in RPM, voltage in V and current in A. Efficiency is calculated as mechanical output power ÷ electrical input power × 100.")

st.subheader("2. Performance overview")
m = metrics(a)
cols = st.columns(5)
for col, key in zip(cols, ["Peak torque (Nm)","Peak mechanical power (kW)","Mean efficiency (%)","Peak temperature (°C)","Rows"]):
    val = m[key]
    col.metric(key, "—" if pd.isna(val) else (f"{val:.1f}" if isinstance(val,(int,float,np.number)) else str(val)))

left, right = st.columns(2)
with left:
    fig = px.line(a, x="rpm", y="torque_nm", markers=True, title="Torque vs RPM · Configuration A")
    fig.update_layout(xaxis_title="Speed (RPM)", yaxis_title="Torque (Nm)")
    st.plotly_chart(fig, use_container_width=True)
with right:
    fig = px.line(a, x="rpm", y="mechanical_power_w", markers=True, title="Mechanical power vs RPM · Configuration A")
    fig.update_layout(xaxis_title="Speed (RPM)", yaxis_title="Mechanical power (W)")
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
with left:
    fig = px.line(a, x="rpm", y="efficiency_pct", markers=True, title="Calculated efficiency vs RPM")
    fig.update_layout(xaxis_title="Speed (RPM)", yaxis_title="Efficiency (%)")
    st.plotly_chart(fig, use_container_width=True)
with right:
    if a["temperature_c"].notna().any():
        fig = px.line(a, x="rpm", y="temperature_c", markers=True, title="Temperature vs RPM")
        fig.update_layout(xaxis_title="Speed (RPM)", yaxis_title="Temperature (°C)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No temperature column was supplied.")

st.subheader("3. Data quality and anomaly screening")
flags = flag_outliers(a)
anomaly_df = a.copy()
anomaly_df["statistical_flag"] = flags.map({True:"Review",False:"—"})
st.write(f"**{int(flags.sum())}** row(s) flagged for review using an interquartile-range screen across torque, current, temperature and calculated efficiency.")
st.dataframe(anomaly_df, use_container_width=True, hide_index=True)

if b is not None:
    st.subheader("4. Configuration comparison")
    mb = metrics(b)
    compare_keys = ["Peak torque (Nm)","Peak speed (RPM)","Peak mechanical power (kW)","Mean efficiency (%)","Peak temperature (°C)"]
    comp = pd.DataFrame({"Metric":compare_keys, "Configuration A":[m[k] for k in compare_keys], "Configuration B":[mb[k] for k in compare_keys]})
    st.dataframe(comp, use_container_width=True, hide_index=True)
    compare_plot = pd.concat([
        a.assign(configuration="A"),
        b.assign(configuration="B")
    ], ignore_index=True)
    metric_choice = st.selectbox("Compare performance metric", ["torque_nm","mechanical_power_w","efficiency_pct","temperature_c"])
    if compare_plot[metric_choice].notna().any():
        fig = px.line(compare_plot, x="rpm", y=metric_choice, color="configuration", markers=True,
                      title=f"Configuration A vs B · {metric_choice}")
        st.plotly_chart(fig, use_container_width=True)
    st.caption("Comparison is meaningful only when both files use comparable test conditions, sensors, units and measurement procedures.")
else:
    st.subheader("4. Configuration comparison")
    st.info("Upload a second file to compare two motor configurations.")

st.subheader("5. Automated engineering observations")
notes = observations(a, flags)
for note in notes:
    st.write("• " + note)

st.subheader("6. Export")
csv_bytes = anomaly_df.to_csv(index=False).encode("utf-8")
st.download_button("Download processed data (CSV)", csv_bytes, file_name="motor_test_analysis.csv", mime="text/csv")
pdf_bytes = make_pdf("Motor Test Intelligence Report", a, m, notes)
st.download_button("Download engineering summary (PDF)", pdf_bytes, file_name="motor_test_report.pdf", mime="application/pdf")

with st.expander("How are the calculations made?"):
    st.latex(r"P_{mechanical}(W)=T(Nm)\\times\\frac{2\\pi\\times RPM}{60}")
    st.latex(r"P_{electrical}(W)=V\\times I")
    st.latex(r"Efficiency(\\%)=\\frac{P_{mechanical}}{P_{electrical}}\\times100")
    st.write("The anomaly screen uses a simple 1.5×IQR rule. It is an exploratory data-quality aid, not a trained fault-detection model.")
with st.expander("Prototype limitations and safe use"):
    st.markdown("""
    - Sample values are synthetic and are included only to demonstrate the workflow.
    - No Ferrstron confidential data, motor design files or internal specifications are included.
    - No claim is made that this software is approved for design release, safety certification or production decisions.
    - Confirm units, sensor calibration, test boundary and operating conditions before interpreting results.
    - Efficiency above 100% is retained and flagged for review rather than silently corrected.
    """)
