from pxr import UsdGeom, Sdf, Usd, UsdShade
import prim_xform
import utils
import imp


def set_mesh_at_frame(stage, mesh_object, opt_attributes, usd_mesh, usd_mesh_prim, usd_mesh_primvar, is_constant, material_to_usd, frame=None):
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


def add_mesh(app, params, path_for_objects, stage, mesh_object, materials_opt, root_path):
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
    usd_xform, ref_stage = prim_xform.add_xform(app, params, path_for_objects, True, stage, mesh_object, root_path)
    # add mesh prim component
    usd_mesh = UsdGeom.Mesh.Define(ref_stage, str(usd_xform.GetPath()) + "/" + "Mesh")
    usd_mesh_prim = ref_stage.GetPrimAtPath(usd_mesh.GetPath())
    usd_mesh_primvar = UsdGeom.PrimvarsAPI(usd_mesh)  # for creating primvar attributes

    # add refs to all materials of the object
    material_to_usd = {}  # dont' use material.add_material() method, because here we need additional information about added materials
    ref_path = materials_opt.get("ref_path", None)
    if ref_path is not None:
        for xsi_mat in mesh_object.Materials:
            mat_name = utils.buil_material_name(xsi_mat)
            mat_ref = ref_stage.DefinePrim(str(usd_xform.GetPath()) + "/" + mat_name)
            mat_ref.GetReferences().AddReference(ref_path, "/" + xsi_mat.Library.Name + "/" + xsi_mat.Name)
            material_to_usd[utils.build_material_identifier(xsi_mat)] = UsdShade.Material(ref_stage.GetPrimAtPath(mat_ref.GetPath()))
        # bind the main material
        main_material = mesh_object.Material
        if utils.build_material_identifier(xsi_mat) in material_to_usd:
            UsdShade.MaterialBindingAPI(usd_mesh_prim).Bind(material_to_usd[utils.build_material_identifier(main_material)])

    is_constant = utils.is_constant_topology(mesh_object, params.get("animation", None))

    if opt.get("use_subdiv", False):
        usd_mesh.CreateSubdivisionSchemeAttr().Set("catmullClark")
    else:
        usd_mesh.CreateSubdivisionSchemeAttr().Set("none")
    if opt_animation is None:
        set_mesh_at_frame(ref_stage, mesh_object, opt_attributes, usd_mesh, usd_mesh_prim, usd_mesh_primvar, is_constant, material_to_usd)
    else:
        for frame in range(opt_animation[0], opt_animation[1] + 1):
            set_mesh_at_frame(ref_stage, mesh_object, opt_attributes, usd_mesh, usd_mesh_prim, usd_mesh_primvar, is_constant, material_to_usd, frame=frame)
    ref_stage.Save()

    return usd_xform
