from win32com.client import constants
from pxr import Usd, UsdGeom
import os
import prim_mesh
import prim_xform
import prim_camera
import prim_light
import prim_hair
import imp


def get_file_name(full_name):
    parts = full_name.split(".")
    return ".".join(parts[:-1])


def export(app, file_path, params):
    imp.reload(prim_xform)
    imp.reload(prim_mesh)
    imp.reload(prim_camera)
    imp.reload(prim_light)
    imp.reload(prim_hair)

    stage = Usd.Stage.CreateNew(file_path)
    path_head, path_tail = os.path.split(file_path)
    path_for_objects = path_head + "\\" + get_file_name(path_tail) + "_objects\\"
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    if params["animation"] is not None:
        stage.SetStartTimeCode(params["animation"][0])
        stage.SetEndTimeCode(params["animation"][1])
    root_path = ""
    exported_objects = []  # store here ObjectID of exported objects
    if len(params["objects_list"]) == 1 and params["objects_list"][0].ObjectID == app.ActiveProject2.ActiveScene.Root.ObjectID:
        for obj in app.ActiveProject2.ActiveScene.Root.Children:
            export_step(app, params, path_for_objects, stage, obj, exported_objects, root_path)
    else:
        for obj in params["objects_list"]:
            export_step(app, params, path_for_objects, stage, obj, exported_objects, root_path)
    stage.Save()


def is_stands(pc_object):
    pc_geo = pc_object.GetActivePrimitive2().Geometry
    strands_position_attr = pc_geo.GetICEAttributeFromName("StrandPosition")
    strands_data = strands_position_attr.DataArray2D
    return len(strands_data) > 0


def export_step(app, params, path_for_objects, stage, obj, exported_objects, root_path):
    opt_object_types = params.get("object_types", ())
    opt = params.get("options", {})
    obj_type = obj.Type
    if obj.ObjectID not in exported_objects:
        usd_pointer = None
        if obj_type == constants.siPolyMeshType and obj_type in opt_object_types:
            usd_pointer = prim_mesh.add_mesh(app, params, path_for_objects, stage, obj, root_path)
        elif obj_type == constants.siCameraPrimType and obj_type in opt_object_types:
            usd_pointer = prim_camera.add_camera(app, params, path_for_objects, stage, obj, root_path)
        elif obj_type == constants.siLightPrimType and obj_type in opt_object_types:
            usd_pointer = prim_light.add_light(app, params, path_for_objects, stage, obj, root_path)
        elif obj_type == "hair" and obj_type in opt_object_types:
            pass
            # usd_pointer = prim_hair.add_hair(app, params, stage, obj, root_path)
            # should implement c++ command for reading hair point positions
        elif obj_type == "pointcloud" and obj_type in opt_object_types and is_stands(obj) and "strands" in opt_object_types:
            usd_pointer = prim_hair.add_strands(app, params, path_for_objects, stage, obj, root_path)
        elif obj_type == "pointcloud" and obj_type in opt_object_types and not is_stands(obj):
            # simple pointcloud
            pass
        elif (obj_type == constants.siNullPrimType or obj_type == "CameraRoot") and constants.siNullPrimType in opt_object_types:
            usd_pointer, ref_stage = prim_xform.add_xform(app, params, path_for_objects, False, stage, obj, root_path)
        else:
            if obj_type != "CameraInterest":  # camera interest can be recteated from cameta transform and focus distance
                if not opt.get("ignore_unknown", True):
                    # all unsupported object are nulls, so they are Xforms
                    print("Unknown object " + obj_type + ". Degrade to xform")
                    usd_pointer, ref_stage = prim_xform.add_xform(app, params, path_for_objects, False, stage, obj, root_path)
        # continue recirsive process
        if usd_pointer is not None:
            exported_objects.append(obj.ObjectID)
            for child in obj.Children:
                export_step(app, params, path_for_objects, stage, child, exported_objects, str(usd_pointer.GetPath()))
