from pxr import UsdGeom, Usd
from prim_xform import add_xform
import utils
import imp


def set_camera_focallength(xsi_camera, usd_camera, frame=None):
    xsi_focal_length = (xsi_camera.Parameters("projplanedist").Value if frame is None else xsi_camera.Parameters("projplanedist").GetValue2(frame))
    if frame is None:
        usd_camera.CreateFocalLengthAttr().Set(xsi_focal_length)
    else:
        usd_camera.CreateFocalLengthAttr().Set(xsi_focal_length, Usd.TimeCode(frame))


def set_camera_focusdistance(xsi_camera, usd_camera, frame=None):
    xsi_interest = xsi_camera.Interest
    # get global position of the camera and the interest
    xsi_camera_position = xsi_camera.Kinematics.Global.Transform.Translation if frame is None else xsi_camera.Kinematics.Local.GetTransform2(frame).Translation
    xsi_interest_position = xsi_interest.Kinematics.Global.Transform.Translation if frame is None else xsi_interest.Kinematics.Local.GetTransform2(frame).Translation
    if frame is None:
        usd_camera.CreateFocusDistanceAttr().Set(utils.get_distance(xsi_camera_position, xsi_interest_position))
    else:
        usd_camera.CreateFocusDistanceAttr().Set(utils.get_distance(xsi_camera_position, xsi_interest_position), Usd.TimeCode(frame))


def add_camera(app, params, path_for_objects, stage, xsi_camera, root_path):
    imp.reload(utils)
    usd_xform, ref_stage, ref_stage_asset = add_xform(app, params, path_for_objects, True, stage, xsi_camera, root_path)
    usd_camera = UsdGeom.Camera.Define(ref_stage, str(usd_xform.GetPath()) + "/" + xsi_camera.Name)
    # set time independent attributes
    # perspective or ortographic
    if xsi_camera.Parameters("proj").Value == 0:
        usd_camera.CreateProjectionAttr().Set(UsdGeom.Tokens.orthographic)
    else:
        usd_camera.CreateProjectionAttr().Set(UsdGeom.Tokens.perspective)

    # clipping planes
    usd_camera.CreateClippingRangeAttr().Set((xsi_camera.Parameters("near").Value, xsi_camera.Parameters("far").Value))

    # visibility
    xsi_vis_prop = xsi_camera.Properties("Visibility")
    usd_camera.CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible if xsi_vis_prop.Parameters("viewvis").Value is False else UsdGeom.Tokens.inherited)

    # aperture size, w = 1024 pixels
    xsi_w = 1024
    xsi_aspect = xsi_camera.Parameters("aspect").Value
    usd_camera.CreateHorizontalApertureAttr().Set(xsi_w)
    usd_camera.CreateVerticalApertureAttr().Set(xsi_w / xsi_aspect)
    # offset is zero
    usd_camera.CreateHorizontalApertureOffsetAttr().Set(0)
    usd_camera.CreateVerticalApertureOffsetAttr().Set(0)

    opt_animation = params.get("animation", None)
    if opt_animation is None or not utils.is_focallength_animated(xsi_camera, opt_animation):
        set_camera_focallength(xsi_camera, usd_camera)
    else:
        for frame in range(opt_animation[0], opt_animation[1] + 1):
            set_camera_focallength(xsi_camera, usd_camera, frame)

    if opt_animation is None or not utils.is_focusdistance_animated(xsi_camera, opt_animation):
        set_camera_focusdistance(xsi_camera, usd_camera)
    else:
        for frame in range(opt_animation[0], opt_animation[1] + 1):
            set_camera_focusdistance(xsi_camera, usd_camera, frame)
    ref_stage.Save()

    return stage.GetPrimAtPath(root_path + str(usd_xform.GetPath()))
