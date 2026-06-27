from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np
import pandas as pd


DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "Atlantic_Spain.csv"
TOP_N = 50


@dataclass(frozen=True)
class PreparedData:
    raw: pd.DataFrame
    daily: pd.DataFrame
    lifecycle: pd.DataFrame
    stage_daily: pd.DataFrame
    churn_daily: pd.DataFrame
    validation: pd.DataFrame
    kpis: dict


def normalize_text(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = re.sub(r"\s+", " ", text.strip().lower())
    return text


def parse_dates_robustly(series: pd.Series) -> pd.Series:
    dates = pd.to_datetime(series, format="%d-%m-%Y", errors="coerce")
    mask = dates.isna() & series.notna()
    if mask.any():
        dates[mask] = pd.to_datetime(series[mask], errors="coerce")
    return dates


def read_playlist_csv(path_or_buffer) -> pd.DataFrame:
    name = ""
    if hasattr(path_or_buffer, "name"):
        name = str(path_or_buffer.name).lower()
    elif isinstance(path_or_buffer, (str, Path)):
        name = str(path_or_buffer).lower()

    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(path_or_buffer)
    else:
        df = pd.read_csv(path_or_buffer)

    expected = {
        "date",
        "position",
        "song",
        "artist",
        "popularity",
        "duration_ms",
        "album_type",
        "total_tracks",
        "is_explicit",
        "album_cover_url",
    }
    missing = sorted(expected.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    return df


def validate_raw(raw: pd.DataFrame) -> pd.DataFrame:
    work = raw.copy()
    work["date_dt"] = parse_dates_robustly(work["date"])
    work["song_key"] = work["song"].map(normalize_text) + " | " + work["artist"].map(normalize_text)

    by_day = (
        work.groupby(["date", "date_dt"], dropna=False)
        .agg(
            raw_rows=("position", "size"),
            unique_positions=("position", "nunique"),
            duplicate_positions=("position", lambda s: int(s.duplicated().sum())),
            duplicate_song_artist=("song_key", lambda s: int(s.duplicated().sum())),
            invalid_positions=("position", lambda s: int(((s < 1) | (s > TOP_N)).sum())),
        )
        .reset_index()
    )
    by_day["passes_50_rule"] = by_day["raw_rows"].eq(TOP_N) & by_day["unique_positions"].eq(TOP_N)
    return by_day.sort_values("date_dt")


def clean_daily(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["date_dt"] = parse_dates_robustly(df["date"])
    df = df.dropna(subset=["date_dt"])
    df["song_norm"] = df["song"].map(normalize_text)
    df["artist_norm"] = df["artist"].map(normalize_text)
    df["song_key"] = df["song_norm"] + " | " + df["artist_norm"]
    df["album_type"] = df["album_type"].map(lambda x: normalize_text(x).title())
    df["is_explicit"] = df["is_explicit"].astype(bool)
    df["duration_min"] = df["duration_ms"] / 60000

    sort_cols = ["date_dt", "position", "popularity", "song_key"]
    df = df.sort_values(sort_cols)
    df = df.drop_duplicates(["date_dt", "position"], keep="last")
    df = df.sort_values(["date_dt", "position"]).reset_index(drop=True)
    return df


def build_lifecycle(daily: pd.DataFrame) -> pd.DataFrame:
    ordered = daily.sort_values(["song_key", "date_dt", "position"]).copy()
    grouped = ordered.groupby("song_key", sort=False)

    lifecycle = grouped.agg(
        song=("song", "first"),
        artist=("artist", "first"),
        album_type=("album_type", "first"),
        is_explicit=("is_explicit", "first"),
        total_tracks=("total_tracks", "median"),
        duration_min=("duration_min", "median"),
        entry_date=("date_dt", "min"),
        exit_date=("date_dt", "max"),
        observed_days=("date_dt", "nunique"),
        peak_position=("position", "min"),
        avg_position=("position", "mean"),
        median_position=("position", "median"),
        avg_popularity=("popularity", "mean"),
        peak_popularity=("popularity", "max"),
        latest_popularity=("popularity", "last"),
        album_cover_url=("album_cover_url", "first"),
    ).reset_index()

    first_peak = (
        ordered.sort_values(["song_key", "position", "date_dt"])
        .drop_duplicates("song_key", keep="first")[["song_key", "date_dt"]]
        .rename(columns={"date_dt": "peak_date"})
    )
    lifecycle = lifecycle.merge(first_peak, on="song_key", how="left")
    lifecycle["calendar_span_days"] = (lifecycle["exit_date"] - lifecycle["entry_date"]).dt.days + 1
    lifecycle["entry_to_peak_days"] = (lifecycle["peak_date"] - lifecycle["entry_date"]).dt.days + 1
    lifecycle["retention_ratio"] = lifecycle["observed_days"] / lifecycle["calendar_span_days"].clip(lower=1)
    lifecycle["release_form"] = np.where(lifecycle["album_type"].eq("Single"), "Single", "Album")
    lifecycle["explicit_label"] = np.where(lifecycle["is_explicit"], "Explicit", "Clean")
    return lifecycle.sort_values(["observed_days", "peak_position"], ascending=[False, True]).reset_index(drop=True)


def classify_stage(row: pd.Series) -> str:
    if row["days_since_entry"] <= 7:
        return "New Entry"
    if row["position"] <= 10 and row["top10_rolling_3"] >= 2:
        return "Peak Phase"
    if row["rank_delta"] >= 2:
        return "Growth Phase"
    if row["rank_delta"] <= -2:
        return "Decline Phase"
    if 11 <= row["position"] <= 35 and abs(row["rolling_delta_3"]) <= 2:
        return "Mature Phase"
    if row["rank_delta"] < 0:
        return "Decline Phase"
    if row["rank_delta"] > 0:
        return "Growth Phase"
    return "Mature Phase"


def build_stage_daily(daily: pd.DataFrame, lifecycle: pd.DataFrame) -> pd.DataFrame:
    df = daily.merge(
        lifecycle[
            [
                "song_key",
                "entry_date",
                "exit_date",
                "peak_date",
                "observed_days",
                "calendar_span_days",
                "entry_to_peak_days",
                "retention_ratio",
                "explicit_label",
                "release_form",
            ]
        ],
        on="song_key",
        how="left",
    )
    df = df.sort_values(["song_key", "date_dt"]).copy()
    df["previous_position"] = df.groupby("song_key")["position"].shift(1)
    df["rank_delta"] = df["previous_position"] - df["position"]
    df["rank_delta"] = df["rank_delta"].fillna(0)
    df["days_since_entry"] = (df["date_dt"] - df["entry_date"]).dt.days + 1
    df["top10_flag"] = df["position"].le(10).astype(int)
    df["top10_rolling_3"] = (
        df.groupby("song_key")["top10_flag"]
        .rolling(3, min_periods=1)
        .sum()
        .reset_index(level=0, drop=True)
    )
    df["rolling_delta_3"] = (
        df.groupby("song_key")["rank_delta"]
        .rolling(3, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )
    df["stage"] = df.apply(classify_stage, axis=1)
    return df.sort_values(["date_dt", "position"]).reset_index(drop=True)


def build_churn(stage_daily: pd.DataFrame) -> pd.DataFrame:
    dates = sorted(stage_daily["date_dt"].unique())
    rows = []
    previous_keys: set[str] | None = None
    for date in dates:
        current = stage_daily.loc[stage_daily["date_dt"].eq(date), "song_key"]
        current_keys = set(current)
        if previous_keys is None:
            entries = len(current_keys)
            exits = 0
            overlap = 0
            churn_rate = np.nan
            stability = np.nan
        else:
            entries = len(current_keys - previous_keys)
            exits = len(previous_keys - current_keys)
            overlap = len(current_keys & previous_keys)
            churn_rate = (entries + exits) / (2 * TOP_N)
            stability = overlap / TOP_N
        rows.append(
            {
                "date_dt": date,
                "entries": entries,
                "exits": exits,
                "overlap": overlap,
                "churn_rate": churn_rate,
                "retention_stability_index": stability,
                "month": pd.Timestamp(date).to_period("M").to_timestamp(),
            }
        )
        previous_keys = current_keys
    return pd.DataFrame(rows)


def summarize_kpis(daily: pd.DataFrame, lifecycle: pd.DataFrame, churn: pd.DataFrame, validation: pd.DataFrame) -> dict:
    avg_days = lifecycle["observed_days"].mean()
    avg_peak = lifecycle["entry_to_peak_days"].mean()
    avg_churn = churn["churn_rate"].dropna().mean()
    stability = churn["retention_stability_index"].dropna().mean()

    explicit = lifecycle.groupby("explicit_label")["observed_days"].mean()
    release = lifecycle.groupby("release_form")["observed_days"].mean()

    explicit_score = np.nan
    if "Explicit" in explicit and "Clean" in explicit and explicit["Clean"] != 0:
        explicit_score = explicit["Explicit"] / explicit["Clean"]

    single_album_ratio = np.nan
    if "Single" in release and "Album" in release and release["Album"] != 0:
        single_album_ratio = release["Single"] / release["Album"]

    missing_dates = pd.date_range(daily["date_dt"].min(), daily["date_dt"].max()).difference(
        pd.Index(daily["date_dt"].unique())
    )

    return {
        "date_min": daily["date_dt"].min(),
        "date_max": daily["date_dt"].max(),
        "raw_rows": int(validation["raw_rows"].sum()) if not validation.empty else np.nan,
        "clean_rows": len(daily),
        "playlist_days": daily["date_dt"].nunique(),
        "unique_songs": lifecycle["song_key"].nunique(),
        "average_days_on_playlist": avg_days,
        "entry_to_peak_time": avg_peak,
        "playlist_churn_rate": avg_churn,
        "retention_stability_index": stability,
        "explicit_lifecycle_score": explicit_score,
        "single_vs_album_longevity_ratio": single_album_ratio,
        "validation_failed_days": int((~validation["passes_50_rule"]).sum()) if not validation.empty else 0,
        "missing_calendar_dates": len(missing_dates),
        "missing_dates": [d.strftime("%Y-%m-%d") for d in missing_dates],
    }


def prepare_data(path_or_buffer=DEFAULT_DATA_PATH) -> PreparedData:
    raw = read_playlist_csv(path_or_buffer)
    validation = validate_raw(raw)
    daily = clean_daily(raw)
    lifecycle = build_lifecycle(daily)
    stage_daily = build_stage_daily(daily, lifecycle)
    churn_daily = build_churn(stage_daily)
    kpis = summarize_kpis(daily, lifecycle, churn_daily, validation)
    return PreparedData(raw, daily, lifecycle, stage_daily, churn_daily, validation, kpis)


def monthly_rotation(churn_daily: pd.DataFrame) -> pd.DataFrame:
    return (
        churn_daily.dropna(subset=["churn_rate"])
        .groupby("month")
        .agg(
            avg_entries=("entries", "mean"),
            avg_exits=("exits", "mean"),
            avg_churn_rate=("churn_rate", "mean"),
            avg_stability=("retention_stability_index", "mean"),
        )
        .reset_index()
    )


def attribute_summary(lifecycle: pd.DataFrame, attribute: str) -> pd.DataFrame:
    return (
        lifecycle.groupby(attribute, dropna=False)
        .agg(
            songs=("song_key", "nunique"),
            avg_days=("observed_days", "mean"),
            median_days=("observed_days", "median"),
            avg_time_to_peak=("entry_to_peak_days", "mean"),
            avg_peak_position=("peak_position", "mean"),
            avg_retention_ratio=("retention_ratio", "mean"),
            avg_popularity=("avg_popularity", "mean"),
        )
        .reset_index()
        .sort_values("avg_days", ascending=False)
    )


def stage_distribution(stage_daily: pd.DataFrame) -> pd.DataFrame:
    return (
        stage_daily.groupby("stage")
        .size()
        .reset_index(name="observations")
        .assign(share=lambda d: d["observations"] / d["observations"].sum())
        .sort_values("observations", ascending=False)
    )


def top_lifecycle_table(lifecycle: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    cols = [
        "song",
        "artist",
        "release_form",
        "explicit_label",
        "entry_date",
        "exit_date",
        "observed_days",
        "calendar_span_days",
        "peak_position",
        "entry_to_peak_days",
        "avg_popularity",
    ]
    return lifecycle[cols].head(n).copy()
