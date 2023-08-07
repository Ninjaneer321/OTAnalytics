from datetime import timedelta
from math import floor
from pathlib import Path

from moviepy.video.io.VideoFileClip import VideoFileClip
from PIL import Image

from OTAnalytics.domain.track import PilImage, TrackImage
from OTAnalytics.domain.video import VideoReader


class InvalidVideoError(Exception):
    pass


class FrameDoesNotExistError(Exception):
    pass


class MoviepyVideoReader(VideoReader):
    def get_frame(self, video_path: Path, index: int) -> TrackImage:
        """Get image of video at `frame`.

        Args:
            video_path (Path): path to the video_path.
            index (int): the frame of the video to get.

        Raises:
            FrameDoesNotExistError: if frame does not exist.

        Returns:
            ndarray: the image as an multi-dimensional array.
        """
        try:
            clip = VideoFileClip(str(video_path.absolute()))
        except IOError as e:
            raise InvalidVideoError(f"{str(video_path)} is not a valid video") from e
        found = None
        max_frames = clip.fps * clip.duration
        for frame_no, np_frame in enumerate(clip.iter_frames()):
            if frame_no == (index % max_frames):
                found = np_frame
                break
        clip.close()
        if found is None:
            raise FrameDoesNotExistError(f"frame number '{index}' does not exist")
        return PilImage(Image.fromarray(found))

    def get_frame_number_for(self, video_path: Path, delta: timedelta) -> int:
        try:
            clip = VideoFileClip(str(video_path.absolute()))
        except IOError as e:
            raise InvalidVideoError(f"{str(video_path)} is not a valid video") from e
        return floor(clip.fps * delta.total_seconds())
