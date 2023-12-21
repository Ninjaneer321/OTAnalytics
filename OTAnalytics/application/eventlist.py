from OTAnalytics.domain.event import Event, EventType, SceneEventBuilder
from OTAnalytics.domain.geometry import calculate_direction_vector
from OTAnalytics.domain.track import Detection, TrackDataset


class SceneActionDetector:
    """Detect when a road user enters or leaves the scene.

    Args:
        scene_event_builder (SceneEventBuilder): the builder to build scene events
    """

    def __init__(self, scene_event_builder: SceneEventBuilder) -> None:
        self._event_builder = scene_event_builder

    def detect_enter_scene(
        self, from_detection: Detection, to_detection: Detection, classification: str
    ) -> Event:
        """Detect the first time a road user enters the scene.

        Args:
            tracks (Track): the track associated with the road user

        Returns:
            Iterable[Event]: the enter scene event
        """
        self._event_builder.add_event_type(EventType.ENTER_SCENE)
        self._event_builder.add_road_user_type(classification)
        self._event_builder.add_direction_vector(
            calculate_direction_vector(
                from_detection.x, from_detection.y, to_detection.x, to_detection.y
            )
        )
        self._event_builder.add_event_coordinate(from_detection.x, from_detection.y)

        return self._event_builder.create_event(from_detection)

    def detect_leave_scene(
        self, from_detection: Detection, to_detection: Detection, classification: str
    ) -> Event:
        """Detect the last time a road user is seen before leaving the scene.

        Args:
            tracks (Track): the track associated with the road user

        Returns:
            Iterable[Event]: the leave scene event
        """
        self._event_builder.add_event_type(EventType.LEAVE_SCENE)
        self._event_builder.add_road_user_type(classification)
        self._event_builder.add_direction_vector(
            calculate_direction_vector(
                from_detection.x, from_detection.y, to_detection.x, to_detection.y
            )
        )
        self._event_builder.add_event_coordinate(to_detection.x, to_detection.y)

        return self._event_builder.create_event(to_detection)

    def detect(self, tracks: TrackDataset) -> list[Event]:
        """Detect all enter and leave scene events.

        Args:
            tracks (Iterable[Track]): the tracks under inspection

        Returns:
            Iterable[Event]: the scene events
        """
        events: list[Event] = []
        for track in tracks.as_list():
            events.append(
                self.detect_enter_scene(
                    track.detections[0], track.detections[1], track.classification
                )
            )
            events.append(
                self.detect_leave_scene(
                    track.detections[-2], track.detections[-1], track.classification
                )
            )
        return events
