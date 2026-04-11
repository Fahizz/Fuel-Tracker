from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class CycleConfig:
    cycle_start: date
    start_odometer: float
    daily_commute_km: float = 0.0
    mileage_kmpl: float = 14.0
    target_cap: float = 19300.0
    price_min: float = 100.0
    price_max: float = 103.0
    tank_max_litres: float = 45.0
    discount_threshold: float = 2500.0
    discount_amount: float = 100.0
    seed: Optional[int] = None
    end_odometer: Optional[float] = None

    def validate(self) -> None:
        if self.mileage_kmpl <= 0:
            raise ValueError("mileage must be > 0")
        if self.daily_commute_km < 0:
            raise ValueError("daily commute km must be >= 0")
        if self.price_min <= 0:
            raise ValueError("fuel price min must be > 0")
        if self.price_max < self.price_min:
            raise ValueError("fuel price max must be >= fuel price min")
        if self.tank_max_litres <= 0:
            raise ValueError("tank max litres must be > 0")
        if self.start_odometer < 0:
            raise ValueError("start odometer must be >= 0")
        if self.end_odometer is not None and self.end_odometer < self.start_odometer:
            raise ValueError("end odometer must be >= start odometer")


@dataclass
class RefuelEntry:
    number: int
    litres: float
    price_per_litre: float
    amount: float
    discount: float
    final_bill: float


@dataclass
class CycleSummary:
    cycle_start: date
    cycle_end: date
    working_days: int
    office_km: float
    extra_weekend_km: float
    total_km: float
    mileage_kmpl: float
    fuel_used_litres: float
    raw_fuel_cost: float
    final_billed_total: float
    start_odometer: float
    end_odometer: float


@dataclass
class PlanResult:
    summary: CycleSummary
    refuels: List[RefuelEntry]
    total_litres: float
    total_raw_cost: float
    total_final_billed: float
