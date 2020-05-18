from pxr import Usd, UsdGeom
import utils
import imp


def add_transform_to_xfo(usd_xform, obj, opt_anim):
    if opt_anim is None:
        usd_xform.AddTransformOp().Set(utils.build_transform(obj))
    else:
        usd_tfm = usd_xform.AddTransformOp()
        for frame in range(opt_anim[0], opt_anim[1] + 1):
            usd_tfm.Set(utils.build_transform(obj, frame), Usd.TimeCode(frame))


def add_visibility_to_xfo(usd_xform, xsi_obj):
    xsi_vis_prop = xsi_obj.Properties("Visibility")
    usd_xform.CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible if xsi_vis_prop.Parameters("viewvis").Value is False else UsdGeom.Tokens.inherited)


def add_xform(app, params, path_for_objects, create_ref, stage, obj, root_path, is_instance=False):
    imp.reload(utils)
    # we should create a new stage and reference the old one to this new
    opt_animation = params.get("animation", None)
    # xsi_vis_prop = obj.Properties("Visibility")
    if create_ref:
        new_stage_name = obj.FullName + "." + utils.get_extension_from_params(params)
        stage_asset_path = path_for_objects + new_stage_name
        new_stage = Usd.Stage.CreateNew(stage_asset_path)
        utils.add_stage_metadata(new_stage, params)

        # add dfault root xform node for this new stage
        usd_xform = UsdGeom.Xform.Define(new_stage, "/" + obj.Name)
        # reference main stage to this new stage
        ref = stage.DefinePrim(root_path + "/" + obj.Name)
        ref.GetReferences().AddReference("./" + utils.get_last_folder(path_for_objects) + "/" + new_stage_name, "/" + obj.Name)
        if is_instance:
            ref.SetInstanceable(True)
        refXform = UsdGeom.Xformable(ref)
        add_visibility_to_xfo(refXform, obj)
        # refXform.CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible if xsi_vis_prop.Parameters("viewvis").Value is False else UsdGeom.Tokens.inherited)
    else:
        usd_xform = UsdGeom.Xform.Define(stage, root_path + "/" + obj.Name)
        add_visibility_to_xfo(usd_xform, obj)
        # usd_xform.CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible if xsi_vis_prop.Parameters("viewvis").Value is False else UsdGeom.Tokens.inherited)

    if create_ref:
        add_transform_to_xfo(refXform, obj, opt_animation)
    else:
        add_transform_to_xfo(usd_xform, obj, opt_animation)

    if create_ref:
        return usd_xform, new_stage, stage_asset_path
    else:
        return usd_xform, None, None


def get_transform(usd_item):
    usd_xform = UsdGeom.Xformable(usd_item)
    times_array = usd_xform.GetTimeSamples()  # array of time samples, it empty if no animation
    if len(times_array) == 0:
        usd_transform = usd_xform.GetLocalTransformation()
    else:
        usd_transform = [usd_xform.GetLocalTransformation(t) for t in times_array]
    return (usd_transform, times_array)


def get_visibility(usd_item):
    usd_xform = UsdGeom.Xformable(usd_item)
    vis_attr = usd_xform.ComputeVisibility()
    return vis_attr == "inherited"


def emit_null(app, null_name, usd_tfm, visibility, usd_prim, xsi_parent):
    xsi_null = app.GetPrim("Null", null_name, xsi_parent)
    utils.set_xsi_transform(app, xsi_null, usd_tfm)
    utils.set_xsi_visibility(xsi_null, visibility)
    return xsi_null
