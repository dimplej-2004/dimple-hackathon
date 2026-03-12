import csv
import json
import os
import random
from typing import List, Dict, Any, Optional, Tuple

from channels import Channel


TRANSACTIONS_CSV = 'transactions.csv'
OUTPUT_JSON = 'submission.json'


from typing import Union, TextIO


def load_transactions(csv_input: Union[str, TextIO]) -> List[Dict[str, Any]]:
    """Read transactions from a CSV file path or file-like object.

    Accepts either a filesystem path or an object with a ``read()`` method
    (e.g. io.StringIO or a Streamlit UploadedFile).

    The CSV is expected to have a header row which is ignored automatically.
    """
    transactions: List[Dict[str, Any]] = []
    close_after = False
    if isinstance(csv_input, str):
        csvfile = open(csv_input, newline='')
        close_after = True
    else:
        csvfile = csv_input  # assume file-like

    reader = csv.DictReader(csvfile)
    for row in reader:
        # skip invalid rows
        try:
            transactions.append({
                'tx_id': row['tx_id'],
                'amount': float(row['amount']),
                'arrival_time': int(row['arrival_time']),
                'max_delay': int(row['max_delay']),
                'priority': int(row['priority']),
            })
        except Exception:
            # header or malformed row, ignore
            continue

    if close_after:
        csvfile.close()

    return transactions


def save_results(output_path: str, assignments: List[Dict[str, Any]], metrics: Dict[str, Any]) -> None:
    """Dump assignments and metrics to JSON."""
    output = {
        'assignments': assignments,
        'metrics': metrics,
    }
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)


def build_channels(
    outage_config: Optional[Dict[str, List[Tuple[int, int]]]] = None,
) -> List[Channel]:
    """Create standard channels, applying outages if provided.

    outage_config example:
        {'FAST': [(50,60)], 'STANDARD': [], 'BULK': [(10,20), (30,40)]}
    """
    channels = [
        Channel(channel_id='FAST', latency=1, capacity=2, fee=5),
        Channel(channel_id='STANDARD', latency=3, capacity=3, fee=2),
        Channel(channel_id='BULK', latency=6, capacity=5, fee=1),
    ]
    if outage_config:
        for ch in channels:
            if ch.channel_id in outage_config:
                ch.outages = outage_config[ch.channel_id]
    return channels


def generate_scenario(scenario: str, count: int = 100) -> List[Dict[str, Any]]:
    """Return a list of synthetic transactions based on the scenario type."""
    txs: List[Dict[str, Any]] = []
    for i in range(count):
        if scenario == 'normal':
            arrival = random.randint(0, 100)
            amount = random.uniform(100, 5000)
            max_delay = random.randint(5, 30)
            priority = random.randint(1, 5)
        elif scenario == 'peak':
            arrival = random.randint(0, 20)  # burst near start
            amount = random.uniform(100, 2000)
            max_delay = random.randint(1, 10)
            priority = random.randint(1, 5)
        elif scenario == 'emergency':
            arrival = random.randint(0, 100)
            amount = random.uniform(500, 10000)
            max_delay = random.randint(0, 5)
            priority = random.randint(4, 5)
        elif scenario == 'large_value':
            arrival = random.randint(0, 100)
            amount = random.uniform(10000, 100000)
            max_delay = random.randint(5, 50)
            priority = random.randint(1, 3)
        else:
            # default random
            arrival = random.randint(0, 100)
            amount = random.uniform(100, 10000)
            max_delay = random.randint(1, 30)
            priority = random.randint(1, 5)
        txs.append({
            'tx_id': f"TX{i+1}",
            'amount': amount,
            'arrival_time': arrival,
            'max_delay': max_delay,
            'priority': priority,
        })
    return txs
