from pxr import UsdGeom, Sdf, Usd, UsdShade
import prim_xform
import utils
import imp


def set_mesh_at_frame(app, stage, mesh_object, opt_attributes, usd_mesh, usd_mesh_prim, usd_mesh_primvar, is_constant, material_to_usd, frame=None, force_frame=False):
    if frame is not None and force_frame:
        app.SetValue("PlayControl.Current", frame, "")
        app.SetValue("PlayControl.Key", frame, "")
    # read mesh data
    xsi_polygonmesh = mesh_object.GetActivePrimitive3().Geometry if frame is None else mesh_object.GetActivePrimitive3(frame).GetGeometry3(frame)
    xsi_mesh_data = xsi_polygonmesh.Get2()
    # 1: ((p1.x, p2.x, ...), (p1.y, p2.y, ...), (p1.z, p2.z, ...))
    # 2: (4<-polygon size, 0, 1, 5, 6, 4<-second polygon size, 45, 64, 34, 22, ...)
    xsi_point_positions = []
    xsi_polygon_sizes = []
    xsi_polygon_point_indexes = []
    for i in range(len(xsi_mesh_data[0][0])):
        xsi_point_positions.append((xsi_mesh_data[0][0][i], xsi_mesh_data[0][1][i], xsi_mesh_data[0][2][i]))
    is_size = True
    polygon_corner = 0
    for v in xsi_mesh_data[1]:
        if is_size:
            xsi_polygon_sizes.append(v)
            polygon_corner = 0
            is_size = False
        else:
            xsi_polygon_point_indexes.append(v)
            polygon_corner += 1
            if polygon_corner == xsi_polygon_sizes[-1]:
                is_size = True

    usd_extent = usd_mesh_prim.CreateAttribute("extent", Sdf.ValueTypeNames.Float3Array)
    if frame is None:
        usd_extent.Set(utils.get_bounding_box(xsi_point_positions))
    else:
        usd_extent.Set(utils.get_bounding_box(xsi_point_positions), Usd.TimeCode(frame))

    # set mesh attributes
    usd_points_attr = usd_mesh.CreatePointsAttr()
    if frame is None:
        usd_points_attr.Set(xsi_point_positions)
    else:
        usd_points_attr.Set(xsi_point_positions, Usd.TimeCode(frame))

    usd_face_vertex_attr = usd_mesh.CreateFaceVertexCountsAttr()
    if frame is None or is_constant:
        usd_face_vertex_attr.Set(xsi_polygon_sizes)
    else:
        usd_face_vertex_attr.Set(xsi_polygon_sizes, Usd.TimeCode(frame))

    usd_face_indexes_attr = usd_mesh.CreateFaceVertexIndicesAttr()
    if frame is None or is_constant:  # set topology at frame only if we change it, otherwise set universal values
        usd_face_indexes_attr.Set(xsi_polygon_point_indexes)
    else:
        usd_face_indexes_attr.Set(xsi_polygon_point_indexes, Usd.TimeCode(frame))

    xsi_sample_clusters = None
    if "normal" in opt_attributes or "color" in opt_attributes or "uvmap" in opt_attributes:
        xsi_sample_clusters = xsi_polygonmesh.Clusters.Filter("sample")

    # clusters write at each frame, because values may changed, even if clusters are the same

    # normals
    if "normal" in opt_attributes:
        xsi_normals = []
        for xsi_polygon in xsi_polygonmesh.Polygons:
            p_samples = xsi_polygon.Samples
            p_nodes = xsi_polygon.Nodes
            for ps_index in range(p_samples.Count):
                xsi_normals.append(utils.vector_to_tuple(p_nodes[ps_index].Normal))
        # may be normals were modified
        for xsi_cluster in xsi_sample_clusters:
            for prop in xsi_cluster.Properties:
                if prop.Type == "normal":
                    cls_sample_index = xsi_cluster.Elements.Array  # store sample indexes in the array (s1, s2, s3, ...), but it is not ordered. Data elements in the same order as in this array
                    # for example cls_sample_index = [3, 1] it means that the fist value in the data for 3-d sample, the second - for 1-t sample
                    xsi_normal_data = prop.Elements.Array  # it contains only modified data
                    for i in range(len(cls_sample_index)):
                        xsi_normals[cls_sample_index[i]] = (xsi_normal_data[0][i], xsi_normal_data[1][i], xsi_normal_data[2][i])
        usd_normals_attr = usd_mesh.CreateNormalsAttr()
        if frame is None:
            usd_normals_attr.Set(xsi_normals)
        else:
            usd_normals_attr.Set(xsi_normals, Usd.TimeCode(frame))
        usd_mesh.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)

    # vertex color
    if "color" in opt_attributes:
        for xsi_cluster in xsi_sample_clusters:
            if xsi_cluster.IsAlwaysComplete():
                for prop in xsi_cluster.Properties:
                    if prop.Type == "vertexcolor":
                        xsi_color_data = prop.Elements.Array  # [(r1, r2, r3, ...), (g1, g2, g3, ...), (b1, b2, b3, ...), (a1, a2, a3, ...)]
                        xsi_colors = []
                        for i in range(len(xsi_color_data[0])):
                            xsi_colors.append((xsi_color_data[0][i], xsi_color_data[1][i], xsi_color_data[2][i]))
                        usd_vertex_color_attr = usd_mesh_primvar.CreatePrimvar(prop.Name, Sdf.ValueTypeNames.Color3fArray, UsdGeom.Tokens.faceVarying)
                        if frame is None:
                            usd_vertex_color_attr.Set(xsi_colors)
                        else:
                            usd_vertex_color_attr.Set(xsi_colors, Usd.TimeCode(frame))

    # uv maps
    if "uvmap" in opt_attributes:
        for xsi_cluster in xsi_sample_clusters:
            if xsi_cluster.IsAlwaysComplete():
                for prop in xsi_cluster.Properties:
                    if prop.Type == "uvspace":
                        xsi_uv_data = prop.Elements.Array  # [(u1, u2, u3, ...), (v1, v2, v3, ...), (w1, w2, w3, ...)], wi = 0
                        xsi_uv = []
                        for i in range(len(xsi_uv_data[0])):
                            xsi_uv.append((xsi_uv_data[0][i], xsi_uv_data[1][i]))
                        usd_uv_attr = usd_mesh_primvar.CreatePrimvar(prop.Name, Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying)
                        if frame is None:
                            usd_uv_attr.Set(xsi_uv)
                        else:
                            usd_uv_attr.Set(xsi_uv, Usd.TimeCode(frame))

    # weightmaps
    if "weightmap" in opt_attributes:
        xsi_vertex_clusters = xsi_polygonmesh.Clusters.Filter("pnt")
        for pnt_cluster in xsi_vertex_clusters:
            if pnt_cluster.IsAlwaysComplete():
                index_to_vertex = pnt_cluster.Elements.Array  # use it for map from cluster index to vertex index
                for cls_prop in pnt_cluster.Properties:
                    if cls_prop.Type == "wtmap":  # this complete cluster is weight map
                        prop_name = cls_prop.Name
                        xsi_cluster_data = []
                        c_elements = cls_prop.Elements
                        c_count = len(c_elements)
                        for c_e in range(c_count):
                            xsi_cluster_data.append((index_to_vertex[c_e], c_elements[c_e][0]))
                        xsi_cluster_data = sorted(xsi_cluster_data, key=lambda x: x[0])
                        xsi_weights = []
                        for c in xsi_cluster_data:
                            xsi_weights.append(c[1])
                        usd_weight_attr = usd_mesh_primvar.CreatePrimvar(prop_name, Sdf.ValueTypeNames.FloatArray, UsdGeom.Tokens.vertex)
                        if frame is None:
                            usd_weight_attr.Set(xsi_weights)
                        else:
                            usd_weight_attr.Set(xsi_weights, Usd.TimeCode(frame))

    # vertex creases
    if "vertex_creases" in opt_attributes:
        xsi_vertex_creases_values = []
        xsi_vertex_crease_indexes = []
        for xsi_vertex in xsi_polygonmesh.Vertices:
            if xsi_vertex.Crease > 0.001:
                xsi_vertex_creases_values.append(xsi_vertex.Crease)  # 10.0 is equal to maximum value
                xsi_vertex_crease_indexes.append(xsi_vertex.Index)
        if len(xsi_vertex_creases_values) > 0:
            usd_corner_indices_attr = usd_mesh.CreateCornerIndicesAttr()
            usd_corner_sharpness_attr = usd_mesh.CreateCornerSharpnessesAttr()
            if frame is None:
                usd_corner_indices_attr.Set(xsi_vertex_crease_indexes)
                usd_corner_sharpness_attr.Set(xsi_vertex_creases_values)
            else:
                usd_corner_indices_attr.Set(xsi_vertex_crease_indexes, Usd.TimeCode(frame))
                usd_corner_sharpness_attr.Set(xsi_vertex_creases_values, Usd.TimeCode(frame))

    # edges creases
    if "edge_creases" in opt_attributes:
        xsi_edge_vertex_indexes = []  # [e1.1, v1.2, e2.1, e2.2, e3.1, e3.2, ...]
        edge_count = 0
        xsi_edge_creases = []
        for xsi_edge in xsi_polygonmesh.Edges:
            xsi_edge_crease = xsi_edge.Crease
            if xsi_edge_crease > 0.001:
                xsi_edge_creases.append(xsi_edge_crease)
                edge_count += 1
                for xsi_vert in xsi_edge.Vertices:
                    xsi_edge_vertex_indexes.append(xsi_vert.Index)
        if edge_count > 0:
            usd_crease_indeces_attr = usd_mesh.CreateCreaseIndicesAttr()
            usd_crease_length_attr = usd_mesh.CreateCreaseLengthsAttr()
            usd_crease_sharpness_attr = usd_mesh.CreateCreaseSharpnessesAttr()
            if frame is None:
                usd_crease_indeces_attr.Set(xsi_edge_vertex_indexes)
                usd_crease_length_attr.Set([2] * edge_count)
                usd_crease_sharpness_attr.Set(xsi_edge_creases)
            else:
                usd_crease_indeces_attr.Set(xsi_edge_vertex_indexes, Usd.TimeCode(frame))
                usd_crease_length_attr.Set([2] * edge_count, Usd.TimeCode(frame))
                usd_crease_sharpness_attr.Set(xsi_edge_creases, Usd.TimeCode(frame))

    # polygon clusters
    if "cluster" in opt_attributes:
        xsi_poly_clusters = xsi_polygonmesh.Clusters.Filter("poly")
        for xsi_poly_cluster in xsi_poly_clusters:
            c_name = xsi_poly_cluster.Name
            c_elements = xsi_poly_cluster.Elements
            xsi_indices_array = []
            for e in c_elements:
                xsi_indices_array.append(e)
            usd_subset_path = str(usd_mesh.GetPath()) + "/" + c_name
            usd_subset = UsdGeom.Subset.Define(stage, usd_subset_path)
            usd_subset.CreateElementTypeAttr(UsdGeom.Tokens.face)
            usd_subset.CreateIndicesAttr(xsi_indices_array)

            # bind cluster material if it differs form the main object material
            xsi_cluster_material = xsi_poly_cluster.Material
            if not utils.is_materials_equals(mesh_object.Material, xsi_cluster_material):
                mat_identifier = utils.build_material_identifier(xsi_cluster_material)
                if mat_identifier in material_to_usd:
                    UsdShade.MaterialBindingAPI(usd_subset).Bind(material_to_usd[mat_identifier])


def add_mesh(app, params, path_for_objects, stage, mesh_object, materials_opt, root_path, progress_bar=None):
    '''stage is a root stage
       mesh_object is a polygonmesh X3DObject
       root_path is a string for the parent path in the stage
    '''
    imp.reload(prim_xform)
    imp.reload(utils)
    opt_attributes = params["attr_list"]
    opt_animation = params.get("animation", None)
    opt = params.get("options", {})
    # create root xform
    usd_xform, ref_stage, ref_stage_asset = prim_xform.add_xform(app, params, path_for_objects, True, stage, mesh_object, root_path)
    # add mesh prim component
    usd_mesh = UsdGeom.Mesh.Define(ref_stage, str(usd_xform.GetPath()) + "/" + "Mesh")
    usd_mesh_prim = ref_stage.GetPrimAtPath(usd_mesh.GetPath())
    usd_mesh_primvar = UsdGeom.PrimvarsAPI(usd_mesh)  # for creating primvar attributes

    # add refs to all materials of the object
    material_to_usd = {}  # dont' use material.add_material() method, because here we need additional information about added materials
    material_asset_path = materials_opt.get("asset_path", None)
    if material_asset_path is not None:
        rel_material_path = utils.transform_path_to_relative(ref_stage_asset, material_asset_path)
        for xsi_mat in mesh_object.Materials:
            mat_name = utils.buil_material_name(xsi_mat)
            mat_ref = ref_stage.DefinePrim(str(usd_xform.GetPath()) + "/" + mat_name)
            mat_ref.GetReferences().AddReference(rel_material_path, "/" + xsi_mat.Library.Name + "/" + xsi_mat.Name)
            material_to_usd[utils.build_material_identifier(xsi_mat)] = UsdShade.Material(ref_stage.GetPrimAtPath(mat_ref.GetPath()))
        # bind the main material
        main_material = mesh_object.Material
        if utils.build_material_identifier(xsi_mat) in material_to_usd:
            UsdShade.MaterialBindingAPI(usd_mesh_prim).Bind(material_to_usd[utils.build_material_identifier(main_material)])

    is_constant = utils.is_constant_topology(app, mesh_object, params.get("animation", None), opt.get("force_change_frame", False))

    if opt.get("use_subdiv", False):
        usd_mesh.CreateSubdivisionSchemeAttr().Set("catmullClark")
    else:
        usd_mesh.CreateSubdivisionSchemeAttr().Set("none")
    if opt_animation is None:
        set_mesh_at_frame(app, ref_stage, mesh_object, opt_attributes, usd_mesh, usd_mesh_prim, usd_mesh_primvar, is_constant, material_to_usd)
    else:
        for frame in range(opt_animation[0], opt_animation[1] + 1):
            if progress_bar is not None:
                progress_bar.Caption = utils.build_export_object_caption(mesh_object, frame)
            set_mesh_at_frame(app, ref_stage, mesh_object, opt_attributes, usd_mesh, usd_mesh_prim, usd_mesh_primvar, is_constant, material_to_usd, frame=frame, force_frame=opt.get("force_change_frame", False))
    ref_stage.Save()

    return stage.GetPrimAtPath(root_path + str(usd_xform.GetPath()))


def read_points(usd_mesh):
    usd_points = usd_mesh.GetPointsAttr()
    times = usd_points.GetTimeSamples()
    points_array = []
    for frame in times:
        points_at_frame = usd_points.Get(frame)
        points_array.append((frame, points_at_frame))
    sorted(points_array, key=lambda x: x[0])

    return points_array


def read_face_sizes(usd_mesh):
    usd_sizes = usd_mesh.GetFaceVertexCountsAttr()
    times = usd_sizes.GetTimeSamples()
    if len(times) <= 1:
        return [(0, usd_sizes.Get())]
    else:
        array = []
        for frame in times:
            sizes_at_frame = usd_sizes.Get(frame)
            array.append((frame, sizes_at_frame))
        sorted(array, key=lambda x: x[0])
        return array


def read_face_indexes(usd_mesh):
    usd_indexes = usd_mesh.GetFaceVertexIndicesAttr()
    times = usd_indexes.GetTimeSamples()
    if len(times) <= 1:
        return [(0, usd_indexes.Get())]
    else:
        array = []
        for frame in times:
            indexes_at_frame = usd_indexes.Get(frame)
            array.append((frame, indexes_at_frame))
        sorted(array, key=lambda x: x[0])
        return array


def read_mesh_data(file_path, mesh_path, data_dict):
    stage = Usd.Stage.Open(file_path)
    usd_mesh = UsdGeom.Mesh(stage.GetPrimAtPath(mesh_path))
    # we should get data of all attributes from usd_mesh and save it to data_dict by different keys
    # animated format is the following: it is an array of tuples [(frame, data at frame), ...]
    # if there is only one frame (or zero), then data is an one-element array [(0, data)]
    data_dict["points"] = read_points(usd_mesh)
    data_dict["face_sizes"] = read_face_sizes(usd_mesh)
    data_dict["face_indexes"] = read_face_indexes(usd_mesh)


def set_geometry_from_data(xsi_geometry, mesh_options, mesh_data, frame):
    # mesh_options contains keys: attributes, is_topology_change
    # this method calls every frame from operator update
    # it use data, stored in mesh_data user data inside operator
    xsi_vertex_count = xsi_geometry.Vertices.Count
    points_data = mesh_data["points"]
    points = utils.get_closest_data(points_data, frame)
    xsi_points_postions = utils.usd_to_xsi_vertex_array(points)  # convert to xsi-specific format
    if xsi_vertex_count == 0 or mesh_options["is_topology_change"] or xsi_vertex_count != len(points):
        # cerate all topology
        face_size_data = mesh_data["face_sizes"]
        face_indexes_data = mesh_data["face_indexes"]
        # find points closest to the frame
        face_size = utils.get_closest_data(face_size_data, frame)
        face_indexes = utils.get_closest_data(face_indexes_data, frame)

        xsi_geometry.Set(xsi_points_postions, utils.usd_to_xsi_faces_array(face_indexes, face_size))
    else:
        # set only point positions
        xsi_geometry.Vertices.PositionArray = xsi_points_postions


def set_geometry(xsi_geometry, usd_mesh, mesh_options):
    '''mesh_options contains "attributes" - list of geometry attributes
    '''
    # build polygons data
    usd_points = usd_mesh.GetPointsAttr()
    usd_face_counts = usd_mesh.GetFaceVertexCountsAttr()
    usd_face_indexes = usd_mesh.GetFaceVertexIndicesAttr()

    usd_points_array = usd_points.Get()
    usd_face_counts_array = usd_face_counts.Get()
    usd_face_indexes_array = usd_face_indexes.Get()

    xsi_geometry.Set(utils.usd_to_xsi_vertex_array(usd_points_array), utils.usd_to_xsi_faces_array(usd_face_indexes_array, usd_face_counts_array))


def emit_mesh(app, options, mesh_name, usd_tfm, visibility, usd_prim, xsi_parent):
    imp.reload(utils)
    usd_mesh = UsdGeom.Mesh(usd_prim)
    xsi_mesh = app.GetPrim("EmptyPolygonMesh", mesh_name, xsi_parent)
    utils.set_xsi_transform(app, xsi_mesh, usd_tfm)
    utils.set_xsi_visibility(xsi_mesh, visibility)
    xsi_geometry = xsi_mesh.ActivePrimitive.Geometry

    mesh_attributes = options.get("attributes", [])
    is_animated, is_topology_changed = utils.is_animated_mesh(usd_mesh, mesh_attributes)
    mesh_options = {"attributes": mesh_attributes}
    if not is_animated:
        # simply apply geometry
        mesh_options["is_topology_change"] = True  # for non-operator approach we should create full topology
        set_geometry(xsi_geometry, usd_mesh, mesh_options)
    else:
        # create operator, which updates topology every frame
        operator = app.AddCustomOp("USDMeshOperator", xsi_mesh.ActivePrimitive, "", "USDMeshOperator")
        operator.Parameters("file_path").Value = options["file_path"]
        operator.Parameters("mesh_path").Value = str(usd_prim.GetPath())
        operator.Parameters("is_topology_change").Value = is_topology_changed
        operator.Parameters("is_uvs").Value = "uvmap" in mesh_attributes
        operator.Parameters("is_normals").Value = "normal" in mesh_attributes
        operator.Parameters("is_color").Value = "color" in mesh_attributes
        operator.Parameters("is_weightmap").Value = "weightmap" in mesh_attributes
        operator.Parameters("is_cluster").Value = "cluster" in mesh_attributes
        operator.Parameters("is_vertex_creases").Value = "vertex_creases" in mesh_attributes
        operator.Parameters("is_edges_creases").Value = "edge_creases" in mesh_attributes

        operator.AlwaysEvaluate = True

    return xsi_mesh
