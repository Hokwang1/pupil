import ctypes
import logging
import multiprocessing
import time
from multiprocessing.sharedctypes import SynchronizedBase
from multiprocessing.synchronize import Event as EventClass

from .camera import NeonCameraInterface
from .definitions import LEFT_EYE_CAM_INTRINSICS, MODULE_SPEC, RIGHT_EYE_CAM_INTRINSICS
from .network import NetworkInterface


class BackgroundCameraSharingManager:
    def __init__(
        self,
        timebase: "SynchronizedBase[ctypes.c_double]",  # mp.Value
        ipc_pub_url: str,
        ipc_sub_url: str,
        ipc_push_url: str,
        topic_prefix: str,
        wait_for_process_start: bool = True,
    ):
        process_started_event = multiprocessing.Event()
        self.should_stop_running_event = multiprocessing.Event()

        self._background_process = multiprocessing.Process(
            name="Shared Camera Process",
            target=self._event_loop,
            args=(
                process_started_event,
                self.should_stop_running_event,
                timebase,
                ipc_pub_url,
                ipc_sub_url,
                ipc_push_url,
                topic_prefix,
            ),
        )
        self._background_process.start()

        if wait_for_process_start:
            process_started_event.wait()

    def stop(self):
        self.should_stop_running_event.set()
        self._background_process.join(timeout=5.0)
        if self.is_running:
            logging.getLogger(__name__ + ".foreground").warning(
                "Background process could not be terminated"
            )

    @property
    def is_running(self) -> bool:
        return self._background_process.exitcode is None

    @staticmethod
    def _event_loop(
        process_started_event: EventClass,
        should_stop_running_event: EventClass,
        timebase: "SynchronizedBase[ctypes.c_double]",  # mp.Value
        ipc_pub_url: str,
        ipc_sub_url: str,
        ipc_push_url: str,
        topic_prefix: str = "shared_camera.",
    ):
        with (
            NetworkInterface(
                topic_prefix=topic_prefix,
                ipc_pub_url=ipc_pub_url,
                ipc_sub_url=ipc_sub_url,
                ipc_push_url=ipc_push_url,
            ) as network,
            NeonCameraInterface(MODULE_SPEC) as camera,
        ):
            process_started_event.set()

            last_status_update = time.perf_counter()
            first_update = last_status_update
            num_frames_recv = 0
            num_frames_forwarded = 0

            while not should_stop_running_event.is_set():
                frame = camera.get_shared_frame(0.5)
                if frame is not None:
                    num_frames_recv += 1
                    frame.timestamp -= timebase.value
                split_frames = camera.split_shared_frame(frame)
                if split_frames is not None:
                    num_frames_forwarded += 1
                    network.send_eye_frame(
                        split_frames.right, RIGHT_EYE_CAM_INTRINSICS, eye_id=0
                    )
                    network.send_eye_frame(
                        split_frames.left, LEFT_EYE_CAM_INTRINSICS, eye_id=1
                    )
                now = time.perf_counter()
                if now - last_status_update > 5.0:
                    total_time = now - first_update
                    fps = num_frames_forwarded / total_time

                    network.logger.debug(
                        f"{num_frames_recv=} {num_frames_forwarded=} in {total_time=} "
                        f"seconds (~ {fps:.0f} FPS)"
                    )
                    last_status_update = now
