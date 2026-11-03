# Ferrstron Motor Test Intelligence — Demo Prototype

A deployable Streamlit prototype for analysing motor test CSV/Excel files.

## Included features
- CSV and Excel upload for one or two configurations
- Column-name normalisation for common aliases
- Mechanical output power, electrical input power and calculated efficiency
- Torque/RPM, power/RPM, efficiency/RPM and temperature/RPM plots
- Side-by-side configuration summary and graph
- Simple IQR statistical outlier screening
- Processed CSV export and PDF summary report
- Synthetic example data so the app opens immediately

## Run locally

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit (usually http://localhost:8501).

## Deploy

### Streamlit Community Cloud
1. Create a GitHub repository and upload the contents of this ZIP.
2. In Streamlit Community Cloud, create an app from that repository.
3. Set the main file path to `app.py`.
4. Deploy.

### Render
1. Create a new Web Service from the GitHub repository.
2. Render detects `render.yaml`, or use:
   - Build command: `pip install -r requirements.txt`
   - Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

## Input data format

Required numeric columns (case/spacing aliases supported):
- `rpm`
- `torque_nm`
- `voltage_v`
- `current_a`

Optional:
- `temperature_c`

Units must be RPM, Nm, V, A and °C. The app assumes these units when calculating power and efficiency.

## Important engineering limitations

This is a demonstration tool, not a validated industrial engineering system. The included sample datasets are synthetic. Before using real test data:
- confirm column definitions and units;
- confirm whether voltage/current are DC bus values, phase values, RMS values, or another measurement boundary;
- confirm torque and speed sensor calibration;
- agree on thermal limits and acceptable operating envelopes with qualified engineers;
- validate calculations against an independently checked reference test;
- do not use the app alone for design release, safety decisions, certification or warranty claims.

The IQR anomaly screen only flags statistical outliers. It does not diagnose faults or predict remaining useful life. The app does not connect to live sensors, CAD, electromagnetic simulation or company systems.
