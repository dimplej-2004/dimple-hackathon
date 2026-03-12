import csv
import json
import os
from typing import List, Dict, Any

from channels import Channel
from scheduler import Scheduler
from cost_calculator import total_system_cost


TRANSACTIONS_CSV = 'transactions.csv'
OUTPUT_JSON = 'submission.json'


def load_transactions(csv_path: str) -> List[Dict[str, Any]]:
    """Read transactions from a CSV file into a list of dictionaries."""
    transactions: List[Dict[str, Any]] = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile, fieldnames=['tx_id', 'amount', 'arrival_time', 'max_delay', 'priority'])
        for row in reader:
            # convert numeric fields
            transactions.append({
                'tx_id': row['tx_id'],
                'amount': float(row['amount']),
                'arrival_time': int(row['arrival_time']),
                'max_delay': int(row['max_delay']),
                'priority': int(row['priority']),
            })
    return transactions


def build_channels() -> List[Channel]:
    """Construct the three settlement channels described in the spec."""
    return [
        Channel(channel_id='FAST', latency=1, capacity=2, fee=5),
        Channel(channel_id='STANDARD', latency=3, capacity=3, fee=2),
        Channel(channel_id='BULK', latency=6, capacity=5, fee=1),
    ]


def main():
    cwd = os.getcwd()
    csv_path = os.path.join(cwd, TRANSACTIONS_CSV)
    if not os.path.exists(csv_path):
        print(f"transactions.csv not found in {cwd}")
        return

    txs = load_transactions(csv_path)
    channels = build_channels()
    scheduler = Scheduler(channels)
    assignments, total_cost = scheduler.schedule(txs)

    # compute cost using helper (assignments may not include channel fees)
    calc = total_system_cost(txs, assignments)

    output = {
        'assignments': assignments,
        'total_system_cost_estimate': calc,
    }

    with open(os.path.join(cwd, OUTPUT_JSON), 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Written scheduling result to {OUTPUT_JSON}")


if __name__ == '__main__':
    main()
