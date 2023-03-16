from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

import OTAnalytics.plugin_parser.ottrk_dataformat as ottrk_format
from OTAnalytics.domain.track import Detection, Track, TrackId, TrackRepository


@pytest.fixture
def valid_detection_dict() -> dict:
    return {
        ottrk_format.CLASS: "car",
        ottrk_format.CONFIDENCE: 0.5,
        ottrk_format.X: 0.0,
        ottrk_format.Y: 0.0,
        ottrk_format.W: 0.0,
        ottrk_format.H: 0.0,
        ottrk_format.FRAME: 1,
        ottrk_format.OCCURRENCE: datetime(2022, 1, 1, 1, 0, 0),
        ottrk_format.INPUT_FILE_PATH: Path("path/to/file.otdet"),
        ottrk_format.INTERPOLATED_DETECTION: False,
        "track_id": TrackId(1),
    }


class TestDetection:
    @pytest.mark.parametrize(
        "confidence,x,y,w,h,frame,track_id",
        [
            (-1, 1, 1, 1, 1, 1, 1),
            (2, 1, 1, 1, 1, 1, 1),
            (0, -0.0001, 1, 1, 1, 1, 1),
            (0, -1, -0.0001, 1, 1, 1, 1),
            (0, 2, 1, 1, -0.0001, 1, 1),
            (0, 2, 1, 1, 1, 0, 1),
            (0, 1, 1, 1, 1, 1, -1),
            (0, 1, 1, 1, 1, 1, 0),
        ],
    )
    def test_value_error_raised_with_invalid_arg(
        self,
        confidence: float,
        x: float,
        y: float,
        w: float,
        h: float,
        frame: int,
        track_id: TrackId,
    ) -> None:
        with pytest.raises(ValueError):
            Detection(
                classification="car",
                confidence=confidence,
                x=x,
                y=y,
                w=w,
                h=h,
                frame=frame,
                occurrence=datetime(2022, 1, 1, 1, 0, 0),
                input_file_path=Path("path/to/file.otdet"),
                interpolated_detection=False,
                track_id=track_id,
            )

    def test_instantiation_with_valid_args(self, valid_detection_dict: dict) -> None:
        det = Detection(**valid_detection_dict)
        assert det.classification == valid_detection_dict[ottrk_format.CLASS]
        assert det.confidence == valid_detection_dict[ottrk_format.CONFIDENCE]
        assert det.x == valid_detection_dict[ottrk_format.X]
        assert det.y == valid_detection_dict[ottrk_format.Y]
        assert det.w == valid_detection_dict[ottrk_format.W]
        assert det.h == valid_detection_dict[ottrk_format.H]
        assert det.frame == valid_detection_dict[ottrk_format.FRAME]
        assert det.occurrence == valid_detection_dict[ottrk_format.OCCURRENCE]
        assert det.input_file_path == valid_detection_dict[ottrk_format.INPUT_FILE_PATH]
        assert (
            det.interpolated_detection
            == valid_detection_dict[ottrk_format.INTERPOLATED_DETECTION]
        )
        assert det.track_id == valid_detection_dict["track_id"]


class TestTrack:
    @pytest.mark.parametrize("id", [0, -1, 0.5])
    def test_value_error_raised_with_invalid_arg(
        self, valid_detection_dict: dict, id: int
    ) -> None:
        detection = Detection(**valid_detection_dict)
        with pytest.raises(ValidationError):
            Track(id=id, detections=[detection])

    def test_raise_error_on_empty_detections(self) -> None:
        with pytest.raises(ValidationError):
            Track(id=1, detections=[])

    def test_instantiation_with_valid_args(self, valid_detection_dict: dict) -> None:
        detection = Detection(**valid_detection_dict)
        track = Track(id=TrackId(5), detections=[detection])
        assert track.id == TrackId(5)
        assert track.detections == [detection]


class TestTrackRepository:
    def test_add(self) -> None:
        track = Mock()
        repository = TrackRepository()

        repository.add(track)

        assert track in repository.get_all()

    def test_add_all(self) -> None:
        first_track = Mock()
        second_track = Mock()
        repository = TrackRepository()

        repository.add_all([first_track, second_track])

        assert first_track in repository.get_all()
        assert second_track in repository.get_all()

    def test_get_by_id(self) -> None:
        first_track = Mock()
        first_track.id.return_value = TrackId(1)
        second_track = Mock()
        repository = TrackRepository()
        repository.add_all([first_track, second_track])

        returned = repository.get_for(first_track.id)

        assert returned == first_track
