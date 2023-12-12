from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from OTAnalytics.application.project import Project
from OTAnalytics.domain.flow import Flow
from OTAnalytics.domain.section import Section
from OTAnalytics.domain.video import Video


@dataclass(frozen=True)
class OtConfig:
    project: Project
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
