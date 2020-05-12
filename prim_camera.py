from pxr import UsdGeom, Usd
from prim_xform import add_xform
import math


def get_distance(start, end):
    return math.sqrt((start.X - end.X)**2 + (start.Y - end.Y)**2 + (start.Z - end.Z)**2)


def set_camera_at_frame(xsi_camera, usd_camera, frame=None):
    xsi_interest = xsi_camera.Interest
    # get global position of the camera and the interest
    xsi_camera_position = xsi_camera.Kinematics.Global.Transform.Translation if frame is None else xsi_camera.Kinematics.Local.GetTransform2(frame).Translation
    xsi_interest_position = xsi_interest.Kinematics.Global.Transform.Translation if frame is None else xsi_interest.Kinematics.Local.GetTransform2(frame).Translation
    xsi_focal_length = (xsi_camera.Parameters("projplanedist").Value if frame is None else xsi_camera.Parameters("projplanedist").GetValue2(frame))
    if frame is None:
        usd_camera.CreateFocalLengthAttr().Set(xsi_focal_length)
        usd_camera.CreateFocusDistanceAttr().Set(get_distance(xsi_camera_position, xsi_interest_position))
    else:
        usd_camera.CreateFocalLengthAttr().Set(xsi_focal_length, Usd.TimeCode(frame))
        usd_camera.CreateFocusDistanceAttr().Set(get_distance(xsi_camera_position, xsi_interest_position), Usd.TimeCode(frame))


def add_camera(app, params, path_for_objects, stage, xsi_camera, root_path):
    usd_xform, ref_stage = add_xform(app, params, path_for_objects, True, stage, xsi_camera, root_path)
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
    if opt_animation is None:
        set_camera_at_frame(xsi_camera, usd_camera)
    else:
        for frame in range(opt_animation[0], opt_animation[1] + 1):
            set_camera_at_frame(xsi_camera, usd_camera, frame)
    ref_stage.Save()

    return usd_xform
