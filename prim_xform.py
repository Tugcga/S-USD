from pxr import Usd, UsdGeom
import utils
import imp


def add_xform(app, params, path_for_objects, create_ref, stage, obj, root_path):
    imp.reload(utils)
    # we should create a new stage and reference the old one to this new
    opt_animation = params.get("animation", None)
    xsi_vis_prop = obj.Properties("Visibility")
    if create_ref:
        new_stage_name = obj.FullName + ".usda"
        new_stage = Usd.Stage.CreateNew(path_for_objects + new_stage_name)
        utils.add_stage_metadata(new_stage, params)

        # add dfault root xform node for this new stage
        usd_xform = UsdGeom.Xform.Define(new_stage, "/" + obj.Name)
        # reference main stage to this new stage
        # ref = stage.OverridePrim(root_path + "/" + obj.Name)
        ref = stage.DefinePrim(root_path + "/" + obj.Name)
        ref.GetReferences().AddReference("./" + utils.get_last_folder(path_for_objects) + "/" + new_stage_name, "/" + obj.Name)
        refXform = UsdGeom.Xformable(ref)
        refXform.CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible if xsi_vis_prop.Parameters("viewvis").Value is False else UsdGeom.Tokens.inherited)
    else:
        usd_xform = UsdGeom.Xform.Define(stage, root_path + "/" + obj.Name)
        usd_xform.CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible if xsi_vis_prop.Parameters("viewvis").Value is False else UsdGeom.Tokens.inherited)

    if opt_animation is None:
        if create_ref:
            refXform.AddTransformOp().Set(utils.build_transform(obj))
        else:
            usd_xform.AddTransformOp().Set(utils.build_transform(obj))
    else:
        if create_ref:
            usd_tfm = refXform.AddTransformOp()
            for frame in range(opt_animation[0], opt_animation[1] + 1):
                usd_tfm.Set(utils.build_transform(obj, frame), Usd.TimeCode(frame))
        else:
            usd_tfm = usd_xform.AddTransformOp()
            for frame in range(opt_animation[0], opt_animation[1] + 1):
                usd_tfm.Set(utils.build_transform(obj, frame), Usd.TimeCode(frame))

    if create_ref:
        return usd_xform, new_stage
    else:
        return usd_xform, None
