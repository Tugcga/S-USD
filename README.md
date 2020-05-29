# What is it

This is a basic integration of the Pixar's USD format into Softimage. This plugin is work in progress, but potentially it will allow export and import scenes to and from usd-format. 

There are some conceptual problems with general purposes formats, like *.usd. In principle, this format can store any kind of data, and all data from a Softimage's scene can be stored in a usd-file. May be more important not only to export the data, but import it back to Softimage or to another DCC. Importer to other DCC does not know about all custom data, stored in the usd-file. It can recognize only default objects in the file. Also, other DCC can not supports some structures, which exists in Softimage. For example: ICE-trees, render passes, operators on different stack modes and so on. That's why the plugin export to usd-format only data, which supports by default.

Each scene from Softimage exports to several usd-files. The main file contains only hierarchical scheme of the scene. Each item in this file has the reference to separate usd-file, which stores the data, corresponding to each individual object in the scene. All these references stores in separate folder. For example, if the main file has the name scene.usd, then references files will be stored into the folder /scene_assets/...

## How to install

Copy files from the repository to the /Application/Plugins folder inside any workgroup. Also, binary files of the USD compiled with Python 2.7 should be installed in the system.

# What can be exported from Softimage

1. Polygon meshes. All non-transform animation of the mesh is backed into vertices positions. If during the animation the topology of the mesh is not changed, then only vertex positions stored in different time samples. In other case, polygon indexes are also saved for each time sample. The addon trying to reduce the amount of saved data. For this it checks is the object has any animated attrbiutes, and export animation only for these ones. Each polygon mesh store the following attributes:

- vertices and polygons

- normals

- crease edges and creases vertices (in particular hard edges and hard vertices)

- vertex colors as *color3f[]* primvar with *faceVarying* interpolation

- uv coordinates as *texCoord2f[]* primvar with *faceVarying* interpolation

- weightmaps as *float[]* primvar with *vertex* interpolation

- polygon clusters

2. Hair objects. Each hair object store data in BasisCurves schema. It contains the following data:

- point positions and vertex count in each strand

- width of each strand near each point

3. Pointcloud with strands. Stores the same data as for build-in hairs.

4. Pointcloud without strands but with particles. This object stores in Points schema and contains the following data:

- point positions

- point sizes

5. Lights. Softimage's lights converted to Distance, Disk, Rectangle or Sphere lights. Each light also store the shader. Also addon recognizes a Sycles lights and export it as Sphere, Distant, Portal, Rectangle, Disk or Dome lights.

6. Cameras.

7. Nulls. These objects stores as basic Xform schema and contains only transform matrix.

8. Models. Each model exports as separate object. All subobjects stores as references inside this model.

9. Models instances.

10. Materials. Addon does not export actual node trees of materials. It creates only the basic template, and bind these materials to objects and clusters.


# What can be imported to Softimage

1. Polygon meshes. If the mesh contains animation, then the addon adds an operator, which updates the mesh data (obtained from usd-file) at each frame. For each polygon mesh addon imports the following attributes:

- vertices and polygons. If the mesh has different topology in different frames, then all other attributes are ignored, and the operator updates only the mesh topology. So, in dynamic topology no uvs, no normals and so on.

- normals.

- edge and vertex creases. The crease data takes from the first frame and does not updates in other frames for the mesh.

- vertex colors. The addon interpret as vertex color any primvar with the type *color3[]* with *vertex* or *faceVarying* interpolation.

- uv-cooridnates. The addon interpret as uv any primvar with the type *texCoord2f[]* or *float2[]* with *vertex* or *faceVarying* interpolation.

- weightmaps. The addon interpret as wegitmap any primvar fir *float[]* type with *vertex* interpolation.

- polygon clusters.

2. Pointclouds. The addon saves the all data of the points (in fact only position and radius of the points) to *.icecache file for each frame in the usd-file. The it use this cache file in the ICE-tree. All cache files saves to the /Project/Simulation/usd_cache/usd_file_name/ folder.

3. Hairs. As for pointcloud, the addon save hairs data as strands into *.icecahe files.

4. Lights. If the Sycles addon is installed, then there is possibility to chose the type of the imported lights: default Softimage lights or special Sycles lights.

5. Cameras.

6. Nulls.

7. Models and model instances.

8. Materials. If the usd-file contains materials, then the addon creates the library with the same name as the name of the usd-file and add default phong materials to it. Also, if any object or cluster has binding to the material, then the addon assign the corresponding material to the object or cluster.