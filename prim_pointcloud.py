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


def read_points(usd_pointcloud):
    to_return = []
    usd_points = usd_pointcloud.GetPointsAttr()
    times = usd_points.GetTimeSamples()
    sorted(times)
    if len(times) <= 0:
        to_return.append((0, usd_points.Get()))
    else:
        for frame in times:
            points_at_frame = usd_points.Get(frame)
            to_return.append((frame, points_at_frame))

    return to_return


def read_widths(usd_points):
    to_return = []
    usd_widths = usd_points.GetWidthsAttr()
    times = usd_widths.GetTimeSamples()
    sorted(times)
    if len(times) <= 0:
        to_return.append((0, usd_widths.Get()))
    else:
        for frame in times:
            widths_at_frame = usd_widths.Get(frame)
            to_return.append((frame, widths_at_frame))

    return to_return


def read_points_data(data_dict, file_path=None, points_path=None, usd_points=None):
    if usd_points is None:
        stage = Usd.Stage.Open(file_path)
        usd_points = UsdGeom.Points(stage.GetPrimAtPath(points_path))
    data_dict["points"] = read_points(usd_points)
    data_dict["widths"] = read_widths(usd_points)


def create_usd_load_tree(app, xsi_points):
    # create attribute
    point_attr_name = "usd_points"
    xsi_points.AddICEAttribute(point_attr_name, 16, 2, 1)

    # add ice-tree and connect nodes
    tree = app.ApplyOp("ICETree", xsi_points.Parent.Parent, "siNode", "", "", 0)[0]
    # delete all points
    delete_point_node = app.AddICENode("$XSI_DSPRESETS\\ICENodes\\DeletePointNode", tree)
    app.SetValue(delete_point_node.FullName + ".deleted", True, "")
    app.ConnectICENodes(tree.FullName + ".port1", delete_point_node.FullName + ".execute")

    # add points node
    add_point_node = app.AddICENode("$XSI_DSPRESETS\\ICENodes\\AddPointNode", tree)
    app.AddPortToICENode(tree.FullName + ".port1", "siNodePortDataInsertionLocationAfter")
    app.ConnectICENodes(tree.FullName + ".port2", add_point_node.FullName + ".add")

    # get from custom attribute
    get_data_node = app.AddICENode("$XSI_DSPRESETS\\ICENodes\\GetDataNode", tree)
    app.SetValue(get_data_node.FullName + ".reference", "self." + point_attr_name, "")
    app.ConnectICENodes(add_point_node.FullName + ".positions1", get_data_node.FullName + ".value")

    return tree


def set_pointcloud_from_data(app, xsi_points, points_data, xsi_math, frame=None):
    # set poit positions
    if "points" in points_data and len(points_data["points"]) > 0:
        points = utils.get_closest_data(points_data["points"], 0 if frame is None else frame)
        points_array = []
        for p in points:
            points_array.append(xsi_math.CreateVector3(p[0], p[1], p[2]))

        points_attr = xsi_points.GetICEAttributeFromName("usd_points")
        points_attr.DataArray = [points_array]


def emit_pointcloud(app, options, pointloud_name, usd_tfm, visibility, usd_prim, xsi_parent):
    imp.reload(utils)
    usd_points = UsdGeom.Points(usd_prim)
    xsi_points = app.GetPrim("PointCloud", pointloud_name, xsi_parent)
    utils.set_xsi_transform(app, xsi_points, usd_tfm)
    utils.set_xsi_visibility(xsi_points, visibility)

    tree = create_usd_load_tree(app, xsi_points.ActivePrimitive.Geometry)

    if not utils.is_animated_points(usd_points):
        points_data = {}
        read_points_data(points_data, usd_points=usd_points)
        xsi_geometry = xsi_points.ActivePrimitive.Geometry
        set_pointcloud_from_data(app, xsi_geometry, points_data, options["XSIMath"])
    else:
        operator = app.AddCustomOp("USDPointsOperator", xsi_points.ActivePrimitive, "", "USDPointsOperator")
        operator.Parameters("file_path").Value = options["file_path"]
        operator.Parameters("points_path").Value = str(usd_prim.GetPath())
        operator.AlwaysEvaluate = True

        # swap ICE-tree and operator (ICE-tree should be at the top)
        app.MoveOperatorAfter(xsi_points.ActivePrimitive, tree, operator)

    return xsi_points
