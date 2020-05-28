from win32com.client import constants
from pxr import Usd, UsdGeom
import time
import os
import prim_mesh
import prim_xform
import prim_camera
import prim_light
import prim_hair
import prim_model
import prim_pointcloud
import materials
import utils
import imp

DEBUG_MODE = True


def export(app, file_path, params, xsi_toolkit):
    if DEBUG_MODE:
        imp.reload(prim_xform)
        imp.reload(prim_mesh)
        imp.reload(prim_camera)
        imp.reload(prim_light)
        imp.reload(prim_hair)
        imp.reload(prim_model)
        imp.reload(prim_pointcloud)
        imp.reload(materials)
        imp.reload(utils)

    start_time = time.time()

    progress_bar = xsi_toolkit.ProgressBar
    progress_bar.Caption = ""
    progress_bar.CancelEnabled = False
    progress_bar.Visible = True

    stage = Usd.Stage.CreateNew(file_path)
    path_head, path_tail = os.path.split(file_path)
    path_for_objects = path_head + "\\" + utils.get_file_name(path_tail) + "_objects\\"
    utils.add_stage_metadata(stage, params)

    opts = params.get("options", None)
    if opts is not None:
        opts["extension"] = utils.get_file_extension(file_path)

    is_materials = True
    mats = params.get("materials", None)
    if mats is not None:
        is_materials = mats.get("is_materials", True)

    root_path = ""
    materials_opt = {}  # some parameters of the exported materials
    material_asset_path = None
    if is_materials:
        materials_path = path_head + "\\" + utils.get_file_name(path_tail) + "_materials." + opts["extension"]
        material_asset_path = materials.export_materials(app, params, stage, materials_path, progress_bar)
    materials_opt["asset_path"] = material_asset_path

    exported_objects = []  # store here ObjectID of exported objects
    if len(params["objects_list"]) == 1 and params["objects_list"][0].ObjectID == app.ActiveProject2.ActiveScene.Root.ObjectID:
        for obj in app.ActiveProject2.ActiveScene.Root.Children:
            export_step(app, params, path_for_objects, stage, obj, exported_objects, materials_opt, root_path, progress_bar)
    else:
        for obj in params["objects_list"]:
            export_step(app, params, path_for_objects, stage, obj, exported_objects, materials_opt, root_path, progress_bar)
    stage.Save()

    progress_bar.Visible = False

    finish_time = time.time()
    print("[USD Export]: total export time " + str(finish_time - start_time) + " seconds")


def export_step(app, params, path_for_objects, stage, obj, exported_objects, materials_opt, root_path, progress_bar=None):
    opt_object_types = params.get("object_types", ())
    opt = params.get("options", {})
    obj_type = obj.Type
    if progress_bar is not None:
        progress_bar.Caption = utils.build_export_object_caption(obj)
    if obj.ObjectID not in exported_objects:
        usd_pointer = None
        if obj_type == constants.siPolyMeshType and obj_type in opt_object_types:
            # mesh
            usd_pointer = prim_mesh.add_mesh(app, params, path_for_objects, stage, obj, materials_opt, root_path, progress_bar)
        elif obj_type == constants.siCameraPrimType and obj_type in opt_object_types:
            # camera
            usd_pointer = prim_camera.add_camera(app, params, path_for_objects, stage, obj, root_path)
        elif obj_type == constants.siLightPrimType and obj_type in opt_object_types:
            # light
            usd_pointer = prim_light.add_light(app, params, path_for_objects, stage, obj, root_path)
        elif obj_type == "hair" and obj_type in opt_object_types:
            # xsi hair
            usd_pointer = prim_hair.add_hair(app, params, path_for_objects, stage, obj, materials_opt, root_path, progress_bar)
        elif obj_type == "pointcloud" and obj_type in opt_object_types and utils.is_stands(obj) and "strands" in opt_object_types:
            # strands hair
            usd_pointer = prim_hair.add_strands(app, params, path_for_objects, stage, obj, materials_opt, root_path, progress_bar)
        elif obj_type == "pointcloud" and obj_type in opt_object_types and not utils.is_stands(obj):
            # pointcloud
            usd_pointer = prim_pointcloud.add_pointcloud(app, params, path_for_objects, stage, obj, materials_opt, root_path, progress_bar)
        elif obj_type == constants.siModelType:
            # model
            master = obj.InstanceMaster
            if master is None:
                # this is model
                # for models does not go to it childrens, because all models export as separate usd-files
                prim_model.add_model(app, params, path_for_objects, stage, obj, materials_opt, root_path)
                exported_objects.append(obj.ObjectID)
            else:
                # this is an instance of the model
                master_id = master.ObjectID
                if master_id not in exported_objects:
                    # master is not exported, do this
                    prim_model.add_model(app, params, path_for_objects, stage, master, materials_opt, root_path)
                    exported_objects.append(master.ObjectID)
                # next export the link of the instance
                usd_model = stage.DefinePrim(root_path + "/" + obj.Name)
                usd_model.GetReferences().AddReference("./" + utils.get_last_folder(path_for_objects) + "/" + master.FullName + ".usda", "/" + master.Name)
                usd_model.SetInstanceable(True)
                usd_pointer = UsdGeom.Xformable(usd_model)
                prim_xform.add_transform_to_xfo(usd_pointer, obj, params.get("animation", None))
                prim_xform.add_visibility_to_xfo(usd_pointer, obj)
        elif (obj_type == constants.siNullPrimType and constants.siNullPrimType in opt_object_types) or (obj_type == "CameraRoot" and constants.siCameraPrimType in opt_object_types):
            # null
            usd_pointer, ref_stage, ref_stage_asset = prim_xform.add_xform(app, params, path_for_objects, False, stage, obj, root_path)
        elif obj_type in ["cyclesPoint", "cyclesSun", "cyclesSpot", "cyclesArea", "cyclesBackground"]:
            # cycles light
            usd_pointer = prim_light.add_cycles_light(app, params, path_for_objects, stage, obj, materials_opt, root_path)
        else:
            if obj_type != "CameraInterest":  # camera interest can be recteated from cameta transform and focus distance
                if not opt.get("ignore_unknown", True):
                    # all unsupported object are nulls, so they are Xforms
                    print("Unknown object " + obj_type + ". Degrade to xform")
                    usd_pointer, ref_stage, ref_stage_asset = prim_xform.add_xform(app, params, path_for_objects, False, stage, obj, root_path)
        # continue recirsive process
        if usd_pointer is not None:
            exported_objects.append(obj.ObjectID)
            for child in obj.Children:
                export_step(app, params, path_for_objects, stage, child, exported_objects, materials_opt, str(usd_pointer.GetPath()), progress_bar)
