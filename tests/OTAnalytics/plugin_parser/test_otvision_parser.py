import bz2
from datetime import datetime
from pathlib import Path

import pytest
import ujson

import OTAnalytics.plugin_parser.ottrk_dataformat as ottrk_format
from OTAnalytics.adapter_intersect.intersect import (
    ShapelyIntersectImplementationAdapter,
)
from OTAnalytics.application.eventlist import SectionActionDetector
from OTAnalytics.domain import geometry, section
from OTAnalytics.domain.event import EVENT_LIST, Event, EventType, SectionEventBuilder
from OTAnalytics.domain.geometry import (
    DirectionVector2D,
    ImageCoordinate,
    RelativeOffsetCoordinate,
)
from OTAnalytics.domain.intersect import IntersectBySplittingTrackLine
from OTAnalytics.domain.section import Area, Coordinate, LineSection, Section, SectionId
from OTAnalytics.domain.track import (
    CalculateTrackClassificationByMaxConfidence,
    Detection,
    Track,
    TrackId,
)
from OTAnalytics.plugin_intersect.intersect import ShapelyIntersector
from OTAnalytics.plugin_parser.otvision_parser import (
    InvalidSectionData,
    OtEventListParser,
    OtsectionParser,
    OttrkParser,
    _parse_bz2,
    _write_bz2,
)


@pytest.fixture
def ottrk_sample(test_data_dir: Path) -> Path:
    return test_data_dir / "Sample_FR20_2020-01-01_00-00-00.ottrk"


@pytest.fixture
def sample_track_det_1() -> Detection:
    return Detection(
        classification="car",
        confidence=0.8448739051818848,
        x=153.6923828125,
        y=136.2128448486328,
        w=76.55817413330078,
        h=46.49921417236328,
        frame=1,
        occurrence=datetime.strptime(
            "2020-01-01 00:00:00.000000", ottrk_format.DATE_FORMAT
        ),
        input_file_path=Path(
            "test/data/Testvideo_Cars-Cyclist_FR20_2020-01-01_00-00-00.otdet"
        ),
        interpolated_detection=False,
        track_id=TrackId(1),
    )


@pytest.fixture
def sample_track_det_1_dict() -> dict:
    return {
        "class": "car",
        "confidence": 0.8448739051818848,
        "x": 153.6923828125,
        "y": 136.2128448486328,
        "w": 76.55817413330078,
        "h": 46.49921417236328,
        "frame": 1,
        "occurrence": "2020-01-01 00:00:00.000000",
        "input_file_path": "test/data/Testvideo_Cars-Cyclist_FR20_2020-01-01_00-00-00.otdet",  # noqa
        "interpolated-detection": False,
        "first": True,
        "finished": False,
        "track-id": 1,
    }


@pytest.fixture
def sample_track_det_2() -> Detection:
    return Detection(
        classification="car",
        confidence=0.8319828510284424,
        x=155.19091796875,
        y=136.7307891845703,
        w=77.07390594482422,
        h=46.8974609375,
        frame=2,
        occurrence=datetime.strptime(
            "2020-01-01 00:00:00.050000", ottrk_format.DATE_FORMAT
        ),
        input_file_path=Path(
            "test/data/Testvideo_Cars-Cyclist_FR20_2020-01-01_00-00-00.otdet"
        ),
        interpolated_detection=False,
        track_id=TrackId(1),
    )


@pytest.fixture
def sample_track_det_2_dict() -> dict:
    return {
        "class": "car",
        "confidence": 0.8319828510284424,
        "x": 155.19091796875,
        "y": 136.7307891845703,
        "w": 77.07390594482422,
        "h": 46.8974609375,
        "frame": 2,
        "occurrence": "2020-01-01 00:00:00.050000",
        "input_file_path": "test/data/Testvideo_Cars-Cyclist_FR20_2020-01-01_00-00-00.otdet",  # noqa
        "interpolated-detection": False,
        "first": False,
        "finished": False,
        "track-id": 1,
    }


@pytest.fixture
def sample_track_det_3() -> Detection:
    return Detection(
        classification="car",
        confidence=0.829952597618103,
        x=158.3513641357422,
        y=137.06912231445312,
        w=75.2576904296875,
        h=49.759117126464844,
        frame=3,
        occurrence=datetime.strptime(
            "2020-01-01 00:00:00.100000", ottrk_format.DATE_FORMAT
        ),
        input_file_path=Path(
            "test/data/Testvideo_Cars-Cyclist_FR20_2020-01-01_00-00-00.otdet"
        ),
        interpolated_detection=False,
        track_id=TrackId(1),
    )


@pytest.fixture
def sample_track_det_3_dict() -> dict:
    return {
        "class": "car",
        "confidence": 0.829952597618103,
        "x": 158.3513641357422,
        "y": 137.06912231445312,
        "w": 75.2576904296875,
        "h": 49.759117126464844,
        "frame": 3,
        "occurrence": "2020-01-01 00:00:00.100000",
        "input_file_path": "test/data/Testvideo_Cars-Cyclist_FR20_2020-01-01_00-00-00.otdet",  # noqa
        "interpolated-detection": False,
        "first": False,
        "finished": False,
        "track-id": 1,
    }


@pytest.fixture
def expected_sample_tracks(
    sample_track_det_1: Detection,
    sample_track_det_2: Detection,
    sample_track_det_3: Detection,
) -> list[Track]:
    return [
        Track(
            id=TrackId(1),
            classification="car",
            detections=[
                sample_track_det_1,
                sample_track_det_2,
                sample_track_det_3,
            ],
        )
    ]


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


class TestOttrkParser:
    ottrk_parser: OttrkParser = OttrkParser(
        CalculateTrackClassificationByMaxConfidence()
    )

    def test_parse_whole_ottrk(self, ottrk_path: Path) -> None:
        self.ottrk_parser.parse(ottrk_path)

    def test_parse_ottrk_sample(
        self, ottrk_sample: Path, expected_sample_tracks: list[Track]
    ) -> None:
        result_tracks = self.ottrk_parser.parse(ottrk_sample)

        assert result_tracks == expected_sample_tracks

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
        sample_track_det_1: Detection,
        sample_track_det_2: Detection,
        sample_track_det_3: Detection,
        sample_track_det_1_dict: dict,
        sample_track_det_2_dict: dict,
        sample_track_det_3_dict: dict,
    ) -> None:
        result_sorted = self.ottrk_parser._parse_detections(
            [sample_track_det_1_dict, sample_track_det_2_dict, sample_track_det_3_dict]
        )
        result_unsorted = self.ottrk_parser._parse_detections(
            [sample_track_det_3_dict, sample_track_det_1_dict, sample_track_det_2_dict]
        )

        expected_sorted = {
            TrackId(1): [sample_track_det_1, sample_track_det_2, sample_track_det_3]
        }
        expected_unsorted = {
            TrackId(1): [sample_track_det_3, sample_track_det_1, sample_track_det_2]
        }

        assert expected_sorted == result_sorted
        assert expected_unsorted == result_unsorted

    def test_parse_tracks(
        self,
        sample_track_det_1: Detection,
        sample_track_det_2: Detection,
        sample_track_det_3: Detection,
        sample_track_det_1_dict: dict,
        sample_track_det_2_dict: dict,
        sample_track_det_3_dict: dict,
    ) -> None:
        result_sorted_tracks = self.ottrk_parser._parse_tracks(
            [sample_track_det_1_dict, sample_track_det_2_dict, sample_track_det_3_dict]
        )
        result_unsorted_tracks = self.ottrk_parser._parse_tracks(
            [sample_track_det_3_dict, sample_track_det_1_dict, sample_track_det_2_dict]
        )

        expected_sorted = [
            Track(
                id=TrackId(1),
                classification="car",
                detections=[sample_track_det_1, sample_track_det_2, sample_track_det_3],
            )
        ]

        assert expected_sorted == result_sorted_tracks
        assert expected_sorted == result_unsorted_tracks

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
            start=first_coordinate,
            end=second_coordinate,
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
            InvalidSectionData, parser._parse_section, {section.TYPE: section.LINE}
        )

    def test_convert_section(self) -> None:
        some_section: Section = LineSection(
            id=SectionId("some"),
            relative_offset_coordinates={
                EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
            },
            plugin_data={},
            start=Coordinate(0, 0),
            end=Coordinate(1, 1),
        )
        other_section: Section = LineSection(
            id=SectionId("other"),
            relative_offset_coordinates={
                EventType.SECTION_ENTER: RelativeOffsetCoordinate(0, 0)
            },
            plugin_data={},
            start=Coordinate(1, 0),
            end=Coordinate(0, 1),
        )
        sections = [some_section, other_section]
        parser = OtsectionParser()

        content = parser._convert(sections)

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
            start=start,
            end=end,
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
                    section.START: {
                        geometry.X: 0,
                        geometry.Y: 0,
                    },
                    section.END: {
                        geometry.X: 1,
                        geometry.Y: 1,
                    },
                }
            ]
        }
        save_path = test_data_tmp_dir / "sections.otflow"
        _write_bz2(section_data, save_path)

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
            start=start,
            end=end,
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
                    section.START: {
                        geometry.X: 0,
                        geometry.Y: 0,
                    },
                    section.END: {
                        geometry.X: 1,
                        geometry.Y: 1,
                    },
                    section.PLUGIN_DATA: {"key_1": "some_data", "1": "some_data"},
                }
            ]
        }
        save_path = test_data_tmp_dir / "sections.otflow"
        _write_bz2(section_data, save_path)

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

        event_list_parser = OtEventListParser()
        content = event_list_parser._convert([first_event, second_event])

        assert content == {EVENT_LIST: [first_event.to_dict(), second_event.to_dict()]}

    def test_serialize_events(
        self, tracks: list[Track], sections: list[Section], test_data_tmp_dir: Path
    ) -> None:
        # Setup
        shapely_intersection_adapter = ShapelyIntersectImplementationAdapter(
            ShapelyIntersector()
        )
        line_section = sections[0]

        if isinstance(line_section, LineSection):
            line_section_intersector = IntersectBySplittingTrackLine(
                implementation=shapely_intersection_adapter, line_section=line_section
            )

        section_event_builder = SectionEventBuilder()

        section_action_detector = SectionActionDetector(
            intersector=line_section_intersector,
            section_event_builder=section_event_builder,
        )

        enter_events = section_action_detector.detect_enter_actions(
            sections=[line_section], tracks=tracks
        )

        event_list_parser = OtEventListParser()
        event_list_file = test_data_tmp_dir / "eventlist.json"
        event_list_parser.serialize(enter_events, event_list_file)
        assert event_list_file.exists()
