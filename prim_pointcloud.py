from pxr import UsdGeom, Usd, Sdf
import os
import icecache
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


def write_ice_cache_at_frame(folder_path, object_name, points_data, width_data, strands_data, frame=None):
    nb_particles = len(points_data)
    ic = icecache.icecache(nb_particles)
    ic.addPointPosition(points_data)
    ic.addScalar("Size", width_data)
    # ic.addVector3("StrandPosition", strands_data)
    ic.write(folder_path + object_name + ("_" + str(frame) if frame is not None else "") + ".icecache")


def write_ice_cache(usd_pointcloud, is_strands, xsi_object, project_path):
    folder_path = project_path + "\\Simulation\\usd_cache\\"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    usd_points = usd_pointcloud.GetPointsAttr()
    point_times = usd_points.GetTimeSamples()
    usd_width = usd_pointcloud.GetWidthsAttr()
    width_times = usd_width.GetTimeSamples()

    if is_strands:
        usd_segments = usd_pointcloud.GetCurveVertexCountsAttr()
        segments_times = usd_segments.GetTimeSamples()

    is_constant_points = len(point_times) <= 1
    is_constant_widths = len(width_times) <= 1
    if is_strands:
        is_constant_segments = len(segments_times) <= 1

    if is_constant_points:
        points_data = usd_points.Get()
        # for strands we use as point positions onlt each segment poit
        if is_strands:
            if is_constant_segments:
                segments_data = usd_segments.Get()
            else:
                segments_data = usd_segments.Get(0)
            # extract strands data
            strands_data = [v for v in points_data]
            points_data = utils.extract_subarray(points_data, segments_data)
        # get the first width values
        if is_constant_widths:
            width_data = usd_width.Get()
        else:
            width_data = usd_width.Get(width_times[0])

        if is_strands:
            width_data = utils.extract_subarray(width_data, segments_data)
        write_ice_cache_at_frame(folder_path, xsi_object.Name, points_data, width_data, strands_data)
    else:
        for frame in point_times:
            points_data = usd_points.Get(frame)
            if is_constant_widths:
                width_data = usd_width.Get()
            else:
                # here we assume that animation samples of the width are the same as for points
                width_data = usd_width.Get(frame)
            write_ice_cache_at_frame(folder_path, xsi_object.Name, points_data, width_data, None, frame=int(frame + 0.5))
    return is_constant_points


def build_ice_tree(app, xsi_points, is_constant):
    tree = app.ApplyOp("ICETree", xsi_points, "siNode", "", "", 0)[0]
    node = app.AddICENode("$XSI_DSPRESETS\\ICENodes\\CacheOnFileNode", tree)

    # set parameters
    app.SetValue(node.FullName + ".FilePath", "[project path]/Simulation/usd_cache", "")
    app.SetValue(node.FullName + ".FileName", "[object]" if is_constant else "[object]_[frame]", "")

    # set read
    app.SetValue(node.FullName + ".filemode", 2, "")

    # execute
    app.ConnectICENodes(tree.FullName + ".port1", node.FullName + ".execute")


def emit_pointcloud(app, options, pointloud_name, usd_tfm, visibility, usd_prim, is_strands, xsi_parent):
    imp.reload(utils)
    usd_object = UsdGeom.BasisCurves(usd_prim) if is_strands else UsdGeom.Points(usd_prim)
    xsi_points = app.GetPrim("PointCloud", pointloud_name, xsi_parent)
    utils.set_xsi_transform(app, xsi_points, usd_tfm)
    utils.set_xsi_visibility(xsi_points, visibility)
    if "project_path" in options:
        is_constant = write_ice_cache(usd_object, is_strands, xsi_points, options["project_path"])
        # build ice-tree with caching node
        build_ice_tree(app, xsi_points, is_constant)

    return xsi_points
