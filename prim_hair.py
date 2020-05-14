from pxr import UsdGeom, Sdf, Usd
import prim_xform
import materials
import utils
import imp


def set_curves_data(usd_curves, usd_curves_prim, data_points, data_vertex_count, data_width, frame=None):
    # prepare usd attributes
    usd_curves.CreateTypeAttr(UsdGeom.Tokens.cubic)
    usd_curves.CreateBasisAttr(UsdGeom.Tokens.bspline)

    usd_points = usd_curves.CreatePointsAttr()
    usd_vertex_count = usd_curves.CreateCurveVertexCountsAttr()
    usd_width = usd_curves.CreateWidthsAttr()

    # set values
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
        usd_extent.Set(utils.get_bounding_box(data_points))
    else:
        usd_extent.Set(utils.get_bounding_box(data_points), Usd.TimeCode(frame))


def set_hair_at_frame(app, xsi_hair, usd_curves, usd_curves_prim, frame=None):
    # read the data
    if frame is None:
        xsi_pos, xsi_length, xsi_width = app.GetHairData(xsi_hair)
    else:
        xsi_pos, xsi_length, xsi_width = app.GetHairData(xsi_hair, frame)

    data_points = []
    for i in range(len(xsi_pos) // 3):
        data_points.append((xsi_pos[3*i], xsi_pos[3*i + 1], xsi_pos[3*i + 2]))

    set_curves_data(usd_curves, usd_curves_prim, data_points, list(xsi_length), xsi_width, frame)


def add_hair(app, params, path_for_objects, stage, xsi_hair, materials_opt, root_path, progress_bar=None):
    imp.reload(utils)
    imp.reload(prim_xform)
    imp.reload(materials)
    usd_xform, ref_stage = prim_xform.add_xform(app, params, path_for_objects, True, stage, xsi_hair, root_path)
    usd_curves = UsdGeom.BasisCurves.Define(ref_stage, str(usd_xform.GetPath()) + "/" + xsi_hair.Name)
    usd_curves_prim = ref_stage.GetPrimAtPath(usd_curves.GetPath())

    materials.add_material(materials_opt, xsi_hair.Material, ref_stage, usd_xform, usd_curves_prim)

    opt_animation = params.get("animation", None)
    if opt_animation is None:
        set_hair_at_frame(app, xsi_hair, usd_curves, usd_curves_prim)
    else:
        for frame in range(opt_animation[0], opt_animation[1] + 1):
            if progress_bar is not None:
                progress_bar.Caption = utils.build_export_object_caption(xsi_hair, frame)
            set_hair_at_frame(app, xsi_hair, usd_curves, usd_curves_prim, frame)
    ref_stage.Save()

    return usd_xform


def set_strands_at_frame(xsi_geometry, usd_curves, usd_curves_prim, frame=None):
    # we should get point positions, strand positions and size attribute
    xsi_pp = xsi_geometry.GetICEAttributeFromName("PointPosition")
    xsi_sp = xsi_geometry.GetICEAttributeFromName("StrandPosition")
    xsi_size = xsi_geometry.GetICEAttributeFromName("Size")
    # read data
    xsi_pp_data = xsi_pp.DataArray
    xsi_sp_data = xsi_sp.DataArray2D
    xsi_size_data = xsi_size.DataArray
    # the size of xsi_pp_data and xsi_size_data are strands count

    # next from arrays with the data
    data_points = []
    data_vertex_count = []
    data_width = []
    for strand_index in range(len(xsi_pp_data)):
        # start point
        data_points.append(utils.vector_to_tuple(xsi_pp_data[strand_index]))
        # next strand points
        for p_index in range(len(xsi_sp_data[strand_index])):
            data_points.append(utils.vector_to_tuple(xsi_sp_data[strand_index][p_index]))
        data_vertex_count.append(len(xsi_sp_data[strand_index]) + 1)
        data_width += [xsi_size_data[strand_index] if strand_index < len(xsi_size_data) else xsi_size_data[-1]] * (len(xsi_sp_data[strand_index]) + 1)

    set_curves_data(usd_curves, usd_curves_prim, data_points, data_vertex_count, data_width, frame)


def add_strands(app, params, path_for_objects, stage, xsi_pc, materials_opt, root_path, progress_bar=None):
    imp.reload(utils)
    imp.reload(prim_xform)
    imp.reload(materials)
    usd_xform, ref_stage = prim_xform.add_xform(app, params, path_for_objects, True, stage, xsi_pc, root_path)
    usd_curves = UsdGeom.BasisCurves.Define(ref_stage, str(usd_xform.GetPath()) + "/" + xsi_pc.Name)
    usd_curves_prim = ref_stage.GetPrimAtPath(usd_curves.GetPath())

    materials.add_material(materials_opt, xsi_pc.Material, ref_stage, usd_xform, usd_curves_prim)

    opt_animation = params.get("animation", None)
    if opt_animation is None:
        set_strands_at_frame(xsi_pc.GetActivePrimitive3().Geometry, usd_curves, usd_curves_prim)
    else:
        for frame in range(opt_animation[0], opt_animation[1] + 1):
            if progress_bar is not None:
                progress_bar.Caption = utils.build_export_object_caption(xsi_pc, frame)
            set_strands_at_frame(xsi_pc.GetActivePrimitive3(frame).GetGeometry3(frame), usd_curves, usd_curves_prim, frame)
    ref_stage.Save()

    return usd_xform
