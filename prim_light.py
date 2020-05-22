from pxr import Usd, UsdLux, UsdShade
from prim_xform import add_xform
import materials
import utils
import imp


def set_light_at_frame(xsi_light, xsi_light_type, xsi_geom_type, usd_light, frame=None, change_keys=None):
    if xsi_light_type == 0 and xsi_geom_type == 1:  # rectangular light
        if frame is None:
            usd_light.CreateWidthAttr().Set(xsi_light.Parameters("LightAreaXformSX").Value)
            usd_light.CreateHeightAttr().Set(xsi_light.Parameters("LightAreaXformSY").Value)
        else:
            if change_keys[0]:
                usd_light.CreateWidthAttr().Set(xsi_light.Parameters("LightAreaXformSX").GetValue(frame), Usd.TimeCode(frame))
            else:
                usd_light.CreateWidthAttr().Set(xsi_light.Parameters("LightAreaXformSX").Value)
            if change_keys[1]:
                usd_light.CreateHeightAttr().Set(xsi_light.Parameters("LightAreaXformSY").GetValue(frame), Usd.TimeCode(frame))
            else:
                usd_light.CreateHeightAttr().Set(xsi_light.Parameters("LightAreaXformSY").Value)
    if xsi_light_type == 0 and (xsi_geom_type == 2 or xsi_geom_type == 3):  # disc or sphere light
        if frame is None:
            usd_light.CreateRadiusAttr().Set(xsi_light.Parameters("LightAreaXformSX").Value)
        else:
            if change_keys[0]:
                usd_light.CreateWidthAttr().Set(xsi_light.Parameters("LightAreaXformSX").GetValue(frame), Usd.TimeCode(frame))
            else:
                usd_light.CreateWidthAttr().Set(xsi_light.Parameters("LightAreaXformSX").Value)
    if xsi_light_type == 0 and xsi_geom_type == 4:  # cylinder light
        if frame is None:
            usd_light.CreateRadiusAttr().Set(xsi_light.Parameters("LightAreaXformSX").Value)
            usd_light.CreateLengthAttr().Set(xsi_light.Parameters("LightAreaXformSZ").Value)
        else:
            if change_keys[0]:
                usd_light.CreateWidthAttr().Set(xsi_light.Parameters("LightAreaXformSX").GetValue(frame), Usd.TimeCode(frame))
            else:
                usd_light.CreateWidthAttr().Set(xsi_light.Parameters("LightAreaXformSX").Value)
            if change_keys[2]:
                usd_light.CreateWidthAttr().Set(xsi_light.Parameters("LightAreaXformSZ").GetValue(frame), Usd.TimeCode(frame))
            else:
                usd_light.CreateWidthAttr().Set(xsi_light.Parameters("LightAreaXformSZ").Value)


def add_light(app, params, path_for_objects, stage, xsi_light, root_path):  # here me add only basic parameters, all other will be defined in the material
    imp.reload(materials)
    imp.reload(utils)
    # basic transform
    usd_xform, ref_stage, ref_stage_asset = add_xform(app, params, path_for_objects, True, stage, xsi_light, root_path)
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

    # export light shader to material
    materials_opt = params.get("materials", None)
    if materials_opt is not None:
        is_materials = materials_opt.get("is_materials", True)
        if is_materials:
            usd_material = UsdShade.Material.Define(ref_stage, str(usd_xform.GetPath()) + "/Shader")
            xsi_root_shader = xsi_light.Parameters("LightShader")
            if xsi_root_shader is not None:
                materials.set_material_complete(xsi_root_shader, ref_stage, usd_material)
            # bind shader to the light
            UsdShade.MaterialBindingAPI(usd_light).Bind(usd_material)

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
        changes_size_key = [False, False, False]  # for x, y and z. If True, then this dimension is changed by animation
        if opt_animation is None or not utils.is_area_light_animated(xsi_light, opt_animation, changes_size_key):
            set_light_at_frame(xsi_light, xsi_light_type, xsi_geom_type, usd_light)
        else:
            for frame in range(opt_animation[0], opt_animation[1] + 1):
                set_light_at_frame(xsi_light, xsi_light_type, xsi_geom_type, usd_light, frame=frame, change_keys=changes_size_key)
    ref_stage.Save()

    return stage.GetPrimAtPath(root_path + str(usd_xform.GetPath()))


def set_color(usd_light, value, anim_opt):
    usd_light.CreateColorAttr(value)


def set_diffuse(usd_light, value, anim_opt):
    usd_light.CreateDiffuseAttr(value)


def set_specular(usd_light, value, anim_opt):
    usd_light.CreateSpecularAttr(value)


def set_intensity(usd_light, xsi_param, anim_opt):
    attr = usd_light.CreateIntensityAttr()
    if anim_opt is None or not utils.is_param_animated(xsi_param, anim_opt):
        attr.Set(xsi_param.Value)
    else:
        for frame in range(anim_opt[0], anim_opt[1] + 1):
            attr.Set(xsi_param.GetValue(frame), Usd.TimeCode(frame))


def set_distance_angle(usd_light, xsi_param, anim_opt):
    attr = usd_light.CreateAngleAttr()
    if anim_opt is None or not utils.is_param_animated(xsi_param, anim_opt):
        attr.Set(xsi_param.Value)
    else:
        for frame in range(anim_opt[0], anim_opt[1] + 1):
            attr.Set(xsi_param.GetValue(frame), Usd.TimeCode(frame))


def set_radius(usd_light, xsi_param, anim_opt):
    attr = usd_light.CreateRadiusAttr()
    if anim_opt is None or not utils.is_param_animated(xsi_param, anim_opt):
        attr.Set(xsi_param.Value)
    else:
        for frame in range(anim_opt[0], anim_opt[1] + 1):
            attr.Set(xsi_param.GetValue(frame), Usd.TimeCode(frame))


def set_ellipse_radius(usd_light, xsi_param_width, xsi_param_height, anim_opt):
    attr = usd_light.CreateRadiusAttr()
    if anim_opt is None or not (utils.is_param_animated(xsi_param_width, anim_opt) or utils.is_param_animated(xsi_param_height, anim_opt)):
        attr.Set((xsi_param_width.Value + xsi_param_height.Value) / 2)
    else:
        for frame in range(anim_opt[0], anim_opt[1] + 1):
            attr.Set((xsi_param_width.GetValue(frame) + xsi_param_height.GetValue(frame)) / 2, Usd.TimeCode(frame))


def set_rect_size(usd_light, xsi_param_width, xsi_param_height, anim_opt):
    attr_width = usd_light.CreateWidthAttr()
    if anim_opt is None or not utils.is_param_animated(xsi_param_width, anim_opt):
        attr_width.Set(xsi_param_width.Value)
    else:
        for frame in range(anim_opt[0], anim_opt[1] + 1):
            attr_width.Set(xsi_param_width.GetValue(frame), Usd.TimeCode(frame))

    attr_heigh = usd_light.CreateHeightAttr()
    if anim_opt is None or not utils.is_param_animated(xsi_param_height, anim_opt):
        attr_heigh.Set(xsi_param_height.Value)
    else:
        for frame in range(anim_opt[0], anim_opt[1] + 1):
            attr_heigh.Set(xsi_param_height.GetValue(frame), Usd.TimeCode(frame))


def add_cycles_light(app, params, path_for_objects, stage, cyc_light, materials_opt, root_path):
    usd_xform, ref_stage, ref_stage_asset = add_xform(app, params, path_for_objects, True, stage, cyc_light, root_path)
    light_type = cyc_light.Type
    usd_light = None
    anim_opt = params.get("animation", None)
    if light_type == "cyclesPoint":
        usd_light = UsdLux.SphereLight.Define(ref_stage, str(usd_xform.GetPath()) + "/" + cyc_light.Name)
        set_color(usd_light, (1.0, 1.0, 1.0), anim_opt)
        set_diffuse(usd_light, 1.0, anim_opt)
        set_specular(usd_light, 1.0, anim_opt)
        set_intensity(usd_light, cyc_light.Parameters("power"), anim_opt)

        set_radius(usd_light, cyc_light.Parameters("size"), anim_opt)
    elif light_type == "cyclesSun":
        usd_light = UsdLux.DistantLight.Define(ref_stage, str(usd_xform.GetPath()) + "/" + cyc_light.Name)
        set_color(usd_light, (1.0, 1.0, 1.0), anim_opt)
        set_diffuse(usd_light, 1.0, anim_opt)
        set_specular(usd_light, 1.0, anim_opt)
        set_intensity(usd_light, cyc_light.Parameters("power"), anim_opt)

        set_distance_angle(usd_light, cyc_light.Parameters("angle"), anim_opt)
    elif light_type == "cyclesSpot":
        # spot light is not supported by usd
        pass
    elif light_type == "cyclesArea":
        xsi_portal = cyc_light.Parameters("is_portal")
        if xsi_portal is not None and xsi_portal.Value:
            usd_light = UsdLux.LightPortal.Define(ref_stage, str(usd_xform.GetPath()) + "/" + cyc_light.Name)
        else:
            xsi_shape = cyc_light.Parameters("shape")
            if xsi_shape is not None:
                xsi_shape_value = xsi_shape.Value
                if xsi_shape_value < 0.5:
                    usd_light = UsdLux.RectLight.Define(ref_stage, str(usd_xform.GetPath()) + "/" + cyc_light.Name)
                    set_color(usd_light, (1.0, 1.0, 1.0), anim_opt)
                    set_diffuse(usd_light, 1.0, anim_opt)
                    set_specular(usd_light, 1.0, anim_opt)
                    set_intensity(usd_light, cyc_light.Parameters("power"), anim_opt)

                    set_rect_size(usd_light, cyc_light.Parameters("sizeU"), cyc_light.Parameters("sizeV"), anim_opt)
                else:
                    usd_light = UsdLux.DiskLight.Define(ref_stage, str(usd_xform.GetPath()) + "/" + cyc_light.Name)
                    set_color(usd_light, (1.0, 1.0, 1.0), anim_opt)
                    set_diffuse(usd_light, 1.0, anim_opt)
                    set_specular(usd_light, 1.0, anim_opt)
                    set_intensity(usd_light, cyc_light.Parameters("power"), anim_opt)

                    set_ellipse_radius(usd_light, cyc_light.Parameters("sizeU"), cyc_light.Parameters("sizeV"), anim_opt)
    elif light_type == "cyclesBackground":
        usd_light = UsdLux.DomeLight.Define(ref_stage, str(usd_xform.GetPath()) + "/" + cyc_light.Name)
        set_color(usd_light, (1.0, 1.0, 1.0), anim_opt)
        set_diffuse(usd_light, 1.0, anim_opt)
        set_specular(usd_light, 1.0, anim_opt)

    if usd_light is not None:
        usd_light_prim = ref_stage.GetPrimAtPath(usd_light.GetPath())
        materials.add_material(materials_opt, cyc_light.Material, ref_stage, ref_stage_asset, usd_xform, usd_light_prim)

    return stage.GetPrimAtPath(root_path + str(usd_xform.GetPath()))
