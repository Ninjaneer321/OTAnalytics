from typing import Callable, Iterable, Sequence

from OTAnalytics.domain.event import Event
from OTAnalytics.domain.geometry import RelativeOffsetCoordinate
from OTAnalytics.domain.intersect import IntersectParallelizationStrategy
from OTAnalytics.domain.section import Section
from OTAnalytics.domain.track import Track


class SequentialIntersect(IntersectParallelizationStrategy):
    """Executes the intersection of tracks and sections in sequential order."""

    @property
    def num_processes(self) -> int:
        return 1

    def execute(
        self,
        intersect: Callable[
            [Iterable[Track], Iterable[Section], RelativeOffsetCoordinate],
            Iterable[Event],
        ],
        tasks: Sequence[
            tuple[Iterable[Track], Iterable[Section], RelativeOffsetCoordinate]
        ],
    ) -> list[Event]:
        events: list[Event] = []
        for task in tasks:
            tracks, sections, offset = task
            events.extend(intersect(tracks, sections, offset))
        return events

    def set_num_processes(self, value: int) -> None:
        pass
