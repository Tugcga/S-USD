from pxr import Usd, UsdShade, Sdf, UsdGeom
import utils
import imp
import os

DEBUG_MODE = False


def add_material(materials_opt, xsi_mat, stage, stage_asset_path, usd_xform, usd_prim, is_bind=True):  # do the same in prim_mesh
    material_asset_path = materials_opt.get("asset_path", None)
    if material_asset_path is not None:
        rel_material_path = utils.transform_path_to_relative(stage_asset_path, material_asset_path)
        mat_name = utils.buil_material_name(xsi_mat)
        mat_ref = stage.DefinePrim(str(usd_xform.GetPath()) + "/" + mat_name)
        mat_ref.GetReferences().AddReference(rel_material_path, "/" + xsi_mat.Library.Name + "/" + xsi_mat.Name)
        # bind the main material
        if is_bind:
            UsdShade.MaterialBindingAPI(usd_prim).Bind(UsdShade.Material(stage.GetPrimAtPath(mat_ref.GetPath())))


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


def set_material_complete(root_shader, stage, usd_material):
    pass


def export_materials(app, params, stage, materials_path, progress_bar=None):
    if DEBUG_MODE:
        imp.reload(utils)

    # create new stage for materials
    materials_folder, materials_file_name = os.path.split(materials_path)
    mat_stage = Usd.Stage.CreateNew(materials_path)

    # we should iterate by libraries in the scene
    scene = app.ActiveProject2.ActiveScene
    for library in scene.MaterialLibraries:
        lib_name = library.Name
        mat_stage.DefinePrim("/" + lib_name)
        # iterate by all materials inside the library
        for mat in library.Items:
            if progress_bar is not None:
                progress_bar.Caption = "Export material " + mat.Name + " (library " + lib_name + ")"
            mat_name = mat.Name
            # add material to usd
            usd_material = UsdShade.Material.Define(mat_stage, "/" + lib_name + "/" + mat_name)
            set_material(mat, mat_stage, usd_material)

    mat_stage.Save()

    return materials_path


def export_materials_in_stage(app, params, stage, progress_bar=None):
    if DEBUG_MODE:
        imp.reload(utils)

    scene = app.ActiveProject2.ActiveScene
    usd_scope = UsdGeom.Scope.Define(stage, "/Materials")
    for library in scene.MaterialLibraries:
        lib_name = library.Name
        stage.DefinePrim(str(usd_scope.GetPath()) + "/" + lib_name)
        for mat in library.Items:
            if progress_bar is not None:
                progress_bar.Caption = "Export material " + mat.Name + " (library " + lib_name + ")"
            mat_name = mat.Name
            # add material to usd
            usd_material = UsdShade.Material.Define(stage, str(usd_scope.GetPath()) + "/" + lib_name + "/" + mat_name)
            set_material(mat, stage, usd_material)
    return str(usd_scope.GetPath())


# --------------------------------------------------------------
# ------------------------Import--------------------------------
def import_clear_library(app, lib_name):
    lib = utils.get_library(app, lib_name, create=False)
    if lib is not None:
        app.DeleteObj(lib)


def import_material(app, usd_material, library_name=None):
    '''it return xsi_material, created if needed for usd_material
    '''
    if DEBUG_MODE:
        imp.reload(utils)

    if usd_material.GetPath() == "":
        return None
    else:
        usd_path = usd_material.GetPath()
        library = utils.get_library(app, library_name)
        material_name = utils.get_last_hierarchy(str(usd_path))
        xsi_material = utils.find_material_in_library(library, material_name)
        if xsi_material is not None:
            return xsi_material
        else:
            xsi_material = app.SICreateMaterial("$XSI_DSPRESETS\\Shaders\\Material\\Phong", material_name, library)  # create default material
            return xsi_material
