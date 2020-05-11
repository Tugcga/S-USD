from pxr import Usd, UsdGeom, Gf


def build_transform(obj, frame=None):
    tfm_matrix = obj.Kinematics.Local.Transform.Matrix4 if frame is None else obj.Kinematics.Local.GetTransform2(frame).Matrix4
    return Gf.Matrix4d(
            tfm_matrix.Value(0, 0), tfm_matrix.Value(0, 1), tfm_matrix.Value(0, 2), tfm_matrix.Value(0, 3),
            tfm_matrix.Value(1, 0), tfm_matrix.Value(1, 1), tfm_matrix.Value(1, 2), tfm_matrix.Value(1, 3),
            tfm_matrix.Value(2, 0), tfm_matrix.Value(2, 1), tfm_matrix.Value(2, 2), tfm_matrix.Value(2, 3),
            tfm_matrix.Value(3, 0), tfm_matrix.Value(3, 1), tfm_matrix.Value(3, 2), tfm_matrix.Value(3, 3),
        )


def add_xform(app, params, stage, obj, root_path):
    # create prim
    opt_animation = params.get("animation", None)
    usd_xform = UsdGeom.Xform.Define(stage, root_path + "/" + obj.Name)
    xsi_vis_prop = obj.Properties("Visibility")
    # visibility_render = obj.Properties("Visibility").rendvis.Value
    usd_xform.CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible if xsi_vis_prop.Parameters("viewvis").Value is False else UsdGeom.Tokens.inherited)
    # add transform
    if opt_animation is None:
        usd_xform.AddTransformOp().Set(build_transform(obj))
    else:
        usd_tfm = usd_xform.AddTransformOp()
        for frame in range(opt_animation[0], opt_animation[1] + 1):
            usd_tfm.Set(build_transform(obj, frame), Usd.TimeCode(frame))
    return usd_xform
