from win32com.client import constants
from pxr import Usd
import utils
import prim_xform
import prim_mesh
import imp


def import_usd(app, file_path, options):
    imp.reload(utils)
    imp.reload(prim_xform)
    imp.reload(prim_mesh)
    is_clear = options.get("clear_scene", False)
    options["instances"] = {}  # key - path of the imported master object, value - link to the corresponding xsi-object
    options["file_path"] = file_path
    last_object_to_remove = None
    if is_clear:
        scene_root = app.ActiveProject2.ActiveScene.Root
        for child in scene_root.Children:
            if child.Type != "CameraRoot":
                app.DeleteObj("B:" + child.Name)
            else:
                last_object_to_remove = child

    stage = Usd.Stage.Open(file_path)
    root = stage.GetPseudoRoot()
    for item in root.GetChildren():
        import_item(app, options, item, stage, app.ActiveProject2.ActiveScene.Root, is_root=True)
    # for prim_ref in stage.Traverse():
        # print(prim_ref.GetPath())

    '''if last_object_to_remove is not None:
        app.DeleteObj("B:" + last_object_to_remove.Name)'''


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
        if k in ["Mesh", "Camera", "Points", "BasisCurves", "DiskLight", "RectLight", "DomeLight", "SphereLight", "DistantLight"]:
            to_return += len(v)
            names.add(k)
    return to_return, list(names)


def import_item_simple(app, options, usd_item, usd_stage, xsi_parent):
    '''import item and all it subcomponents in simple mode (in non-xform based approach)
    '''
    local_root = emit_item(app, options, usd_item, xsi_parent)
    if local_root is not None:
        for child in usd_item.GetChildren():
            # for all, exept Xform. For Xform we will try to use import_item
            item_type = child.GetTypeName()
            new_object = None
            if item_type != "Xform":
                new_object = emit_item(app, options, child, local_root)
            import_item(app, options, child, usd_stage, new_object if new_object is not None else local_root)


def emit_item(app, options, usd_item, xsi_parent, predefined_name=None, predefined_visibility=None, predefined_tfm=None):
    '''return new created object
    '''
    item_type = usd_item.GetTypeName()
    new_object = None
    xform_name = predefined_name if predefined_name is not None else usd_item.GetName()
    usd_tfm = predefined_tfm if predefined_tfm is not None else prim_xform.get_transform(usd_item)
    is_visible = predefined_visibility if predefined_visibility is not None else prim_xform.get_visibility(usd_item)
    if item_type == "Xform" and constants.siNullPrimType in options["object_types"]:
        new_object = prim_xform.emit_null(app, xform_name, usd_tfm, is_visible, usd_item, xsi_parent)
    elif item_type == "Mesh" and constants.siPolyMeshType in options["object_types"]:
        new_object = prim_mesh.emit_mesh(app, options, xform_name, usd_tfm, is_visible, usd_item, xsi_parent)

    return new_object


def import_item(app, options, usd_item, usd_stage, xsi_parent, is_root=False):
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
                    import_item(app, options, child, usd_stage, xsi_model)
                # save the link to the model onject
                options["instances"][str(usd_master.GetPath())] = xsi_model
        else:
            childrens = geather_childrens(usd_item)  # this is a dict with key - prim type, value - array of prims
            ess_comp_count, ess_comp_names = get_number_of_essential_components(childrens)
            if ess_comp_count == 0 and constants.siNullPrimType in options["object_types"]:
                # all childrens are XForms, so current object should be also null
                # create it and iterate throw children
                new_object = emit_item(app, options, usd_item, xsi_parent, predefined_name=xform_name, predefined_visibility=is_visible, predefined_tfm=usd_tfm)
            elif ess_comp_count == 1 and not utils.is_contains_transform(childrens[ess_comp_names[0]][0]):
                # there is exactly one essential componen and it does not contains transfrom
                # so, current xform is object with this component
                if ess_comp_names[0] == "Mesh" and constants.siPolyMeshType in options["object_types"]:
                    new_object = emit_item(app, options, childrens["Mesh"][0], xsi_parent, predefined_name=xform_name, predefined_visibility=is_visible, predefined_tfm=usd_tfm)
            else:
                # current is Xform, but it contains either several essential components, or one component but with transform
                # in this case we should create the null and all subcomponents emit as separate objects
                import_item_simple(app, options, usd_item, usd_stage, xsi_parent)
            if new_object is not None:
                for child in childrens.get("Xform", []):
                    import_item(app, options, child, usd_stage, new_object)
    else:
        if is_root:
            import_item_simple(app, options, usd_item, usd_stage, xsi_parent)
        else:
            for child in usd_item.GetChildren():
                import_item_simple(app, options, child, usd_stage, xsi_parent)
