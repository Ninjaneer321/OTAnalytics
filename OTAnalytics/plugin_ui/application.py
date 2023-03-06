import tkinter
from abc import abstractmethod
from pathlib import Path

import customtkinter
from customtkinter import CTk, CTkButton

from OTAnalytics.application.datastore import Datastore
from OTAnalytics.domain.section import Coordinate, LineSection, Section
from OTAnalytics.plugin_parser.otvision_parser import (
    OtsectionParser,
    OttrkParser,
    OttrkVideoParser,
)


class OTAnalyticsApplication:
    def __init__(self) -> None:
        self._datastore: Datastore

    def add_tracks_of_file(self, track_file: Path) -> None:
        self._datastore.load_track_file(file=track_file)

    def add_sections_of_file(self, sections_file: Path) -> None:
        self._datastore.load_section_file(file=sections_file)

    def start(self) -> None:
        self.setup_application()
        self.start_internal()

    @abstractmethod
    def start_internal(self) -> None:
        pass

    def setup_application(self) -> None:
        """
        Build all required objects and inject them where necessary
        """
        track_parser = OttrkParser()
        section_parser = OtsectionParser()
        video_parser = OttrkVideoParser()
        self._datastore = Datastore(track_parser, section_parser, video_parser)


class OTAnalyticsCli(OTAnalyticsApplication):
    def __init__(self) -> None:
        pass

    def start_internal(self) -> None:
        # TODO parse config and add track and section files
        pass


class OTAnalyticsGui(OTAnalyticsApplication):
    def __init__(self) -> None:
        self._app: CTk

    def load_tracks_in_file(self) -> None:
        track_file = Path("")  # TODO read from file chooser
        self._datastore.load_track_file(file=track_file)

    def load_sections_in_file(self) -> None:
        section_file = Path("")  # TODO read from file chooser
        self._datastore.load_section_file(file=section_file)

    def start(self) -> None:
        self.setup_application()
        self.show_gui()

    def show_gui(self) -> None:
        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")

        self._app = CTk()
        self._app.geometry("800x600")

        self.add_track_loader()
        self.add_section_loader()

        self._app.mainloop()

    def add_track_loader(self) -> None:
        button = CTkButton(
            master=self._app,
            text="Read tracks",
            command=self.load_tracks_in_file,
        )
        button.place(relx=0.25, rely=0.5, anchor=tkinter.CENTER)

    def add_section_loader(self) -> None:
        button = CTkButton(
            master=self._app,
            text="Read sections",
            command=self.load_sections_in_file,
        )
        button.place(relx=0.5, rely=0.5, anchor=tkinter.CENTER)

    def add_section_button(self) -> None:
        button = CTkButton(
            master=self._app,
            text="Add sections",
            command=self.add_section,
        )
        button.place(relx=0.75, rely=0.5, anchor=tkinter.CENTER)

    def add_section(self) -> None:
        section: Section = LineSection(
            id="north",
            start=Coordinate(0, 1),
            end=Coordinate(2, 3),
        )
        self._datastore.add_section(section)
