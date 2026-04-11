from __future__ import annotations

import math
import random
from datetime import date
from typing import List, Optional

from .calendar import count_working_days, cycle_dates
from .discount import apply_discount
from .models import CycleConfig, CycleSummary, PlanResult, RefuelEntry


def _round2(v: float) -> float:
    return round(v, 2)


def compute_target_litres(target_cap: float, planning_price: float) -> float:
    """Max litres affordable under the target cap at a given price."""
    return target_cap / planning_price


def compute_target_km(target_litres: float, mileage: float) -> float:
    return target_litres * mileage


def compute_office_km(working_days: int, daily_commute_km: float) -> float:
    return working_days * daily_commute_km


def compute_extra_weekend_km(total_km: float, office_km: float) -> float:
    return max(0.0, total_km - office_km)


def _generate_prices(rng: random.Random, n: int, price_min: float, price_max: float) -> List[float]:
    return [_round2(rng.uniform(price_min, price_max)) for _ in range(n)]


def _allocate_refuels(
    target_litres: float,
    tank_max: float,
    rng: random.Random,
    prices: List[float],
    target_cap: float,
) -> List[RefuelEntry]:
    """Allocate refuel volumes across n refuels, rebalancing the last one."""
    n = len(prices)

    if n == 0:
        return []

    # Preferred range for main refuels
    main_min = 35.0
    main_max = min(44.5, tank_max - 0.5)

    if n == 1:
        vol = min(target_litres, tank_max - 0.01)
        vol = _round2(vol)
        amt = _round2(vol * prices[0])
        disc = apply_discount(amt)
        return [RefuelEntry(1, vol, prices[0], amt, disc, _round2(amt - disc))]

    # Allocate main refuels (all except last)
    main_refuels_count = n - 1
    volumes: List[float] = []

    for i in range(main_refuels_count):
        vol = _round2(rng.uniform(main_min, main_max))
        volumes.append(vol)

    # Last refuel is the balancer
    remaining = target_litres - sum(volumes)

    # If remaining is negative or too large, redistribute
    if remaining < 0:
        # Scale down main refuels proportionally
        excess = sum(volumes) - target_litres
        for i in range(main_refuels_count):
            reduction = excess * (volumes[i] / sum(volumes))
            volumes[i] = _round2(volumes[i] - reduction)
        remaining = _round2(target_litres - sum(volumes))

    if remaining >= tank_max:
        return []  # Signal that we need more refuels

    volumes.append(_round2(remaining))

    # Now compute amounts and check cap
    entries: List[RefuelEntry] = []
    running_cost = 0.0

    for i, (vol, price) in enumerate(zip(volumes, prices)):
        amt = _round2(vol * price)
        running_cost += amt
        entries.append(RefuelEntry(
            number=i + 1,
            litres=vol,
            price_per_litre=price,
            amount=amt,
            discount=0.0,
            final_bill=0.0,
        ))

    # Rebalance last refuel so raw total never exceeds cap.
    # Work backwards through entries if needed.
    for idx in range(len(entries) - 1, -1, -1):
        raw_total = _round2(sum(e.amount for e in entries))
        if raw_total <= target_cap:
            break
        entry = entries[idx]
        overshoot = raw_total - target_cap
        # Floor the litres down to ensure rounding doesn't push us back over
        reduce_litres = overshoot / entry.price_per_litre
        new_litres = entry.litres - reduce_litres
        # Floor to 2 decimals to guarantee we don't exceed cap
        new_litres = math.floor(new_litres * 100) / 100
        entry.litres = max(0.0, new_litres)
        entry.amount = _round2(entry.litres * entry.price_per_litre)

    # Apply discounts
    for e in entries:
        e.discount = apply_discount(e.amount)
        e.final_bill = _round2(e.amount - e.discount)

    return entries


def _try_plan(
    target_litres: float,
    tank_max: float,
    rng: random.Random,
    n_refuels: int,
    price_min: float,
    price_max: float,
    target_cap: float,
) -> Optional[List[RefuelEntry]]:
    prices = _generate_prices(rng, n_refuels, price_min, price_max)
    entries = _allocate_refuels(target_litres, tank_max, rng, prices, target_cap)
    if not entries and n_refuels > 0:
        return None
    # Validate all under tank max
    for e in entries:
        if e.litres > tank_max:
            return None
    return entries


def plan_refuels(
    target_litres: float,
    cfg: CycleConfig,
    rng: random.Random,
) -> List[RefuelEntry]:
    """Plan refuels: try 4 first, fall back to 5."""
    # Save RNG state to retry with same sequence logic
    state = rng.getstate()
    result = _try_plan(target_litres, cfg.tank_max_litres, rng, 4, cfg.price_min, cfg.price_max, cfg.target_cap)
    if result is not None:
        return result
    # Reset and try 5
    rng.setstate(state)
    result = _try_plan(target_litres, cfg.tank_max_litres, rng, 5, cfg.price_min, cfg.price_max, cfg.target_cap)
    if result is not None:
        return result
    raise ValueError("Cannot plan refuels within constraints (target too high for tank/price limits)")


def plan_cycle_spend(cfg: CycleConfig) -> PlanResult:
    """Spend-driven mode: plan cycle to maximize spend up to cap."""
    cfg.validate()
    rng = random.Random(cfg.seed)

    start, end = cycle_dates(cfg.cycle_start)
    working_days = count_working_days(start, end)

    planning_price = (cfg.price_min + cfg.price_max) / 2
    target_litres = compute_target_litres(cfg.target_cap, planning_price)
    target_km = compute_target_km(target_litres, cfg.mileage_kmpl)
    office_km = compute_office_km(working_days, cfg.daily_commute_km)
    extra_km = compute_extra_weekend_km(target_km, office_km)
    total_km = _round2(office_km + extra_km)

    refuels = plan_refuels(target_litres, cfg, rng)

    total_litres = _round2(sum(e.litres for e in refuels))
    total_raw = _round2(sum(e.amount for e in refuels))
    total_final = _round2(sum(e.final_bill for e in refuels))
    fuel_used = total_litres
    end_odometer = _round2(cfg.start_odometer + total_km)

    summary = CycleSummary(
        cycle_start=start,
        cycle_end=end,
        working_days=working_days,
        office_km=_round2(office_km),
        extra_weekend_km=_round2(extra_km),
        total_km=total_km,
        mileage_kmpl=cfg.mileage_kmpl,
        fuel_used_litres=_round2(fuel_used),
        raw_fuel_cost=total_raw,
        final_billed_total=total_final,
        start_odometer=cfg.start_odometer,
        end_odometer=end_odometer,
    )

    return PlanResult(
        summary=summary,
        refuels=refuels,
        total_litres=total_litres,
        total_raw_cost=total_raw,
        total_final_billed=total_final,
    )


def plan_cycle_odometer(cfg: CycleConfig) -> PlanResult:
    """Odometer-driven mode: plan based on start/end odometer."""
    cfg.validate()
    if cfg.end_odometer is None:
        raise ValueError("end_odometer is required for odometer-driven mode")

    rng = random.Random(cfg.seed)

    start, end = cycle_dates(cfg.cycle_start)
    total_km = _round2(cfg.end_odometer - cfg.start_odometer)
    fuel_used = _round2(total_km / cfg.mileage_kmpl)

    # In odometer mode, target_litres = fuel_used
    target_litres = fuel_used

    refuels = plan_refuels(target_litres, cfg, rng)

    total_litres = _round2(sum(e.litres for e in refuels))
    total_raw = _round2(sum(e.amount for e in refuels))
    total_final = _round2(sum(e.final_bill for e in refuels))

    working_days = count_working_days(start, end)
    office_km = compute_office_km(working_days, cfg.daily_commute_km)
    extra_km = compute_extra_weekend_km(total_km, office_km)

    summary = CycleSummary(
        cycle_start=start,
        cycle_end=end,
        working_days=working_days,
        office_km=_round2(office_km),
        extra_weekend_km=_round2(extra_km),
        total_km=total_km,
        mileage_kmpl=cfg.mileage_kmpl,
        fuel_used_litres=_round2(fuel_used),
        raw_fuel_cost=total_raw,
        final_billed_total=total_final,
        start_odometer=cfg.start_odometer,
        end_odometer=cfg.end_odometer,
    )

    return PlanResult(
        summary=summary,
        refuels=refuels,
        total_litres=total_litres,
        total_raw_cost=total_raw,
        total_final_billed=total_final,
    )
