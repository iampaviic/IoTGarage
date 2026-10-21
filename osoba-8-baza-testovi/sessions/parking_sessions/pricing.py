"""Pricing rule.

Default ("real") rule agreed for the project:
  * the first 15 minutes are free (grace period)
  * after that every *started* hour of the whole stay costs 1.50 EUR
  * at most 15.00 EUR per started 24 h block

  duration      price
  0:00 - 15:00  0.00
  15:01 - 1:00  1.50
  1:00:01-2:00  3.00
  ...

The "demo" profile multiplies time by 60 so one real minute is billed as one
hour; a two-minute demonstration then produces a visible price.
All arithmetic is done in integer cents.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PricingPolicy:
    free_minutes: int = 15
    price_per_started_hour_cents: int = 150
    daily_cap_cents: Optional[int] = 1500
    time_multiplier: float = 1.0
    currency: str = "EUR"
    name: str = "real"

    @classmethod
    def real(cls) -> "PricingPolicy":
        return cls()

    @classmethod
    def demo(cls) -> "PricingPolicy":
        return cls(time_multiplier=60.0, name="demo")

    @classmethod
    def from_env(cls) -> "PricingPolicy":
        profile = os.environ.get("PRICING_PROFILE", "real").lower()
        if profile == "demo":
            return cls.demo()
        if profile == "real":
            return cls.real()
        raise ValueError("PRICING_PROFILE must be 'real' or 'demo', got %r" % profile)

    def billed_seconds(self, duration_s: float) -> float:
        if duration_s < 0:
            raise ValueError("negative duration")
        return duration_s * self.time_multiplier

    def started_hours(self, duration_s: float) -> int:
        billed = self.billed_seconds(duration_s)
        if billed <= self.free_minutes * 60:
            return 0
        return int(math.ceil(billed / 3600.0))

    def price_cents(self, duration_s: float) -> int:
        hours = self.started_hours(duration_s)
        if hours == 0:
            return 0
        rate = self.price_per_started_hour_cents
        if self.daily_cap_cents is None:
            return hours * rate
        full_days, rest_hours = divmod(hours, 24)
        return full_days * self.daily_cap_cents + min(rest_hours * rate, self.daily_cap_cents)

    def describe(self) -> str:
        text = "prvih %d min besplatno, zatim %.2f %s po zapocetom satu" % (
            self.free_minutes, self.price_per_started_hour_cents / 100.0, self.currency)
        if self.daily_cap_cents is not None:
            text += ", najvise %.2f %s po danu" % (self.daily_cap_cents / 100.0, self.currency)
        if self.time_multiplier != 1.0:
            text += " (DEMO: vrijeme x%g)" % self.time_multiplier
        return text
