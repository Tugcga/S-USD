from pxr import UsdGeom, Usd, Sdf, UsdShade
import os
import icecache
import prim_xform
import materials
import utils
import imp

DEBUG_MODE = False

# ---------------------------------------------------------
# ----------------------export-----------------------------


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
        data_width.append(xsi_size_data[index] if index < len(xsi_size_data) else 0.0)

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
    if DEBUG_MODE:
        imp.reload(prim_xform)
        imp.reload(materials)
        imp.reload(utils)

    opt_animation = params.get("animation", None)
    usd_xform, ref_stage, ref_stage_asset = prim_xform.add_xform(app, params, path_for_objects, True, stage, pointcloud_object, root_path)
    usd_points = UsdGeom.Points.Define(ref_stage, str(usd_xform.GetPath()) + "/" + "Pointcloud")
    usd_points_prim = ref_stage.GetPrimAtPath(usd_points.GetPath())

    materials.add_material(materials_opt, pointcloud_object.Material, ref_stage, ref_stage_asset, usd_xform, usd_points_prim)
    opt = params.get("options", {})

    if opt_animation is None or not utils.is_poincloud_animated(pointcloud_object, opt_animation):
        set_pointcloud_at_frame(pointcloud_object.GetActivePrimitive3().Geometry, usd_points, usd_points_prim)
    else:
        for frame in range(opt_animation[0], opt_animation[1] + 1):
            if progress_bar is not None:
                progress_bar.Caption = utils.build_export_object_caption(pointcloud_object, frame)
            if opt.get("force_change_frame", False):
                app.SetValue("PlayControl.Current", frame, "")
                app.SetValue("PlayControl.Key", frame, "")
            set_pointcloud_at_frame(pointcloud_object.GetActivePrimitive3(frame).GetGeometry3(frame), usd_points, usd_points_prim, frame=frame)

    return stage.GetPrimAtPath(root_path + str(usd_xform.GetPath()))


# ---------------------------------------------------------
# ----------------------import-----------------------------


def split_positions_to_strands_and_points(raw_positions, segment_length):
    strands = []
    points = []
    current_strand = 0
    in_strand_index = 0
    one_strand = []
    for pos in raw_positions:
        if in_strand_index == 0:
            points.append([pos[0], pos[1], pos[2]])
        else:
            one_strand.append([pos[0], pos[1], pos[2]])
        in_strand_index += 1
        if in_strand_index == segment_length[current_strand]:
            strands.append(one_strand)
            one_strand = []
            in_strand_index = 0
            current_strand += 1

    return strands, points


def write_ice_cache_at_frame(folder_path, object_name, raw_points, width_data, segments_data, frame=None):
    if DEBUG_MODE:
        imp.reload(icecache)

    if segments_data is not None:
        strands_data, points_data = split_positions_to_strands_and_points(raw_points, segments_data)
        width_data = utils.extract_subarray(width_data, segments_data)
    else:
        points_data = [[p[0], p[1], p[2]] for p in raw_points]

    nb_particles = len(points_data)
    ic = icecache.ICECache(nb_particles)
    ic.add_point_position(points_data)
    ic.add_scalar("Size", width_data)
    if segments_data is not None:
        ic.add_strand_position(strands_data)
    ic.write(folder_path + object_name + ("_" + str(frame) if frame is not None else "") + ".icecache")


def write_ice_cache(usd_pointcloud, is_strands, xsi_object, project_path, file_name, up_key, ignore_tfm):
    folder_path = project_path + "\\Simulation\\usd_cache\\" + file_name + "\\"
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

    segments_data = None

    if is_constant_points:
        in_tfm = usd_pointcloud.GetLocalTransformation()
        if ignore_tfm is False and utils.is_matrices_are_different_arrays(in_tfm, [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]) is False:
            ignore_tfm = True

        tfm_positions = usd_points.Get() if ignore_tfm else [utils.vector_mult_to_matrix(p, in_tfm) for p in usd_points.Get()]
        raw_positions = tfm_positions if up_key is "Y" else [[p[0], p[2], p[1]] for p in tfm_positions]
        if is_strands:
            if is_constant_segments:
                segments_data = usd_segments.Get()
            else:
                segments_data = usd_segments.Get(0)
        if is_constant_widths:
            width_data = usd_width.Get()
        else:
            width_data = usd_width.Get(width_times[0])
        write_ice_cache_at_frame(folder_path, xsi_object.Name, raw_positions, width_data, segments_data)
    else:
        for frame in point_times:
            frame_ignore_tfm = ignore_tfm
            in_tfm = usd_pointcloud.GetLocalTransformation(frame)
            if frame_ignore_tfm is False and utils.is_matrices_are_different_arrays(in_tfm, [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]) is False:
                frame_ignore_tfm = True

            tfm_positions = usd_points.Get(frame) if frame_ignore_tfm else [utils.vector_mult_to_matrix(p, in_tfm) for p in usd_points.Get(frame)]
            raw_positions = tfm_positions if up_key is "Y" else [[p[0], p[2], p[1]] for p in tfm_positions]
            if is_strands:
                if is_constant_segments:
                    segments_data = usd_segments.Get()
                else:
                    segments_data = usd_segments.Get(frame)
            if is_constant_widths:
                width_data = usd_width.Get()
            else:
                width_data = usd_width.Get(frame)
            write_ice_cache_at_frame(folder_path, xsi_object.Name, raw_positions, width_data, segments_data, frame=int(frame + 0.5))

    return is_constant_points


def build_ice_tree(app, xsi_points, is_constant, file_name):
    tree = app.ApplyOp("ICETree", xsi_points, "siNode", "", "", 0)[0]
    node = app.AddICENode("$XSI_DSPRESETS\\ICENodes\\CacheOnFileNode", tree)

    # set parameters
    app.SetValue(node.FullName + ".FilePath", "[project path]/Simulation/usd_cache/" + file_name + "/", "")
    app.SetValue(node.FullName + ".FileName", "[object]" if is_constant else "[object]_[frame]", "")

    # set read
    app.SetValue(node.FullName + ".filemode", 2, "")

    # execute
    app.ConnectICENodes(tree.FullName + ".port1", node.FullName + ".execute")


def emit_pointcloud(app, options, pointloud_name, usd_tfm, visibility, usd_prim, is_strands, xsi_parent, is_simple=False):
    '''if is_simple is True, then we should ignore in-object ransform
    '''
    if DEBUG_MODE:
        imp.reload(materials)
        imp.reload(utils)

    usd_object = UsdGeom.BasisCurves(usd_prim) if is_strands else UsdGeom.Points(usd_prim)
    xsi_points = app.GetPrim("PointCloud", pointloud_name, xsi_parent)

    if options.get("is_materials", False):
        usd_material = UsdShade.MaterialBindingAPI(usd_prim).GetDirectBinding().GetMaterial()
        xsi_material = materials.import_material(app, usd_material, library_name=options["file_name"])
        if xsi_material is not None:
            app.AssignMaterial(xsi_material.FullName + "," + xsi_points.FullName)

    utils.set_xsi_transform(app, xsi_points, usd_tfm, up_key=options["up_axis"])
    utils.set_xsi_visibility(xsi_points, visibility)
    if "project_path" in options:
        is_constant = write_ice_cache(usd_object, is_strands, xsi_points, options["project_path"], options["file_name"], options["up_axis"], is_simple)
        # build ice-tree with caching node
        build_ice_tree(app, xsi_points, is_constant, options["file_name"])

    return xsi_points
