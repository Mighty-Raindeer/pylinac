from __future__ import annotations

import copy
import io
import math
import tempfile
from pathlib import Path
from unittest import TestCase

import matplotlib.pyplot as plt
import numpy as np

from pylinac import WinstonLutz
from pylinac.core.array_utils import create_dicom_files_from_3d_array
from pylinac.core.geometry import Vector, vector_is_close
from pylinac.core.io import TemporaryZipDirectory
from pylinac.core.scale import MachineScale
from pylinac.metrics.features import is_round
from pylinac.winston_lutz import (
    Axis,
    WinstonLutz2D,
    WinstonLutzResult,
    bb_projection_gantry_plane,
    bb_projection_long,
)
from tests_basic.utils import (
    CloudFileMixin,
    FromDemoImageTesterMixin,
    FromURLTesterMixin,
    get_file_from_cloud_test_repo,
    get_folder_from_cloud_test_repo,
    save_file,
)

TEST_DIR = "Winston-Lutz"


class TestBBProjection(TestCase):
    """Test the BB isoplane projections"""

    def test_longitudinal_projection(self):
        # in coordinate space, positive is in, but in plotting space, positive is out
        # thus, we return the opposite sign than the coordinate space
        # dead center
        assert (
            bb_projection_long(
                offset_in=0, offset_up=0, offset_left=0, sad=1000, gantry=0
            )
            == 0
        )
        # up-only won't change it
        assert (
            bb_projection_long(
                offset_in=0, offset_up=30, offset_left=0, sad=1000, gantry=0
            )
            == 0
        )
        # long-only won't change it
        assert (
            bb_projection_long(
                offset_in=20, offset_up=0, offset_left=0, sad=1000, gantry=0
            )
            == 20
        )
        # left-only won't change it
        assert (
            bb_projection_long(
                offset_in=0, offset_up=0, offset_left=15, sad=1000, gantry=0
            )
            == 0
        )
        # in and up will make it look further away at gantry 0
        assert math.isclose(
            bb_projection_long(
                offset_in=10, offset_up=10, offset_left=0, sad=1000, gantry=0
            ),
            10.1,
            abs_tol=0.005,
        )
        # in and down will make it closer at gantry 0
        assert math.isclose(
            bb_projection_long(
                offset_in=10, offset_up=-10, offset_left=0, sad=1000, gantry=0
            ),
            9.9,
            abs_tol=0.005,
        )
        # in and up will make it look closer at gantry 180
        assert math.isclose(
            bb_projection_long(
                offset_in=10, offset_up=10, offset_left=0, sad=1000, gantry=180
            ),
            9.9,
            abs_tol=0.005,
        )
        # in and down will make it further away at gantry 180
        assert math.isclose(
            bb_projection_long(
                offset_in=10, offset_up=-10, offset_left=0, sad=1000, gantry=180
            ),
            10.1,
            abs_tol=0.005,
        )
        # in and left will make it closer at gantry 90
        assert math.isclose(
            bb_projection_long(
                offset_in=10, offset_up=0, offset_left=10, sad=1000, gantry=90
            ),
            9.9,
            abs_tol=0.005,
        )
        # in and right will make it further away at gantry 90
        assert math.isclose(
            bb_projection_long(
                offset_in=10, offset_up=0, offset_left=-10, sad=1000, gantry=90
            ),
            10.1,
            abs_tol=0.005,
        )
        # in and right will make it closer at gantry 270
        assert math.isclose(
            bb_projection_long(
                offset_in=10, offset_up=0, offset_left=-10, sad=1000, gantry=270
            ),
            9.9,
            abs_tol=0.005,
        )
        # in and left won't change at gantry 0
        assert math.isclose(
            bb_projection_long(
                offset_in=10, offset_up=0, offset_left=10, sad=1000, gantry=0
            ),
            10,
            abs_tol=0.005,
        )
        # double the sad will half the effect:
        # in and up will make it look further away at gantry 0
        assert math.isclose(
            bb_projection_long(
                offset_in=10, offset_up=10, offset_left=0, sad=1000, gantry=0
            ),
            10.1,
            abs_tol=0.005,
        )
        # out and up will make it look further away at gantry 0
        assert math.isclose(
            bb_projection_long(
                offset_in=-10, offset_up=10, offset_left=0, sad=1000, gantry=0
            ),
            -10.1,
            abs_tol=0.005,
        )
        # out and up will make it look closer at gantry 180
        assert math.isclose(
            bb_projection_long(
                offset_in=-10, offset_up=10, offset_left=0, sad=1000, gantry=180
            ),
            -9.9,
            abs_tol=0.005,
        )
        # out and down will make it look closer at gantry 0
        assert math.isclose(
            bb_projection_long(
                offset_in=-10, offset_up=-10, offset_left=0, sad=1000, gantry=0
            ),
            -9.9,
            abs_tol=0.005,
        )
        # out and down will make it look further out at gantry 180
        assert math.isclose(
            bb_projection_long(
                offset_in=-10, offset_up=-10, offset_left=0, sad=1000, gantry=180
            ),
            -10.1,
            abs_tol=0.005,
        )

    def test_gantry_plane_projection(self):
        # left is negative, right is positive
        # dead center
        assert (
            bb_projection_gantry_plane(offset_up=0, offset_left=0, sad=1000, gantry=0)
            == 0
        )
        # up-only at gantry 0 is still 0
        assert (
            bb_projection_gantry_plane(offset_up=10, offset_left=0, sad=1000, gantry=0)
            == 0
        )
        # up-only at gantry 90 is exactly negative the offset
        assert (
            bb_projection_gantry_plane(offset_up=10, offset_left=0, sad=1000, gantry=90)
            == -10
        )
        # down-only at gantry 90 is exactly the offset
        assert (
            bb_projection_gantry_plane(
                offset_up=-10, offset_left=0, sad=1000, gantry=90
            )
            == 10
        )
        # left-only at gantry 0 is exactly negative the offset
        assert (
            bb_projection_gantry_plane(offset_up=0, offset_left=10, sad=1000, gantry=0)
            == -10
        )
        # right-only at gantry 0 is exactly negative the offset
        assert (
            bb_projection_gantry_plane(offset_up=0, offset_left=-10, sad=1000, gantry=0)
            == 10
        )
        # left-only at gantry 180 is exactly the offset
        assert (
            bb_projection_gantry_plane(
                offset_up=0, offset_left=10, sad=1000, gantry=180
            )
            == 10
        )
        # left and up at gantry 0 makes the bb appear away from CAX
        assert math.isclose(
            bb_projection_gantry_plane(
                offset_up=10, offset_left=20, sad=1000, gantry=0
            ),
            -20.2,
            abs_tol=0.005,
        )
        # left and down at gantry 0 makes the bb appear closer to the CAX
        assert math.isclose(
            bb_projection_gantry_plane(
                offset_up=-10, offset_left=20, sad=1000, gantry=0
            ),
            -19.8,
            abs_tol=0.005,
        )
        # left and up at gantry 180 makes the bb appear closer to CAX
        assert math.isclose(
            bb_projection_gantry_plane(
                offset_up=10, offset_left=20, sad=1000, gantry=180
            ),
            19.8,
            abs_tol=0.005,
        )
        # left and up at gantry 90 makes the bb appear closer to CAX
        assert math.isclose(
            bb_projection_gantry_plane(
                offset_up=10, offset_left=20, sad=1000, gantry=90
            ),
            -9.8,
            abs_tol=0.005,
        )
        # left and down at gantry 90 makes the bb appear closer to CAX
        assert math.isclose(
            bb_projection_gantry_plane(
                offset_up=-10, offset_left=20, sad=1000, gantry=90
            ),
            9.8,
            abs_tol=0.005,
        )
        # left and down at gantry 270 makes the bb appear further from the CAX
        assert math.isclose(
            bb_projection_gantry_plane(
                offset_up=-10, offset_left=20, sad=1000, gantry=270
            ),
            -10.2,
            abs_tol=0.005,
        )
        # right and down at gantry 270 makes the bb appear closer the CAX
        assert math.isclose(
            bb_projection_gantry_plane(
                offset_up=-10, offset_left=-20, sad=1000, gantry=270
            ),
            -9.8,
            abs_tol=0.005,
        )


class TestWLLoading(TestCase, FromDemoImageTesterMixin, FromURLTesterMixin):
    klass = WinstonLutz
    demo_load_method = "from_demo_images"
    url = "winston_lutz.zip"

    def test_loading_from_config_mapping(self):
        path = get_file_from_cloud_test_repo([TEST_DIR, "noisy_WL_30x5.zip"])
        with TemporaryZipDirectory(path) as z:
            config = {
                "WL G=0, C=0, P=0; Field=(30, 30)mm; BB=5mm @ left=0, in=0, up=0; Gantry tilt=0, Gantry sag=0.dcm": (
                    11,
                    12,
                    13,
                ),
                "WL G=90, C=0, P=0; Field=(30, 30)mm; BB=5mm @ left=0, in=0, up=0; Gantry tilt=0, Gantry sag=0.dcm": (
                    21,
                    22,
                    23,
                ),
                "WL G=180, C=0, P=0; Field=(30, 30)mm; BB=5mm @ left=0, in=0, up=0; Gantry tilt=0, Gantry sag=0.dcm": (
                    31,
                    32,
                    33,
                ),
                "WL G=270, C=0, P=0; Field=(30, 30)mm; BB=5mm @ left=0, in=0, up=0; Gantry tilt=0, Gantry sag=0.dcm": (
                    41,
                    42,
                    43,
                ),
            }
            wl = WinstonLutz(z, axis_mapping=config)
        wl.analyze()
        self.assertEqual(wl.images[0].gantry_angle, 11)
        self.assertEqual(wl.images[2].collimator_angle, 32)
        self.assertEqual(wl.images[3].couch_angle, 43)

    def test_loading_from_config_mapping_from_zip(self):
        path = get_file_from_cloud_test_repo([TEST_DIR, "noisy_WL_30x5.zip"])
        config = {
            "WL G=0, C=0, P=0; Field=(30, 30)mm; BB=5mm @ left=0, in=0, up=0; Gantry tilt=0, Gantry sag=0.dcm": (
                11,
                12,
                13,
            ),
            "WL G=90, C=0, P=0; Field=(30, 30)mm; BB=5mm @ left=0, in=0, up=0; Gantry tilt=0, Gantry sag=0.dcm": (
                21,
                22,
                23,
            ),
            "WL G=180, C=0, P=0; Field=(30, 30)mm; BB=5mm @ left=0, in=0, up=0; Gantry tilt=0, Gantry sag=0.dcm": (
                31,
                32,
                33,
            ),
            "WL G=270, C=0, P=0; Field=(30, 30)mm; BB=5mm @ left=0, in=0, up=0; Gantry tilt=0, Gantry sag=0.dcm": (
                41,
                42,
                43,
            ),
        }
        wl = WinstonLutz.from_zip(path, axis_mapping=config)
        wl.analyze()
        self.assertEqual(wl.images[0].gantry_angle, 11)
        self.assertEqual(wl.images[2].collimator_angle, 32)
        self.assertEqual(wl.images[3].couch_angle, 43)

    def test_using_filenames_overrides_axis_mapping(self):
        """If using filenames flag with axis mapping, file names take precedent. This is because
        RadMachine uses the axis mapping all the time now with the manual input feature
        """
        path = get_file_from_cloud_test_repo([TEST_DIR, "named_wl.zip"])
        config = {
            "wl_gantry13_collimator154_couch88.dcm": (
                0,
                2,
                4,
            ),
            "wl_gantry38_collimator12_couch34.dcm": (
                21,
                22,
                23,
            ),
            "wl_gantry78_collimator88_couch11.dcm": (
                31,
                32,
                33,
            ),
            "wl_gantry98_collimator_23_couch46.dcm": (
                41,
                42,
                43,
            ),
        }
        wl = WinstonLutz.from_zip(path, axis_mapping=config, use_filenames=True)
        wl.analyze()
        self.assertEqual(wl.images[0].gantry_angle, 13)
        self.assertEqual(wl.images[2].collimator_angle, 88)
        self.assertEqual(wl.images[3].couch_angle, 46)

    def test_loading_1_image_fails(self):
        with self.assertRaises(ValueError):
            folder = get_folder_from_cloud_test_repo(
                ["Winston-Lutz", "lutz", "1_image"]
            )
            WinstonLutz(folder)

    def test_invalid_dir(self):
        with self.assertRaises(ValueError):
            WinstonLutz(r"nonexistant/dir")

    def test_load_from_file_object(self):
        path = get_file_from_cloud_test_repo([TEST_DIR, "noisy_WL_30x5.zip"])
        ref_w = WinstonLutz.from_zip(path)
        ref_w.analyze()
        with open(path, "rb") as f:
            w = WinstonLutz.from_zip(f)
            w.analyze()
        self.assertIsInstance(w, WinstonLutz)
        self.assertEqual(w.gantry_iso_size, ref_w.gantry_iso_size)

    def test_load_from_stream(self):
        path = get_file_from_cloud_test_repo([TEST_DIR, "noisy_WL_30x5.zip"])
        ref_w = WinstonLutz.from_zip(path)
        ref_w.analyze()
        with open(path, "rb") as f:
            s = io.BytesIO(f.read())
            w = WinstonLutz.from_zip(s)
            w.analyze()
        self.assertIsInstance(w, WinstonLutz)
        self.assertEqual(w.gantry_iso_size, ref_w.gantry_iso_size)

    def test_load_2d_from_stream(self):
        path = get_file_from_cloud_test_repo(
            ["Winston-Lutz", "lutz", "1_image", "gantry0.dcm"]
        )
        ref_w = WinstonLutz2D(path)
        ref_w.analyze()
        with open(path, "rb") as f:
            s = io.BytesIO(f.read())
            w = WinstonLutz2D(s)
            w.analyze()
        self.assertIsInstance(w, WinstonLutz2D)
        self.assertEqual(w.bb, ref_w.bb)

    def test_loading_tiff(self):
        path = get_file_from_cloud_test_repo([TEST_DIR, "AQA.zip"])
        ref_w = WinstonLutz.from_zip(
            path,
            dpi=200,
            sid=1000,
            axis_mapping={
                r"AQA_A_03082023.tif": (0, 0, 0),
                r"AQA_B_03082023.tif": (0, 0, 0),
            },
        )
        ref_w.analyze(bb_size_mm=30)
        results = ref_w.results_data()
        self.assertEqual(results.num_gantry_images, 2)

    def test_tiff_missing_dpi(self):
        path = get_file_from_cloud_test_repo([TEST_DIR, "AQA.zip"])
        with self.assertRaises(ValueError):
            WinstonLutz.from_zip(
                path,
                sid=1000,
                axis_mapping={
                    r"AQA_A_03082023.tif": (0, 0, 0),
                    r"AQA_B_03082023.tif": (0, 0, 0),
                },
            )

    def test_tiff_missing_sid(self):
        path = get_file_from_cloud_test_repo([TEST_DIR, "AQA.zip"])
        with self.assertRaises(ValueError):
            WinstonLutz.from_zip(
                path,
                dpi=100,
                axis_mapping={
                    r"AQA_A_03082023.tif": (0, 0, 0),
                    r"AQA_B_03082023.tif": (0, 0, 0),
                },
            )

    def test_missing_axis_mapping(self):
        path = get_file_from_cloud_test_repo([TEST_DIR, "AQA.zip"])
        with self.assertRaises(ValueError):
            WinstonLutz.from_zip(path, dpi=100, sid=1000)


class GeneralTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wl = WinstonLutz.from_demo_images()
        cls.wl.analyze(machine_scale=MachineScale.VARIAN_IEC)

    def test_run_demo(self):
        WinstonLutz.run_demo()  # shouldn't raise

    def test_results(self):
        print(self.wl.results())  # shouldn't raise

    def test_not_yet_analyzed(self):
        wl = WinstonLutz.from_demo_images()
        with self.assertRaises(ValueError):
            wl.results()  # not yet analyzed

        with self.assertRaises(ValueError):
            wl.plot_images()

        with self.assertRaises(ValueError):
            wl.plot_summary()

    def test_str_or_enum(self):
        # shouldn't raise
        self.wl.plot_images("Gantry")
        self.wl.plot_images(Axis.GANTRY)

        self.wl.plot_axis_images("Gantry")
        self.wl.plot_axis_images(Axis.GANTRY)

    def test_bb_shift_instructions(self):
        move = self.wl.bb_shift_instructions()
        self.assertTrue("RIGHT" in move)

        move = self.wl.bb_shift_instructions(couch_vrt=-2, couch_lat=1, couch_lng=100)
        self.assertTrue("RIGHT" in move)
        self.assertTrue("VRT" in move)

    def test_results_data(self):
        data = self.wl.results_data()
        self.assertIsInstance(data, WinstonLutzResult)
        self.assertEqual(
            data.num_couch_images,
            self.wl._get_images(axis=(Axis.COUCH, Axis.REFERENCE))[0],
        )
        self.assertEqual(data.max_2d_cax_to_epid_mm, self.wl.cax2epid_distance("max"))
        self.assertEqual(
            data.median_2d_cax_to_epid_mm, self.wl.cax2epid_distance("median")
        )
        self.assertEqual(
            data.image_details[0].bb_location.x,
            self.wl.images[0].results_data().bb_location.x,
        )

    def test_results_data_as_dict(self):
        data_dict = self.wl.results_data(as_dict=True)
        self.assertIn("pylinac_version", data_dict)
        self.assertEqual(
            data_dict["gantry_3d_iso_diameter_mm"], self.wl.gantry_iso_size
        )
        self.assertIsInstance(data_dict["image_details"][0]["bb_location"], dict)
        self.assertAlmostEqual(
            data_dict["image_details"][0]["bb_location"]["x"],
            self.wl.images[0].bb.x,
            delta=0.02,
        )

    def test_results_data_individual_keys_duplicate(self):
        # lucky for us, the demo set has duplicates already
        data_dict = self.wl.results_data(as_dict=True)
        self.assertEqual(
            len(data_dict["keyed_image_details"]), len(self.wl.images)
        )  # even with duplicates, the # should be the same; we shouldn't be overwriting keys
        self.assertIn("G0.0B0.0P0.0", data_dict["keyed_image_details"].keys())
        self.assertIn("G0.0B0.0P0.0_1", data_dict["keyed_image_details"].keys())

    def test_results_data_individual_keys_precisions(self):
        """Setting precision should be reflected in the keys"""
        wl = WinstonLutz.from_demo_images(axes_precision=0)
        wl.analyze()
        data_dict = wl.results_data(as_dict=True)
        self.assertEqual(
            len(data_dict["keyed_image_details"]), len(self.wl.images)
        )  # even with duplicates, the # should be the same; we shouldn't be overwriting keys
        self.assertIn("G0B0P0", data_dict["keyed_image_details"].keys())
        self.assertIn("G0B0P0_1", data_dict["keyed_image_details"].keys())

    def test_bb_too_far_away_fails(self):
        """BB is >20mm from CAX"""
        file = get_file_from_cloud_test_repo([TEST_DIR, "bb_too_far_away.zip"])
        wl = WinstonLutz.from_zip(file)
        with self.assertRaises(ValueError):
            wl.analyze()

    def test_plot_bb_location(self):
        # shouldn't raise
        self.wl.plot_location()

    def test_detection_conditions_passed_down(self):
        class WL(WinstonLutz):
            # override the default detection conditions
            detection_conditions = [is_round]

        wl = WL.from_demo_images()
        self.assertEqual(len(wl.detection_conditions), 1)
        self.assertEqual(wl.detection_conditions[0], is_round)
        self.assertEqual(wl.detection_conditions, wl.images[0].detection_conditions)


class TestPublishPDF(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wl = WinstonLutz.from_demo_images()
        cls.wl.analyze()

    def test_publish_pdf(self):
        # normal publish; shouldn't raise
        with tempfile.TemporaryFile() as t:
            self.wl.publish_pdf(t)

    def test_publish_w_metadata_and_notes(self):
        with tempfile.TemporaryFile() as t:
            self.wl.publish_pdf(t, notes="stuff", metadata={"Unit": "TB1"})


class TestPlottingSaving(TestCase):
    def setUp(self):
        self.wl = WinstonLutz.from_demo_images()
        self.wl.analyze()

    @classmethod
    def tearDownClass(cls):
        plt.close("all")

    def test_plot(self):
        self.wl.plot_images()  # shouldn't raise
        self.wl.plot_images(axis=Axis.GANTRY)
        self.wl.plot_images(axis=Axis.COLLIMATOR)
        self.wl.plot_images(axis=Axis.COUCH)
        self.wl.plot_images(axis=Axis.GB_COMBO)
        self.wl.plot_images(axis=Axis.GBP_COMBO)

    def test_save_to_stream(self):
        items = self.wl.save_images_to_stream()
        assert isinstance(items, dict)
        assert str(self.wl.images[0]) in items.keys()
        assert len(items) == 15

    def test_plot_split_plots(self):
        figs, names = self.wl.plot_images(show=False, split=True)
        assert isinstance(figs[0], plt.Figure)
        assert isinstance(names[0], str)
        assert len(figs) == 9

    def test_save(self):
        save_file(self.wl.save_summary)
        save_file(self.wl.save_images)

    def test_plot_wo_all_axes(self):
        # test that analyzing images w/o gantry images doesn't fail
        wl_zip = get_file_from_cloud_test_repo([TEST_DIR, "Naming.zip"])
        wl = WinstonLutz.from_zip(wl_zip, use_filenames=True)
        wl.analyze()
        wl.plot_summary()  # shouldn't raise


class WinstonLutzMixin(CloudFileMixin):
    wl: WinstonLutz
    dir_path = ["Winston-Lutz"]
    num_images = 0
    zip = True
    bb_size = 5
    sid: float | None = None
    dpi: float | None = None
    axis_mapping: dict | None = None
    low_density_bb = False
    open_field = False
    gantry_iso_size = 0
    collimator_iso_size = 0
    couch_iso_size = 0
    cax2bb_max_distance = 0
    cax2bb_median_distance = 0
    cax2bb_mean_distance = 0
    epid_deviation = None
    bb_shift_vector = Vector()  # vector to place BB at iso
    machine_scale = MachineScale.IEC61217
    axis_of_rotation = {
        0: Axis.REFERENCE
    }  # fill with as many {image#: known_axis_of_rotation} pairs as desired
    print_results = False
    use_filenames = False

    @classmethod
    def new_instance(cls) -> WinstonLutz:
        filename = cls.get_filename()
        if cls.zip:
            wl = WinstonLutz.from_zip(
                filename,
                use_filenames=cls.use_filenames,
                sid=cls.sid,
                dpi=cls.dpi,
                axis_mapping=cls.axis_mapping,
            )
        else:
            wl = WinstonLutz(
                filename,
                use_filenames=cls.use_filenames,
                sid=cls.sid,
                dpi=cls.dpi,
                axis_mapping=cls.axis_mapping,
            )
        return wl

    @classmethod
    def setUpClass(cls):
        cls.wl = cls.new_instance()
        cls.wl.analyze(
            bb_size_mm=cls.bb_size,
            machine_scale=cls.machine_scale,
            low_density_bb=cls.low_density_bb,
            open_field=cls.open_field,
        )
        if cls.print_results:
            print(cls.wl.results())
            print(cls.wl.bb_shift_vector)

    @classmethod
    def tearDownClass(cls):
        plt.close("all")

    def test_number_of_images(self):
        self.assertEqual(self.num_images, len(self.wl.images))

    def test_gantry_iso(self):
        # test iso size
        self.assertAlmostEqual(
            self.wl.gantry_iso_size, self.gantry_iso_size, delta=0.15
        )

    def test_collimator_iso(self):
        # test iso size
        if self.collimator_iso_size is not None:
            self.assertAlmostEqual(
                self.wl.collimator_iso_size, self.collimator_iso_size, delta=0.15
            )

    def test_couch_iso(self):
        # test iso size
        if self.couch_iso_size is not None:
            self.assertAlmostEqual(
                self.wl.couch_iso_size, self.couch_iso_size, delta=0.15
            )

    def test_epid_deviation(self):
        if self.epid_deviation is not None:
            self.assertAlmostEqual(
                max(self.wl.axis_rms_deviation(Axis.EPID)),
                self.epid_deviation,
                delta=0.15,
            )

    def test_bb_max_distance(self):
        self.assertAlmostEqual(
            self.wl.cax2bb_distance(metric="max"), self.cax2bb_max_distance, delta=0.15
        )

    def test_bb_median_distance(self):
        self.assertAlmostEqual(
            self.wl.cax2bb_distance(metric="median"),
            self.cax2bb_median_distance,
            delta=0.1,
        )

    def test_bb_mean_distance(self):
        self.assertAlmostEqual(
            self.wl.cax2bb_distance(metric="mean"), self.cax2bb_mean_distance, delta=0.1
        )

    def test_bb_shift_vector(self):
        self.assertTrue(
            vector_is_close(self.wl.bb_shift_vector, self.bb_shift_vector, delta=0.15),
            msg=f"The vector {self.wl.bb_shift_vector} is not sufficiently close to vector {self.bb_shift_vector}",
        )

    def test_known_axis_of_rotation(self):
        for idx, axis in self.axis_of_rotation.items():
            v_axis = self.wl.images[idx].variable_axis
            self.assertEqual(axis, v_axis)

    def test_bb_size_doesnt_change_result(self):
        """Test that changing the tolerance doesn't change the result"""
        original_max = self.wl.cax2bb_distance(metric="max")
        original_mean = self.wl.cax2bb_distance(metric="mean")
        original_gantry_iso = self.wl.gantry_iso_size
        # re-analyze w/ same settings
        for tolerance in (-2, -1, 1, 2, 3):
            new_wl = self.new_instance()
            # set a min here for cases where the bb is very small (e.g. 1.5mm)
            new_wl.analyze(
                bb_size_mm=max((self.bb_size + tolerance, 1.5)),
                machine_scale=self.machine_scale,
                low_density_bb=self.low_density_bb,
                open_field=self.open_field,
            )
            new_max = new_wl.cax2bb_distance(metric="max")
            new_mean = new_wl.cax2bb_distance(metric="mean")
            self.assertAlmostEqual(original_max, new_max, delta=0.1)
            self.assertAlmostEqual(original_mean, new_mean, delta=0.1)
            self.assertAlmostEqual(
                original_gantry_iso, new_wl.gantry_iso_size, delta=0.1
            )


class WLDemo(WinstonLutzMixin, TestCase):
    num_images = 17
    gantry_iso_size = 1
    collimator_iso_size = 1.2
    couch_iso_size = 2.3
    cax2bb_max_distance = 1.2
    cax2bb_median_distance = 0.7
    cax2bb_mean_distance = 0.6
    machine_scale = MachineScale.VARIAN_IEC
    epid_deviation = 1.3
    axis_of_rotation = {0: Axis.REFERENCE}
    bb_shift_vector = Vector(x=0.4, y=-0.4, z=-0.2)
    delete_file = False

    @classmethod
    def setUpClass(cls):
        cls.wl = cls.new_instance()
        cls.wl.analyze(machine_scale=cls.machine_scale)

    @classmethod
    def new_instance(cls) -> WinstonLutz:
        return WinstonLutz.from_demo_images()

    def test_different_scale_has_different_shift(self):
        assert "RIGHT" in self.wl.bb_shift_instructions()
        assert self.wl.bb_shift_vector.x > 0.1
        new_wl = WinstonLutz.from_demo_images()
        new_wl.analyze(machine_scale=MachineScale.IEC61217)
        assert new_wl.bb_shift_vector.x < 0.1
        assert "LEFT" in new_wl.bb_shift_instructions()

    def test_multiple_analyses_gives_same_result(self):
        original_vector = copy.copy(self.wl.bb_shift_vector)
        # re-analyze w/ same settings
        self.wl.analyze(machine_scale=self.machine_scale)
        new_vector = self.wl.bb_shift_vector
        assert vector_is_close(original_vector, new_vector, delta=0.05)


class WLPerfect30x8(WinstonLutzMixin, TestCase):
    """30x30mm field, 8mm BB"""

    file_name = "perfect_WL_30x8.zip"
    num_images = 4
    gantry_iso_size = 0
    collimator_iso_size = 0
    couch_iso_size = 0
    cax2bb_max_distance = 0
    cax2bb_median_distance = 0
    epid_deviation = 0
    bb_shift_vector = Vector()


class WLPerfect30x2(WinstonLutzMixin, TestCase):
    """30x30mm field, 2mm BB"""

    file_name = "perfect_WL_30x2mm.zip"
    num_images = 4
    gantry_iso_size = 0
    collimator_iso_size = 0
    couch_iso_size = 0
    cax2bb_max_distance = 0
    cax2bb_median_distance = 0
    epid_deviation = 0
    bb_shift_vector = Vector()
    bb_size = 2


class WLPerfect10x4(WinstonLutzMixin, TestCase):
    """10x10mm field, 4mm BB"""

    file_name = "perfect_WL_10x4.zip"
    num_images = 4
    gantry_iso_size = 0
    collimator_iso_size = 0
    couch_iso_size = 0
    cax2bb_max_distance = 0
    cax2bb_median_distance = 0
    epid_deviation = 0
    bb_shift_vector = Vector()


class WLNoisy30x5(WinstonLutzMixin, TestCase):
    """30x30mm field, 5mm BB. S&P noise added"""

    file_name = "noisy_WL_30x5.zip"
    num_images = 4
    gantry_iso_size = 0.08
    collimator_iso_size = 0
    couch_iso_size = 0
    cax2bb_max_distance = 0
    cax2bb_median_distance = 0
    epid_deviation = 0
    bb_shift_vector = Vector()


class WLLateral3mm(WinstonLutzMixin, TestCase):
    # verified independently
    file_name = "lat3mm.zip"
    num_images = 4
    gantry_iso_size = 0.5
    cax2bb_max_distance = 3.8
    cax2bb_median_distance = 2.3
    cax2bb_mean_distance = 2.3
    bb_shift_vector = Vector(x=-3.6, y=0.5, z=0.6)


class WLReferenceIsLargestRMS(WinstonLutzMixin, TestCase):
    """If the reference image had the largest error, it was not reported"""

    # dataset has 1mm error on first image and 0 at others

    file_name = "Ref_is_largest_error.zip"
    num_images = 3
    gantry_iso_size = 0
    cax2bb_max_distance = 1
    cax2bb_median_distance = 0
    cax2bb_mean_distance = 0.33
    bb_shift_vector = Vector(x=1, y=0, z=0)

    def test_largest_error_at_ref_is_reported(self):
        self.assertAlmostEqual(
            self.wl.results_data().max_gantry_rms_deviation_mm, 1, places=2
        )


class WLLongitudinal3mm(WinstonLutzMixin, TestCase):
    # verified independently
    file_name = "lng3mm.zip"
    num_images = 4
    gantry_iso_size = 0.5
    cax2bb_max_distance = 3.9
    cax2bb_median_distance = 3.7
    cax2bb_mean_distance = 3.7
    bb_shift_vector = Vector(x=-0.63, y=3.6, z=0.6)


class WLVertical3mm(WinstonLutzMixin, TestCase):
    file_name = "vrt3mm.zip"
    num_images = 4
    gantry_iso_size = 0.5
    cax2bb_max_distance = 3.8
    cax2bb_median_distance = 2.3
    cax2bb_mean_distance = 2.3
    bb_shift_vector = Vector(x=-0.5, y=0.5, z=3.6)
    print_results = True


class WLDontUseFileNames(WinstonLutzMixin, TestCase):
    file_name = "Naming.zip"
    num_images = 4
    gantry_iso_size = 0.3
    cax2bb_max_distance = 0.9
    cax2bb_median_distance = 0.8
    cax2bb_mean_distance = 0.8
    bb_shift_vector = Vector(x=-0.4, y=0.6, z=0.6)
    axis_of_rotation = {
        0: Axis.REFERENCE,
        1: Axis.GANTRY,
        2: Axis.GANTRY,
        3: Axis.GANTRY,
    }


class WLUseFileNames(WinstonLutzMixin, TestCase):
    file_name = "Naming.zip"
    use_filenames = True
    num_images = 4
    collimator_iso_size = 1.2
    cax2bb_max_distance = 0.9
    cax2bb_median_distance = 0.8
    cax2bb_mean_distance = 0.8
    bb_shift_vector = Vector(y=0.6)
    axis_of_rotation = {
        0: Axis.COLLIMATOR,
        1: Axis.COLLIMATOR,
        2: Axis.COLLIMATOR,
        3: Axis.COLLIMATOR,
    }


class WLBadFilenames(TestCase):
    def test_bad_filenames(self):
        # tests_basic that using filenames with incorrect syntax will fail
        wl_dir = get_file_from_cloud_test_repo([TEST_DIR, "Bad-Names.zip"])
        with self.assertRaises(ValueError):
            wl = WinstonLutz.from_zip(wl_dir, use_filenames=True)
            wl.analyze()


class KatyiX0(WinstonLutzMixin, TestCase):
    # independently verified
    file_name = ["Katy iX", "0.zip"]
    num_images = 17
    gantry_iso_size = 1
    collimator_iso_size = 1
    couch_iso_size = 1.3
    cax2bb_max_distance = 1.2
    cax2bb_median_distance = 0.8
    cax2bb_mean_distance = 0.7
    machine_scale = MachineScale.VARIAN_IEC
    bb_shift_vector = Vector(x=-0.5, y=0.4, z=-0.5)
    print_results = True


class KatyiX1(WinstonLutzMixin, TestCase):
    file_name = ["Katy iX", "1.zip"]
    num_images = 17
    gantry_iso_size = 1.1
    collimator_iso_size = 0.7
    couch_iso_size = 0.6
    cax2bb_max_distance = 1.2
    cax2bb_median_distance = 0.3
    cax2bb_mean_distance = 0.4
    bb_shift_vector = Vector(x=0.3, y=-0.2, z=0.3)


class KatyiX2(WinstonLutzMixin, TestCase):
    file_name = ["Katy iX", "2.zip"]
    num_images = 17
    gantry_iso_size = 0.9
    collimator_iso_size = 0.8
    couch_iso_size = 1.5
    cax2bb_max_distance = 1.1
    cax2bb_median_distance = 0.5
    cax2bb_mean_distance = 0.6
    machine_scale = MachineScale.VARIAN_IEC
    bb_shift_vector = Vector(x=0.4, y=-0.1, z=0.1)


class KatyiX3(WinstonLutzMixin, TestCase):
    file_name = ["Katy iX", "3 (with crosshair).zip"]
    num_images = 17
    gantry_iso_size = 1.1
    collimator_iso_size = 1.3
    couch_iso_size = 1.8
    cax2bb_max_distance = 1.25
    cax2bb_median_distance = 0.8
    cax2bb_mean_distance = 0.75
    machine_scale = MachineScale.VARIAN_IEC
    bb_shift_vector = Vector(x=-0.3, y=0.4, z=-0.5)


class KatyTB0(WinstonLutzMixin, TestCase):
    file_name = ["Katy TB", "0.zip"]
    num_images = 17
    gantry_iso_size = 0.9
    collimator_iso_size = 0.8
    couch_iso_size = 1.3
    cax2bb_max_distance = 1.07
    cax2bb_median_distance = 0.8
    cax2bb_mean_distance = 0.8
    machine_scale = MachineScale.VARIAN_IEC
    axis_of_rotation = {-1: Axis.REFERENCE}
    bb_shift_vector = Vector(x=-0.7, y=-0.1, z=-0.2)


class KatyTB1(WinstonLutzMixin, TestCase):
    file_name = ["Katy TB", "1.zip"]
    num_images = 16
    gantry_iso_size = 0.9
    collimator_iso_size = 0.8
    couch_iso_size = 1.1
    cax2bb_max_distance = 1
    cax2bb_median_distance = 0.7
    cax2bb_mean_distance = 0.6
    axis_of_rotation = {0: Axis.GANTRY}
    machine_scale = MachineScale.VARIAN_IEC
    bb_shift_vector = Vector(x=-0.6, y=-0.2)


class KatyTB2(WinstonLutzMixin, TestCase):
    file_name = ["Katy TB", "2.zip"]
    num_images = 17
    gantry_iso_size = 1
    collimator_iso_size = 0.7
    couch_iso_size = 0.7
    cax2bb_max_distance = 1.1
    cax2bb_median_distance = 0.4
    cax2bb_mean_distance = 0.5
    axis_of_rotation = {-1: Axis.REFERENCE}
    bb_shift_vector = Vector(x=0.0, y=-0.2, z=-0.6)


class ChicagoTBFinal(WinstonLutzMixin, TestCase):
    # verified independently
    file_name = ["Chicago", "WL-Final_C&G&C_Final.zip"]
    num_images = 17
    gantry_iso_size = 0.91
    collimator_iso_size = 0.1
    couch_iso_size = 0.3
    cax2bb_max_distance = 0.5
    cax2bb_median_distance = 0.3
    cax2bb_mean_distance = 0.3
    axis_of_rotation = {0: Axis.GBP_COMBO}
    bb_shift_vector = Vector(y=0.1)


class ChicagoTB52915(WinstonLutzMixin, TestCase):
    file_name = ["Chicago", "WL_05-29-15_Final.zip"]
    num_images = 16
    gantry_iso_size = 0.6
    collimator_iso_size = 0.3
    couch_iso_size = 0.3
    cax2bb_max_distance = 0.5
    cax2bb_median_distance = 0.3
    cax2bb_mean_distance = 0.3
    bb_shift_vector = Vector(z=0.2)


class TrueBeam3120213(WinstonLutzMixin, TestCase):
    file_name = ["TrueBeam 3", "120213.zip"]
    num_images = 26
    cax2bb_max_distance = 0.9
    cax2bb_median_distance = 0.35
    cax2bb_mean_distance = 0.4
    gantry_iso_size = 1.1
    collimator_iso_size = 0.7
    couch_iso_size = 0.7
    bb_shift_vector = Vector(x=-0.1, y=-0.2, z=0.2)


class SugarLandiX2015(WinstonLutzMixin, TestCase):
    file_name = ["Sugarland iX", "2015", "Lutz2.zip"]
    num_images = 17
    gantry_iso_size = 1.3
    collimator_iso_size = 0.5
    couch_iso_size = 1.3
    cax2bb_max_distance = 1.67
    cax2bb_median_distance = 1.05
    cax2bb_mean_distance = 1.1
    machine_scale = MachineScale.VARIAN_IEC
    bb_shift_vector = Vector(x=0.4, y=-0.7, z=0.1)


class BayAreaiX0(WinstonLutzMixin, TestCase):
    # aka the demo images
    file_name = ["Bay Area iX", "0.zip"]
    num_images = 17
    gantry_iso_size = 1
    collimator_iso_size = 1.1
    couch_iso_size = 2.3
    cax2bb_max_distance = 1.25
    cax2bb_median_distance = 0.6
    cax2bb_mean_distance = 0.6
    machine_scale = MachineScale.VARIAN_IEC
    bb_shift_vector = Vector(x=0.3, y=-0.4, z=-0.2)


class DAmoursElektaOffset(WinstonLutzMixin, TestCase):
    """An Elekta dataset, with the BB centered."""

    file_name = ["Michel DAmours - WLGantry_Offset_x=-1cm,y=+1cm,z=-1cm.zip"]
    num_images = 8
    gantry_iso_size = 1.1
    cax2bb_max_distance = 17.5
    cax2bb_median_distance = 14.3
    cax2bb_mean_distance = 13.8
    bb_shift_vector = Vector(x=10.2, y=-9.2, z=-11.1)  # independently verified


class DAmoursElektaXOffset(WinstonLutzMixin, TestCase):
    """An Elekta dataset, with the BB centered."""

    file_name = ["Michel D'Amours - WL_Shift_x=+1cm.zip"]
    num_images = 8
    gantry_iso_size = 1.1
    cax2bb_max_distance = 9.5
    cax2bb_median_distance = 6.9
    cax2bb_mean_distance = 6
    bb_shift_vector = Vector(x=-9.5, y=0.3, z=0.1)  # independently verified


class DAmoursElektaCentered(WinstonLutzMixin, TestCase):
    """An Elekta dataset, with the BB centered."""

    file_name = ["Michel D'Amours - GantryWL_BBCentered.zip"]
    num_images = 8
    gantry_iso_size = 1.1
    collimator_iso_size = None
    couch_iso_size = None
    cax2bb_max_distance = 0.8
    cax2bb_median_distance = 0.5
    cax2bb_mean_distance = 0.6
    bb_shift_vector = Vector(y=0.4)


class DeBr6XElekta(WinstonLutzMixin, TestCase):
    """An Elekta dataset, with the BB centered."""

    file_name = ["DeBr", "6X_Elekta_Ball_Bearing.zip"]
    num_images = 8
    gantry_iso_size = 1.8
    collimator_iso_size = 1.8
    couch_iso_size = None
    cax2bb_max_distance = 1.0
    cax2bb_median_distance = 0.7
    cax2bb_mean_distance = 0.6
    bb_shift_vector = Vector(x=0.4, y=-0.2)


class LargeFieldCouchPresent(WinstonLutzMixin, TestCase):
    """A very large field where the couch is present"""

    file_name = ["large_field_couch_present.zip"]
    num_images = 4
    gantry_iso_size = 0.8
    collimator_iso_size = None
    couch_iso_size = None
    cax2bb_max_distance = 1.3
    cax2bb_median_distance = 1
    cax2bb_mean_distance = 1
    bb_shift_vector = Vector(x=0.5, y=-0.7, z=0.8)


class LowDensityBB(WinstonLutzMixin, TestCase):
    """An air-like BB where the signal increases vs attenuates. Requires passing the right parameter"""

    file_name = ["low_density_bb_simulated.zip"]
    num_images = 4
    low_density_bb = True
    gantry_iso_size = 0.0
    collimator_iso_size = None
    couch_iso_size = None
    cax2bb_max_distance = 0
    cax2bb_median_distance = 0
    cax2bb_mean_distance = 0
    bb_shift_vector = Vector(x=0, y=0, z=0)


class kVImages(WinstonLutzMixin, TestCase):
    """kV image-based WL set. Have to set the parameters correctly"""

    file_name = ["kV_cube_images.zip"]
    num_images = 4
    low_density_bb = True
    open_field = True
    bb_size = 2
    gantry_iso_size = 0.15
    collimator_iso_size = None
    couch_iso_size = None
    cax2bb_max_distance = 0.26
    cax2bb_median_distance = 0.18
    cax2bb_mean_distance = 0.18
    axis_of_rotation = {-1: Axis.REFERENCE}
    bb_shift_vector = Vector(x=-0.24, y=0, z=0)


class TIFFImages(WinstonLutzMixin, TestCase):
    """Tiff image set. Hell hath frozen over"""

    file_name = ["AQA.zip"]
    num_images = 2
    sid = 1000
    dpi = 200
    # I don't know the actual axis values, this is just to get a result
    axis_mapping = {
        "AQA_A_03082023.tif": (0, 0, 0),
        "AQA_B_03082023.tif": (90, 0, 0),
    }
    bb_size = 30
    gantry_iso_size = 0.15
    collimator_iso_size = None
    couch_iso_size = None
    cax2bb_max_distance = 1.14
    cax2bb_median_distance = 0.82
    cax2bb_mean_distance = 0.8
    axis_of_rotation = {-1: Axis.GANTRY}
    bb_shift_vector = Vector(x=1.1, y=0.34, z=-0.30)


class VarianBBkV(WinstonLutzMixin, TestCase):
    """kV image-based WL set using the super tiny Varian BB. Have to set the parameters correctly"""

    file_name = ["Varian_BB_kV.zip"]
    num_images = 4
    low_density_bb = True
    open_field = True
    bb_size = 1.5
    gantry_iso_size = 0.15
    collimator_iso_size = None
    couch_iso_size = None
    cax2bb_max_distance = 0.42
    cax2bb_median_distance = 0.31
    cax2bb_mean_distance = 0.28
    axis_of_rotation = {-1: Axis.REFERENCE}
    bb_shift_vector = Vector(x=-0.24, y=0.2, z=-0.15)


def _create_sigmoidal_array(array: np.ndarray, steepness: float = 1.0):
    # Apply the sigmoid function with a given steepness
    return 1 / (1 + np.exp(-steepness * array))


def create_sphere(
    radius: float,
    shape: tuple[int, int, int],
    offset: tuple[float, float, float] = (0, 0, 0),
) -> np.ndarray:
    """Create a 3D numpy array with a BB inside. Thanks ChatGPT."""
    # axis 0: positive -> left, offset, 1: positive -> up, 2: positive -> in
    # Calculate the center of the array
    center = np.array(shape) / 2 - 0.5 + np.array(offset)
    # Create a grid of indices
    indices = np.indices(shape)
    # Calculate the distance of each point from the center
    distances = np.sqrt(
        np.sum((indices - center[:, np.newaxis, np.newaxis, np.newaxis]) ** 2, axis=0)
    )
    # Set values inside the sphere to the distance from the center
    arr = radius - distances
    arr[arr <= 0] = 0  # Clamp negative intensity values to 0
    # Apply a sigmoidal function to the array to make the edges sharper and
    # the BB more "flat" in the center
    arr = _create_sigmoidal_array(arr)
    arr *= 1000  # Scale intensity to a reasonable range
    arr -= arr.min()  # set background to 0
    return arr


def create_wl_dicom_stack(
    bb_radius: float = 5,
    dicom_shape: tuple[int, int, int] = (100, 100, 100),
    bb_offset: tuple[float, float, float] = (0, 0, 0),
) -> Path:
    sphere_array = create_sphere(bb_radius, dicom_shape, offset=bb_offset)
    return create_dicom_files_from_3d_array(sphere_array)


class GeneratedWLCBCT:
    bb_size = 5
    bb_offset = {"left": 0, "up": 0, "in": 0}
    array_shape = (100, 100, 100)
    zip = False
    raw_pixels = True

    @classmethod
    def get_filename(cls) -> Path:
        # generate the fake cbct
        return create_wl_dicom_stack(
            bb_radius=cls.bb_size,
            dicom_shape=cls.array_shape,
            bb_offset=(cls.bb_offset["left"], cls.bb_offset["up"], cls.bb_offset["in"]),
        )


class CBCTWinstonLutzMixin(WinstonLutzMixin):
    low_density_bb = True
    open_field = True
    num_images = 4
    collimator_iso_size = 0
    couch_iso_size = 0
    gantry_iso_size = 0
    raw_pixels = False

    @classmethod
    def new_instance(cls) -> WinstonLutz:
        filename = cls.get_filename()
        if cls.zip:
            wl = WinstonLutz.from_cbct_zip(
                filename,
                use_filenames=cls.use_filenames,
                sid=cls.sid,
                dpi=cls.dpi,
                axis_mapping=cls.axis_mapping,
                raw_pixels=cls.raw_pixels,
            )
        else:
            wl = WinstonLutz.from_cbct(
                filename,
                use_filenames=cls.use_filenames,
                sid=cls.sid,
                dpi=cls.dpi,
                axis_mapping=cls.axis_mapping,
                raw_pixels=cls.raw_pixels,
            )
        return wl

    @classmethod
    def setUpClass(cls):
        cls.wl = cls.new_instance()
        cls.wl.analyze(
            bb_size_mm=cls.bb_size,
            machine_scale=cls.machine_scale,
            low_density_bb=cls.low_density_bb,
            open_field=cls.open_field,
        )
        if cls.print_results:
            print(cls.wl.results())
            print(cls.wl.bb_shift_vector)


class TestFrenchCBCT(CBCTWinstonLutzMixin, TestCase):
    file_name = ["cbct_wl_real.zip"]
    cax2bb_max_distance = 0.23
    cax2bb_median_distance = 0.22
    cax2bb_mean_distance = 0.22
    machine_scale = MachineScale.VARIAN_IEC
    bb_shift_vector = Vector(x=0.2, y=0, z=-0.2)


class TestPerfectCBCT(GeneratedWLCBCT, CBCTWinstonLutzMixin, TestCase):
    bb_offset = {"left": 0, "up": 0, "in": 0}
    cax2bb_max_distance = 0
    cax2bb_median_distance = 0
    cax2bb_mean_distance = 0
    bb_shift_vector = Vector(x=0, y=0, z=0)


class TestOffsetLeftCBCT(GeneratedWLCBCT, CBCTWinstonLutzMixin, TestCase):
    bb_offset = {"left": 5, "up": 0, "in": 0}
    cax2bb_max_distance = 5
    cax2bb_median_distance = 2.5
    cax2bb_mean_distance = 2.5
    bb_shift_vector = Vector(x=-5, y=0, z=0)


class TestOffsetDownCBCT(GeneratedWLCBCT, CBCTWinstonLutzMixin, TestCase):
    bb_offset = {"left": 0, "up": -5, "in": 0}
    cax2bb_max_distance = 5
    cax2bb_median_distance = 2.5
    cax2bb_mean_distance = 2.5
    bb_shift_vector = Vector(x=0, y=0, z=5)


class TestOffsetInCBCT(GeneratedWLCBCT, CBCTWinstonLutzMixin, TestCase):
    bb_offset = {"left": 0, "up": 0, "in": 5}
    cax2bb_max_distance = 5
    cax2bb_median_distance = 5
    cax2bb_mean_distance = 5
    bb_shift_vector = Vector(x=0, y=-5, z=0)
