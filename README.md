# Spain50 Analytics 🇪🇸🎵

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://spain50analytics.streamlit.app/)
[![GitHub license](https://img.shields.io/github/license/Sunny210405/Spain_50_Analytics?color=1DB954&style=flat-square)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square&color=1DB954)](https://www.python.org/)

An advanced, interactive analytics dashboard designed to analyze and track the **Daily Top 50 Playlist Intelligence** in Spain. It parses raw music data to deliver insights on song survival, audience retention, lifecycle progression, content maturity metrics, and artist/track churn.

🔗 **Live Dashboard:** [https://spain50analytics.streamlit.app/](https://spain50analytics.streamlit.app/)

---

## 🚀 Key Features

* 📊 **Lifecycle Stage Distribution**: Track how songs transition through stages: *New Entry*, *Growth*, *Peak*, *Mature*, and *Decline*.
* 📈 **Song Timelines**: Visualize position tracks, popularity trends, and lifecycle milestones for individual songs.
* 🔄 **Entry/Exit Flows**: Analyze incoming and outgoing track behavior to pinpoint playlist rotation velocities.
* 🔞 **Content Maturity (Explicit vs Clean)**: Deep-dive into explicit content ratios, longevity differences, and track release forms (Singles vs Albums).
* 📉 **Churn & Retention**: Calculate monthly rotation, daily playlist stability indices, and survivor ratios.
* 🔍 **Interactive Song Explorer**: Search and filter the entire historical music catalog with visual metrics.
* 🛡️ **Raw Data Validation**: Automated rules verifying playlist size integrity (e.g., checking the 50-entry rule).

---

## 🛠️ Tech Stack & Design System

* **Backend**: Python (Pandas, NumPy, Pathlib)
* **Frontend**: Streamlit
* **Visualizations**: Altair & Vega-Lite
* **Design & Theme**: Curated Spotify-Dark interface, premium *Outfit* typography, responsive layouts, acrylic/glassmorphic sidebar, and subtle animated background glows.

---

## 📂 Repository Structure

```
├── .streamlit/
│   └── config.toml         # Theme settings (colors, fonts, etc.)
├── src/
│   └── lifecycle_analysis.py  # Core data processing & calculation engine
├── reports/
│   ├── research_paper.md   # EDA, research methodology, and insights
│   └── executive_summary.md # Stakeholder executive summary
├── output/                 # Generated analytical metrics
│   ├── churn_daily.csv
│   ├── daily_metrics.csv
│   ├── lifecycle_metrics.csv
│   └── monthly_metrics.csv
├── app.py                  # Streamlit application entrypoint
├── generate_reports.py     # Script to calculate stats and export CSV reports
├── requirements.txt        # Project dependencies
└── README.md               # Documentation
```

---

## 💻 Local Setup & Execution

### 1. Prerequisites
Ensure you have **Python 3.9+** installed on your machine.

### 2. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/Sunny210405/Spain_50_Analytics.git
cd Spain_50_Analytics
pip install -r requirements.txt
```

### 3. Generate Analytical Reports
To regenerate the processed metrics and markdown reports:
```bash
python generate_reports.py
```

### 4. Run the Dashboard Locally
Launch the Streamlit dashboard:
```bash
streamlit run app.py
```

---

## 🧑‍💻 Author
Created with ❤️ by **[SUNNY](https://github.com/Sunny210405)**.
