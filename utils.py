from pxr import UsdGeom, Gf
import os


# --------------------USD specific----------------------------
def add_stage_metadata(stage, params):
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    if params["animation"] is not None:
        stage.SetStartTimeCode(params["animation"][0])
        stage.SetEndTimeCode(params["animation"][1])


def build_transform(obj, frame=None):
    tfm_matrix = obj.Kinematics.Local.Transform.Matrix4 if frame is None else obj.Kinematics.Local.GetTransform2(frame).Matrix4
    return Gf.Matrix4d(
            tfm_matrix.Value(0, 0), tfm_matrix.Value(0, 1), tfm_matrix.Value(0, 2), tfm_matrix.Value(0, 3),
            tfm_matrix.Value(1, 0), tfm_matrix.Value(1, 1), tfm_matrix.Value(1, 2), tfm_matrix.Value(1, 3),
            tfm_matrix.Value(2, 0), tfm_matrix.Value(2, 1), tfm_matrix.Value(2, 2), tfm_matrix.Value(2, 3),
            tfm_matrix.Value(3, 0), tfm_matrix.Value(3, 1), tfm_matrix.Value(3, 2), tfm_matrix.Value(3, 3),
        )


def is_contains_transform(usd_prim):
    usd_props = usd_prim.GetPropertyNames()
    return "xformOp:transform" in usd_props


def is_animated_mesh(usd_mesh, attributes):
    '''return the pair (is_animated, is_topology_changed)
    if at least one valid attribute has non-zero time samples, then is_animated = True
    '''
    # check for minimal data and normals
    # minimal mesh data
    points_attr = usd_mesh.GetPointsAttr()
    faces_attr = usd_mesh.GetFaceVertexCountsAttr()
    faces_indexes_attr = usd_mesh.GetFaceVertexIndicesAttr()
    is_topology_changed = False
    is_animated = False
    if points_attr.IsAuthored() and faces_attr.IsAuthored() and faces_indexes_attr.IsAuthored():
        points_times = points_attr.GetTimeSamples()
        faces_times = faces_attr.GetTimeSamples()
        faces_indexes_times = faces_indexes_attr.GetTimeSamples()
        is_topology_changed = len(faces_times) > 1 or len(faces_indexes_times) > 1
        if is_topology_changed or len(points_times) > 1:
            is_animated = True
            return is_animated, is_topology_changed
        else:
            # next check specific attributes
            # normals
            if "normal" in attributes:
                normals_attr = usd_mesh.GetNormalsAttr()
                if normals_attr.IsAuthored():
                    normals_times = normals_attr.GetTimeSamples()
                    if len(normals_times) > 1:
                        is_animated = True
                        return is_animated, is_topology_changed

    return is_animated, is_topology_changed


# --------------------XSI specific----------------------------
def get_plugin_path(app, plugin_name):
    plugins = app.Plugins
    for p in plugins:
        if p.Name == plugin_name:
            return p.OriginPath
    return None


def is_stands(pc_object):
    pc_geo = pc_object.GetActivePrimitive2().Geometry
    strands_position_attr = pc_geo.GetICEAttributeFromName("StrandPosition")
    strands_data = strands_position_attr.DataArray2D
    return len(strands_data) > 0


def is_constant_topology(app, mesh, opt_anim, force_change_frame):
    if opt_anim is None:
        return True
    else:
        # get number of points at the first frame
        geo = mesh.GetActivePrimitive3(opt_anim[0]).GetGeometry3(opt_anim[0])
        vertex_count = len(geo.Vertices)
        # next iterate by other frames
        for frame in range(opt_anim[0] + 1, opt_anim[1] + 1):
            if force_change_frame:
                app.SetValue("PlayControl.Current", frame, "")
                app.SetValue("PlayControl.Key", frame, "")
            geo_frame = mesh.GetActivePrimitive3(frame).GetGeometry3(frame)
            verts_frame = len(geo_frame.Vertices)
            if vertex_count != verts_frame:
                return False
        return True


def vector_to_tuple(vector):
    return (vector.X, vector.Y, vector.Z)


def is_materials_equals(mat_a, mat_b):
    return mat_a.Name == mat_b.Name and mat_a.Library.Name == mat_b.Library.Name


def buil_material_name(material):
    return material.Library.Name + "_" + material.Name


def build_material_identifier(material):
    return (material.Library.Name, material.Name)


def build_export_object_caption(obj, frame=None):
    return "Export object " + obj.Name + (" (frame " + str(frame) + ")" if frame is not None else "")


def set_xsi_transform_at_frame(app, xsi_object, usd_tfm, frame=None):
    # set tfm matrix
    tfm_matrix = xsi_object.Kinematics.Local.Transform.Matrix4
    row_00 = usd_tfm.GetRow(0)
    row_01 = usd_tfm.GetRow(1)
    row_02 = usd_tfm.GetRow(2)
    row_03 = usd_tfm.GetRow(3)
    tfm_matrix.Set(row_00[0], row_00[1], row_00[2], row_00[3],
                   row_01[0], row_01[1], row_01[2], row_01[3],
                   row_02[0], row_02[1], row_02[2], row_02[3],
                   row_03[0], row_03[1], row_03[2], row_03[3])
    # form transform
    new_transfrom = xsi_object.Kinematics.Local.Transform
    new_transfrom.SetMatrix4(tfm_matrix)
    # apply transform
    xsi_object.Kinematics.Local.Transform = new_transfrom
    if frame is not None:
        xsi_translation = new_transfrom.Translation
        xsi_rotation = new_transfrom.Rotation.XYZAngles
        xsi_scale = new_transfrom.Scaling
        # set keys
        app.SaveKey(xsi_object.Name + ".kine.local.posx", frame, xsi_translation.X)
        app.SaveKey(xsi_object.Name + ".kine.local.posy", frame, xsi_translation.Y)
        app.SaveKey(xsi_object.Name + ".kine.local.posz", frame, xsi_translation.Z)
        app.SaveKey(xsi_object.Name + ".kine.local.rotx", frame, xsi_rotation.X * 180.0 / 3.14)
        app.SaveKey(xsi_object.Name + ".kine.local.roty", frame, xsi_rotation.Y * 180.0 / 3.14)
        app.SaveKey(xsi_object.Name + ".kine.local.rotz", frame, xsi_rotation.Z * 180.0 / 3.14)
        app.SaveKey(xsi_object.Name + ".kine.local.sclx", frame, xsi_scale.X)
        app.SaveKey(xsi_object.Name + ".kine.local.scly", frame, xsi_scale.Y)
        app.SaveKey(xsi_object.Name + ".kine.local.sclz", frame, xsi_scale.Z)


def set_xsi_transform(app, xsi_obj, usd_tfm):
    tfm_data = usd_tfm[0]
    time_samples = usd_tfm[1]
    if len(time_samples) == 0:
        # no animation
        set_xsi_transform_at_frame(app, xsi_obj, tfm_data)
    else:
        for i in range(len(time_samples)):
            frame = time_samples[i]
            set_xsi_transform_at_frame(app, xsi_obj, tfm_data[i], frame=frame)


def set_xsi_visibility(xsi_obj, is_visible):
    # in Softimage visibility is not inherited from parent objects. SO, in our case "inherited" means visible
    vis_prop = xsi_obj.Properties("Visibility")
    vis_prop.Parameters("viewvis").Value = is_visible
    vis_prop.Parameters("rendvis").Value = is_visible


def get_play_control_parameter(app, key):
    prop_list = app.ActiveProject.Properties
    play_ctrl = prop_list("Play Control")
    frame_param = play_ctrl.Parameters(key)
    return int(frame_param.Value + 0.5)


def get_current_frame(app):
    return get_play_control_parameter(app, "Current")


def get_start_timeline_frame(app):
    return get_play_control_parameter(app, "In")


def get_end_timeline_frame(app):
    return get_play_control_parameter(app, "Out")


def transpose_vectors_array(array):
    '''transform array of the form [(x1, y1, z1), (x2, y2, z2), ...] to [[x1, x2, ...], [y1, y2, ...], [z1, z2, ...]]
    '''
    x = []
    y = []
    z = []
    for v in array:
        x.append(v[0])
        y.append(v[1])
        z.append(v[2])
    return [x, y, z]


def transpose_2vectors_array(array):
    '''transform array of the form [(x1, y1), (x2, y2), ...] to [[x1, x2, ...], [y1, y2, ...]]
    '''
    x = []
    y = []
    for v in array:
        x.append(v[0])
        y.append(v[1])
    return [x, y]


def transpose_4vectors_array(array):
    '''transform array of the form [(x1, y1, z1, w1), (x2, y2, z2, w2) ...] to [[x1, x2, ...], [y1, y2, ...], [z1, z2, ...], [w1, w2, ...]]
    '''
    x = []
    y = []
    z = []
    w = []
    for v in array:
        x.append(v[0])
        y.append(v[1])
        z.append(v[2])
        w.append(v[3])
    return [x, y, z, w]


def usd_to_xsi_faces_array(face_indexes, face_sizes):
    polygons = []
    index = 0
    for f in face_sizes:
        polygons.append(f)
        for i in range(f):
            polygons.append(face_indexes[index])
            index += 1
    return polygons


# --------------------General----------------------------
def from_scene_path_to_models_path(path):
    path_head, path_tail = os.path.split(path)
    # change last folder from Scene to Models
    folders = path_head.split("\\")
    models_path = "\\".join(folders[:-1]) + "\\Models\\"
    # change extension in the file name
    name_parts = path_tail.split(".")
    file_name = ".".join(name_parts[:-1]) + ".usda"
    return models_path + file_name


def get_last_folder(path):
    parts = path.split("\\")
    return parts[-2]


def get_file_extension(path):
    return path.split(".")[-1]


def get_file_name(full_name):
    parts = full_name.split(".")
    return ".".join(parts[:-1])


def remove_first_folder(path):
    '''transform the path a/b/c/d to a/c/d
    '''
    parts = path.split("/")
    return "/".join([parts[0]] + parts[2:])


def get_bounding_box(positions):
    if len(positions) == 0:
        return [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)]

    min_x = positions[0][0]
    min_y = positions[0][1]
    min_z = positions[0][2]
    max_x = positions[0][0]
    max_y = positions[0][1]
    max_z = positions[0][2]
    for p in positions:
        if p[0] < min_x:
            min_x = p[0]
        elif p[0] > max_x:
            max_x = p[0]
        if p[1] < min_y:
            min_y = p[1]
        elif p[1] > max_y:
            max_y = p[1]
        if p[2] < min_z:
            min_z = p[2]
        elif p[2] > max_z:
            max_z = p[2]
    return [(min_x, min_y, min_z), (max_x, max_y, max_z)]


def get_index_in_array(array, value):  # also for tuple
    for a_index in range(len(array)):
        if array[a_index] == value:
            return a_index
    return None


def get_extension_from_params(params):
    opts = params.get("options", None)
    if opts is None:
        return "usd"
    else:
        return opts.get("extension", "usd")


def verify_extension(file_path):
    path_head, path_tail = os.path.split(file_path)
    point_index = path_tail.rfind(".")
    if point_index < 0:
        return file_path + ".usda"
    else:
        file_ext = path_tail[point_index + 1:]
        if file_ext in ["usd", "usda", "usdz"]:
            return file_path
        else:
            return path_head + "\\" + path_tail[:point_index] + ".usda"


def transform_path_to_relative(path, base_path):
    '''transform absolute path to relative with respect to base_path
    '''
    return os.path.relpath(base_path, path)[3:]


def get_closest_data(array, key):
    ''' for array [(0, a), (2, b), (3, c), (5, d)] and key = 3 return c

     we assume, that array is ordered by the first element in the tuple
     find closest value by binary search algorithm
    '''
    if len(array) == 1:
        return array[0][1]
    else:
        steps = 0
        start = 0
        end = len(array) - 1
        while end - start > 1:
            middle = (start + end) // 2
            if array[middle][0] < key:
                start = middle
            else:
                end = middle
            steps += 1
        if abs(key - array[start][0]) < abs(key - array[end][0]):
            return array[start][1]
        else:
            return array[end][1]


def collapse_usd_hard_edges_data(indices, length, sharpness):
    '''convert three attributes for usd edge sharpness to one array of triples (v_start, v_end, sharpness)
    '''
    to_return = []
    shift = 0
    for segment_index in range(len(length)):
        l = length[segment_index]
        for i in range(l - 1):
            to_return.append((indices[shift + i], indices[shift + i + 1], sharpness[segment_index]))
        shift += l

    return to_return


def remove_last_part(original_str):
    '''convert string aaa.bbb.ccc to aaa.bbb
    '''
    parts = original_str.split(".")
    if len(parts) > 1:
        sub_parts = parts[:-1]
        return ".".join(sub_parts)
    else:
        return original_str


def get_index_in_array_for_value(array, v):
    for a_index in range(len(array)):
        a = array[a_index]
        if a[0] == v:
            return a_index
    return None


def get_index_in_array_for_pair(array, v0, v1):
    for a_index in range(len(array)):
        a = array[a_index]
        if (a[0] == v0 and a[1] == v1) or (a[0] == v1 and a[1] == v0):
            return a_index
    return None


def get_in_dict(dict, key, default=None):
    '''the same as dict.get(key, default)
    XSI build-in dictionary does not supports this default method
    '''
    if key in dict:
        return dict[key]
    else:
        return default
