from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.lifecycle_analysis import (
    DEFAULT_DATA_PATH,
    attribute_summary,
    monthly_rotation,
    prepare_data,
    stage_distribution,
    top_lifecycle_table,
)


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
OUTPUT = ROOT / "output"


def pct(value: float) -> str:
    return "n/a" if pd.isna(value) else f"{value:.1%}"


def num(value: float, digits: int = 1) -> str:
    return "n/a" if pd.isna(value) else f"{value:.{digits}f}"


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No data._"
    formatted = df.copy()
    for col in formatted.columns:
        if pd.api.types.is_datetime64_any_dtype(formatted[col]):
            formatted[col] = formatted[col].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_float_dtype(formatted[col]):
            formatted[col] = formatted[col].map(lambda x: "" if pd.isna(x) else f"{x:.2f}")
    formatted = formatted.fillna("").astype(str)
    headers = list(formatted.columns)
    rows = formatted.values.tolist()

    def esc(value: str) -> str:
        return value.replace("|", "\\|")

    header_line = "| " + " | ".join(esc(h) for h in headers) + " |"
    divider = "| " + " | ".join("---" for _ in headers) + " |"
    row_lines = ["| " + " | ".join(esc(v) for v in row) + " |" for row in rows]
    return "\n".join([header_line, divider, *row_lines])


def write_reports(data_path=DEFAULT_DATA_PATH) -> None:
    REPORTS.mkdir(exist_ok=True)
    OUTPUT.mkdir(exist_ok=True)

    prepared = prepare_data(data_path)
    k = prepared.kpis
    lifecycle = prepared.lifecycle
    stage_daily = prepared.stage_daily
    churn = prepared.churn_daily

    explicit = attribute_summary(lifecycle, "explicit_label")
    release = attribute_summary(lifecycle, "release_form")
    stages = stage_distribution(stage_daily)
    monthly = monthly_rotation(churn)
    top_songs = top_lifecycle_table(lifecycle, 12)
    failed_validation = prepared.validation[~prepared.validation["passes_50_rule"]]

    lifecycle.to_csv(OUTPUT / "song_lifecycle_metrics.csv", index=False)
    stage_daily.to_csv(OUTPUT / "daily_lifecycle_stages.csv", index=False)
    churn.to_csv(OUTPUT / "daily_churn_metrics.csv", index=False)
    monthly.to_csv(OUTPUT / "monthly_rotation_metrics.csv", index=False)

    clean_avg = explicit.loc[explicit["explicit_label"].eq("Clean"), "avg_days"].iloc[0]
    exp_avg = explicit.loc[explicit["explicit_label"].eq("Explicit"), "avg_days"].iloc[0]
    single_avg = release.loc[release["release_form"].eq("Single"), "avg_days"].iloc[0]
    album_avg = release.loc[release["release_form"].eq("Album"), "avg_days"].iloc[0]

    research = f"""# Atlantic Spain Top 50 Song Lifecycle Research Paper

## Abstract

This study converts Atlantic Recording Corporation's Spain Top 50 daily playlist snapshots into lifecycle intelligence. Instead of treating popularity as a static rank outcome, the analysis measures entry speed, peak timing, survival, churn, maturity stage, and content-attribute effects across Spanish playlist behavior.

## Data And Scope

- Source file: `{Path(data_path).name}`
- Raw rows: {k["raw_rows"]:,}
- Cleaned analytical rows: {k["clean_rows"]:,}
- Date range: {k["date_min"].strftime("%Y-%m-%d")} to {k["date_max"].strftime("%Y-%m-%d")}
- Playlist days observed: {k["playlist_days"]:,}
- Unique normalized song-artist pairs: {k["unique_songs"]:,}
- Missing calendar dates inside range: {k["missing_calendar_dates"]} ({", ".join(k["missing_dates"]) if k["missing_dates"] else "none"})

## Data Validation And Normalization

Song identity was normalized by lowercasing and trimming whitespace across song and artist fields. Lifecycle calculations use one row per `date + position`, preserving the latest row when duplicate positions occur on the same date. This keeps each analytical snapshot aligned with the Top 50 structure.

Validation found {k["validation_failed_days"]} raw date(s) that failed the exact 50-entry rule:

{md_table(failed_validation[["date", "raw_rows", "unique_positions", "duplicate_positions", "duplicate_song_artist", "passes_50_rule"]])}

## Lifecycle Construction

For each normalized song-artist pair, the study computed entry date, exit date, observed playlist days, calendar span, peak position, first peak date, entry-to-peak days, average position, popularity levels, explicit flag, release form, duration, and album size. Observed days measure the number of daily snapshots in which a song appears, while calendar span measures the first-to-last appearance window.

## Key Performance Indicators

| KPI | Value | Interpretation |
|---|---:|---|
| Average days on playlist | {num(k["average_days_on_playlist"])} days | Typical playlist survival across unique songs |
| Entry-to-peak time | {num(k["entry_to_peak_time"])} days | Average maturity speed from first appearance to best rank |
| Playlist churn rate | {pct(k["playlist_churn_rate"])} | Average daily replacement intensity |
| Retention stability index | {pct(k["retention_stability_index"])} | Average day-to-day overlap of Top 50 songs |
| Explicit lifecycle score | {num(k["explicit_lifecycle_score"], 2)}x | Explicit average longevity divided by clean longevity |
| Single vs album longevity ratio | {num(k["single_vs_album_longevity_ratio"], 2)}x | Single average longevity divided by album-track longevity |

## Lifecycle Stage Distribution

{md_table(stages)}

The stage mix indicates how much of Spain's Top 50 inventory is being used for fresh discovery, peak holding, mid-rank durability, and decline management. New entries are intentionally separated from growth because Spain's playlist dynamics are highly sensitive to release freshness.

## Playlist Rotation And Churn

Average daily churn is {pct(k["playlist_churn_rate"])}, meaning roughly {num(k["playlist_churn_rate"] * 50)} net entry-equivalent positions rotate per day. The retention stability index of {pct(k["retention_stability_index"])} shows that the market has meaningful continuity but still rotates quickly enough to require tight release-week and post-peak planning.

Monthly rotation profile:

{md_table(monthly)}

## Explicit Vs Clean Lifecycle Behavior

{md_table(explicit)}

Explicit tracks averaged {num(exp_avg)} observed playlist days versus {num(clean_avg)} for clean tracks. The explicit lifecycle score of {num(k["explicit_lifecycle_score"], 2)}x suggests that explicit repertoire is not merely a short-lived novelty category in this dataset; it can mature with comparable or stronger retention when the track is already accepted by playlist listeners.

## Single Vs Album Lifecycle Behavior

{md_table(release)}

Singles averaged {num(single_avg)} observed playlist days versus {num(album_avg)} for album tracks. The single-to-album longevity ratio of {num(k["single_vs_album_longevity_ratio"], 2)}x indicates that singles have a survival advantage in Spain's Top 50 environment, supporting single-led campaign pacing and careful album-focus selection.

## Top Lifecycle Performers

{md_table(top_songs)}

## Strategic Recommendations

1. Prioritize the first seven days as a separate operating window. New-entry behavior should be monitored daily because early movement determines whether marketing should intensify, hold, or pivot.
2. Treat peak timing as a maturity trigger. Songs that peak quickly but lose rank need fast creative refresh, playlist negotiation, or social amplification before the decline phase hardens.
3. Keep singles at the center of Spain release strategy. The dataset shows stronger longevity for singles than album tracks, so album campaigns should identify only the most retention-capable focus tracks for playlist pushes.
4. Do not automatically soften explicit repertoire assumptions. Explicit tracks show durable lifecycle behavior in this data and should be evaluated by retention and peak behavior rather than maturity concerns alone.
5. Use churn to time follow-up actions. Higher-churn months require more aggressive entry support and shorter optimization cycles; lower-churn months reward sustained catalog and mid-rank maintenance.

## Limitations

The dataset does not include true release dates, stream counts, playlist add source, listener demographics, paid media spend, or off-platform social signals. "Freshness" is therefore measured as first observed playlist appearance, not actual market release age. One raw date contains duplicate position snapshots and four calendar dates are absent from the observed span, so cleaned lifecycle metrics should be interpreted as playlist-observed behavior rather than exhaustive market behavior.

## Conclusion

Spain's Top 50 behavior can be managed as a lifecycle system: entry, growth, peak, maturity, and decline. The analysis gives Atlantic Spain-specific signals for release timing, marketing intensity, catalog balance, explicit-content planning, and single-versus-album prioritization, avoiding direct copyover from US or UK playlist assumptions.
"""

    executive = f"""# Executive Summary: Atlantic Spain Music Lifecycle Intelligence

## Purpose

Atlantic Recording Corporation needs Spain-specific playlist lifecycle intelligence because the market is shaped by Latin and regional genre influence, release freshness, fast playlist rotation, and distinct explicit-content maturity patterns.

## Headline Findings

- The cleaned dataset covers {k["playlist_days"]:,} Top 50 daily snapshots from {k["date_min"].strftime("%Y-%m-%d")} to {k["date_max"].strftime("%Y-%m-%d")}.
- Average song survival is {num(k["average_days_on_playlist"])} observed playlist days.
- Songs take an average of {num(k["entry_to_peak_time"])} days from first observed entry to best rank.
- Average playlist churn is {pct(k["playlist_churn_rate"])}, while day-to-day stability is {pct(k["retention_stability_index"])}.
- Explicit tracks show a {num(k["explicit_lifecycle_score"], 2)}x lifecycle score versus clean tracks.
- Singles show a {num(k["single_vs_album_longevity_ratio"], 2)}x longevity ratio versus album tracks.

## Implications For Stakeholders

Spain should not be managed with a generic US or UK release model. The playlist requires fast early monitoring, quick post-peak decisions, and single-led release planning. Explicit content should be evaluated through actual retention behavior, not assumed to age out faster.

## Recommended Actions

1. Establish a seven-day release command window for every priority track.
2. Use entry-to-peak timing to decide when marketing pressure should increase or taper.
3. Maintain single-led planning, with album tracks promoted selectively based on early retention.
4. Monitor monthly churn to adjust playlist pitching and paid-media timing.
5. Track explicit and clean content separately in weekly performance reviews.

## Governance Note

The analytical table enforces one Top 50 entry per position per date. One raw date failed the 50-entry validation rule and four calendar dates are missing, so public reporting should describe results as playlist-observed lifecycle behavior.
"""

    (REPORTS / "research_paper.md").write_text(research, encoding="utf-8")
    (REPORTS / "executive_summary.md").write_text(executive, encoding="utf-8")



if __name__ == "__main__":
    write_reports()
