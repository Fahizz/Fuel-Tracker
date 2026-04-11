# Fuel Reimbursement Cycle Planner

A deterministic monthly fuel planning tool for car reimbursement workflows.

## Features

- **Spend-driven mode**: Maximizes fuel spend up to a configurable monthly cap
- **Odometer-driven mode**: Plans refuels based on known start/end odometer readings
- Realistic refuelling patterns (35–44.5L main refuels with a balancing final refuel)
- Per-refuel discount logic (INR 100 off bills above INR 2,500)
- Deterministic output with configurable random seed
- Export to Excel and JSON
- CLI and Streamlit web UI

## Project Structure

```
Fuel tracker/
├── engine/
│   ├── __init__.py
│   ├── models.py       # Data classes (CycleConfig, RefuelEntry, etc.)
│   ├── calendar.py     # Cycle dates, working day count
│   ├── planner.py      # Core planning logic
│   └── discount.py     # Discount calculation
├── tests/
│   └── test_engine.py  # Unit tests
├── app.py              # Streamlit web UI
├── cli.py              # Command-line interface
├── export.py           # Excel and JSON export
├── requirements.txt
└── README.md
```

## Setup

```bash
pip install -r requirements.txt
```

## Usage

### CLI

**Spend-driven mode (default):**

```bash
python cli.py --start-date 2026-04-15 --start-odo 50000 --daily-km 52 --mileage 14 --seed 42
```

**Odometer-driven mode:**

```bash
python cli.py --mode odometer --start-date 2026-04-15 --start-odo 50000 --end-odo 52700 --mileage 14 --seed 42
```

**With export:**

```bash
python cli.py --start-date 2026-04-15 --start-odo 50000 --seed 42 --export-json plan.json --export-excel plan.xlsx
```

### Streamlit Web UI

```bash
streamlit run app.py
```

### Running Tests

```bash
pytest tests/ -v
```

## Business Rules

| Rule | Default |
|------|---------|
| Cycle window | 15th to 14th |
| Commute days | Monday–Friday |
| Monthly cap | INR 19,300 |
| Diesel price range | INR 100–103/L |
| Tank max per refuel | 45L |
| Discount threshold | INR 2,500 per bill |
| Discount amount | INR 100 |
| Preferred refuel count | 4 (5 if needed) |

## Sample Output

```
============================================================
  CYCLE SUMMARY
============================================================
  Cycle:              2026-04-15 to 2026-05-14
  Working Days:       22
  Office Commute KM:  1144.0
  Extra Weekend KM:   1519.61
  Total KM Driven:    2663.61
  Mileage (km/l):     14.0
  Fuel Used (litres): 190.26
  Raw Fuel Cost:      INR 19299.74
  Final Billed Total: INR 18899.74
  Start Odometer:     50000.0
  End Odometer:       52663.61
```
