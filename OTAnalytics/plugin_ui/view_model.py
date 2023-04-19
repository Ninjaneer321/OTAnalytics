from abc import ABC, abstractmethod

from OTAnalytics.domain.section import Section
from OTAnalytics.plugin_ui.abstract_canvas import AbstractCanvas
from OTAnalytics.plugin_ui.abstract_treeview import AbstractTreeviewSections


class ViewModel(ABC):
    @abstractmethod
    def set_canvas(self, canvas: AbstractCanvas) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_treeview_sections(self, treeview: AbstractTreeviewSections) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_selected_section_id(self, id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_tracks(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_sections(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_sections(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_section(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_new_section(self, section: Section) -> None:
        raise NotImplementedError

    @abstractmethod
    def edit_section_geometry(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def edit_section_metadata(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def remove_section(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def refresh_sections_on_gui(self) -> None:
        pass
