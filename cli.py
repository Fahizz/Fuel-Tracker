#!/usr/bin/env python3
"""CLI for Fuel Reimbursement Cycle Planner."""

import argparse
import sys
from datetime import date

from engine.models import CycleConfig
from engine.planner import plan_cycle_spend, plan_cycle_odometer
from export import export_json, export_excel


def parse_date(s: str) -> date:
    return date.fromisoformat(s)


def print_result(result):
    s = result.summary
    print("\n" + "=" * 60)
    print("  CYCLE SUMMARY")
    print("=" * 60)
    print(f"  Cycle:              {s.cycle_start} to {s.cycle_end}")
    print(f"  Working Days:       {s.working_days}")
    print(f"  Office Commute KM:  {s.office_km}")
    print(f"  Extra Weekend KM:   {s.extra_weekend_km}")
    print(f"  Total KM Driven:    {s.total_km}")
    print(f"  Mileage (km/l):     {s.mileage_kmpl}")
    print(f"  Fuel Used (litres): {s.fuel_used_litres}")
    print(f"  Raw Fuel Cost:      INR {s.raw_fuel_cost}")
    print(f"  Final Billed Total: INR {s.final_billed_total}")
    print(f"  Start Odometer:     {s.start_odometer}")
    print(f"  End Odometer:       {s.end_odometer}")

    print("\n" + "-" * 60)
    print("  REFUELLING BREAKDOWN")
    print("-" * 60)
    print(f"  {'#':<4} {'Litres':>8} {'Price/L':>9} {'Amount':>10} {'Discount':>10} {'Final':>10}")
    print("  " + "-" * 53)
    for r in result.refuels:
        print(f"  {r.number:<4} {r.litres:>8.2f} {r.price_per_litre:>9.2f} {r.amount:>10.2f} {r.discount:>10.2f} {r.final_bill:>10.2f}")

    print("  " + "-" * 53)
    total_disc = round(sum(r.discount for r in result.refuels), 2)
    print(f"  {'TOT':<4} {result.total_litres:>8.2f} {'':>9} {result.total_raw_cost:>10.2f} {total_disc:>10.2f} {result.total_final_billed:>10.2f}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Fuel Reimbursement Cycle Planner")
    parser.add_argument("--mode", choices=["spend", "odometer"], default="spend", help="Planning mode")
    parser.add_argument("--start-date", required=True, type=parse_date, help="Cycle start date (YYYY-MM-DD, must be 15th)")
    parser.add_argument("--start-odo", required=True, type=float, help="Start odometer reading")
    parser.add_argument("--end-odo", type=float, help="End odometer (required for odometer mode)")
    parser.add_argument("--daily-km", type=float, default=52.0, help="Daily office commute km")
    parser.add_argument("--mileage", type=float, default=14.0, help="Mileage in km/l")
    parser.add_argument("--cap", type=float, default=19300.0, help="Monthly target cap in INR")
    parser.add_argument("--price-min", type=float, default=100.0, help="Min diesel price per litre")
    parser.add_argument("--price-max", type=float, default=103.0, help="Max diesel price per litre")
    parser.add_argument("--seed", type=int, help="Random seed for determinism")
    parser.add_argument("--export-json", type=str, help="Export to JSON file")
    parser.add_argument("--export-excel", type=str, help="Export to Excel file")

    args = parser.parse_args()

    cfg = CycleConfig(
        cycle_start=args.start_date,
        start_odometer=args.start_odo,
        daily_commute_km=args.daily_km,
        mileage_kmpl=args.mileage,
        target_cap=args.cap,
        price_min=args.price_min,
        price_max=args.price_max,
        seed=args.seed,
        end_odometer=args.end_odo,
    )

    try:
        if args.mode == "spend":
            result = plan_cycle_spend(cfg)
        else:
            result = plan_cycle_odometer(cfg)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print_result(result)

    if args.export_json:
        export_json(result, args.export_json)
        print(f"\nExported JSON to {args.export_json}")

    if args.export_excel:
        export_excel(result, args.export_excel)
        print(f"Exported Excel to {args.export_excel}")


if __name__ == "__main__":
    main()
