from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class Channel:
    """Represents a settlement channel with latency, capacity and fee.

    The channel keeps track of scheduled transactions as a list of
    (start_time, end_time) tuples so that we can check capacity at
    any given time.  Primary identifier is ``channel_id`` but a
    convenience ``name`` property is provided for compatibility with
    earlier examples.
    """
    channel_id: str
    latency: int
    capacity: int
    fee: float
    schedule: List[Tuple[int, int]] = field(default_factory=list)
    outages: List[Tuple[int, int]] = field(default_factory=list)

    def __post_init__(self):
        # ensure outages sorted
        self.outages.sort()

    @property
    def name(self) -> str:
        """Alias for ``channel_id`` as requested by the new interface."""
        return self.channel_id

    # simple interface methods for earlier usage patterns
    def can_process(self, current_time: int) -> bool:
        """Return True if there is capacity to start a transaction at
        ``current_time`` (ignores any specific transaction parameters).
        """
        return self._can_schedule_at(current_time)

    def assign(self, start_time: int) -> None:
        """Record a transaction starting at ``start_time``.

        Equivalent to :meth:`add_transaction` in the advanced model.
        """
        self.add_transaction(start_time)

    def earliest_available_start(self, arrival_time: int, max_delay: int) -> int:
        """Return the earliest start time where this channel can process a
        transaction arriving at `arrival_time` within `max_delay`.

        The start time must satisfy:
          start >= arrival_time
          start <= arrival_time + max_delay
        and for the interval [start, start+latency) the number of
        concurrent transactions must be < capacity.

        If no such start exists, return -1.
        """
        # we'll scan from arrival_time to arrival_time+max_delay inclusive
        deadline = arrival_time + max_delay
        for t in range(arrival_time, deadline + 1):
            if self._can_schedule_at(t):
                return t
        return -1

    def _can_schedule_at(self, start: int) -> bool:
        """Check if a transaction can be scheduled starting at `start`.

        We assume the transaction occupies [start, start+latency).
        """
        end = start + self.latency
        # first, cannot schedule if outage intersects the interval
        for o_start, o_end in self.outages:
            if o_start < end and start < o_end:
                return False
        # count concurrent intervals overlapping [start, end)
        concurrent = 0
        for s, e in self.schedule:
            # overlap if s < end and start < e
            if s < end and start < e:
                concurrent += 1
                if concurrent >= self.capacity:
                    return False
        return True

    def add_transaction(self, start: int) -> None:
        """Record a scheduled transaction starting at `start`."""
        self.schedule.append((start, start + self.latency))

    def clone(self) -> "Channel":
        """Return a shallow copy of this channel (schedules and outages duplicated)."""
        return Channel(
            channel_id=self.channel_id,
            latency=self.latency,
            capacity=self.capacity,
            fee=self.fee,
            schedule=list(self.schedule),
            outages=list(self.outages),
        )
