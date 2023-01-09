import logging
from typing import Any, Optional, Sequence

from ..base_backend import Base_Manager, Base_Source, SourceInfo
from ..hmd_streaming import HMD_Streaming_Source
from .background import BackgroundCameraSharingManager
from .camera import NeonCameraInterface
from .definitions import NEON_SHARED_EYE_CAM_TOPIC, SCENE_CAM_SPEC

logger = logging.getLogger(__name__)


class Neon_Manager(Base_Manager):
    SUBJECT_REQUEST_SHARED_CAMERA_START: str = "neon_backend.shared_camera.should_start"

    def __init__(self, g_pool):
        super().__init__(g_pool)
        self._neon_eye_camera_sharing_manager: Optional[
            BackgroundCameraSharingManager
        ] = None
        logger.debug(
            "Neon backend manager launched with "
            f"{NeonCameraInterface.find_all_connected_device_uids()}"
        )

    def get_devices(self) -> Sequence[SourceInfo]:
        """Return source infos for all devices that the backend supports."""
        return (
            [SourceInfo(label="Neon", manager=self, key="neon")]
            if NeonCameraInterface.any_device_connected()
            else []
        )

    def get_cameras(self) -> Sequence[SourceInfo]:
        # devices = NeonCameraInterface.find_all_connected_device_uids()
        # return [
        #     SourceInfo(
        #         label=f"{device['name']} @ Local USB",
        #         manager=self,
        #         key=f"cam.{device['uid']}",
        #     )
        #     for device in self.devices
        #     if not any(
        #         pattern in device["name"] for pattern in self.ignore_name_patterns
        #     )
        #     and (device["idVendor"], device["idProduct"]) not in self.ignore_vid_pid
        # ]
        return []

    def activate(self, key: Any) -> None:
        """Activate a source (device or camera) by key from source info."""
        if key == "neon":
            self.auto_activate_source()

    def auto_activate_source(self):
        logger.debug("Auto activating Neon source.")

        # self.enable_neon_eye_camera_sharing()
        source_uid = NeonCameraInterface.find_connected_device_uid(SCENE_CAM_SPEC)
        if source_uid is None:
            logger.warning("No Neon scene camera connected")
            return
        settings = {
            "frame_size": (SCENE_CAM_SPEC.width, SCENE_CAM_SPEC.height),
            "frame_rate": SCENE_CAM_SPEC.fps,
            "uid": source_uid,
            "name": "Neon Scene Camera v1",
        }
        self.notify_all(
            {"subject": "start_plugin", "name": "UVC_Source", "args": settings}
        )
        for eye in range(2):
            self.notify_all(
                {
                    "subject": "start_eye_plugin",
                    "target": f"eye{eye}",
                    "name": "Neon_Eye_Cam_Source",
                }
            )

    def on_notify(self, notification):
        if notification["subject"] == self.SUBJECT_REQUEST_SHARED_CAMERA_START:
            self.enable_neon_eye_camera_sharing()
        return super().on_notify(notification)

    def enable_neon_eye_camera_sharing(self):
        if (
            self._neon_eye_camera_sharing_manager is None
            or not self._neon_eye_camera_sharing_manager.is_running
        ):
            logger.debug("Launching BackgroundCameraSharingManager")
            self._neon_eye_camera_sharing_manager = BackgroundCameraSharingManager(
                timebase=self.g_pool.timebase,
                ipc_pub_url=self.g_pool.ipc_pub_url,
                ipc_push_url=self.g_pool.ipc_push_url,
                ipc_sub_url=self.g_pool.ipc_sub_url,
                wait_for_process_start=True,
                topic_prefix=NEON_SHARED_EYE_CAM_TOPIC,
            )
            logger.debug("Launched BackgroundCameraSharingManager")

    def cleanup(self):
        if self._neon_eye_camera_sharing_manager is not None:
            self._neon_eye_camera_sharing_manager.stop()
        return super().cleanup()


class Neon_Eye_Cam_Source(HMD_Streaming_Source):
    def __init__(self, g_pool, topics=None, *args, **kwargs):
        if topics is None:
            topics = (NEON_SHARED_EYE_CAM_TOPIC + g_pool.process,)  # type: ignore
        super().__init__(
            g_pool,
            topics=topics,
            flip_preview=False,
            *args,
            **kwargs,
        )
        self.notify_all({"subject": Neon_Manager.SUBJECT_REQUEST_SHARED_CAMERA_START})

        eye = {"eye0": "right", "eye1": "left"}.get(g_pool.process, None)
        self.name = f"Neon {eye} eye camera"

    @classmethod
    def base_class(cls):
        return Base_Source
