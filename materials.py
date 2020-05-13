from pxr import Usd, UsdShade, Sdf
import utils
import imp


def set_material(xsi_material, stage, usd_material):
    # only one simple node
    usd_material_path = str(usd_material.GetPath())
    usd_shader = UsdShade.Shader.Define(stage, usd_material_path + "/PBRShader")
    usd_shader.CreateIdAttr("UsdPreviewSurface")
    usd_shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)
    usd_shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)

    # duffuse input
    usd_shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set((1.0, 1.0, 1.0))
    # output
    usd_shader.CreateOutput("out", Sdf.ValueTypeNames.Color3f)

    # setup output
    usd_material.CreateSurfaceOutput().ConnectToSource(usd_shader, "out")


def export_materials(app, params, stage, path_for_objects, root_path, materials_map):
    imp.reload(utils)
    # create new stage for materials
    mats_stage_name = "materials." + utils.get_extension_from_params(params)
    mat_stage = Usd.Stage.CreateNew(path_for_objects + mats_stage_name)
    # add prim to it
    mat_root = mat_stage.DefinePrim("/materials")
    # and reference to it from the main stage
    # ref = stage.DefinePrim(root_path + "/materials")
    # ref.GetReferences().AddReference("./" + utils.get_last_folder(path_for_objects) + "/" + mats_stage_name, "/materials")

    # we should iterate by libraries in the scene
    scene = app.ActiveProject2.ActiveScene
    for library in scene.MaterialLibraries:
        lib_name = library.Name
        # iterate by all materials inside the library
        for mat in library.Items:
            mat_name = mat.Name
            # add material to usd
            usd_material = UsdShade.Material.Define(mat_stage, str(mat_root.GetPath()) + "/" + lib_name + "_" + mat_name)
            materials_map[utils.build_material_identifier(mat)] = usd_material
            set_material(mat, mat_stage, usd_material)

    mat_stage.Save()

    return ("./" + utils.get_last_folder(path_for_objects) + "/" + mats_stage_name, "/materials")
