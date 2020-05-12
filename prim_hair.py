from pxr import UsdGeom, Sdf, Usd
from prim_xform import add_xform
from prim_mesh import get_bounding_box


def add_hair(app, params, stage, xsi_hair, root_path):
    usd_xform = add_xform(app, params, stage, xsi_hair, root_path)
    usd_curves = UsdGeom.BasisCurves.Define(stage, str(usd_xform.GetPath()) + "/" + xsi_hair.Name)

    return usd_xform


def vector_to_tuple(vector):
    return (vector.X, vector.Y, vector.Z)


def set_strands_at_frame(usd_curves, usd_curves_prim, xsi_geometry, frame=None):
    # we should get point positions, strand positions and size attribute
    xsi_pp = xsi_geometry.GetICEAttributeFromName("PointPosition")
    xsi_sp = xsi_geometry.GetICEAttributeFromName("StrandPosition")
    xsi_size = xsi_geometry.GetICEAttributeFromName("Size")
    # read data
    xsi_pp_data = xsi_pp.DataArray
    xsi_sp_data = xsi_sp.DataArray2D
    xsi_size_data = xsi_size.DataArray
    # the size of xsi_pp_data and xsi_size_data are strands count

    # prepare usd attributes
    usd_curves.CreateTypeAttr(UsdGeom.Tokens.cubic)
    usd_curves.CreateBasisAttr(UsdGeom.Tokens.bspline)

    usd_points = usd_curves.CreatePointsAttr()
    usd_vertex_count = usd_curves.CreateCurveVertexCountsAttr()
    usd_width = usd_curves.CreateWidthsAttr()

    # next from arrays with the data
    data_points = []
    data_vertex_count = []
    data_width = []
    for strand_index in range(len(xsi_pp_data)):
        # start point
        data_points.append(vector_to_tuple(xsi_pp_data[strand_index]))
        # next strand points
        for p_index in range(len(xsi_sp_data[strand_index])):
            data_points.append(vector_to_tuple(xsi_sp_data[strand_index][p_index]))
        data_vertex_count.append(len(xsi_sp_data[strand_index]) + 1)
        data_width += [xsi_size_data[strand_index] if strand_index < len(xsi_size_data) else xsi_size_data[-1]] * (len(xsi_sp_data[strand_index]) + 1)

    if frame is None:
        usd_points.Set(data_points)
        usd_vertex_count.Set(data_vertex_count)
        usd_width.Set(data_width)
    else:
        usd_points.Set(data_points, Usd.TimeCode(frame))
        usd_vertex_count.Set(data_vertex_count, Usd.TimeCode(frame))
        usd_width.Set(data_width, Usd.TimeCode(frame))

    # set bounding box
    usd_extent = usd_curves_prim.CreateAttribute("extent", Sdf.ValueTypeNames.Float3Array)
    if frame is None:
        usd_extent.Set(get_bounding_box(data_points))
    else:
        usd_extent.Set(get_bounding_box(data_points), Usd.TimeCode(frame))


def add_strands(app, params, path_for_objects, stage, xsi_pc, root_path):
    usd_xform, ref_stage = add_xform(app, params, path_for_objects, True, stage, xsi_pc, root_path)
    usd_curves = UsdGeom.BasisCurves.Define(ref_stage, str(usd_xform.GetPath()) + "/" + xsi_pc.Name)
    usd_curves_prim = ref_stage.GetPrimAtPath(usd_curves.GetPath())

    opt_animation = params.get("animation", None)
    if opt_animation is None:
        set_strands_at_frame(usd_curves, usd_curves_prim, xsi_pc.GetActivePrimitive3().Geometry)
    else:
        for frame in range(opt_animation[0], opt_animation[1] + 1):
            set_strands_at_frame(usd_curves, usd_curves_prim, xsi_pc.GetActivePrimitive3(frame).GetGeometry3(frame), frame)

    return usd_xform
