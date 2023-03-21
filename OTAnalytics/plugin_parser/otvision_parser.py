import bz2
from datetime import datetime
from pathlib import Path
from typing import Iterable, Tuple

import ujson

import OTAnalytics.plugin_parser.ottrk_dataformat as ottrk_format
from OTAnalytics.application.datastore import (
    SectionParser,
    TrackParser,
    Video,
    VideoParser,
)
from OTAnalytics.domain import section
from OTAnalytics.domain.section import Area, Coordinate, LineSection, Section
from OTAnalytics.domain.track import Detection, Track, TrackId

ENCODING: str = "UTF-8"


def _parse_bz2(path: Path) -> dict:
    """Parse JSON bz2.

    Args:
        path (Path): Path to bz2 JSON.

    Returns:
        dict: The content of the JSON file.
    """
    with bz2.open(path, "rt", encoding=ENCODING) as file:
        return ujson.load(file)


def _write_bz2(data: dict, path: Path) -> None:
    """Parse JSON bz2.

    Args:
        dict: The content of the JSON file.
        path (Path): Path to bz2 JSON.
    """
    with bz2.open(path, "wt", encoding=ENCODING) as file:
        ujson.dump(data, file)


class OttrkParser(TrackParser):
    """Parse an ottrk file and convert its contents to our domain objects namely
    `Tracks`.

    Args:
        TrackParser (TrackParser): extends TrackParser interface.
    """

    def parse(self, ottrk_file: Path) -> list[Track]:
        """Parse ottrk file and convert its content to domain level objects namely
        `Track`s.

        Args:
            ottrk_file (Path): the file to

        Returns:
            list[Track]: the tracks.
        """
        ottrk_dict = _parse_bz2(ottrk_file)
        dets_list: list[dict] = ottrk_dict[ottrk_format.DATA][ottrk_format.DETECTIONS]
        tracks = self._parse_tracks(dets_list)
        return tracks

    def _parse_tracks(self, dets: list[dict]) -> list[Track]:
        """Parse the detections of ottrk located at ottrk["data"]["detections"].

        This method will also sort the detections belonging to a track by their
        occurrence.

        Args:
            dets (list[dict]): the detections in dict format.

        Returns:
            list[Track]: the tracks.
        """
        tracks_dict = self._parse_detections(dets)
        tracks: list[Track] = []
        for track_id, detections in tracks_dict.items():
            sort_dets_by_frame = sorted(detections, key=lambda det: det.occurrence)
            tracks.append(Track(id=track_id, detections=sort_dets_by_frame))
        return tracks

    def _parse_detections(self, det_list: list[dict]) -> dict[TrackId, list[Detection]]:
        """Convert dict to Detection objects and group them by their track id."""
        tracks_dict: dict[TrackId, list[Detection]] = {}
        for det_dict in det_list:
            det = Detection(
                classification=det_dict[ottrk_format.CLASS],
                confidence=det_dict[ottrk_format.CONFIDENCE],
                x=det_dict[ottrk_format.X],
                y=det_dict[ottrk_format.Y],
                w=det_dict[ottrk_format.W],
                h=det_dict[ottrk_format.H],
                frame=det_dict[ottrk_format.FRAME],
                occurrence=datetime.strptime(
                    det_dict[ottrk_format.OCCURRENCE], ottrk_format.DATE_FORMAT
                ),
                input_file_path=det_dict[ottrk_format.INPUT_FILE_PATH],
                interpolated_detection=det_dict[ottrk_format.INTERPOLATED_DETECTION],
                track_id=TrackId(det_dict[ottrk_format.TRACK_ID]),
            )
            if not tracks_dict.get(det.track_id):
                tracks_dict[det.track_id] = []

            tracks_dict[det.track_id].append(det)  # Group detections by track id
        return tracks_dict


class UnknownSectionType(Exception):
    pass


class OtsectionParser(SectionParser):
    def parse(self, file: Path) -> list[Section]:
        content: dict = _parse_bz2(file)
        sections: list[Section] = [
            self._parse_section(entry) for entry in content.get(section.SECTIONS, [])
        ]
        return sections

    def _parse_section(self, entry: dict) -> Section:
        match (entry.get(section.TYPE)):
            case section.LINE:
                return self._parse_line_section(entry)
            case section.AREA:
                return self._parse_area_section(entry)

        raise UnknownSectionType()

    def _parse_line_section(self, data: dict) -> Section:
        section_id = data.get(section.ID, "no-id")
        start = self._parse_coordinate(data.get(section.START, {}))
        end = self._parse_coordinate(data.get(section.END, {}))
        return LineSection(section_id, start, end)

    def _parse_area_section(self, data: dict) -> Section:
        section_id = data.get(section.ID, "no-id")
        coordinates = self._parse_coordinates(data)
        return Area(section_id, coordinates)

    def _parse_coordinates(self, data: dict) -> list[Coordinate]:
        return [
            self._parse_coordinate(entry) for entry in data.get(section.COORDINATES, [])
        ]

    def _parse_coordinate(self, data: dict) -> Coordinate:
        return Coordinate(
            x=data.get(section.X, 0),
            y=data.get(section.Y, 0),
        )

    def serialize(self, sections: Iterable[Section], file: Path) -> None:
        content = self._serialize(sections)
        _write_bz2(content, file)

    def _serialize(self, sections: Iterable[Section]) -> dict[str, list[dict]]:
        return {section.SECTIONS: [section.to_dict() for section in sections]}


class OttrkVideoParser(VideoParser):
    def parse(self, file: Path) -> Tuple[list[TrackId], list[Video]]:
        return [], []
