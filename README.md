# Atlantic Spain Lifecycle Analytics

This project analyzes Atlantic Spain Top 50 playlist data through song lifecycle, stage, churn, and content maturity metrics.

## Files

- `app.py` - Streamlit dashboard.
- `src/lifecycle_analysis.py` - reusable lifecycle and KPI logic.
- `generate_reports.py` - creates markdown reports and CSV metric exports.
- `reports/research_paper.md` - EDA, methodology, insights, and recommendations.
- `reports/executive_summary.md` - stakeholder summary.
- `output/*.csv` - generated lifecycle, stage, churn, and monthly metrics.

## Run

```powershell
pip install -r requirements.txt
python generate_reports.py
streamlit run app.py
```

The dashboard defaults to `C:\Users\janaa\Downloads\Spain_50_Analytics\Atlantic_Spain.csv` and also supports CSV upload.
