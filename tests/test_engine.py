"""Unit tests for the fuel planning engine."""

import pytest
from datetime import date

from engine.calendar import cycle_dates, count_working_days
from engine.discount import apply_discount
from engine.models import CycleConfig
from engine.planner import (
    compute_target_litres,
    compute_target_km,
    compute_office_km,
    compute_extra_weekend_km,
    plan_cycle_spend,
    plan_cycle_odometer,
    plan_refuels,
)
import random


# --- calendar tests ---

class TestCycleDates:
    def test_normal_month(self):
        start, end = cycle_dates(date(2026, 4, 15))
        assert start == date(2026, 4, 15)
        assert end == date(2026, 5, 14)

    def test_december_wraps_year(self):
        start, end = cycle_dates(date(2026, 12, 15))
        assert end == date(2027, 1, 14)

    def test_january(self):
        start, end = cycle_dates(date(2026, 1, 15))
        assert end == date(2026, 2, 14)

    def test_non_15th_raises(self):
        with pytest.raises(ValueError, match="15th"):
            cycle_dates(date(2026, 4, 1))


class TestWorkingDays:
    def test_full_week(self):
        # Mon 2026-04-06 to Fri 2026-04-10 = 5 working days
        assert count_working_days(date(2026, 4, 6), date(2026, 4, 10)) == 5

    def test_weekend_excluded(self):
        # Sat 2026-04-11 to Sun 2026-04-12 = 0 working days
        assert count_working_days(date(2026, 4, 11), date(2026, 4, 12)) == 0

    def test_april_cycle(self):
        # Apr 15 (Wed) to May 14 (Thu) 2026
        days = count_working_days(date(2026, 4, 15), date(2026, 5, 14))
        assert days > 0
        assert days <= 23  # max possible working days in ~30 day span

    def test_single_weekday(self):
        # Monday
        assert count_working_days(date(2026, 4, 6), date(2026, 4, 6)) == 1

    def test_single_weekend(self):
        # Saturday
        assert count_working_days(date(2026, 4, 11), date(2026, 4, 11)) == 0


# --- discount tests ---

class TestDiscount:
    def test_above_threshold(self):
        assert apply_discount(3000.0) == 100.0

    def test_at_threshold(self):
        assert apply_discount(2500.0) == 0.0

    def test_below_threshold(self):
        assert apply_discount(2000.0) == 0.0

    def test_custom_threshold(self):
        assert apply_discount(1500.0, threshold=1000.0, discount=50.0) == 50.0

    def test_just_above(self):
        assert apply_discount(2500.01) == 100.0


# --- pure calculation tests ---

class TestComputations:
    def test_target_litres(self):
        litres = compute_target_litres(19300.0, 101.5)
        assert round(litres, 2) == round(19300.0 / 101.5, 2)

    def test_target_km(self):
        km = compute_target_km(190.0, 14.0)
        assert km == 2660.0

    def test_office_km(self):
        assert compute_office_km(22, 52.0) == 1144.0

    def test_extra_weekend_km_positive(self):
        assert compute_extra_weekend_km(2660.0, 1144.0) == 1516.0

    def test_extra_weekend_km_clamped(self):
        assert compute_extra_weekend_km(1000.0, 1144.0) == 0.0


# --- model validation tests ---

class TestValidation:
    def test_valid_config(self):
        cfg = CycleConfig(cycle_start=date(2026, 4, 15), start_odometer=50000)
        cfg.validate()  # should not raise

    def test_negative_mileage(self):
        cfg = CycleConfig(cycle_start=date(2026, 4, 15), start_odometer=50000, mileage_kmpl=-1)
        with pytest.raises(ValueError, match="mileage"):
            cfg.validate()

    def test_negative_commute(self):
        cfg = CycleConfig(cycle_start=date(2026, 4, 15), start_odometer=50000, daily_commute_km=-5)
        with pytest.raises(ValueError, match="daily commute"):
            cfg.validate()

    def test_price_inverted(self):
        cfg = CycleConfig(cycle_start=date(2026, 4, 15), start_odometer=50000, price_min=105, price_max=100)
        with pytest.raises(ValueError, match="price max"):
            cfg.validate()

    def test_odometer_inverted(self):
        cfg = CycleConfig(cycle_start=date(2026, 4, 15), start_odometer=50000, end_odometer=49000)
        with pytest.raises(ValueError, match="end odometer"):
            cfg.validate()


# --- spend-driven plan tests ---

class TestPlanCycleSpend:
    def test_deterministic_with_seed(self):
        cfg = CycleConfig(
            cycle_start=date(2026, 4, 15),
            start_odometer=50000,
            daily_commute_km=52.0,
            mileage_kmpl=14.0,
            seed=42,
        )
        r1 = plan_cycle_spend(cfg)
        r2 = plan_cycle_spend(cfg)
        assert r1.total_raw_cost == r2.total_raw_cost
        assert r1.total_litres == r2.total_litres
        assert len(r1.refuels) == len(r2.refuels)
        for a, b in zip(r1.refuels, r2.refuels):
            assert a.litres == b.litres
            assert a.price_per_litre == b.price_per_litre

    def test_raw_cost_within_cap(self):
        cfg = CycleConfig(
            cycle_start=date(2026, 4, 15),
            start_odometer=50000,
            daily_commute_km=52.0,
            mileage_kmpl=14.0,
            seed=123,
        )
        result = plan_cycle_spend(cfg)
        assert result.total_raw_cost <= cfg.target_cap

    def test_refuel_count_4_or_5(self):
        cfg = CycleConfig(
            cycle_start=date(2026, 4, 15),
            start_odometer=50000,
            daily_commute_km=52.0,
            mileage_kmpl=14.0,
            seed=42,
        )
        result = plan_cycle_spend(cfg)
        assert len(result.refuels) in (4, 5)

    def test_each_refuel_under_tank_max(self):
        cfg = CycleConfig(
            cycle_start=date(2026, 4, 15),
            start_odometer=50000,
            daily_commute_km=52.0,
            mileage_kmpl=14.0,
            seed=42,
        )
        result = plan_cycle_spend(cfg)
        for r in result.refuels:
            assert r.litres < cfg.tank_max_litres

    def test_discount_applied(self):
        cfg = CycleConfig(
            cycle_start=date(2026, 4, 15),
            start_odometer=50000,
            daily_commute_km=52.0,
            mileage_kmpl=14.0,
            seed=42,
        )
        result = plan_cycle_spend(cfg)
        for r in result.refuels:
            if r.amount > 2500:
                assert r.discount == 100.0
            else:
                assert r.discount == 0.0

    def test_end_odometer(self):
        cfg = CycleConfig(
            cycle_start=date(2026, 4, 15),
            start_odometer=50000,
            daily_commute_km=52.0,
            mileage_kmpl=14.0,
            seed=42,
        )
        result = plan_cycle_spend(cfg)
        assert result.summary.end_odometer > cfg.start_odometer

    def test_totals_match_refuels(self):
        cfg = CycleConfig(
            cycle_start=date(2026, 4, 15),
            start_odometer=50000,
            daily_commute_km=52.0,
            mileage_kmpl=14.0,
            seed=42,
        )
        result = plan_cycle_spend(cfg)
        assert result.total_litres == round(sum(r.litres for r in result.refuels), 2)
        assert result.total_raw_cost == round(sum(r.amount for r in result.refuels), 2)
        assert result.total_final_billed == round(sum(r.final_bill for r in result.refuels), 2)


# --- odometer-driven plan tests ---

class TestPlanCycleOdometer:
    def test_basic_odometer(self):
        cfg = CycleConfig(
            cycle_start=date(2026, 4, 15),
            start_odometer=50000,
            end_odometer=52700,
            daily_commute_km=52.0,
            mileage_kmpl=14.0,
            seed=42,
        )
        result = plan_cycle_odometer(cfg)
        assert result.summary.total_km == 2700.0
        expected_fuel = round(2700.0 / 14.0, 2)
        assert result.summary.fuel_used_litres == expected_fuel

    def test_requires_end_odometer(self):
        cfg = CycleConfig(
            cycle_start=date(2026, 4, 15),
            start_odometer=50000,
            mileage_kmpl=14.0,
        )
        with pytest.raises(ValueError, match="end_odometer"):
            plan_cycle_odometer(cfg)

    def test_deterministic(self):
        cfg = CycleConfig(
            cycle_start=date(2026, 4, 15),
            start_odometer=50000,
            end_odometer=52700,
            mileage_kmpl=14.0,
            seed=99,
        )
        r1 = plan_cycle_odometer(cfg)
        r2 = plan_cycle_odometer(cfg)
        assert r1.total_raw_cost == r2.total_raw_cost


# --- refuel planning edge cases ---

class TestRefuelPlanning:
    def test_small_target_uses_4_refuels(self):
        cfg = CycleConfig(
            cycle_start=date(2026, 4, 15),
            start_odometer=50000,
            target_cap=15000.0,
            seed=42,
        )
        rng = random.Random(42)
        target_litres = compute_target_litres(15000.0, 101.5)
        refuels = plan_refuels(target_litres, cfg, rng)
        assert len(refuels) == 4

    def test_multiple_seeds_all_valid(self):
        for s in range(10):
            cfg = CycleConfig(
                cycle_start=date(2026, 4, 15),
                start_odometer=50000,
                daily_commute_km=52.0,
                mileage_kmpl=14.0,
                seed=s,
            )
            result = plan_cycle_spend(cfg)
            assert result.total_raw_cost <= cfg.target_cap
            for r in result.refuels:
                assert r.litres < cfg.tank_max_litres
            assert len(result.refuels) in (4, 5)
