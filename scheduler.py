from typing import List, Dict, Any, Tuple
from channels import Channel
from cost_calculator import compute_cost_for_assignment, compute_failure_cost


class Scheduler:
    """Greedy scheduler assigning transactions to channels.

    Channels provided should correspond to:
      FAST   latency=1 capacity=2 fee=5
      STANDARD latency=3 capacity=3 fee=2
      BULK   latency=6 capacity=5 fee=1

    Transactions are dicts with keys:
      tx_id, amount, arrival_time, max_delay, priority

    A simple greedy algorithm processes transactions in arrival order
    (higher priority first on ties) and places each on the channel that
    can start the earliest within the allowed delay.  If multiple channels
    tie on start time we pick the one with the lowest fee.
    """

    def __init__(self, channels: List[Channel]):
        self.channels = channels

    def schedule(self, transactions: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], float]:
        ordered = sorted(transactions, key=lambda t: (t['arrival_time'], -t['priority']))
        assignments: List[Dict[str, Any]] = []
        total_cost = 0.0

        for tx in ordered:
            best_option: Dict[str, Any] = None
            best_cost = float('inf')
            chosen_channel: Channel = None

            for ch in self.channels:
                start = ch.earliest_available_start(tx['arrival_time'], tx['max_delay'])
                if start == -1:
                    continue
                cost = compute_cost_for_assignment(tx, start, ch.fee)
                if (
                    best_option is None
                    or start < best_option['start_time']
                    or (start == best_option['start_time'] and cost < best_cost)
                ):
                    best_cost = cost
                    best_option = {
                        'tx_id': tx['tx_id'],
                        'channel_id': ch.channel_id,
                        'start_time': start,
                        'channel_fee': ch.fee,
                    }
                    chosen_channel = ch

            if chosen_channel:
                chosen_channel.add_transaction(best_option['start_time'])
                assignments.append(best_option)
                total_cost += best_cost
            else:
                total_cost += compute_failure_cost(tx)
                assignments.append({
                    'tx_id': tx['tx_id'],
                    'channel_id': None,
                    'start_time': None,
                    'channel_fee': 0,
                })

        return assignments, total_cost

