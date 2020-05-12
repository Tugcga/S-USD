from pxr import Usd, UsdLux
from prim_xform import add_xform


def set_light_at_frame(usd_light, xsi_light, xsi_light_type, xsi_geom_type, frame=None):
    if xsi_light_type == 0 and xsi_geom_type == 1:  # rectangular light
        usd_light.CreateWidthAttr().Set(xsi_light.Parameters("LightAreaXformSX").Value, Usd.TimeCode(frame))
        usd_light.CreateHeightAttr().Set(xsi_light.Parameters("LightAreaXformSY").Value, Usd.TimeCode(frame))
    if xsi_light_type == 0 and (xsi_geom_type == 2 or xsi_geom_type == 3):  # disc or sphere light
        usd_light.CreateRadiusAttr().Set(xsi_light.Parameters("LightAreaXformSX").Value, Usd.TimeCode(frame))
    if xsi_light_type == 0 and xsi_geom_type == 4:  # cylinder light
        usd_light.CreateRadiusAttr().Set(xsi_light.Parameters("LightAreaXformSX").Value, Usd.TimeCode(frame))
        usd_light.CreateLengthAttr().Set(xsi_light.Parameters("LightAreaXformSZ").Value, Usd.TimeCode(frame))


def add_light(app, params, path_for_objects, stage, xsi_light, root_path):  # here me add only basic parameters, all other will be defined in the material
    # basic transform
    usd_xform, ref_stage = add_xform(app, params, path_for_objects, True, stage, xsi_light, root_path)
    # get the type of the light
    xsi_light_type = xsi_light.Parameters("Type").Value
    usd_light = None
    xsi_geom_type = -1
    if xsi_light_type == 0:  # point (also area light)
        xsi_is_area = xsi_light.Parameters("LightArea").Value
        xsi_geom_type = xsi_light.Parameters("LightAreaGeom").Value
        if xsi_is_area:
            if xsi_geom_type == 1:  # rectangular
                usd_light = UsdLux.RectLight.Define(ref_stage, str(usd_xform.GetPath()) + "/" + xsi_light.Name)
            elif xsi_geom_type == 2:  # disc
                usd_light = UsdLux.DiskLight.Define(ref_stage, str(usd_xform.GetPath()) + "/" + xsi_light.Name)
            elif xsi_geom_type == 3:  # sphere
                usd_light = UsdLux.SphereLight.Define(ref_stage, str(usd_xform.GetPath()) + "/" + xsi_light.Name)
            elif xsi_geom_type == 4:  # cylinder
                usd_light = UsdLux.CylinderLight.Define(ref_stage, str(usd_xform.GetPath()) + "/" + xsi_light.Name)
    elif xsi_light_type == 1:  # infinite
        usd_light = UsdLux.DistantLight.Define(ref_stage, str(usd_xform.GetPath()) + "/" + xsi_light.Name)
    elif xsi_light_type == 2:  # spot
        usd_light = UsdLux.DistantLight.Define(ref_stage, str(usd_xform.GetPath()) + "/" + xsi_light.Name)

    if usd_light is not None:
        # set neutral color
        usd_light.CreateColorAttr().Set((1.0, 1.0, 1.0))

        # diffuse and specular coefficients
        xsi_is_diffuse = xsi_light.Parameters("DiffuseContribution").Value
        xsi_is_specular = xsi_light.Parameters("SpecularContribution").Value
        usd_light.CreateDiffuseAttr().Set(1.0 if xsi_is_diffuse else 0.0)
        usd_light.CreateSpecularAttr().Set(1.0 if xsi_is_specular else 0.0)

        # default intensity = 1.0
        usd_light.CreateIntensityAttr().Set(1.0)

        # set animated parameters
        opt_animation = params["animation"]
        if opt_animation is not None:
            for frame in range(opt_animation[0], opt_animation[1] + 1):
                set_light_at_frame(usd_light, xsi_light, xsi_light_type, xsi_geom_type, frame)
    ref_stage.Save()

    return usd_xform
