from pxr import UsdGeom, Sdf, Usd, UsdShade
from win32com.client import constants
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
    to_return = []
    usd_points = usd_mesh.GetPointsAttr()
    times = usd_points.GetTimeSamples()
    sorted(times)
    if len(times) <= 0:
        to_return.append((0, usd_points.Get()))
    else:
        for frame in times:
            points_at_frame = usd_points.Get(frame)
            to_return.append((frame, points_at_frame))

    return to_return


def read_face_sizes(usd_mesh):
    usd_sizes = usd_mesh.GetFaceVertexCountsAttr()
    times = usd_sizes.GetTimeSamples()
    sorted(times)
    if len(times) <= 1:
        return [(0, usd_sizes.Get())]
    else:
        array = []
        for frame in times:
            sizes_at_frame = usd_sizes.Get(frame)
            array.append((frame, sizes_at_frame))
        # sorted(array, key=lambda x: x[0])
        return array


def read_face_indexes(usd_mesh):
    usd_indexes = usd_mesh.GetFaceVertexIndicesAttr()
    times = usd_indexes.GetTimeSamples()
    sorted(times)
    if len(times) <= 1:
        return [(0, usd_indexes.Get())]
    else:
        array = []
        for frame in times:
            indexes_at_frame = usd_indexes.Get(frame)
            array.append((frame, indexes_at_frame))
        # sorted(array, key=lambda x: x[0])
        return array


def read_edges_creases(usd_mesh):
    '''return array [(frame1, data1), ...], where each data is array of triples [(v_star, v_end, sharpness), ...]
    '''
    to_return = []
    indices_attr = usd_mesh.GetCreaseIndicesAttr()
    length_attr = usd_mesh.GetCreaseLengthsAttr()
    sharpness_attr = usd_mesh.GetCreaseSharpnessesAttr()
    times = indices_attr.GetTimeSamples()
    sorted(times)
    if indices_attr.IsAuthored() and length_attr.IsAuthored() and sharpness_attr.IsAuthored() and len(times) == len(length_attr.GetTimeSamples()) and len(times) == len(sharpness_attr.GetTimeSamples()):
        if len(times) <= 1:
            to_return.append((0, utils.collapse_usd_hard_edges_data(indices_attr.Get(), length_attr.Get(), sharpness_attr.Get())))
        else:
            for frame in times:
                to_return.append((frame, utils.collapse_usd_hard_edges_data(indices_attr.Get(frame), length_attr.Get(frame), sharpness_attr.Get(frame))))

    return to_return


def read_vertex_creases(usd_mesh):
    '''return array [(frame1, data1), ...]
    each data is an array of pairs [(indexes, sharpness), ...] for each vertex in the cluster
    '''
    to_return = []
    # get attributes
    indexes_attr = usd_mesh.GetCornerIndicesAttr()
    sharpness_attr = usd_mesh.GetCornerSharpnessesAttr()
    indexes_times = indexes_attr.GetTimeSamples()
    sharpness_times = sharpness_attr.GetTimeSamples()
    if indexes_attr.IsAuthored() and sharpness_attr.IsAuthored() and len(indexes_times) == len(sharpness_times):
        times = indexes_times
        sorted(times)
        if len(times) <= 1:
            to_return.append((0, zip(indexes_attr.Get(), sharpness_attr.Get())))
        else:
            for frame in times:
                to_return.append((frame, zip(indexes_attr.Get(frame), sharpness_attr.Get(frame))))

    return to_return


def read_normals(usd_mesh):
    to_return = []
    usd_normals = usd_mesh.GetNormalsAttr()
    times = usd_normals.GetTimeSamples()
    sorted(times)
    if len(times) <= 1:
        to_return.append((0, usd_normals.Get()))
    else:
        for frame in times:
            vals_at_frame = usd_normals.Get(frame)
            to_return.append((frame, vals_at_frame))

    return to_return


def read_uvs(usd_mesh):
    '''store uvs in array [uv1, uv2, ...], where each uv is a pair (name, array [(frame1, data1), (frame2, data2), ...])
    '''
    primvars = usd_mesh.GetPrimvars()
    to_return = []
    for p in primvars:
        type_strings = p.GetTypeName().aliasesAsStrings
        if "texCoord2f[]" in type_strings:
            # this is uv primvar
            uv_data = []
            uv_name = p.GetBaseName()
            uv_time = p.GetTimeSamples()
            sorted(uv_time)
            uv_attribute = p.GetAttr()
            if len(uv_time) <= 1:
                uv_data.append((0, uv_attribute.Get()))
            else:
                for frame in uv_time:
                    uv_data.append((frame, uv_attribute.Get(frame)))
            to_return.append((uv_name, uv_data))

    return to_return


def read_vertex_colors(usd_mesh):
    primvars = usd_mesh.GetPrimvars()
    to_return = []
    for p in primvars:
        type_strings = p.GetTypeName().aliasesAsStrings
        interpolation = p.GetInterpolation()
        if "color3f[]" in type_strings and interpolation == "faceVarying":
            # vertex colors are only face-varuing
            color_data = []
            color_name = p.GetBaseName()
            color_time = p.GetTimeSamples()
            sorted(color_time)
            color_attribute = p.GetAttr()
            if len(color_time) <= 1:
                color_data.append((0, color_attribute.Get()))
            else:
                for frame in color_time:
                    color_data.append((frame, color_attribute.Get(frame)))
            to_return.append((color_name, color_data))

    return to_return


def read_weightmaps(usd_mesh):
    '''result is array [(name, weightmap), ...], each weightmap is an array [(frame1, data1), ...]
    '''
    primvars = usd_mesh.GetPrimvars()
    to_return = []
    for p in primvars:
        type_strings = p.GetTypeName().aliasesAsStrings
        interpolation = p.GetInterpolation()
        if interpolation == "vertex" and "float[]" in type_strings:
            # weightmaps only per-vertex and has float values
            weight_data = []
            weight_name = p.GetBaseName()
            weight_time = p.GetTimeSamples()
            sorted(weight_time)
            weight_attr = p.GetAttr()
            if len(weight_time) <= 1:
                weight_data.append((0, weight_attr.Get()))
            else:
                for frame in weight_time:
                    weight_data.append((frame, weight_attr.Get(frame)))
            to_return.append((weight_name, weight_data))
    return to_return


def read_clusters(usd_mesh):
    '''return an array of pair [(name, [indices]), ...]
    '''
    to_return = []
    usd_prim = usd_mesh.GetPrim()

    for child in usd_prim.GetChildren():
        type_name = child.GetTypeName()
        if type_name == "GeomSubset":
            # this is a cluster
            element_type_attr = None
            indices_attr = None
            child_attributes = child.GetAttributes()
            for attr in child_attributes:
                if attr.IsAuthored():
                    if attr.GetName() == "elementType":
                        element_type_attr = attr
                    elif attr.GetName() == "indices":
                        indices_attr = attr
            if element_type_attr is not None and indices_attr is not None and element_type_attr.Get() == "face":
                to_return.append((child.GetName(), indices_attr.Get()))

    return to_return


def read_mesh_data(mesh_options, data_dict, file_path=None, mesh_path=None, usd_mesh=None):
    # mesh_options = {"attributes": ('uvmap', 'normal', 'color', 'weightmap', 'cluster', 'vertex_creases', 'edge_creases')}
    if usd_mesh is None:
        stage = Usd.Stage.Open(file_path)
        usd_mesh = UsdGeom.Mesh(stage.GetPrimAtPath(mesh_path))
    # we should get data of all attributes from usd_mesh and save it to data_dict by different keys
    # animated format is the following: it is an array of tuples [(frame, data at frame), ...]
    # if there is only one frame (or zero), then data is an one-element array [(0, data)]
    data_dict["points"] = read_points(usd_mesh)
    data_dict["face_sizes"] = read_face_sizes(usd_mesh)
    data_dict["face_indexes"] = read_face_indexes(usd_mesh)
    attrs = mesh_options.get("attributes", [])
    if "normal" in attrs:
        data_dict["normals"] = read_normals(usd_mesh)
    if "uvmap" in attrs:
        data_dict["uvs"] = read_uvs(usd_mesh)
    if "color" in attrs:
        data_dict["colors"] = read_vertex_colors(usd_mesh)
    if "weightmap" in attrs:
        data_dict["weightmaps"] = read_weightmaps(usd_mesh)
    if "vertex_creases" in attrs:
        data_dict["vertex_creases"] = read_vertex_creases(usd_mesh)
    if "edge_creases" in attrs:
        data_dict["edge_creases"] = read_edges_creases(usd_mesh)
    if "cluster" in attrs:
        data_dict["cluster"] = read_clusters(usd_mesh)


def set_geometry_from_data(app, xsi_geometry, mesh_options, mesh_data, frame=None):
    # mesh_options contains keys: attributes, is_topology_change
    # this method calls every frame from operator update (or at once, if the mesh is constructed without operator)
    # it use data, stored in mesh_data user data inside operator
    xsi_vertex_count = xsi_geometry.Vertices.Count
    points_data = mesh_data["points"]
    points = utils.get_closest_data(points_data, frame)
    xsi_points_postions = utils.transpose_vectors_array(points)  # convert to xsi-specific format
    is_mesh_empty = False

    if xsi_vertex_count == 0 or mesh_options["is_topology_change"] or xsi_vertex_count != len(points):
        # cerate all topology
        face_size_data = mesh_data["face_sizes"]
        face_indexes_data = mesh_data["face_indexes"]
        # find points closest to the frame
        face_size = utils.get_closest_data(face_size_data, frame)
        face_indexes = utils.get_closest_data(face_indexes_data, frame)

        xsi_geometry.Set(xsi_points_postions, utils.usd_to_xsi_faces_array(face_indexes, face_size))

        # setup clusters only at once, when we create the topology
        for cluster_data in mesh_data["cluster"]:
            xsi_geometry.AddCluster(constants.siPolygonCluster, cluster_data[0], cluster_data[1])
        is_mesh_empty = True
    else:
        # set only point positions
        xsi_geometry.Vertices.PositionArray = xsi_points_postions

    # next setup all other attributes
    normals_data = mesh_data.get("normals", None)
    if normals_data is not None:
        normals = utils.get_closest_data(normals_data, 0 if frame is None else frame)  # array of vector coordinates
        if normals is not None and len(normals) > 0:
            normals_cls = None
            # may be geometry already contains normal cluster, find it
            if not is_mesh_empty:
                find_path = xsi_geometry.Parent.FullName + ".cls." + "User_Normal_Cluster"
                normals_cls = app.Dictionary.GetObject(find_path, False)
            # if we did not find normal cluster, create the new one
            if normals_cls is None:
                normals_cls = xsi_geometry.AddCluster(constants.siSampledPointCluster, "User_Normal_Cluster")
            normal_name = "User_Normal_Property"
            # try to find normals property
            normals_prop = None
            if not is_mesh_empty:
                find_path = xsi_geometry.Parent.FullName + ".cls." + "User_Normal_Cluster." + normal_name
                normals_prop = app.Dictionary.GetObject(find_path, False)
            if normals_prop is None:
                new_normals_prop = app.AddProp("User Normal Property", normals_cls.FullName, constants.siDefaultPropagation, normal_name)
                normals_prop = new_normals_prop[1][0]
            xsi_normals = utils.transpose_vectors_array(normals)
            normals_prop.Elements.Array = ([tuple(xsi_normals[0]), tuple(xsi_normals[1]), tuple(xsi_normals[2])])

    uvs_data = mesh_data.get("uvs", None)
    if uvs_data is not None:
        uvs_cls = None
        if not is_mesh_empty:
            find_path = xsi_geometry.Parent.FullName + ".cls." + "UVCoordinates"
            uvs_cls = app.Dictionary.GetObject(find_path, False)
        for uv_data in uvs_data:
            # get uvs in frame
            uv_name = uv_data[0]
            uv_coordinates = utils.get_closest_data(uv_data[1], 0 if frame is None else frame)
            if uvs_cls is None:
                uvs_cls = xsi_geometry.AddCluster(constants.siSampledPointCluster, "UVCoordinates")
            uv_prop = None
            if not is_mesh_empty:
                find_path = xsi_geometry.Parent.FullName + ".cls." + "UVCoordinates." + uv_name
                uv_prop = app.Dictionary.GetObject(find_path, False)
            if uv_prop is None:
                new_uv_prop = app.AddProp("Texture Projection", uvs_cls.FullName, constants.siDefaultPropagation, uv_name)
                uv_prop = new_uv_prop[1][0]
            uv_array = utils.transpose_2vectors_array(uv_coordinates)
            uv_prop.Elements.Array = tuple([tuple(uv_array[0]), tuple(uv_array[1]), tuple([0]*len(uv_array[0]))])

    colors_data = mesh_data.get("colors", None)
    if colors_data is not None:
        pass

    weightmaps_data = mesh_data.get("weightmaps", None)
    if weightmaps_data is not None:
        pass

    vertex_creases_data = mesh_data.get("vertex_creases", None)
    if vertex_creases_data is not None:
        pass

    edge_creases_data = mesh_data.get("edge_creases", None)
    if edge_creases_data is not None:
        pass


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

    xsi_geometry.Set(utils.transpose_vectors_array(usd_points_array), utils.usd_to_xsi_faces_array(usd_face_indexes_array, usd_face_counts_array))


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
        data_dict = {}
        read_mesh_data(mesh_options, data_dict, usd_mesh=usd_mesh)
        set_geometry_from_data(app, xsi_geometry, mesh_options, data_dict)
        # set_geometry(xsi_geometry, usd_mesh, mesh_options)
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
