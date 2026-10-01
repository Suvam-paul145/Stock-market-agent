from datetime import timedelta
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd

NY = ZoneInfo("America/New_York")


def market_context(now):
    """Regular US equity sessions, including DST, holidays and shortened days."""
    if now.tzinfo is None:
        raise ValueError("An aware cutoff is required")
    calendar = xcals.get_calendar("XNYS", start=(now - timedelta(days=850)).date(),
                                  end=(now + timedelta(days=10)).date())
    schedule = calendar.schedule
    current = pd.Timestamp(now)
    opened = schedule[schedule["open"] <= current]
    # Allow 20 minutes for delayed/corrected daily data before using a completed bar.
    completed = schedule[schedule["close"] + pd.Timedelta(minutes=20) <= current]
    session, closed = opened.index[-1], completed.index[-1]
    session_row = opened.iloc[-1]
    return dict(
        calendar="XNYS regular sessions", calendar_version=xcals.__version__,
        session=session.date().isoformat(), completed_session=closed.date().isoformat(),
        session_open=session_row["open"].isoformat(), session_close=session_row["close"].isoformat(),
        market_open=bool(session_row["open"] <= current < session_row["close"]),
        is_today=session.date() == now.astimezone(NY).date(),
        expected_sessions=[s.date().isoformat() for s in completed.index[-253:]],
        next_open=schedule[schedule["open"] > current].iloc[0]["open"].isoformat(),
    )
