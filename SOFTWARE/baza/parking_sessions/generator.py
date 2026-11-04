"""Generate realistic, fictional test sessions.

Used for: filling the analytics dashboard during development, load-testing
queries, and unit tests. Plates are random but follow the Croatian format
(city code, 3-4 digits, 1-2 letters) and never belong to real people on
purpose - do not replace them with real registrations.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from parking_sessions.models import Session
from parking_sessions.pricing import PricingPolicy

CITY_CODES = ["ZG", "ST", "RI", "OS", "ZD", "PU", "VŽ", "KA", "SB", "DU", "ŠI", "BJ", "KC", "SK"]
SUFFIX_LETTERS = "ABCDEFGHIJKLMNOPRSTUVZ"

# relative arrival weight per local hour (morning and afternoon peaks)
HOUR_WEIGHTS = [0.2, 0.1, 0.1, 0.1, 0.2, 0.5, 1.5, 4.0, 6.0, 4.0, 3.0, 3.0,
                3.5, 3.0, 2.5, 3.0, 4.5, 5.0, 3.0, 2.0, 1.5, 1.0, 0.6, 0.3]


def random_plate(rng: random.Random) -> str:
    city = rng.choice(CITY_CODES).translate(str.maketrans("ČĆŠŽĐ", "CCSZD"))
    digits = "".join(rng.choice("0123456789") for _ in range(rng.choice((3, 4))))
    letters = "".join(rng.choice(SUFFIX_LETTERS) for _ in range(rng.choice((1, 2))))
    return city + digits + letters


def generate_sessions(
    days: int = 14,
    per_day: int = 40,
    end: Optional[datetime] = None,
    pricing: Optional[PricingPolicy] = None,
    seed: Optional[int] = 42,
    plate_pool: int = 60,
    active_at_end: int = 2,
    spot_count: int = 6,
) -> List[Session]:
    rng = random.Random(seed)
    pricing = pricing or PricingPolicy()
    end = (end or datetime.now(timezone.utc)).replace(microsecond=0)
    start = end - timedelta(days=days)
    plates = sorted({random_plate(rng) for _ in range(plate_pool * 2)})[:plate_pool]
    busy_until = {}  # plate -> datetime the car leaves (no overlapping stays)
    sessions: List[Session] = []
    counter = 0

    for day in range(days):
        day_start = (start + timedelta(days=day)).replace(hour=0, minute=0, second=0)
        n = max(1, int(rng.gauss(per_day, per_day * 0.15)))
        for _ in range(n):
            hour = rng.choices(range(24), weights=HOUR_WEIGHTS)[0]
            entry = day_start + timedelta(hours=hour, seconds=rng.randrange(3600))
            if entry >= end:
                continue
            # log-normal stay: median ~ 1.5 h, long tail up to a few hours
            duration = int(min(10 * 3600, max(120, rng.lognormvariate(math.log(5400), 0.8))))
            plate = rng.choice(plates)
            if busy_until.get(plate, start) > entry:
                continue
            exit_time = entry + timedelta(seconds=duration)
            counter += 1
            sid = "S-%s-G%04d" % (entry.strftime("%Y%m%d-%H%M%S"), counter)
            manual = rng.random() < 0.04
            if exit_time >= end:
                continue  # would still be inside; active ones are added below
            busy_until[plate] = exit_time
            sessions.append(Session(
                id=sid, plate=plate, status="CLOSED", entry_time=entry, exit_time=exit_time,
                duration_s=duration, price_cents=pricing.price_cents(duration), currency=pricing.currency,
                entry_confidence=round(rng.uniform(0.86, 0.99), 2) if not manual else round(rng.uniform(0.3, 0.8), 2),
                exit_confidence=round(rng.uniform(0.86, 0.99), 2),
                entry_mode="MANUAL" if manual else "AUTO", exit_mode="AUTO",
                spot_id="P%02d" % rng.randint(1, spot_count), note="generated",
            ))

    free_plates = [p for p in plates if busy_until.get(p, start) <= end - timedelta(minutes=30)]
    for i, plate in enumerate(free_plates[:active_at_end]):
        entry = end - timedelta(minutes=rng.randint(5, 25))
        sessions.append(Session(
            id="S-%s-GA%03d" % (entry.strftime("%Y%m%d-%H%M%S"), i), plate=plate, status="ACTIVE",
            entry_time=entry, currency=pricing.currency, entry_confidence=0.93, entry_mode="AUTO",
            spot_id="P%02d" % (i + 1), note="generated",
        ))
    sessions.sort(key=lambda s: s.entry_time)
    return sessions
