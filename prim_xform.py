from pxr import Usd, UsdGeom, Gf


def build_transform(obj, frame=None):
    tfm_matrix = obj.Kinematics.Local.Transform.Matrix4 if frame is None else obj.Kinematics.Local.GetTransform2(frame).Matrix4
    return Gf.Matrix4d(
            tfm_matrix.Value(0, 0), tfm_matrix.Value(0, 1), tfm_matrix.Value(0, 2), tfm_matrix.Value(0, 3),
            tfm_matrix.Value(1, 0), tfm_matrix.Value(1, 1), tfm_matrix.Value(1, 2), tfm_matrix.Value(1, 3),
            tfm_matrix.Value(2, 0), tfm_matrix.Value(2, 1), tfm_matrix.Value(2, 2), tfm_matrix.Value(2, 3),
            tfm_matrix.Value(3, 0), tfm_matrix.Value(3, 1), tfm_matrix.Value(3, 2), tfm_matrix.Value(3, 3),
        )


def get_last_folder(path):
    parts = path.split("\\")
    return parts[-2]


def add_xform(app, params, path_for_objects, create_ref, stage, obj, root_path):
    # we should create a new stage and reference the old one to this new
    opt_animation = params.get("animation", None)
    xsi_vis_prop = obj.Properties("Visibility")
    if create_ref:
        new_stage_name = obj.FullName + ".usda"
        new_stage = Usd.Stage.CreateNew(path_for_objects + new_stage_name)
        # add dfault root xform node for this new stage
        usd_xform = UsdGeom.Xform.Define(new_stage, "/" + obj.Name)
        # reference main stage to this new stage
        ref = stage.OverridePrim(root_path + "/" + obj.Name)
        ref.GetReferences().AddReference("./" + get_last_folder(path_for_objects) + "/" + new_stage_name, "/" + obj.Name)
        refXform = UsdGeom.Xformable(ref)
        refXform.CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible if xsi_vis_prop.Parameters("viewvis").Value is False else UsdGeom.Tokens.inherited)
    else:
        usd_xform = UsdGeom.Xform.Define(stage, root_path + "/" + obj.Name)
        usd_xform.CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible if xsi_vis_prop.Parameters("viewvis").Value is False else UsdGeom.Tokens.inherited)

    if opt_animation is None:
        if create_ref:
            refXform.AddTransformOp().Set(build_transform(obj))
        else:
            usd_xform.AddTransformOp().Set(build_transform(obj))
    else:
        if create_ref:
            usd_tfm = refXform.AddTransformOp()
            for frame in range(opt_animation[0], opt_animation[1] + 1):
                usd_tfm.Set(build_transform(obj, frame), Usd.TimeCode(frame))
        else:
            usd_tfm = usd_xform.AddTransformOp()
            for frame in range(opt_animation[0], opt_animation[1] + 1):
                usd_tfm.Set(build_transform(obj, frame), Usd.TimeCode(frame))

    if create_ref:
        return usd_xform, new_stage
    else:
        return usd_xform, None

    # create prim
    '''opt_animation = params.get("animation", None)
    usd_xform = UsdGeom.Xform.Define(stage, root_path + "/" + obj.Name)
    xsi_vis_prop = obj.Properties("Visibility")
    usd_xform.CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible if xsi_vis_prop.Parameters("viewvis").Value is False else UsdGeom.Tokens.inherited)
    # add transform
    if opt_animation is None:
        usd_xform.AddTransformOp().Set(build_transform(obj))
    else:
        usd_tfm = usd_xform.AddTransformOp()
        for frame in range(opt_animation[0], opt_animation[1] + 1):
            usd_tfm.Set(build_transform(obj, frame), Usd.TimeCode(frame))
    return usd_xform'''
