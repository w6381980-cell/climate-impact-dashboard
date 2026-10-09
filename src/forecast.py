import warnings
from datetime import date, timedelta

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from db import get_conn, init_db

warnings.filterwarnings("ignore")

HORIZON = 7        # kitne din aage ka forecast dikhana hai
TEST_DAYS = 7      # backtest mein har baar kitne din chhupane hain
FOLDS = 3          # backtest kitni baar karna hai
Z80 = 1.2816       # 80% interval ke liye

# (metric ka naam, table, column, kitne pichle din use karne hain, minimum 0 chahiye?)
METRICS = [
    ("pm2_5", "daily_air", "pm2_5_mean", 90, True),
    ("temp_mean_c", "daily_weather", "temp_mean_c", 120, False),
]


def load_series(conn, table, col, city, last_n):
    df = pd.read_sql_query(
        f"SELECT date, {col} AS v FROM {table} WHERE city = ? ORDER BY date",
        conn, params=(city,))
    df["date"] = pd.to_datetime(df["date"])
    s = df.set_index("date")["v"].astype(float)
    s = s.asfreq("D").interpolate(limit=3)   # 1-3 din ke chhote gap bhar do
    return s.dropna().tail(last_n)


def fit_forecast(train, steps):
    """Damped-trend exponential smoothing. (point forecast, sigma) lautata hai."""
    m = ExponentialSmoothing(
        train.values, trend="add", damped_trend=True,
        initialization_method="estimated",
    ).fit()
    fc = np.asarray(m.forecast(steps))
    sigma = float(np.std(m.resid, ddof=1))
    return fc, sigma


def naive_forecast(train, steps):
    """Baseline: pichle 7 din ka average hi aage bhi rahega."""
    level = float(train.tail(7).mean())
    sigma = float(train.diff().dropna().tail(30).std())
    return np.full(steps, level), sigma


def backtest(series):
    """Aakhri 3 hafte ko 3 baar chhupa kar model aur baseline ki galti naapo."""
    err_m, err_n = [], []
    for k in range(FOLDS, 0, -1):
        cut = len(series) - k * TEST_DAYS
        if cut < 30:
            continue
        train = series.iloc[:cut]
        test = series.iloc[cut:cut + TEST_DAYS].values
        fm, _ = fit_forecast(train, TEST_DAYS)
        fn, _ = naive_forecast(train, TEST_DAYS)
        err_m.append(np.mean(np.abs(fm - test)))
        err_n.append(np.mean(np.abs(fn - test)))
    if not err_m:
        return None, None, 0
    return float(np.mean(err_m)), float(np.mean(err_n)), len(err_m)


def main():
    init_db()
    today = date.today()
    run_date = today.isoformat()
    n_fc = 0

    with get_conn() as conn:
        cities = [r[0] for r in conn.execute(
            "SELECT DISTINCT city FROM daily_air ORDER BY city")]

        for city in cities:
            for metric, table, col, last_n, non_negative in METRICS:
                try:
                    s = load_series(conn, table, col, city, last_n)
                    if len(s) < 55:
                        print(f"SKIP {city} {metric}: sirf {len(s)} din ka data")
                        continue

                    mae_m, mae_n, folds = backtest(s)
                    use_model = mae_m is not None and mae_m < mae_n
                    method = "damped_trend_ets" if use_model else "naive_7d_mean"

                    # data jahan khatam hua wahan se aaj tak ka gap bhi cover karna hai
                    last_date = s.index[-1].date()
                    gap = max((today - last_date).days - 1, 0)
                    steps = gap + HORIZON
                    fn = fit_forecast if use_model else naive_forecast
                    fc, sigma = fn(s, steps)

                    rows = []
                    for i in range(steps):
                        d = last_date + timedelta(days=i + 1)
                        if d < today:
                            continue    # sirf aaj aur aage ki tareekhen
                        h = i + 1
                        w = Z80 * sigma * np.sqrt(h)
                        yhat, lo, hi = fc[i], fc[i] - w, fc[i] + w
                        if non_negative:
                            yhat, lo, hi = max(yhat, 0), max(lo, 0), max(hi, 0)
                        rows.append((city, metric, d.isoformat(), run_date,
                                     round(float(yhat), 2), round(float(lo), 2),
                                     round(float(hi), 2), method))
                    rows = rows[:HORIZON]

                    conn.executemany(
                        "INSERT OR REPLACE INTO forecasts VALUES (?,?,?,?,?,?,?,?)", rows)
                    conn.execute(
                        "INSERT OR REPLACE INTO forecast_backtest VALUES (?,?,?,?,?,?,?)",
                        (city, metric, run_date,
                         round(mae_m, 2), round(mae_n, 2), folds, method))
                    n_fc += len(rows)
                    print(f"OK   {city:<10} {metric:<12} method={method:<17} "
                          f"MAE model={mae_m:.2f} naive={mae_n:.2f}")
                except Exception as e:
                    print(f"FAIL {city} {metric} -> {e}")

        conn.commit()

        bt = pd.read_sql_query(
            """SELECT metric, chosen_method, COUNT(*) AS n
               FROM forecast_backtest WHERE run_date = ?
               GROUP BY metric, chosen_method""", conn, params=(run_date,))
        sample = pd.read_sql_query(
            """SELECT city, forecast_date, yhat, lower, upper
               FROM forecasts
               WHERE run_date = ? AND metric = 'pm2_5' AND city = 'Delhi'
               ORDER BY forecast_date""", conn, params=(run_date,))

    print(f"\n{n_fc} forecast rows save hui")
    print("\nKaunsa method kitni jagah chuna gaya:\n", bt.to_string(index=False))
    print("\nDelhi PM2.5 forecast (80% range):\n", sample.to_string(index=False))


if __name__ == "__main__":
    main()