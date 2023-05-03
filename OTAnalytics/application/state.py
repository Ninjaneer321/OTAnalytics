from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable, Generic, Optional, TypeVar

from OTAnalytics.application.datastore import Datastore
from OTAnalytics.domain.filter import FilterElement
from OTAnalytics.domain.geometry import RelativeOffsetCoordinate
from OTAnalytics.domain.section import SectionId, SectionListObserver
from OTAnalytics.domain.track import (
    TrackId,
    TrackImage,
    TrackListObserver,
    TrackObserver,
    TrackSubject,
)


class TrackState(TrackListObserver):
    """
    This state represents the currently selected track.
    """

    def __init__(self) -> None:
        self.selected_track: Optional[TrackId] = None
        self.observers: TrackSubject = TrackSubject()

    def register(self, observer: TrackObserver) -> None:
        """
        Listen to changes of the currently selected track.

        Args:
            observer (TrackObserver): listener to be notified about changes
        """
        self.observers.register(observer)

    def select(self, track_id: TrackId) -> None:
        """
        Select the given track.

        Args:
            track_id (TrackId): track to be selected
        """
        if self.selected_track != track_id:
            self.selected_track = track_id
            self._notify_observers()

    def _notify_observers(self) -> None:
        """
        Notify observers about the currently selected track.
        """
        self.observers.notify(self.selected_track)

    def notify_tracks(self, tracks: list[TrackId]) -> None:
        """
        Notify the state about changes in the track list.

        Args:
            tracks (list[TrackId]): newly added tracks

        Raises:
            IndexError: if the list of tracks is empty
        """
        if not tracks:
            raise IndexError("No tracks to select")
        self.select(tracks[0])


VALUE = TypeVar("VALUE")
Observer = Callable[[Optional[VALUE]], None]


class Subject(Generic[VALUE]):
    """
    Helper class to handle and notify observers
    """

    def __init__(self) -> None:
        self.observers: set[Observer[VALUE]] = set()

    def register(self, observer: Observer[VALUE]) -> None:
        """
        Listen to events.

        Args:
            observer (Observer[VALUE]): listener to add
        """
        self.observers.add(observer)

    def notify(self, value: Optional[VALUE]) -> None:
        """
        Notifies observers about the changed value.

        Args:
            value (Optional[VALUD]): changed value
        """
        [observer(value) for observer in self.observers]


class ObservableProperty(Generic[VALUE]):
    """
    Represents a property of the given type that informs its observers about changes.
    """

    def __init__(self, default: Optional[VALUE] = None) -> None:
        self._property: Optional[VALUE] = default
        self._subject: Subject[VALUE] = Subject[VALUE]()

    def register(self, observer: Observer[VALUE]) -> None:
        """
        Listen to property changes.

        Args:
            observer (Observer[VALUE]): observer to be notified about changes
        """
        self._subject.register(observer)

    def set(self, value: Optional[VALUE]) -> None:
        """
        Change the current value of the property

        Args:
            value (Optional[VALUE]): new value to be set
        """
        if self._property != value:
            self._property = value
            self._subject.notify(value)

    def get(self) -> Optional[VALUE]:
        """
        Get the current value of the property.

        Returns:
            Optional[VALUE]: current value
        """
        return self._property


class FilterElementState:
    """This state represents the current filter settings in the UI.

    Args:
        filter_element (FilterElement): the filter element whose properties are to be
            updated by this class
    """

    def __init__(
        self,
        filter_element: FilterElement,
    ) -> None:
        """_summary_

        Args:
        """
        self._subject = Subject[FilterElement]()
        self._filter_element = filter_element

    @property
    def start_date(self) -> Optional[datetime]:
        return self._filter_element.start_date

    @start_date.setter
    def start_date(self, start_date: datetime) -> None:
        self._filter_element.start_date = start_date
        self._subject.notify(self._filter_element)

    @property
    def end_date(self) -> Optional[datetime]:
        return self._filter_element.end_date

    @end_date.setter
    def end_date(self, end_date: datetime) -> None:
        self._filter_element.end_date = end_date
        self._subject.notify(self._filter_element)

    @property
    def classifications(self) -> list[str]:
        return self._filter_element.classifications

    @classifications.setter
    def classifications(self, classifications: list[str]) -> None:
        self._filter_element.classifications = classifications
        self._subject.notify(self._filter_element)

    def register(self, observer: Observer["FilterElement"]) -> None:
        """Listen to filter element changes.

        Args:
            observer (Observer[&quot;FilterElement&quot;]): observer to be notified
                about changes_
        """
        self._subject.register(observer)


class TrackViewState:
    """
    This state represents the information to be shown on the ui.

    Args:
        filter_element_state (FilterElementState): the filter element state
    """

    def __init__(self, filter_element_state: FilterElementState) -> None:
        self.background_image = ObservableProperty[TrackImage]()
        self.show_tracks = ObservableProperty[bool]()
        self.track_offset = ObservableProperty[RelativeOffsetCoordinate](
            RelativeOffsetCoordinate(0, 0)
        )
        self.filter_element_state = filter_element_state


class Plotter(ABC):
    """Abstraction to plot the background image."""

    @abstractmethod
    def plot(self) -> Optional[TrackImage]:
        pass


class TrackImageUpdater(TrackListObserver):
    """
    This class listens to track changes in the repository and updates the background
    image. It takes into account whether the tracks and sections should be shown or not.
    """

    def __init__(
        self,
        datastore: Datastore,
        track_view_state: TrackViewState,
        plotter: Plotter,
    ) -> None:
        self._datastore = datastore
        self._track_view_state = track_view_state
        self._plotter = plotter
        self._track_view_state.show_tracks.register(self._notify_show_tracks)
        self._track_view_state.track_offset.register(self._notify_track_offset)
        self._track_view_state.filter_element_state.register(
            self._notify_filter_element
        )

    def notify_tracks(self, tracks: list[TrackId]) -> None:
        """
        Will notify this object about changes in the track repository.

        Args:
            tracks (list[TrackId]): list of changed track ids

        Raises:
            IndexError: if the list is empty
        """
        if not tracks:
            raise IndexError("No tracks changed")
        self._update_image()

    def _notify_show_tracks(self, show_tracks: Optional[bool]) -> None:
        """
        Will update the image according to changes of the show tracks property.

        Args:
            show_tracks (Optional[bool]): current value
        """
        self._update()

    def _notify_track_offset(self, offset: Optional[RelativeOffsetCoordinate]) -> None:
        """
        Will update the image according to changes of the track offset property.

        Args:
            offset (Optional[RelativeOffsetCoordinate]): current value
        """
        self._update()

    def _notify_filter_element(self, _: Optional[FilterElement]) -> None:
        self._update()

    def _update(self) -> None:
        """
        Update the image if at least one track is available.
        """
        self._update_image()

    def _update_image(self) -> None:
        """
        Updates the current background image with or without tracks and sections.

        Args:
            track_id (TrackId): track id used to get the video image
        """
        self._track_view_state.background_image.set(self._plotter.plot())


class SectionState(SectionListObserver):
    """
    This state represents the currently selected section.
    """

    def __init__(self) -> None:
        self.selected_section = ObservableProperty[SectionId]()

    def notify_sections(self, sections: list[SectionId]) -> None:
        """
        Notify the state about changes in the section list.

        Args:
            sections (list[SectionId]): newly added sections

        Raises:
            IndexError: if the list of sections is empty
        """
        if not sections:
            raise IndexError("No section to select")
        self.selected_section.set(sections[0])
