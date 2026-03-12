# Airspace Conflict Analysis

Real-world ADS-B flight data analysis pipeline for detecting and characterizing aircraft separation violations in the Dallas/Fort Worth TRACON sector. Built with Python, Jupyter, Docker, and Kubernetes.

---

## Project Overview

This project pulls live aircraft position data from the [OpenSky Network](https://opensky-network.org/) API, applies FAA separation standards to detect conflict events, scores them by risk, and produces an executive-style analytical summary — the kind of workflow an operations analyst would run on real airspace data.

## Project Structure

```
airspace_analysis/
├── notebooks/
│   ├── 01_data_collection.ipynb      # Pull & clean ADS-B data from OpenSky
│   ├── 02_exploratory_analysis.ipynb # Traffic density, altitude, speed, heading
│   ├── 03_conflict_detection.ipynb   # Pairwise FAA separation checks + risk scoring
│   ├── 04_risk_analysis.ipynb        # Hotspot maps, sector metrics, alt-band breakdown
│   └── 05_summary_report.ipynb       # Executive dashboard + analytical conclusions
├── src/
│   └── airspace.py                   # Shared utilities: haversine, conflict 
│   └── get_bbox.py                   # BBOX lookup by ICAO code
├── data/                             # Raw and processed CSVs (git-ignored)
├── outputs/                          # Plots and maps (git-ignored)
├── docker/
│   ├── Dockerfile                    # Jupyter environment container
│   └── .dockerignore
├── k8s/
│   ├── namespace.yaml
│   ├── configmap.yaml                # Airspace parameters as K8s config
│   ├── deployment.yaml               # Pod spec with health probes + resource limits
│   └── service.yaml                  # NodePort service (port 30888)
├── requirements.txt
└── README.md
```

> **Note:** The Docker and Kubernetes skeleton is listed and is currently being developed. In the current commit of this readme, these files are not available.

---

## Quickstart (Local)

### Prerequisites
```bash
pip install -r requirements.txt
```

### Run Notebooks
```bash
jupyter notebook notebooks/
```

Run them in order: `01` → `02` → `03` → `04` → `05`.

> **Note:** Notebook 01 makes live API calls to OpenSky. If the API is unavailable or rate-limited, it will log failures and continue with whatever data was collected.


## Key Analytical Concepts

| Concept | Application |
|---|---|
| **Haversine Formula** | Great-circle distance between aircraft lat/lon positions |
| **FAA 7110.65 Standards** | 3 NM horizontal, 1,000 ft vertical separation minimums |
| **Pairwise O(n²) Check** | Every aircraft pair evaluated at each snapshot |
| **Composite Risk Score** | Separation margin (50%) + severity (30%) + closing speed (20%) |
| **Closing Speed** | Velocity projection onto bearing — determines if aircraft are converging |
| **Innovation / Residual** | Gap between predicted and observed position |

---

## Data Source

[OpenSky Network](https://opensky-network.org/) — anonymous REST API access, no key required.
- Rate limit: 1 request per 10 seconds, 400 requests per day
- Coverage: global ADS-B receivers
- Latency: ~10 second delay from real-time

---
