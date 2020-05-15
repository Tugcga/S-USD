from prim_xform import add_xform
import prim_xform
import export_processor
import imp


def add_model(app, params, path_for_objects, stage, model_object, materials_opt, root_path):
    imp.reload(prim_xform)
    imp.reload(export_processor)
    usd_xform, ref_stage, ref_stage_asset = add_xform(app, params, path_for_objects, True, stage, model_object, root_path)

    model_objects = []
    # create new folder for model subobjects
    model_path_for_objects = path_for_objects + model_object.Name + "_objects\\"
    # change path in materials_opt, add new ..
    for obj in model_object.Children:
        export_processor.export_step(app, params, model_path_for_objects, ref_stage, obj, model_objects, materials_opt, "/" + model_object.Name)
