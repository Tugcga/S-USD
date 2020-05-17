from pxr import UsdGeom, Usd, Sdf
import prim_xform
import materials
import utils
import imp


def set_pointcloud_at_frame(pointcloud_geometry, usd_pointcloud, usd_points_prim, frame=None):
    xsi_pp = pointcloud_geometry.GetICEAttributeFromName("PointPosition")
    xsi_size = pointcloud_geometry.GetICEAttributeFromName("Size")

    xsi_pp_data = xsi_pp.DataArray
    xsi_size_data = xsi_size.DataArray

    usd_points = usd_pointcloud.CreatePointsAttr()
    usd_width = usd_pointcloud.CreateWidthsAttr()

    data_points = []
    data_width = []

    for index in range(len(xsi_pp_data)):
        data_points.append(utils.vector_to_tuple(xsi_pp_data[index]))
        data_width.append(xsi_size_data[index])

    if frame is None:
        usd_points.Set(data_points)
        usd_width.Set(data_width)
    else:
        usd_points.Set(data_points, Usd.TimeCode(frame))
        usd_width.Set(data_width, Usd.TimeCode(frame))

    # set bounding box
    usd_extent = usd_points_prim.CreateAttribute("extent", Sdf.ValueTypeNames.Float3Array)
    if frame is None:
        usd_extent.Set(utils.get_bounding_box(data_points))
    else:
        usd_extent.Set(utils.get_bounding_box(data_points), Usd.TimeCode(frame))


def add_pointcloud(app, params, path_for_objects, stage, pointcloud_object, materials_opt, root_path, progress_bar=None):
    imp.reload(prim_xform)
    imp.reload(materials)
    imp.reload(utils)

    opt_animation = params.get("animation", None)
    usd_xform, ref_stage, ref_stage_asset = prim_xform.add_xform(app, params, path_for_objects, True, stage, pointcloud_object, root_path)
    usd_points = UsdGeom.Points.Define(ref_stage, str(usd_xform.GetPath()) + "/" + "Pointcloud")
    usd_points_prim = ref_stage.GetPrimAtPath(usd_points.GetPath())

    materials.add_material(materials_opt, pointcloud_object.Material, ref_stage, ref_stage_asset, usd_xform, usd_points_prim)

    if opt_animation is None:
        set_pointcloud_at_frame(pointcloud_object.GetActivePrimitive3().Geometry, usd_points, usd_points_prim)
    else:
        for frame in range(opt_animation[0], opt_animation[1] + 1):
            if progress_bar is not None:
                progress_bar.Caption = utils.build_export_object_caption(pointcloud_object, frame)
            set_pointcloud_at_frame(pointcloud_object.GetActivePrimitive3(frame).GetGeometry3(frame), usd_points, usd_points_prim, frame=frame)

    return stage.GetPrimAtPath(root_path + str(usd_xform.GetPath()))
