def import_usd(app, file_path, options):
    is_clear = options.get("clear_scene", False)
    last_object_to_remove = None
    if is_clear:
        scene_root = app.ActiveProject2.ActiveScene.Root
        for child in scene_root.Children:
            if child.Type != "CameraRoot":
                app.DeleteObj("B:" + child.Name)
            else:
                last_object_to_remove = child

    if last_object_to_remove is not None:
        app.DeleteObj("B:" + last_object_to_remove.Name)
