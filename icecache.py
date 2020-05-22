# icecache v1.1
# Original version: Oct-24-2010 Bradley R. Gabe withanar@gmail.com
# modified: 22.05.2020 Shekn
#

"""
MODULE OVERVIEW:
-Provide the number of particles upon instantiation of the icecache object
-Add any number of attribute data sets to the cache using specific methods for data types (see list below)
-To write out data use:    icecache.write(filename, ascii=0)
-By defult, data writes to icecache format. Set the ascii switch to 1 for writing out to text for debugging.


There are different methods for specific data types for caching.
1-dimensional data types (bool, integer, scalar, etc) require a simple 1-d list for data input.
Multi-dimensional data types (3D Vector, Rotation, 4x4 matrix, etc) require a list of lists.

The following forms apply (see usage example below for context):

scalarData = [s0, s1, s2, s3, etc...]
2DVectorData = [[U0, V0], [U1, V1], [U2, V2], ...]
3DVectorData = [[posx0, posy0, posz0], [posx1, posy1, posz1], [posx2, posy2, posz3], ...]

METHODS BY DATA TYPE:

    add_point_position(posData)              3d data
    add_bool(attrName, boolData)             1d data
    add_integer(attrName, integerData)       1d data
    add_scalar(attrName, scalarData)         1d data
    add_vector2(attrName, v2Data)            2d data
    add_vector3(attrName, v3Data)            3d data
    add_vector4(attrName, v4Data)            4d data
    add_quaternion(attrName, quaternionData) 4d data
    add_matrix3(attrName, matrix3Data)       9d data
    add_matrix4(attrName, matrix4Data)       16d data
    add_color(attrName, colorData)           4d data
    add_rotation(attrName, rotData)          4d data

"""


def example_01():
    import icecache
    nbParticles = 2
    ic = icecache.ICECache(nbParticles)

    positions = [[-0.5, 0.0, 0.0], [0.5, 0.0, 0.0]]
    strands_data = [[[-0.25, 0.5, 0.0], [-0.5, 1.0, 0.0]],
                    [[0.25, 0.5, 0.0], [0.5, 1.0, 0.0]]]  # per point, the first array is for the first point and so on
    ids = [0, 1]
    sizes = [0.5, 0.5]

    ic.add_point_position(positions)
    ic.add_integer("ID", ids)
    ic.add_scalar("Size", sizes)
    ic.add_strand_position(strands_data)

    filename = "testcache.1.icecache"

    ic.write(filename, ascii=1)  # ascii moe for debug and understanding only


def example_02():
    import icecache
    import random

    particles_count = 100000
    ic = icecache.ICECache(particles_count)

    positions = [[random.uniform(-10.0, 10.0), random.uniform(-10.0, 10.0), random.uniform(-10.0, 10.0)] for i in range(particles_count)]
    sizes = [random.uniform(0.1, 0.15) for i in range(particles_count)]
    ic.add_point_position(positions)
    ic.add_scalar("Size", sizes)

    ic.write("many_particles.1.icecache")


if __name__ == "__main__":
    example_02()


class ICECache:
    def __init__(self, nb_particles):
        self.nb_particles = nb_particles
        self.attribute_data = {}
        self.cache_data = []
        self.DEBUG = 0

        self.data_types = {
            1: "1I",
            2: "1L",
            4: "1f",
            8: "2f",
            16: "3f",
            32: "4f",
            64: "4f",
            128: "9f",
            256: "16f",
            512: "4f",
            16384: "4f"
        }

    def add_attribute(self,
                      attribute_name,  # attrName:
                      data_type,  # dataType:  1:Bool, 2:Long, 4:Float, 8:Vector2, 16:Vector3, 32:Vector4, 64:Quat, 128:Mat3x3, 256:Mat4x4, 512:Color4, 16384:Rotation
                      structure_type,  # structureType:  1:Single data, 2:Array data
                      context_type,  # contextType:  1:Singleton, 2:Component0D, 4:Component1D, 8:Component2D... see SI SDK docs for more
                      category,  # category:  0:Unknown Category, 1:Built-in attribute, 2:User-defined attribute
                      data  # data
                      ):

        attr_data = {}
        attr_data["data_type"] = data_type
        attr_data["structure_type"] = structure_type
        attr_data["context_type"] = context_type
        attr_data["category"] = category
        attr_data["data"] = data
        self.attribute_data[attribute_name] = attr_data

    def add_point_position(self, pos_data):
        self.add_attribute("pointposition", 16, 1, 2, 1, pos_data)

    def add_strand_position(self, strands_data):
        self.add_attribute("StrandPosition", 16, 2, 2, 2, strands_data)

    def add_bool(self, attr_name, bool_data, structure=1):
        self.add_attribute(attr_name, 1, structure, 2, 2, bool_data)

    def add_integer(self, attr_name, integer_data, structure=1):
        self.add_attribute(attr_name, 2, structure, 2, 2, integer_data)

    def add_scalar(self, attr_name, scalar_data, structure=1):
        self.add_attribute(attr_name, 4, structure, 2, 2, scalar_data)

    def add_vector2(self, attr_name, v2_data, structure=1):
        self.add_attribute(attr_name, 8, structure, 2, 2, v2_data)

    def add_vector3(self, attr_name, v3_data, structure=1):
        self.add_attribute(attr_name, 16, structure, 2, 2, v3_data)

    def add_vector4(self, attr_name, v4_data, structure=1):
        self.add_attribute(attr_name, 32, structure, 2, 2, v4_data)

    def add_quaternion(self, attr_name, quaternion_data, structure=1):
        self.add_attribute(attr_name, 64, structure, 2, 2, quaternion_data)

    def add_matrix3(self, attr_name, matrix3_data, structure=1):
        self.add_attribute(attr_name, 128, structure, 2, 2, matrix3_data)

    def add_matrix4(self, attr_name, matrix4_data, structure=1):
        self.add_attribute(attr_name, 256, structure, 2, 2, matrix4_data)

    def add_color(self, attr_name, color_data, structure=1):
        self.add_attribute(attr_name, 512, structure, 2, 2, color_data)

    def add_rotation(self, attr_name, rot_data, structure=1):
        self.add_attribute(attr_name, 16384, structure, 2, 2, rot_data)

    def write(self, file_name, ascii=0):
        import gzip
        from struct import pack

        self.__write_header()
        self.__write_attribute_defs()
        self.__write_attribute_data()

        if not ascii:
            text = []
            for elem in self.cache_data:
                if self.DEBUG:
                    print(elem)
                type = elem[0]

                if type == "2f":
                    bin = pack(type,
                               float(elem[1]),
                               float(elem[2])
                               )
                elif type == "3f":
                    bin = pack(type,
                               float(elem[1]),
                               float(elem[2]),
                               float(elem[3]),
                               )
                elif type == "4f":
                    bin = pack(type,
                               float(elem[1]),
                               float(elem[2]),
                               float(elem[3]),
                               float(elem[4]),
                               )
                elif type == "9f":
                    bin = pack(type,
                               float(elem[1]),
                               float(elem[2]),
                               float(elem[3]),
                               float(elem[4]),
                               float(elem[5]),
                               float(elem[6]),
                               float(elem[7]),
                               float(elem[8]),
                               float(elem[9])
                               )
                elif type == "16f":
                    bin = pack(type,
                               float(elem[1]),
                               float(elem[2]),
                               float(elem[3]),
                               float(elem[4]),
                               float(elem[5]),
                               float(elem[6]),
                               float(elem[7]),
                               float(elem[8]),
                               float(elem[9]),
                               float(elem[10]),
                               float(elem[11]),
                               float(elem[12]),
                               float(elem[13]),
                               float(elem[14]),
                               float(elem[15]),
                               float(elem[16])
                               )
                else:
                    bin = pack(type, elem[1])
                text.append(bin)

            cachefile = gzip.open(file_name, "wb")
            cachefile.write("".join(text))
            cachefile.close()

        else:
            text = []
            for elem in self.cache_data:
                for item in elem[1:]:
                    text.append(str(item))

            cachefile = open(file_name, "w")
            cachefile.write(" ".join(text))
            cachefile.close()

    def __write_header(self):
        self.cache_data += [["8s", "ICECACHE"]]  # header string
        self.cache_data += [["I", 103]]  # version number
        self.cache_data += [["I", 0]]  # object type, pointcloud
        self.cache_data += [["I", self.nb_particles]]  # point count
        self.cache_data += [["I", 0]]  # edge count
        self.cache_data += [["I", 0]]  # polygon count
        self.cache_data += [["I", 0]]  # sample count
        self.cache_data += [["I", 1]]  # substep
        self.cache_data += [["I", 0]]  # user data blob count
        self.cache_data += [["I", len(self.attribute_data)]]  # attributes count

    def __write_attribute_defs(self):
        attribute_list = list(self.attribute_data.keys())
        attribute_list.sort()

        for attribute in attribute_list:
            data = self.attribute_data[attribute]
            name_length = len(attribute)
            filler = 4 - name_length % 4
            if filler == 4:
                filler = 0
            attribute_name = attribute + "".join(["_"] * filler)

            self.cache_data += [["L", name_length]]  # attribute name length
            # attribute name
            self.cache_data += [[str(len(attribute_name)) + "s", attribute_name]]
            self.cache_data += [["I", data["data_type"]]]  # cache data type
            self.cache_data += [["I", data["structure_type"]]]  # structure type
            self.cache_data += [["I", data["context_type"]]]  # context type
            self.cache_data += [["I", 0]]  # cache database ID, obsolete
            self.cache_data += [["I", data["category"]]]  # category

    def __write_attribute_data(self):
        attribute_list = list(self.attribute_data.keys())
        attribute_list.sort()
        for attribute in attribute_list:
            data = self.attribute_data[attribute]
            data_type = data["data_type"]
            if attribute.lower() == "pointposition":
                self.__write_position_data(data["data"])
            elif data_type == 1:
                self.__write_bool_data(data["data"], data["structure_type"])
            elif data_type == 2:
                self.__write_long_data(data["data"], data["structure_type"])
            elif data_type == 4:
                self.__write_float_data(data["data"], data["structure_type"])
            elif data_type == 8:
                self.__write_vector2_data(data["data"], data["structure_type"])
            elif data_type == 16:
                self.__write_vector3_data(data["data"], data["structure_type"])
            elif data_type == 32:
                self.__write_vector4_data(data["data"], data["structure_type"])
            elif data_type == 64:
                self.__write_vector4_data(data["data"], data["structure_type"])
            elif data_type == 128:
                self.__write_matrix33_data(data["data"], data["structure_type"])
            elif data_type == 256:
                self.__write_matrix44_data(data["data"], data["structure_type"])
            elif data_type == 512:
                self.__write_vector4_data(data["data"], data["structure_type"])
            elif data_type == 16384:
                self.__write_vector4_data(data["data"], data["structure_type"])

    def __get_chunks(self, num):
        if num < 4000:
            return [range(num)]

        outlist = []
        chunks = num / 4000
        for i in range(chunks):
            outlist.append(range((i)*4000, (i+1)*4000))
        outlist.append(range((i+1)*4000, (i+1)*4000 + num % 4000))
        return outlist

    def __write_position_data(self, data):
        self.cache_data += [["I", 0]]  # is constant?
        count = len(data)
        for i in range(count):
            self.cache_data += [["3f"] + data[i][0:3]]

    def __write_bool_data(self, data, structure=1):
        chunks = self.__get_chunks(len(data))
        for chunk in chunks:
            self.cache_data += [["I", 0]]  # is constant?
            for i in chunk:
                if structure == 1:
                    self.cache_data += [["I"] + [data[i]]]
                else:
                    self.cache_data += [["I", len(data[i])]]
                    for a in data[i]:
                        self.cache_data += [["I"] + [a]]

    def __write_long_data(self, data, structure=1):
        chunks = self.__get_chunks(len(data))
        for chunk in chunks:
            self.cache_data += [["I", 0]]  # is constant?
            for i in chunk:
                if structure == 1:
                    self.cache_data += [["L"] + [data[i]]]
                else:
                    self.cache_data += [["I", len(data[i])]]
                    for a in data[i]:
                        self.cache_data += [["L"] + [a]]

    def __write_float_data(self, data, structure=1):
        chunks = self.__get_chunks(len(data))
        for chunk in chunks:
            self.cache_data += [["I", 0]]  # is constant?
            for i in chunk:
                if structure == 1:
                    self.cache_data += [["1f"] + [data[i]]]
                else:
                    self.cache_data += [["I", len(data[i])]]
                    for a in data[i]:
                        self.cache_data += [["1f"] + [a]]

    def __write_vector2_data(self, data, structure=1):
        chunks = self.__get_chunks(len(data))
        for chunk in chunks:
            self.cache_data += [["I", 0]]  # is constant?
            for i in chunk:
                if structure == 1:
                    self.cache_data += [["2f"] + data[i][0:2]]
                else:
                    self.cache_data += [["I", len(data[i])]]
                    for a in data[i]:
                        self.cache_data += [["2f"] + a[0:2]]

    def __write_vector3_data(self, data, structure=1):
        chunks = self.__get_chunks(len(data))
        for chunk in chunks:
            self.cache_data += [["I", 0]]  # is constant?
            for i in chunk:
                if structure == 1:
                    self.cache_data += [["3f"] + data[i][0:3]]
                else:  # for array data (strands, for example), write the number of elements and then actual values
                    self.cache_data += [["I", len(data[i])]]
                    for a in data[i]:
                        self.cache_data += [["3f"] + a[0:3]]

    def __write_vector4_data(self, data, structure=1):
        chunks = self.__get_chunks(len(data))
        for chunk in chunks:
            self.cache_data += [["I", 0]]  # is constant?
            for i in chunk:
                if structure == 1:
                    self.cache_data += [["4f"] + data[i][0:4]]
                else:
                    self.cache_data += [["I", len(data[i])]]
                    for a in data[i]:
                        self.cache_data += [["4f"] + a[0:4]]

    def __write_matrix33_data(self, data, structure=1):
        chunks = self.__get_chunks(len(data))
        for chunk in chunks:
            self.cache_data += [["I", 0]]  # is constant?
            for i in chunk:
                if structure == 1:
                    self.cache_data += [["9f"] + data[i][0:9]]
                else:
                    self.cache_data += [["I", len(data[i])]]
                    for a in data[i]:
                        self.cache_data += [["9f"] + a[0:9]]

    def __write_matrix44_data(self, data, structure=1):
        chunks = self.__get_chunks(len(data))
        for chunk in chunks:
            self.cache_data += [["I", 0]]  # is constant?
            for i in chunk:
                if structure == 1:
                    self.cache_data += [["16f"] + data[i][0:16]]
                else:
                    self.cache_data += [["I", len(data[i])]]
                    for a in data[i]:
                        self.cache_data += [["16f"] + a[0:16]]
