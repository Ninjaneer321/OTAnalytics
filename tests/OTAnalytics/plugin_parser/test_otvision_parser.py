import bz2
from datetime import datetime
from pathlib import Path
from typing import Sequence
from unittest.mock import Mock, call

import pytest
import ujson

from OTAnalytics import version
from OTAnalytics.application.datastore import OtConfig, SectionParser, VideoParser
from OTAnalytics.application.eventlist import SectionActionDetector
from OTAnalytics.domain import geometry, section, video
from OTAnalytics.domain.event import EVENT_LIST, Event, EventType, SectionEventBuilder
from OTAnalytics.domain.geometry import (
    DirectionVector2D,
    ImageCoordinate,
    RelativeOffsetCoordinate,
)
from OTAnalytics.domain.intersect import (
    IntersectBySplittingTrackLine,
    IntersectImplementation,
)
from OTAnalytics.domain.section import (
    SECTIONS,
    Area,
    Coordinate,
    LineSection,
    Section,
    SectionId,
)
from OTAnalytics.domain.track import (
    CalculateTrackClassificationByMaxConfidence,
    Detection,
    Track,
    TrackClassificationCalculator,
    TrackId,
    TrackRepository,
)
from OTAnalytics.domain.video import Video
from OTAnalytics.plugin_parser import dataformat_versions, ottrk_dataformat
from OTAnalytics.plugin_parser.otvision_parser import (
    EVENT_FORMAT_VERSION,
    METADATA,
    NAME,
    PROJECT,
    SECTION_FORMAT_VERSION,
    VERSION,
    InvalidSectionData,
    OtConfigParser,
    OtEventListParser,
    OtsectionParser,
    OttrkFormatFixer,
    OttrkParser,
    _parse,
    _parse_bz2,
    _write_bz2,
    _write_json,
)
from tests.conftest import TrackBuilder


@pytest.fixture
def track_builder_setup_with_sample_data(track_builder: TrackBuilder) -> TrackBuilder:
    return append_sample_data(track_builder, frame_offset=0, microsecond_offset=0)


def append_sample_data(
    track_builder: TrackBuilder,
    frame_offset: int = 0,
    microsecond_offset: int = 0,
) -> TrackBuilder:
    track_builder.add_frame(frame_offset + 1)
    track_builder.add_microsecond(microsecond_offset + 1)
    track_builder.append_detection()

    track_builder.add_frame(frame_offset + 2)
    track_builder.add_microsecond(microsecond_offset + 2)
    track_builder.append_detection()

    track_builder.add_frame(frame_offset + 3)
    track_builder.add_microsecond(microsecond_offset + 3)
    track_builder.append_detection()

    track_builder.add_frame(frame_offset + 4)
    track_builder.add_microsecond(microsecond_offset + 4)
    track_builder.append_detection()

    track_builder.add_frame(frame_offset + 5)
    track_builder.add_microsecond(microsecond_offset + 5)
    track_builder.append_detection()

    return track_builder


@pytest.fixture
def example_json_bz2(test_data_tmp_dir: Path) -> tuple[Path, dict]:
    bz2_json_file = test_data_tmp_dir / "bz2_file.json"
    bz2_json_file.touch()
    content = {"first_name": "John", "last_name": "Doe"}
    with bz2.open(bz2_json_file, "wt", encoding="UTF-8") as out:
        ujson.dump(content, out)
    return bz2_json_file, content


@pytest.fixture
def example_json(test_data_tmp_dir: Path) -> tuple[Path, dict]:
    json_file = test_data_tmp_dir / "file.json"
    json_file.touch()
    content = {"first_name": "John", "last_name": "Doe"}
    with bz2.open(json_file, "wt", encoding="UTF-8") as out:
        ujson.dump(content, out)
    return json_file, content


def mocked_track_repository() -> Mock:
    repository = Mock(spec=TrackRepository)
    repository.get_for.return_value = None
    return repository


def test_parse_compressed_and_uncompressed_section(test_data_tmp_dir: Path) -> None:
    content = {"some": "value", "other": "values"}
    json_file = test_data_tmp_dir / "section.json"
    bzip2_file = test_data_tmp_dir / "section.json.bz2"
    json_file.touch()
    bzip2_file.touch()
    _write_json(content, json_file)
    _write_bz2(content, bzip2_file)
    json_content = _parse(json_file)
    bzip2_content = _parse(bzip2_file)

    assert json_content == content
    assert bzip2_content == content


class TestOttrkFormatFixer:
    def test_no_fixes_in_newest_version(
        self, track_builder_setup_with_sample_data: TrackBuilder
    ) -> None:
        track_builder_setup_with_sample_data.set_otdet_version("1.1")
        content = track_builder_setup_with_sample_data.build_ottrk()
        fixer = OttrkFormatFixer()

        fixed_content = fixer.fix(content)

        assert fixed_content == content

    def test_fix_x_y_coordinates(
        self, track_builder_setup_with_sample_data: TrackBuilder
    ) -> None:
        track_builder_setup_with_sample_data.set_otdet_version("1.0")
        content = track_builder_setup_with_sample_data.build_ottrk()
        input_detections = self.__build_expected_detections(
            track_builder_setup_with_sample_data
        )
        fixer = OttrkFormatFixer()

        fixed_content = fixer.fix(content)

        fixed_detections = fixed_content[ottrk_dataformat.DATA][
            ottrk_dataformat.DETECTIONS
        ]
        assert fixed_detections == input_detections

    def __build_expected_detections(
        self, track_builder_setup_with_sample_data: TrackBuilder
    ) -> list[dict]:
        input_detections = (
            track_builder_setup_with_sample_data.build_serialized_detections()
        )
        for detection in input_detections:
            detection[ottrk_dataformat.X] = -5
            detection[ottrk_dataformat.Y] = -5
        return input_detections


class TestOttrkParser:
    _track_repository = mocked_track_repository()
    ottrk_parser: OttrkParser = OttrkParser(
        CalculateTrackClassificationByMaxConfidence(),
        _track_repository,
    )

    def test_parse_whole_ottrk(self, ottrk_path: Path) -> None:
        # TODO What is the expected result?
        self.ottrk_parser.parse(ottrk_path)

    def test_parse_ottrk_sample(
        self,
        test_data_tmp_dir: Path,
        track_builder_setup_with_sample_data: TrackBuilder,
    ) -> None:
        ottrk_data = track_builder_setup_with_sample_data.build_ottrk()
        ottrk_file = test_data_tmp_dir / "sample_file.ottrk"
        _write_bz2(ottrk_data, ottrk_file)
        result_tracks = self.ottrk_parser.parse(ottrk_file)

        expected_track = track_builder_setup_with_sample_data.build_track()

        assert result_tracks == [expected_track]
        ottrk_file.unlink()

    def test_parse_bz2(self, example_json_bz2: tuple[Path, dict]) -> None:
        example_json_bz2_path, expected_content = example_json_bz2
        result_content = _parse_bz2(example_json_bz2_path)
        assert result_content == expected_content

    def test_parse_bz2_uncompressed_file(self, example_json: tuple[Path, dict]) -> None:
        example_path, expected_content = example_json
        result_content = _parse_bz2(example_path)
        assert result_content == expected_content

    def test_parse_detections_output_has_same_order_as_input(
        self,
        track_builder_setup_with_sample_data: TrackBuilder,
    ) -> None:
        detections: list[
            dict
        ] = track_builder_setup_with_sample_data.build_serialized_detections()

        result_sorted_input = self.ottrk_parser._parse_detections(detections)
        unsorted_detections = [detections[-1], detections[0]] + detections[1:-1]
        result_unsorted_input = self.ottrk_parser._parse_detections(unsorted_detections)

        expected_sorted = {
            TrackId(1): track_builder_setup_with_sample_data.build_detections()
        }

        assert expected_sorted == result_sorted_input
        assert expected_sorted != result_unsorted_input

    def test_parse_tracks(
        self, track_builder_setup_with_sample_data: TrackBuilder
    ) -> None:
        detections: list[
            dict
        ] = track_builder_setup_with_sample_data.build_serialized_detections()

        result_sorted_input = self.ottrk_parser._parse_tracks(detections)
        unsorted_detections = [detections[-1], detections[0]] + detections[1:-1]
        result_unsorted_input = self.ottrk_parser._parse_tracks(unsorted_detections)

        expected_sorted = [track_builder_setup_with_sample_data.build_track()]

        assert expected_sorted == result_sorted_input
        assert expected_sorted == result_unsorted_input

    def test_parse_tracks_merge_with_existing(
        self, track_builder_setup_with_sample_data: TrackBuilder
    ) -> None:
        detections: list[
            dict
        ] = track_builder_setup_with_sample_data.build_serialized_detections()
        deserialized_detections = (
            track_builder_setup_with_sample_data.build_detections()
        )
        existing_track_builder = TrackBuilder()
        append_sample_data(
            existing_track_builder,
            frame_offset=0,
            microsecond_offset=len(detections),
        )
        existing_track = existing_track_builder.build_track()
        merged_classification = "car"
        classificator = Mock(spec=TrackClassificationCalculator)
        classificator.calculate.return_value = merged_classification
        self._track_repository.get_for.return_value = existing_track
        all_detections = deserialized_detections + existing_track.detections
        merged_track = Track(existing_track.id, merged_classification, all_detections)

        result_sorted_input = self.ottrk_parser._parse_tracks(detections)

        expected_sorted = [merged_track]

        assert expected_sorted == result_sorted_input

    def assert_detection_equal(self, d1: Detection, d2: Detection) -> None:
        assert d1.classification == d2.classification
        assert d1.confidence == d2.confidence
        assert d1.x == d2.x
        assert d1.y == d2.y
        assert d1.w == d2.w
        assert d1.h == d2.h
        assert d1.frame == d2.frame
        assert d1.occurrence == d2.occurrence
        assert d1.input_file_path == d2.input_file_path
        assert d1.interpolated_detection == d2.interpolated_detection
        assert d1.track_id == d2.track_id


class TestOtsectionParser:
    def test_parse_section(self, test_data_tmp_dir: Path) -> None:
        first_coordinate = Coordinate(0, 0)
        second_coordinate = Coordinate(1, 1)
        third_coordinate = Coordinate(1, 0)
        line_section: Section = LineSection(
            id=SectionId("some"),
            relative_offset_coordinates={
                EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
            },
            plugin_data={"key_1": "some_data", "key_2": "some_data"},
            coordinates=[first_coordinate, second_coordinate],
        )
        area_section: Section = Area(
            id=SectionId("other"),
            relative_offset_coordinates={
                EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
            },
            plugin_data={"key_1": "some_data", "key_2": "some_data"},
            coordinates=[
                first_coordinate,
                second_coordinate,
                third_coordinate,
                first_coordinate,
            ],
        )
        json_file = test_data_tmp_dir / "section.json"
        json_file.touch()
        sections = [line_section, area_section]
        parser = OtsectionParser()
        parser.serialize(sections, json_file)

        content = parser.parse(json_file)

        assert content == sections

    def test_validate(self) -> None:
        parser = OtsectionParser()
        pytest.raises(
            InvalidSectionData, parser.parse_section, {section.TYPE: section.LINE}
        )

    def test_convert_section(self) -> None:
        some_section: Section = LineSection(
            id=SectionId("some"),
            relative_offset_coordinates={
                EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
            },
            plugin_data={},
            coordinates=[Coordinate(0, 0), Coordinate(1, 1)],
        )
        other_section: Section = LineSection(
            id=SectionId("other"),
            relative_offset_coordinates={
                EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
            },
            plugin_data={},
            coordinates=[Coordinate(1, 0), Coordinate(0, 1)],
        )
        sections = [some_section, other_section]
        parser = OtsectionParser()

        content = parser.convert(sections)

        assert content == {
            section.SECTIONS: [some_section.to_dict(), other_section.to_dict()]
        }

    def test_parse_plugin_data_no_entry(self, test_data_tmp_dir: Path) -> None:
        start = Coordinate(0, 0)
        end = Coordinate(1, 1)
        expected: Section = LineSection(
            id=SectionId("some"),
            relative_offset_coordinates={
                EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
            },
            plugin_data={},
            coordinates=[start, end],
        )

        section_data = {
            section.SECTIONS: [
                {
                    section.ID: "some",
                    section.TYPE: "line",
                    section.RELATIVE_OFFSET_COORDINATES: {
                        EventType.SECTION_ENTER.serialize(): {
                            geometry.X: 0,
                            geometry.Y: 0,
                        }
                    },
                    section.COORDINATES: [
                        {
                            geometry.X: 0,
                            geometry.Y: 0,
                        },
                        {
                            geometry.X: 1,
                            geometry.Y: 1,
                        },
                    ],
                }
            ]
        }
        save_path = test_data_tmp_dir / "sections.otflow"
        _write_json(section_data, save_path)

        parser = OtsectionParser()
        sections = parser.parse(save_path)

        assert sections == [expected]

    def test_parse_plugin_data_with_plugin_data(self, test_data_tmp_dir: Path) -> None:
        start = Coordinate(0, 0)
        end = Coordinate(1, 1)
        expected: Section = LineSection(
            id=SectionId("some"),
            relative_offset_coordinates={
                EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
            },
            plugin_data={"key_1": "some_data", "1": "some_data"},
            coordinates=[start, end],
        )

        section_data = {
            section.SECTIONS: [
                {
                    section.ID: "some",
                    section.TYPE: "line",
                    section.RELATIVE_OFFSET_COORDINATES: {
                        EventType.SECTION_ENTER.serialize(): {
                            geometry.X: 0,
                            geometry.Y: 0,
                        }
                    },
                    section.COORDINATES: [
                        {geometry.X: 0, geometry.Y: 0},
                        {geometry.X: 1, geometry.Y: 1},
                    ],
                    section.PLUGIN_DATA: {"key_1": "some_data", "1": "some_data"},
                }
            ]
        }
        save_path = test_data_tmp_dir / "sections.otflow"
        _write_json(section_data, save_path)

        parser = OtsectionParser()
        sections = parser.parse(save_path)

        assert sections == [expected]


class TestOtEventListParser:
    def test_convert_event(self, test_data_tmp_dir: Path) -> None:
        road_user_id = 1
        road_user_type = "car"
        hostname = "myhostname"
        section_id = SectionId("N")
        direction_vector = DirectionVector2D(1, 0)
        video_name = "my_video_name.mp4"
        first_event = Event(
            road_user_id=road_user_id,
            road_user_type=road_user_type,
            hostname=hostname,
            occurrence=datetime(2022, 1, 1, 0, 0, 0, 0),
            frame_number=1,
            section_id=section_id,
            event_coordinate=ImageCoordinate(0, 0),
            event_type=EventType.SECTION_ENTER,
            direction_vector=direction_vector,
            video_name=video_name,
        )
        second_event = Event(
            road_user_id=road_user_id,
            road_user_type=road_user_type,
            hostname=hostname,
            occurrence=datetime(2022, 1, 1, 0, 0, 0, 10),
            frame_number=2,
            section_id=section_id,
            event_coordinate=ImageCoordinate(10, 0),
            event_type=EventType.SECTION_LEAVE,
            direction_vector=direction_vector,
            video_name=video_name,
        )
        line_section = LineSection(
            id=SectionId("N"),
            relative_offset_coordinates={
                EventType.SECTION_ENTER: RelativeOffsetCoordinate(0.5, 0.5),
                EventType.SECTION_LEAVE: RelativeOffsetCoordinate(0.5, 0.5),
            },
            plugin_data={"foo": "bar"},
            coordinates=[Coordinate(0, 0), Coordinate(1, 0)],
        )
        area_section = Area(
            id=SectionId("S"),
            relative_offset_coordinates={
                EventType.SECTION_ENTER: RelativeOffsetCoordinate(0.5, 0.5),
                EventType.SECTION_LEAVE: RelativeOffsetCoordinate(0.5, 0.5),
            },
            plugin_data={"foo": "bar"},
            coordinates=[
                Coordinate(0, 0),
                Coordinate(0, 10),
                Coordinate(10, 10),
                Coordinate(10, 0),
                Coordinate(0, 0),
            ],
        )
        events = [first_event, second_event]
        sections = [line_section, area_section]

        event_list_parser = OtEventListParser()
        content = event_list_parser._convert(events, sections)

        assert content == {
            METADATA: {
                VERSION: version.__version__,
                SECTION_FORMAT_VERSION: dataformat_versions.otsection_version(),
                EVENT_FORMAT_VERSION: dataformat_versions.otevent_version(),
            },
            SECTIONS: [line_section.to_dict(), area_section.to_dict()],
            EVENT_LIST: [first_event.to_dict(), second_event.to_dict()],
        }

    def test_serialize_events(
        self, tracks: list[Track], sections: list[Section], test_data_tmp_dir: Path
    ) -> None:
        # Setup
        line_section = sections[0]
        shapely_intersection_adapter = Mock(spec=IntersectImplementation)
        shapely_intersection_adapter.split_line_with_line.return_value = []

        if isinstance(line_section, LineSection):
            line_section_intersector = IntersectBySplittingTrackLine(
                implementation=shapely_intersection_adapter, line_section=line_section
            )

        section_event_builder = SectionEventBuilder()

        section_action_detector = SectionActionDetector(
            intersector=line_section_intersector,
            section_event_builder=section_event_builder,
        )

        events = section_action_detector.detect(sections=[line_section], tracks=tracks)

        event_list_parser = OtEventListParser()
        event_list_file = test_data_tmp_dir / "eventlist.json"
        event_list_parser.serialize(events, [line_section], event_list_file)
        assert event_list_file.exists()


class TestOtConfigParser:
    def test_serialize_config(self, test_data_tmp_dir: Path) -> None:
        video_parser = Mock(spec=VideoParser)
        section_parser = Mock(spec=SectionParser)
        config_parser = OtConfigParser(
            video_parser=video_parser,
            section_parser=section_parser,
        )
        name = "My Test Project"
        videos: list[Video] = []
        sections: list[Section] = []
        output = test_data_tmp_dir / "config.otconfig"
        serialized_videos = {"serialized": "videos"}
        serialized_sections = {"serialized": "sections"}
        video_parser.convert.return_value = serialized_videos
        section_parser.convert.return_value = serialized_sections

        config_parser.serialize(
            project_name=name,
            video_files=videos,
            sections=sections,
            file=output,
        )

        serialized_content = _parse(output)
        assert serialized_content == {
            PROJECT: {NAME: name},
            video.VIDEOS: serialized_videos,
            section.SECTIONS: serialized_sections,
        }
        assert video_parser.convert.call_args_list == [
            call(videos, relative_to=test_data_tmp_dir)
        ]
        assert section_parser.convert.call_args_list == [call(sections)]

    def test_parse_config(self, test_data_tmp_dir: Path) -> None:
        video_parser = Mock(spec=VideoParser)
        section_parser = Mock(spec=SectionParser)
        config_parser = OtConfigParser(
            video_parser=video_parser,
            section_parser=section_parser,
        )
        name = "My Test Project"
        videos: Sequence[Video] = ()
        sections: Sequence[Section] = ()
        config_file = test_data_tmp_dir / "config.otconfig"
        serialized_videos = {"serialized": "videos"}
        serialized_sections = {"serialized": "sections"}
        video_parser.convert.return_value = serialized_videos
        section_parser.convert.return_value = serialized_sections
        video_parser.parse_list.return_value = videos
        section_parser.parse_list.return_value = sections

        config_parser.serialize(
            project_name=name,
            video_files=videos,
            sections=sections,
            file=config_file,
        )
        config = config_parser.parse(file=config_file)

        expected_config = OtConfig(project_name=name, videos=videos, sections=sections)
        assert config == expected_config
