"""
(*)~---------------------------------------------------------------------------
Pupil - eye tracking platform
Copyright (C) 2012-2020 Pupil Labs

Distributed under the terms of the GNU
Lesser General Public License (LGPL v3.0).
See COPYING and COPYING.LESSER for license details.
---------------------------------------------------------------------------~(*)
"""

import abc
import logging
import os
import typing as T

import cv2
import numpy as np

from file_methods import load_object, save_object

logger = logging.getLogger(__name__)
__version__ = 1

# These are camera intrinsics that we recorded. They are estimates and generalize our
# setup. Its always better to estimate intrinsics for each camera again.
default_intrinsics = {
    "Pupil Cam1 ID2": {
        "(640, 480)": {
            "dist_coefs": [
                [
                    -0.4261945257015305,
                    0.18094740350081978,
                    0.0007881996581097361,
                    0.00026392537649318074,
                    -0.0367144553787145,
                ]
            ],
            "camera_matrix": [
                [406.74054872359386, 0.0, 332.0196776862145],
                [0.0, 392.27339466867005, 242.29314229816816],
                [0.0, 0.0, 1.0],
            ],
            "cam_type": "radial",
        },
        "(1280, 720)": {
            "dist_coefs": [
                [
                    -0.43738542863224966,
                    0.190570781428104,
                    -0.00125233833830639,
                    0.0018723428760170056,
                    -0.039219091259637684,
                ]
            ],
            "camera_matrix": [
                [829.3510515270362, 0.0, 659.9293047259697],
                [0.0, 799.5709408845464, 373.0776462356668],
                [0.0, 0.0, 1.0],
            ],
            "cam_type": "radial",
        },
        "(1920, 1080)": {
            "dist_coefs": [
                [-0.1804359422372346],
                [0.042312699050507684],
                [-0.048304496525298606],
                [0.022210236517363622],
            ],
            "camera_matrix": [
                [843.364676204713, 0.0, 983.8920955744197],
                [0.0, 819.1042187528645, 537.1633514857654],
                [0.0, 0.0, 1.0],
            ],
            "cam_type": "fisheye",
        },
    },
    "Logitech Webcam C930e": {
        "(640, 480)": {
            "dist_coefs": [
                [
                    0.10313391355051804,
                    -0.24657063652830105,
                    -0.001003806785350075,
                    -0.00046556297715377905,
                    0.1445780352338783,
                ]
            ],
            "camera_matrix": [
                [509.1810293948491, 0.0, 329.6996826114546],
                [0.0, 489.7219438561515, 243.26037641451043],
                [0.0, 0.0, 1.0],
            ],
            "cam_type": "radial",
        },
        "(1280, 720)": {
            "dist_coefs": [
                [
                    0.10152808562655541,
                    -0.23953332793667598,
                    -0.0021208895917640205,
                    -0.00023898995918166237,
                    0.1098748288957075,
                ]
            ],
            "camera_matrix": [
                [773.1676910077922, 0.0, 646.7114347564985],
                [0.0, 743.1525324268981, 363.1646522363395],
                [0.0, 0.0, 1.0],
            ],
            "cam_type": "radial",
        },
        "(1920, 1080)": {
            "dist_coefs": [
                [
                    0.09961660299292627,
                    -0.21847900301383041,
                    -0.0010681464641609897,
                    -0.0014568525518904656,
                    0.09417837101183982,
                ]
            ],
            "camera_matrix": [
                [1120.4309938089518, 0.0, 968.3563459802797],
                [0.0, 1077.3409390197398, 545.695766886239],
                [0.0, 0.0, 1.0],
            ],
            "cam_type": "radial",
        },
    },
    "PI world v1": {
        "(1088, 1080)": {
            "dist_coefs": [
                [
                    -0.12390715699556255,
                    0.09983010007937897,
                    0.0013846287331131738,
                    -0.00036539454816030264,
                    0.020072404577046853,
                    0.2052173022520547,
                    0.009921380887245364,
                    0.06631870205961587,
                ]
            ],
            "camera_matrix": [
                [766.2927454396544, 0.0, 543.6272327745995],
                [0.0, 766.3976103393867, 566.0580149497666],
                [0.0, 0.0, 1.0],
            ],
            "cam_type": "radial",
        }
    },
}

# Add measured intrinsics for the eyes (once for each ID for easy lookup)
for eye_id in (0, 1):
    default_intrinsics.update(
        {
            f"Pupil Cam1 ID{eye_id}": {
                "(320, 240)": {
                    "dist_coefs": [[0.0, 0.0, 0.0, 0.0, 0.0]],
                    "camera_matrix": [
                        [338.456035, 0.0, 160],
                        [0.0, 339.871543, 120],
                        [0.0, 0.0, 1.0],
                    ],
                    "cam_type": "radial",
                },
                "(640, 480)": {
                    "dist_coefs": [[0.0, 0.0, 0.0, 0.0, 0.0]],
                    "camera_matrix": [
                        [670.785555, 0.0, 320],
                        [0.0, 670.837798, 240],
                        [0.0, 0.0, 1.0],
                    ],
                    "cam_type": "radial",
                },
            },
            f"Pupil Cam2 ID{eye_id}": {
                "(192, 192)": {
                    "dist_coefs": [[0.0, 0.0, 0.0, 0.0, 0.0]],
                    "camera_matrix": [
                        [282.976877, 0.0, 96],
                        [0.0, 283.561467, 96],
                        [0.0, 0.0, 1.0],
                    ],
                    "cam_type": "radial",
                },
                "(400, 400)": {
                    "dist_coefs": [[0.0, 0.0, 0.0, 0.0, 0.0]],
                    "camera_matrix": [
                        [561.471804, 0.0, 200],
                        [0.0, 562.494105, 200],
                        [0.0, 0.0, 1.0],
                    ],
                    "cam_type": "radial",
                },
            },
            f"Pupil Cam3 ID{eye_id}": {
                "(192, 192)": {
                    "dist_coefs": [[0.0, 0.0, 0.0, 0.0, 0.0]],
                    "camera_matrix": [
                        [140.0, 0.0, 96],
                        [0.0, 140.0, 96],
                        [0.0, 0.0, 1.0],
                    ],
                    "cam_type": "radial",
                },
                "(400, 400)": {
                    "dist_coefs": [[0.0, 0.0, 0.0, 0.0, 0.0]],
                    "camera_matrix": [
                        [278.50, 0.0, 200],
                        [0.0, 278.55, 200],
                        [0.0, 0.0, 1.0],
                    ],
                    "cam_type": "radial",
                },
            },
        }
    )


class Camera_Model(abc.ABC):
    cam_type = ...  # overwrite in subclasses, used for saving/loading

    def __init__(self, K, D, resolution, name):
        self.K = np.array(K)
        self.D = np.array(D)
        self.resolution = resolution
        self.name = name

    def update_camera_matrix(self, camera_matrix):
        self.K = np.asanyarray(camera_matrix).reshape(self.K.shape)

    def update_dist_coefs(self, dist_coefs):
        self.D = np.asanyarray(dist_coefs).reshape(self.D.shape)

    @property
    def focal_length(self):
        fx = self.K[0, 0]
        fy = self.K[1, 1]
        return (fx + fy) / 2

    @abc.abstractmethod
    def undistort(self, img: np.ndarray) -> np.ndarray:
        ...

    @abc.abstractmethod
    def unprojectPoints(
        self, pts_2d: np.ndarray, use_distortion: bool = True, normalize: bool = False
    ) -> np.ndarray:
        ...

    @abc.abstractmethod
    def projectPoints(
        self,
        object_points,
        rvec: T.Optional[np.ndarray] = None,
        tvec: T.Optional[np.ndarray] = None,
        use_distortion: bool = True,
    ):
        ...

    @abc.abstractmethod
    def undistort_points_to_ideal_point_coordinates(
        self, points: np.ndarray
    ) -> np.ndarray:
        ...

    def undistort_points_on_image_plane(self, points):
        points = self.unprojectPoints(points, use_distortion=True)
        points = self.projectPoints(points, use_distortion=False)
        return points

    def distort_points_on_image_plane(self, points):
        points = self.unprojectPoints(points, use_distortion=False)
        points = self.projectPoints(points, use_distortion=True)
        return points

    @abc.abstractmethod
    def solvePnP(
        self,
        uv3d,
        xy,
        flags: int = cv2.SOLVEPNP_ITERATIVE,
        useExtrinsicGuess: bool = False,
        rvec: T.Optional[np.ndarray] = None,
        tvec: T.Optional[np.ndarray] = None,
    ):
        ...

    subclass_by_cam_type = dict()

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        # register subclasses by cam_type
        if cls.cam_type == ...:
            raise NotImplementedError("Subclass needs to define 'cam_type'!")
        if cls.cam_type in Camera_Model.subclass_by_cam_type:
            raise ValueError(
                f"Error trying to register camera model {cls}: Camera model with"
                f" cam_type '{cls.cam_type}' already exists:"
                f" {Camera_Model.subclass_by_cam_type[cls.cam_type]}"
            )
        Camera_Model.subclass_by_cam_type[cls.cam_type] = cls

    def save(self, directory, custom_name=None):
        """
        Saves the current intrinsics to corresponding camera's intrinsics file. For each
        unique camera name we maintain a single file containing all intrinsics
        associated with this camera name.
        :param directory: save location
        :return:
        """
        cam_name = custom_name or self.name
        intrinsics = {
            "camera_matrix": self.K.tolist(),
            "dist_coefs": self.D.tolist(),
            "resolution": self.resolution,
            "cam_type": self.cam_type,
        }
        # Try to load previously recorded camera intrinsics
        save_path = os.path.join(
            directory, "{}.intrinsics".format(cam_name.replace(" ", "_"))
        )
        try:
            intrinsics_dict = load_object(save_path, allow_legacy=False)
        except Exception:
            intrinsics_dict = {}

        intrinsics_dict["version"] = __version__
        intrinsics_dict[str(self.resolution)] = intrinsics

        save_object(intrinsics_dict, save_path)
        logger.info(
            f"Intrinsics for camera {cam_name} at resolution {self.resolution} saved"
            f" to {save_path}"
        )

    @staticmethod
    def from_file(
        directory: str, cam_name: str, resolution: T.Tuple[int]
    ) -> "Camera_Model":
        """
        Loads recorded intrinsics for the given camera and resolution. If no recorded
        intrinsics are available we fall back to default values. If no default values
        are available, we use dummy intrinsics.
        :param directory: The directory in which to look for the intrinsincs file.
        :param cam_name: Name of the camera, e.g. 'Pupil Cam 1 ID2'.
        :param resolution: Camera resolution.
        """
        file_path = os.path.join(
            directory, "{}.intrinsics".format(cam_name.replace(" ", "_"))
        )
        try:
            intrinsics_dict = load_object(file_path, allow_legacy=False)

            if intrinsics_dict["version"] < __version__:
                logger.warning("Deprecated camera intrinsics found.")
                logger.info(
                    "Please recalculate the camera intrinsics using the Camera"
                    " Intrinsics Estimation."
                )
                os.rename(
                    file_path,
                    "{}.deprecated.v{}".format(file_path, intrinsics_dict["version"]),
                )

            intrinsics = intrinsics_dict[str(resolution)]
            logger.info("Loading previously recorded intrinsics...")
            return Camera_Model._from_raw_intrinsics(cam_name, resolution, intrinsics)
        except Exception:
            logger.debug(
                f"No recorded intrinsics found for camera {cam_name} at resolution"
                f" {resolution}"
            )
            return Camera_Model.from_default(cam_name, resolution)

    @staticmethod
    def from_default(cam_name: str, resolution: T.Tuple[int]) -> "Camera_Model":
        """
        Loads default intrinsics for the given camera and resolution. If no default
        values are available, we use dummy intrinsics.
        :param cam_name: Name of the camera, e.g. 'Pupil Cam 1 ID2'.
        :param resolution: Camera resolution.
        """
        if (
            cam_name in default_intrinsics
            and str(resolution) in default_intrinsics[cam_name]
        ):
            logger.info("Loading default intrinsics!")
            intrinsics = default_intrinsics[cam_name][str(resolution)]
            return Camera_Model._from_raw_intrinsics(cam_name, resolution, intrinsics)
        else:
            logger.warning(
                f"No camera intrinsics available for camera {cam_name} at"
                f" resolution {resolution}!"
            )
            logger.warning("Loading dummy intrinsics, which might decrease accuracy!")
            logger.warning(
                "Consider selecting a different resolution, or running the Camera"
                " Instrinsics Estimation!"
            )
            return Dummy_Camera(resolution, cam_name)

    @staticmethod
    def _from_raw_intrinsics(cam_name, resolution, intrinsics):
        cam_type = intrinsics["cam_type"]
        if cam_type not in Camera_Model.subclass_by_cam_type:
            logger.warning(
                f"Trying to load unknown camera type intrinsics: {cam_type}! Using "
                " dummy intrinsics!"
            )
            return Dummy_Camera(resolution, cam_name)

        camera_model_class = Camera_Model.subclass_by_cam_type[cam_type]
        return camera_model_class(
            intrinsics["camera_matrix"], intrinsics["dist_coefs"], resolution, cam_name
        )


class Fisheye_Dist_Camera(Camera_Model):
    """
    Camera model assuming a lense with fisheye distortion. Provides functionality to
    make use of a fisheye camera model. The implementation of cv2.fisheye is buggy and
    some functions had to be customized.
    """

    cam_type = "fisheye"

    def undistort(self, img):
        """
        Undistortes an image based on the camera model.
        :param img: Distorted input image
        :return: Undistorted image
        """
        R = np.eye(3)

        map1, map2 = cv2.fisheye.initUndistortRectifyMap(
            np.array(self.K),
            np.array(self.D),
            R,
            np.array(self.K),
            self.resolution,
            cv2.CV_16SC2,
        )

        undistorted_img = cv2.remap(
            img,
            map1,
            map2,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
        )

        return undistorted_img

    def unprojectPoints(self, pts_2d, use_distortion=True, normalize=False):
        """
        Undistorts points according to the camera model. cv2.fisheye.undistortPoints
        does *NOT* perform the same unprojection step the original cv2.unprojectPoints
        does. Thus we implement this function ourselves.
        :param pts_2d, shape: Nx2
        :return: Array of unprojected 3d points, shape: Nx3
        """

        pts_2d = np.array(pts_2d, dtype=np.float32)

        # Delete any posibly wrong 3rd dimension
        if pts_2d.ndim == 1 or pts_2d.ndim == 3:
            pts_2d = pts_2d.reshape((-1, 2))

        eps = np.finfo(np.float32).eps

        f = np.array((self.K[0, 0], self.K[1, 1])).reshape(1, 2)
        c = np.array((self.K[0, 2], self.K[1, 2])).reshape(1, 2)
        if use_distortion:
            k = self.D.ravel().astype(np.float32)
        else:
            k = np.asarray(
                [1.0 / 3.0, 2.0 / 15.0, 17.0 / 315.0, 62.0 / 2835.0], dtype=np.float32
            )

        pi = pts_2d.astype(np.float32)
        pw = (pi - c) / f

        theta_d = np.linalg.norm(pw, ord=2, axis=1)
        theta = theta_d
        for j in range(10):
            theta2 = theta ** 2
            theta4 = theta2 ** 2
            theta6 = theta4 * theta2
            theta8 = theta6 * theta2
            theta = theta_d / (
                1 + k[0] * theta2 + k[1] * theta4 + k[2] * theta6 + k[3] * theta8
            )

        scale = np.tan(theta) / (theta_d + eps)

        pts_2d_undist = pw * scale.reshape(-1, 1)

        pts_3d = cv2.convertPointsToHomogeneous(pts_2d_undist)
        pts_3d.shape = -1, 3

        if normalize:
            pts_3d /= np.linalg.norm(pts_3d, axis=1)[:, np.newaxis]

        return pts_3d

    def projectPoints(self, object_points, rvec=None, tvec=None, use_distortion=True):
        """
        Projects a set of points onto the camera plane as defined by the camera model.
        :param object_points: Set of 3D world points
        :param rvec: Set of vectors describing the rotation of the camera when recording
            the corresponding object point
        :param tvec: Set of vectors describing the translation of the camera when
            recording the corresponding object point
        :return: Projected 2D points
        """
        skew = 0

        input_dim = object_points.ndim

        object_points = object_points.reshape((1, -1, 3))

        if rvec is None:
            rvec = np.zeros(3).reshape(1, 1, 3)
        else:
            rvec = np.array(rvec).reshape(1, 1, 3)

        if tvec is None:
            tvec = np.zeros(3).reshape(1, 1, 3)
        else:
            tvec = np.array(tvec).reshape(1, 1, 3)

        if use_distortion:
            _D = self.D
        else:
            _D = np.asarray([[1.0 / 3.0, 2.0 / 15.0, 17.0 / 315.0, 62.0 / 2835.0]])

        image_points, jacobian = cv2.fisheye.projectPoints(
            object_points, rvec, tvec, self.K, _D, alpha=skew
        )

        if input_dim == 2:
            image_points.shape = (-1, 2)
        elif input_dim == 3:
            image_points.shape = (-1, 1, 2)
        return image_points

    def undistort_points_to_ideal_point_coordinates(self, points):
        return cv2.fisheye.undistortPoints(points, self.K, self.D)

    def solvePnP(
        self,
        uv3d,
        xy,
        flags=cv2.SOLVEPNP_ITERATIVE,
        useExtrinsicGuess=False,
        rvec=None,
        tvec=None,
    ):
        try:
            uv3d = np.reshape(uv3d, (1, -1, 3))
        except ValueError:
            raise ValueError("uv3d is not 3d points")
        try:
            xy = np.reshape(xy, (1, -1, 2))
        except ValueError:
            raise ValueError("xy is not 2d points")
        if uv3d.shape[1] != xy.shape[1]:
            raise ValueError("the number of 3d points and 2d points are not the same")

        # opencv cannot handle solvePnP correctly for fisheye distorted cameras, so we
        # undistort manually and call solvePnP without distortion
        xy_undist = self.undistort_points_on_image_plane(xy)
        res = cv2.solvePnP(
            uv3d,
            xy_undist,
            self.K,
            None,
            flags=flags,
            useExtrinsicGuess=useExtrinsicGuess,
            rvec=rvec,
            tvec=tvec,
        )
        return res


class Radial_Dist_Camera(Camera_Model):
    """
    Camera model assuming a lense with radial distortion (this is the defaut model in
    opencv). Provides functionality to make use of a pinhole camera model that is also
    compensating for lense distortion
    """

    cam_type = "radial"

    def undistort(self, img):
        """
        Undistortes an image based on the camera model.
        :param img: Distorted input image
        :return: Undistorted image
        """
        undist_img = cv2.undistort(img, self.K, self.D)
        return undist_img

    def unprojectPoints(self, pts_2d, use_distortion=True, normalize=False):
        """
        Undistorts points according to the camera model.
        :param pts_2d, shape: Nx2
        :return: Array of unprojected 3d points, shape: Nx3
        """
        pts_2d = np.array(pts_2d, dtype=np.float32)

        # Delete any posibly wrong 3rd dimension
        if pts_2d.ndim == 1 or pts_2d.ndim == 3:
            pts_2d = pts_2d.reshape((-1, 2))

        # Add third dimension the way cv2 wants it
        if pts_2d.ndim == 2:
            pts_2d = pts_2d.reshape((-1, 1, 2))

        if use_distortion:
            _D = self.D
        else:
            _D = np.asarray([[0.0, 0.0, 0.0, 0.0, 0.0]])

        pts_2d_undist = cv2.undistortPoints(pts_2d, self.K, _D)

        pts_3d = cv2.convertPointsToHomogeneous(pts_2d_undist)
        pts_3d.shape = -1, 3

        if normalize:
            pts_3d /= np.linalg.norm(pts_3d, axis=1)[:, np.newaxis]

        return pts_3d

    def projectPoints(self, object_points, rvec=None, tvec=None, use_distortion=True):
        """
        Projects a set of points onto the camera plane as defined by the camera model.
        :param object_points: Set of 3D world points
        :param rvec: Set of vectors describing the rotation of the camera when recording
            the corresponding object point
        :param tvec: Set of vectors describing the translation of the camera when
            recording the corresponding object point
        :return: Projected 2D points
        """
        input_dim = object_points.ndim

        object_points = object_points.reshape((1, -1, 3))

        if rvec is None:
            rvec = np.zeros(3).reshape(1, 1, 3)
        else:
            rvec = np.array(rvec).reshape(1, 1, 3)

        if tvec is None:
            tvec = np.zeros(3).reshape(1, 1, 3)
        else:
            tvec = np.array(tvec).reshape(1, 1, 3)

        if use_distortion:
            _D = self.D
        else:
            _D = np.asarray([[0.0, 0.0, 0.0, 0.0, 0.0]])

        image_points, jacobian = cv2.projectPoints(
            object_points, rvec, tvec, self.K, _D
        )

        if input_dim == 2:
            image_points.shape = (-1, 2)
        elif input_dim == 3:
            image_points.shape = (-1, 1, 2)
        return image_points

    def undistort_points_to_ideal_point_coordinates(self, points):
        return cv2.undistortPoints(points, self.K, self.D)

    def solvePnP(
        self,
        uv3d,
        xy,
        flags=cv2.SOLVEPNP_ITERATIVE,
        useExtrinsicGuess=False,
        rvec=None,
        tvec=None,
    ):
        try:
            uv3d = np.reshape(uv3d, (1, -1, 3))
        except ValueError:
            raise ValueError("uv3d is not 3d points")
        try:
            xy = np.reshape(xy, (1, -1, 2))
        except ValueError:
            raise ValueError("xy is not 2d points")
        if uv3d.shape[1] != xy.shape[1]:
            raise ValueError("the number of 3d points and 2d points are not the same")

        res = cv2.solvePnP(
            uv3d,
            xy,
            self.K,
            self.D,
            flags=flags,
            useExtrinsicGuess=useExtrinsicGuess,
            rvec=rvec,
            tvec=tvec,
        )
        return res


class Dummy_Camera(Radial_Dist_Camera):
    """
    Dummy Camera model assuming no lense distortion and idealized camera intrinsics.
    """

    cam_type = "dummy"

    def __init__(self, resolution, name):
        camera_matrix = [
            [1000, 0.0, resolution[0] / 2.0],
            [0.0, 1000, resolution[1] / 2.0],
            [0.0, 0.0, 1.0],
        ]
        dist_coefs = [[0.0, 0.0, 0.0, 0.0, 0.0]]
        super().__init__(camera_matrix, dist_coefs, resolution, name)
