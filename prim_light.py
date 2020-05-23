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
                usd_light.CreateRadiusAttr().Set(xsi_light.Parameters("LightAreaXformSX").GetValue(frame), Usd.TimeCode(frame))
            else:
                usd_light.CreateRadiusAttr().Set(xsi_light.Parameters("LightAreaXformSX").Value)
    if xsi_light_type == 0 and xsi_geom_type == 4:  # cylinder light
        if frame is None:
            usd_light.CreateRadiusAttr().Set(xsi_light.Parameters("LightAreaXformSX").Value)
            usd_light.CreateLengthAttr().Set(xsi_light.Parameters("LightAreaXformSZ").Value)
        else:
            if change_keys[0]:
                usd_light.CreateRadiusAttr().Set(xsi_light.Parameters("LightAreaXformSX").GetValue(frame), Usd.TimeCode(frame))
            else:
                usd_light.CreateRadiusAttr().Set(xsi_light.Parameters("LightAreaXformSX").Value)
            if change_keys[2]:
                usd_light.CreateLengthAttr().Set(xsi_light.Parameters("LightAreaXformSZ").GetValue(frame), Usd.TimeCode(frame))
            else:
                usd_light.CreateLengthAttr().Set(xsi_light.Parameters("LightAreaXformSZ").Value)


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
    if materials_opt is not None and usd_light is not None:
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

        opt_animation = params["animation"]

        # diffuse and specular coefficients
        xsi_is_diffuse = xsi_light.Parameters("DiffuseContribution")
        xsi_is_specular = xsi_light.Parameters("SpecularContribution")
        usd_diffuse_attr = usd_light.CreateDiffuseAttr()
        usd_specular_attr = usd_light.CreateSpecularAttr()
        if opt_animation is None or utils.is_param_animated(xsi_is_diffuse, opt_animation):
            for frame in range(opt_animation[0], opt_animation[1] + 1):
                usd_diffuse_attr.Set(xsi_is_diffuse.GetValue(frame), Usd.TimeCode(frame))
        else:
            usd_diffuse_attr.Set(1.0 if xsi_is_diffuse.Value else 0.0)

        if opt_animation is None or utils.is_param_animated(xsi_is_specular, opt_animation):
            for frame in range(opt_animation[0], opt_animation[1] + 1):
                usd_specular_attr.Set(xsi_is_specular.GetValue(frame), Usd.TimeCode(frame))
        else:
            usd_specular_attr.Set(1.0 if xsi_is_specular.Value else 0.0)

        # default intensity = 1.0
        usd_light.CreateIntensityAttr().Set(1.0)

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


def set_diffuse(usd_light, parameter, anim_opt, value=None):  # value used for background light
    if value is not None:
        usd_light.CreateDiffuseAttr().Set(value)
    else:
        attr = usd_light.CreateDiffuseAttr()
        if anim_opt is None or utils.is_param_animated(parameter, anim_opt):
            for frame in range(anim_opt[0], anim_opt[1] + 1):
                attr.Set(1.0 if parameter.GetValue(frame) else 0.0, Usd.TimeCode(frame))
        else:
            attr.Set(1.0 if parameter.Value else 0.0)


def set_specular(usd_light, parameter, anim_opt, value=None):
    if value is not None:
        usd_light.CreateSpecularAttr().Set(value)
    else:
        attr = usd_light.CreateSpecularAttr()
        if anim_opt is None or utils.is_param_animated(parameter, anim_opt):
            for frame in range(anim_opt[0], anim_opt[1] + 1):
                attr.Set(1.0 if parameter.GetValue(frame) else 0.0, Usd.TimeCode(frame))
        else:
            attr.Set(1.0 if parameter.Value else 0.0)


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
        set_diffuse(usd_light, cyc_light.Parameters("use_diffuse"), anim_opt)
        set_specular(usd_light, cyc_light.Parameters("use_glossy"), anim_opt)
        set_intensity(usd_light, cyc_light.Parameters("power"), anim_opt)

        set_radius(usd_light, cyc_light.Parameters("size"), anim_opt)
    elif light_type == "cyclesSun":
        usd_light = UsdLux.DistantLight.Define(ref_stage, str(usd_xform.GetPath()) + "/" + cyc_light.Name)
        set_color(usd_light, (1.0, 1.0, 1.0), anim_opt)
        set_diffuse(usd_light, cyc_light.Parameters("use_diffuse"), anim_opt)
        set_specular(usd_light, cyc_light.Parameters("use_glossy"), anim_opt)
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
                    set_diffuse(usd_light, cyc_light.Parameters("use_diffuse"), anim_opt)
                    set_specular(usd_light, cyc_light.Parameters("use_glossy"), anim_opt)
                    set_intensity(usd_light, cyc_light.Parameters("power"), anim_opt)

                    set_rect_size(usd_light, cyc_light.Parameters("sizeU"), cyc_light.Parameters("sizeV"), anim_opt)
                else:
                    usd_light = UsdLux.DiskLight.Define(ref_stage, str(usd_xform.GetPath()) + "/" + cyc_light.Name)
                    set_color(usd_light, (1.0, 1.0, 1.0), anim_opt)
                    set_diffuse(usd_light, cyc_light.Parameters("use_diffuse"), anim_opt)
                    set_specular(usd_light, cyc_light.Parameters("use_glossy"), anim_opt)
                    set_intensity(usd_light, cyc_light.Parameters("power"), anim_opt)

                    set_ellipse_radius(usd_light, cyc_light.Parameters("sizeU"), cyc_light.Parameters("sizeV"), anim_opt)
    elif light_type == "cyclesBackground":
        usd_light = UsdLux.DomeLight.Define(ref_stage, str(usd_xform.GetPath()) + "/" + cyc_light.Name)
        set_color(usd_light, (1.0, 1.0, 1.0), anim_opt)
        set_diffuse(usd_light, None, anim_opt, value=1.0)
        set_specular(usd_light, None, anim_opt, value=1.0)

    if usd_light is not None:
        usd_light_prim = ref_stage.GetPrimAtPath(usd_light.GetPath())
        materials.add_material(materials_opt, cyc_light.Material, ref_stage, ref_stage_asset, usd_xform, usd_light_prim)

    return stage.GetPrimAtPath(root_path + str(usd_xform.GetPath()))


# -----------------------------------------------------
# ---------------------import--------------------------
def set_import_parameter(app, xsi_light, param_name, usd_attribute):
    time = usd_attribute.GetTimeSamples()
    if len(time) > 1:
        # parameter is animated
        for frame in time:
            app.SaveKey(xsi_light.Parameters(param_name), frame, usd_attribute.Get(frame))
    else:
        # constant parameter
        xsi_light.Parameters(param_name).Value = usd_attribute.Get()


def set_import_diffuse_param(app, xsi_light, usd_light):
    usd_diffuse = usd_light.GetDiffuseAttr()
    set_import_parameter(app, xsi_light, "DiffuseContribution", usd_diffuse)


def set_import_specular_param(app, xsi_light, usd_light):
    usd_specular = usd_light.GetSpecularAttr()
    set_import_parameter(app, xsi_light, "SpecularContribution", usd_specular)


def set_import_light_geometry(app, xsi_light, usd_light, light_type):
    if light_type == "SphereLight":
        xsi_light.Parameters("LightAreaGeom").Value = 3
        # for sphere set only X
        usd_radius = usd_light.GetRadiusAttr()
        set_import_parameter(app, xsi_light, "LightAreaXformSX", usd_radius)
    elif light_type == "RectLight":
        xsi_light.Parameters("LightAreaGeom").Value = 1
        # for rectangle setup X and Y size
        usd_width = usd_light.GetWidthAttr()
        usd_height = usd_light.GetHeightAttr()
        set_import_parameter(app, xsi_light, "LightAreaXformSX", usd_width)
        set_import_parameter(app, xsi_light, "LightAreaXformSY", usd_height)
    elif light_type == "DiskLight":
        xsi_light.Parameters("LightAreaGeom").Value = 2
        usd_radius = usd_light.GetRadiusAttr()
        set_import_parameter(app, xsi_light, "LightAreaXformSX", usd_radius)
    elif light_type == "CylinderLight":
        xsi_light.Parameters("LightAreaGeom").Value = 4
        # for cylinder X and Z
        usd_radius = usd_light.GetRadiusAttr()
        usd_length = usd_light.GetLengthAttr()
        set_import_parameter(app, xsi_light, "LightAreaXformSX", usd_radius)
        set_import_parameter(app, xsi_light, "LightAreaXformSZ", usd_length)


def emit_default_light(app, light_name, usd_tfm, visibility, usd_prim, light_type, xsi_parent):
    xsi_light = None
    if light_type == "DistantLight":
        xsi_light = app.GetPrimLight("Infinite.Preset", light_name, xsi_parent)
        usd_light = UsdLux.DistantLight(usd_prim)
        # for distance we set transform
        utils.set_xsi_transform(app, xsi_light, usd_tfm)
        utils.set_xsi_visibility(xsi_light, visibility)
        # and diffuse and specular params
        set_import_diffuse_param(app, xsi_light, usd_light)
        set_import_specular_param(app, xsi_light, usd_light)
    else:  # all other lights are point lights
        if light_type in ["SphereLight", "RectLight", "DiskLight", "CylinderLight"]:  # portal and dome lights are not supported by default lights
            xsi_light = app.GetPrimLight("Point.Preset", light_name, xsi_parent)
            # cast ptim to light
            usd_light = UsdLux.SphereLight(usd_prim) if light_type == "SphereLight" else (UsdLux.RectLight(usd_prim) if light_type == "RectLight" else (UsdLux.DiskLight(usd_prim) if light_type == "DiskLight" else UsdLux.CylinderLight(usd_prim)))
            # set transform
            utils.set_xsi_transform(app, xsi_light, usd_tfm)
            utils.set_xsi_visibility(xsi_light, visibility)
            # set diffuse and specular
            set_import_diffuse_param(app, xsi_light, usd_light)
            set_import_specular_param(app, xsi_light, usd_light)
            # enable area light
            xsi_light.Parameters("LightArea").Value = True
            set_import_light_geometry(app, xsi_light, usd_light, light_type)
    return xsi_light


def emit_sycles_light(app, light_name, usd_tfm, visibility, usd_prim, light_type, xsi_parent):
    xsi_light = None
    usd_light = None
    # cylinder light is not suported by cycles lighst
    if light_type == "RectLight":
        xsi_light = app.GetPrim("cyclesArea", light_name, xsi_parent)
        usd_light = UsdLux.RectLight(usd_prim)
        # set width and height
        set_import_parameter(app, xsi_light, "sizeU", usd_light.GetWidthAttr())
        set_import_parameter(app, xsi_light, "sizeV", usd_light.GetHeightAttr())
    elif light_type == "DiskLight":
        xsi_light = app.GetPrim("cyclesArea", light_name, xsi_parent)
        usd_light = UsdLux.DiskLight(usd_prim)
        xsi_light.Parameters("shape").Value = 1
        set_import_parameter(app, xsi_light, "sizeU", usd_light.GetRadiusAttr())
        set_import_parameter(app, xsi_light, "sizeV", usd_light.GetRadiusAttr())
    elif light_type == "LightPortal":
        xsi_light = app.GetPrim("cyclesArea", light_name, xsi_parent)
        usd_light = UsdLux.LightPortal(usd_prim)
        xsi_light.Parameters("is_portal").Value = True
    elif light_type == "SphereLight":
        xsi_light = app.GetPrim("cyclesPoint", light_name, xsi_parent)
        usd_light = UsdLux.SphereLight(usd_prim)
        set_import_parameter(app, xsi_light, "size", usd_light.GetRadiusAttr())
    elif light_type == "DistantLight":
        xsi_light = app.GetPrim("cyclesSun", light_name, xsi_parent)
        usd_light = UsdLux.DistantLight(usd_prim)
        set_import_parameter(app, xsi_light, "angle", usd_light.GetAngleAttr())
    elif light_type == "DomeLight":
        xsi_light = app.GetPrim("cyclesBackground", light_name, xsi_parent)
        usd_light = UsdLux.DomeLight(usd_prim)
    if xsi_light is not None:
        # set transform
        utils.set_xsi_transform(app, xsi_light, usd_tfm)
        utils.set_xsi_visibility(xsi_light, visibility)

        # for all lights (except dome light and portal) we can set diffuse, specular, intensity
        if usd_light is not None and light_type != "DomeLight" and light_type != "LightPortal":
            set_import_parameter(app, xsi_light, "use_diffuse", usd_light.GetDiffuseAttr())
            set_import_parameter(app, xsi_light, "use_glossy", usd_light.GetSpecularAttr())
            set_import_parameter(app, xsi_light, "power", usd_light.CreateIntensityAttr())

    return xsi_light


def emit_light(app, options, light_name, usd_tfm, visibility, usd_prim, light_type, xsi_parent):
    light_mode = options.get("light_mode", 0)
    if light_mode == 1:
        return emit_sycles_light(app, light_name, usd_tfm, visibility, usd_prim, light_type, xsi_parent)
    else:
        return emit_default_light(app, light_name, usd_tfm, visibility, usd_prim, light_type, xsi_parent)
