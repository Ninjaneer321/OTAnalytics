from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from OTAnalytics.application.project import Project
from OTAnalytics.domain.flow import Flow
from OTAnalytics.domain.section import Section
from OTAnalytics.domain.video import Video


@dataclass(frozen=True)
class ExportConfig:
    save_name: str
    save_suffix: str
    event_format: str
    count_intervals: set[int]


@dataclass(frozen=True)
class AnalysisConfig:
    do_events: bool
    do_counting: bool
    otflow_file: Path
    track_files: set[Path]
    export_config: ExportConfig
    num_processes: int
    logfile: Path
    debug: bool


@dataclass(frozen=True)
class OtConfig:
    project: Project
    analysis: AnalysisConfig
    videos: Sequence[Video]
    sections: Sequence[Section]
    flows: Sequence[Flow]


class ConfigParser(ABC):
    """
    Serialize and parse config files generated by OTConfig
    """

    @abstractmethod
    def parse(
        self,
        file: Path,
    ) -> OtConfig:
        pass

    @abstractmethod
    def serialize(
        self,
        project: Project,
        video_files: Iterable[Video],
        sections: Iterable[Section],
        flows: Iterable[Flow],
        file: Path,
    ) -> None:
        pass
