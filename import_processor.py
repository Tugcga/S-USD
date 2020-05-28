from win32com.client import constants
from pxr import Usd, UsdGeom
import time
import utils
import prim_xform
import prim_hair
import prim_mesh
import prim_pointcloud
import prim_light
import prim_camera
import materials
import imp

DEBUG_MODE = True


def import_usd(app, file_path, options, xsi_toolkit):
    if DEBUG_MODE:
        imp.reload(utils)
        imp.reload(prim_xform)
        imp.reload(prim_mesh)
        imp.reload(prim_pointcloud)
        imp.reload(prim_hair)
        imp.reload(prim_light)
        imp.reload(prim_camera)
        imp.reload(materials)

    start_time = time.time()

    progress_bar = xsi_toolkit.ProgressBar
    progress_bar.Caption = ""
    progress_bar.CancelEnabled = False
    progress_bar.Visible = True

    is_clear = options.get("clear_scene", False)
    options["instances"] = {}  # key - path of the imported master object, value - link to the corresponding xsi-object
    options["file_path"] = file_path
    options["project_path"] = app.ActiveProject3.Path
    options["file_name"] = utils.get_file_name_from_path(file_path)  # without extension
    options["import_camera"] = False
    cameras_to_remove = []
    if is_clear:
        progress_bar.Caption = "Clear the scene"
        if options["is_materials"]:
            # clear material library
            materials.import_clear_library(app, options["file_name"])

        scene_root = app.ActiveProject2.ActiveScene.Root
        for child in scene_root.Children:
            if utils.is_contains_camera(child):
                cameras_to_remove.append(child)
            else:
                progress_bar.Caption = "Clear the scene: delete " + child.Name
                app.DeleteObj("B:" + child.Name)

    stage = Usd.Stage.Open(file_path)
    up_axis = UsdGeom.GetStageUpAxis(stage)
    options["up_axis"] = up_axis  # Y or Z (for Softimage Y is more convinient)
    root = stage.GetPseudoRoot()
    for item in root.GetChildren():
        import_item(app, options, item, stage, app.ActiveProject2.ActiveScene.Root, progress_bar, is_root=True)

    if is_clear:
        progress_bar.Caption = "Final clean"
        for cam_index in range(len(cameras_to_remove) + (0 if options["import_camera"] else -1)):  # delete all cameras except the last one, if there are no any new cameras in the imported scene
            app.DeleteObj("B:" + cameras_to_remove[cam_index].Name)

    progress_bar.Visible = False

    finish_time = time.time()
    print("[USD Import]: total import time " + str(finish_time - start_time) + " seconds")


def geather_childrens(usd_prim):
    to_return = {}
    for child in usd_prim.GetChildren():
        child_type = child.GetTypeName()
        if child_type in to_return:
            to_return[child_type].append(child)
        else:
            to_return[child_type] = [child]
    return to_return


def get_number_of_essential_components(components):
    '''components are dictionary, where key - name, value - array
    component essential if it non-epmty and differ from Xform
    '''
    to_return = 0
    names = set()
    for k, v in components.items():
        if k in ["Mesh", "Camera", "Points", "BasisCurves", "DiskLight", "RectLight", "DomeLight", "SphereLight", "DistantLight", "CylinderLight", "LightPortal"]:
            to_return += len(v)
            names.add(k)
    return to_return, list(names)


def import_item_simple(app, options, usd_item, usd_stage, xsi_parent, progress_bar):
    '''import item and all it subcomponents in simple mode (in non-xform based approach)
    '''
    local_root = emit_item(app, options, usd_item, xsi_parent, progress_bar)
    if local_root is not None:
        for child in usd_item.GetChildren():
            # for all, exept Xform. For Xform we will try to use import_item
            item_type = child.GetTypeName()
            new_object = None
            if item_type != "Xform":
                new_object = emit_item(app, options, child, local_root, progress_bar)
            import_item(app, options, child, usd_stage, new_object if new_object is not None else local_root, progress_bar)


def emit_item(app, options, usd_item, xsi_parent, progress_bar, predefined_name=None, predefined_visibility=None, predefined_tfm=None):
    '''return new created object
    '''
    progress_bar.Caption = "Import " + str(usd_item)
    item_type = usd_item.GetTypeName()
    new_object = None
    xform_name = predefined_name if predefined_name is not None else usd_item.GetName()
    usd_tfm = predefined_tfm if predefined_tfm is not None else prim_xform.get_transform(usd_item)
    is_visible = predefined_visibility if predefined_visibility is not None else prim_xform.get_visibility(usd_item)
    if item_type == "Xform" and constants.siNullPrimType in options["object_types"]:
        new_object = prim_xform.emit_null(app, xform_name, usd_tfm, is_visible, usd_item, xsi_parent, options["up_axis"])
    elif item_type == "Mesh" and constants.siPolyMeshType in options["object_types"]:
        new_object = prim_mesh.emit_mesh(app, options, xform_name, usd_tfm, is_visible, usd_item, xsi_parent, is_simple=predefined_name is None)
    elif item_type == "Points" and "pointcloud" in options["object_types"]:
        new_object = prim_pointcloud.emit_pointcloud(app, options, xform_name, usd_tfm, is_visible, usd_item, False, xsi_parent, is_simple=predefined_name is None)
    elif item_type == "BasisCurves" and "strands" in options["object_types"]:
        new_object = prim_pointcloud.emit_pointcloud(app, options, xform_name, usd_tfm, is_visible, usd_item, True, xsi_parent, is_simple=predefined_name is None)
    elif item_type in ["SphereLight", "DistantLight", "LightPortal", "RectLight", "DiskLight", "DomeLight", "CylinderLight"] and constants.siLightPrimType in options["object_types"]:
        new_object = prim_light.emit_light(app, options, xform_name, usd_tfm, is_visible, usd_item, item_type, xsi_parent, is_simple=predefined_name is None)
    elif item_type == "Camera" and constants.siCameraPrimType in options["object_types"]:
        new_object = prim_camera.emit_camera(app, options, xform_name, usd_tfm, is_visible, usd_item, xsi_parent, is_simple=predefined_name is None)
        if new_object is not None:
            options["import_camera"] = True

    return new_object


def import_item(app, options, usd_item, usd_stage, xsi_parent, progress_bar, is_root=False):
    '''Use xform-based approach. It means, that each object defined by subcomponent of the xform node
    options contains keys:
            clear_scene (True/False),
            is_materials (True/False),
            attributes (list of string for polymesh attributes)
            object_types (list of strings for imported objects)
    '''
    item_type = usd_item.GetTypeName()
    if item_type == "Xform":  # check only Xform, because each essential component should be child of the Xform
        new_object = None
        xform_name = usd_item.GetName()
        usd_tfm = prim_xform.get_transform(usd_item)  # usd_tfm is a tuple (array of transforms or one transform, array of time samples)
        is_visible = prim_xform.get_visibility(usd_item)
        if usd_item.IsInstance():
            # this is an instance
            usd_master = usd_item.GetMaster()
            if str(usd_master.GetPath()) in options["instances"]:
                # master already created, use it for instancing model
                xsi_model = options["instances"][str(usd_master.GetPath())]
                xsi_instance = app.Instantiate(xsi_model)[0]
                app.DeselectAll()
                if xsi_parent.ObjectID != app.ActiveProject2.ActiveScene.Root.ObjectID:
                    app.CopyPaste(xsi_instance, "", xsi_parent, 1)
                utils.set_xsi_visibility(xsi_instance, is_visible)
                utils.set_xsi_transform(app, xsi_instance, usd_tfm)
            else:
                # create the model
                app.DeselectAll()
                xsi_model = app.CreateModel("", xform_name, xsi_parent)[0]
                utils.set_xsi_visibility(xsi_model, is_visible)
                utils.set_xsi_transform(app, xsi_model, usd_tfm)
                # instert objects inside this model
                for child in usd_master.GetChildren():
                    import_item(app, options, child, usd_stage, xsi_model, progress_bar)
                # save the link to the model onject
                options["instances"][str(usd_master.GetPath())] = xsi_model
        else:
            childrens = geather_childrens(usd_item)  # this is a dict with key - prim type, value - array of prims
            ess_comp_count, ess_comp_names = get_number_of_essential_components(childrens)
            if ess_comp_count == 0 and constants.siNullPrimType in options["object_types"]:
                # all childrens are XForms, so current object should be also null
                # create it and iterate throw children
                new_object = emit_item(app, options, usd_item, xsi_parent, progress_bar, predefined_name=xform_name, predefined_visibility=is_visible, predefined_tfm=usd_tfm)
            elif ess_comp_count == 1 and not utils.is_contains_transform(childrens[ess_comp_names[0]][0]):
                # there is exactly one essential componen and it does not contains transfrom
                # so, current xform is object with this component
                if ess_comp_names[0] == "Mesh" and constants.siPolyMeshType in options["object_types"]:
                    new_object = emit_item(app, options, childrens["Mesh"][0], xsi_parent, progress_bar, predefined_name=xform_name, predefined_visibility=is_visible, predefined_tfm=usd_tfm)
                elif ess_comp_names[0] == "Points" and "pointcloud" in options["object_types"]:
                    new_object = emit_item(app, options, childrens["Points"][0], xsi_parent, progress_bar, predefined_name=xform_name, predefined_visibility=is_visible, predefined_tfm=usd_tfm)
                elif ess_comp_names[0] == "BasisCurves" and "strands" in options["object_types"]:
                    new_object = emit_item(app, options, childrens["BasisCurves"][0], xsi_parent, progress_bar, predefined_name=xform_name, predefined_visibility=is_visible, predefined_tfm=usd_tfm)
                elif ess_comp_names[0] == "Camera" and constants.siCameraPrimType in options["object_types"]:
                    new_object = emit_item(app, options, childrens["Camera"][0], xsi_parent, progress_bar, predefined_name=xform_name, predefined_visibility=is_visible, predefined_tfm=usd_tfm)
                elif ess_comp_names[0] == "SphereLight" and constants.siLightPrimType in options["object_types"]:
                    new_object = emit_item(app, options, childrens["SphereLight"][0], xsi_parent, progress_bar, predefined_name=xform_name, predefined_visibility=is_visible, predefined_tfm=usd_tfm)
                elif ess_comp_names[0] == "DistantLight" and constants.siLightPrimType in options["object_types"]:
                    new_object = emit_item(app, options, childrens["DistantLight"][0], xsi_parent, progress_bar, predefined_name=xform_name, predefined_visibility=is_visible, predefined_tfm=usd_tfm)
                elif ess_comp_names[0] == "LightPortal" and constants.siLightPrimType in options["object_types"]:
                    new_object = emit_item(app, options, childrens["LightPortal"][0], xsi_parent, progress_bar, predefined_name=xform_name, predefined_visibility=is_visible, predefined_tfm=usd_tfm)
                elif ess_comp_names[0] == "RectLight" and constants.siLightPrimType in options["object_types"]:
                    new_object = emit_item(app, options, childrens["RectLight"][0], xsi_parent, progress_bar, predefined_name=xform_name, predefined_visibility=is_visible, predefined_tfm=usd_tfm)
                elif ess_comp_names[0] == "DiskLight" and constants.siLightPrimType in options["object_types"]:
                    new_object = emit_item(app, options, childrens["DiskLight"][0], xsi_parent, progress_bar, predefined_name=xform_name, predefined_visibility=is_visible, predefined_tfm=usd_tfm)
                elif ess_comp_names[0] == "DomeLight" and constants.siLightPrimType in options["object_types"]:
                    new_object = emit_item(app, options, childrens["DomeLight"][0], xsi_parent, progress_bar, predefined_name=xform_name, predefined_visibility=is_visible, predefined_tfm=usd_tfm)
                elif ess_comp_names[0] == "CylinderLight" and constants.siLightPrimType in options["object_types"]:
                    new_object = emit_item(app, options, childrens["CylinderLight"][0], xsi_parent, progress_bar, predefined_name=xform_name, predefined_visibility=is_visible, predefined_tfm=usd_tfm)
            else:
                # current is Xform, but it contains either several essential components, or one component but with transform
                # in this case we should create the null and all subcomponents emit as separate objects
                import_item_simple(app, options, usd_item, usd_stage, xsi_parent, progress_bar)
            if new_object is not None:
                for child in childrens.get("Xform", []):
                    import_item(app, options, child, usd_stage, new_object, progress_bar)
    else:
        if is_root:
            import_item_simple(app, options, usd_item, usd_stage, xsi_parent, progress_bar)
        else:
            for child in usd_item.GetChildren():
                import_item_simple(app, options, child, usd_stage, xsi_parent, progress_bar)
