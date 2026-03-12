from typing import Dict, Any


def compute_delay_penalty(amount: float, delay: int) -> float:
    return 0.001 * amount * delay


def compute_failure_cost(tx: Dict[str, Any]) -> float:
    """Return the penalty when a transaction cannot be scheduled."""
    return 0.5 * tx['amount']


def compute_cost_for_assignment(tx: Dict[str, Any], start_time: int, channel_fee: float) -> float:
    """Return total cost of assigning a transaction to a channel.

    Cost formula:
      channel fee + delay penalty

    (Failure penalty handled separately.)
    """
    delay = start_time - tx['arrival_time']
    return channel_fee + compute_delay_penalty(tx['amount'], delay)


def total_system_cost(
    transactions: Dict[str, Any],
    assignments: Dict[str, Any]
) -> float:
    """Compute the overall system cost given the original transactions and
    the assignment results.

    ``transactions`` should be a list of transaction dicts, and ``assignments``
    a list of dicts with keys ``tx_id``, ``channel_id`` and ``start_time``.

    The total cost is the sum of:
      * channel fee (if assigned)
      * delay penalty
      * failure penalty (if not assigned)
    """
    # build lookup by tx_id for quick access
    tx_map = {tx['tx_id']: tx for tx in transactions}
    total = 0.0
    for a in assignments:
        tx = tx_map.get(a['tx_id'])
        if tx is None:
            continue
        if a['channel_id'] is None or a['start_time'] is None:
            total += compute_failure_cost(tx)
        else:
            total += compute_cost_for_assignment(tx, a['start_time'], a.get('channel_fee', 0))
    return total
