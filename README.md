# What is it

This is a basic integration of the Pixar's USD format into Softimage. This plugin is work in progress, but potentially it will allow export and import scenes to and from usd-format. 

There are some conceptual problems with general purposes formats, like *.usd. In principle, this format can store any kind of data, and all data from a Softimage's scene can be stored in a usd-file. May be more important not only to export the data, but import it back to Softimage or to another DCC. Importer to other DCC does not know about all custom data, stored in the usd-file. It can recognize only default objects in the file. Also, other DCC can not suppport some structures, which exists in Softimage. For example: ICE-trees, render passes, operators on different stack modes and so on. That's why the plugin export to usd-format only data, which supports by default.

Each scene from Softimage exports to several usd-files. The main file contains only hierarchical scheme of the scene. Each item in this file has the reference to separate usd-file, which stores the data, corresponding to each individual object in the scene. All these references stores in separate folder. For example, if the main file has the name scene.usd, then references files will be stored into the folder /scene_objects/... If materials are exported, then the scene_materials.usd file will be created. This file contains data for all materials. 

## How to install

Copy files from the repository to the /Application/Plugins folder inside any workgroup. Binary files of the USD compiled with Python 2.7 should be installed in the system.

# What can be exported from Softimage

1. Polygon meshes. Each polygon mesh store the following attributes:

- vertices and polygons

- normals

- crease edges and creases vertices (in particular hard edges and hard vertices)

- vertex colors

- uv coordinates

- weightmaps

- polygon clusters with corresponding materials

2. Hair objects. Each hair object store data in BasisCurves schema. It contains the following data:

- point positions and vertex count in each strand

- width of each strand near each point

3. Pointcloud with strands. Stores the same data is for build-in hairs.

4. Pointcloud without strands but with particles. This object stores in Points schema and contains the following data:

- point positions

- point sizes

5. Lights. Softimage's lights converted to Distance, Disk, Rectangle or Sphere lights. Each light also store the shader.

6. Cameras.

7. Nulls. These objects stores as basic Xform schema and contains only transform matrix.

8. Models. Each model exports as separate object. All subobjects stores as references inside this model.

9. Models instances.

10. Materials.


# What can be imported to Softimage

Noting.