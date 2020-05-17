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
    '''import item and all it subcomponents in simple mode
    '''
    local_root = emit_item(app, options, usd_item, xsi_parent)
    if local_root is not None:
        print("iterate by " + str(usd_item))
        for child in usd_item.GetChildren():
            print("child: " + str(child))
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
    if item_type == "Xform" and constants.siNullPrimType in options["object_types"]:
        xform_name = predefined_name if predefined_name is not None else usd_item.GetName()
        usd_tfm = predefined_tfm if predefined_tfm is not None else prim_xform.get_transform(usd_item)
        is_visible = predefined_visibility if predefined_visibility is not None else prim_xform.get_visibility(usd_item)
        new_object = prim_xform.emit_null(app, xform_name, usd_tfm, is_visible, usd_item, xsi_parent)
    elif item_type == "Mesh" and constants.siPolyMeshType in options["object_types"]:
        xform_name = usd_item.GetName()
        usd_tfm = prim_xform.get_transform(usd_item)
        is_visible = prim_xform.get_visibility(usd_item)
        new_object = prim_mesh.emit_mesh(app, xform_name, usd_tfm, is_visible, usd_item, xsi_parent)

    return new_object


def import_item(app, options, usd_item, usd_stage, xsi_parent, is_root=False):
    '''options contains keys:
            clear_scene (True/False),
            is_materials (True/False),
            attributes (list of string for polymesh attributes)
            object_types (list of strings for imported objects)
    '''
    item_type = usd_item.GetTypeName()
    if item_type == "Xform":  # check only Xform, because each essential component should be child of the Xform
        new_object = None
        xform_name = usd_item.GetName()
        usd_tfm = prim_xform.get_transform(usd_item)
        is_visible = prim_xform.get_visibility(usd_item)
        childrens = geather_childrens(usd_item)  # this is a dict with key - prim type, value - array of prims
        ess_comp_count, ess_comp_names = get_number_of_essential_components(childrens)
        if ess_comp_count == 0 and constants.siNullPrimType in options["object_types"]:
            # all childrens are XForms, so current object should be also null
            # create it and iterate throw children
            # new_object = prim_xform.emit_null(app, xform_name, usd_tfm, is_visible, usd_item, xsi_parent)
            new_object = emit_item(app, options, usd_item, xsi_parent, predefined_name=xform_name, predefined_visibility=is_visible, predefined_tfm=usd_tfm)
        elif ess_comp_count == 1 and not utils.is_contains_transform(childrens[ess_comp_names[0]][0]):
            # there is exactly one essential componen and it does not contains transfrom
            # so, current xform is object with this component
            if ess_comp_names[0] == "Mesh" and constants.siPolyMeshType in options["object_types"]:
                # new_object = prim_mesh.emit_mesh(app, xform_name, usd_tfm, is_visible, childrens["Mesh"][0], xsi_parent)
                new_object = emit_item(app, options, usd_item, xsi_parent, predefined_name=xform_name, predefined_visibility=is_visible, predefined_tfm=usd_tfm)
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
