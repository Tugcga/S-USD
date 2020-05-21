# icecache v1.1
# Oct-24-2010
# Bradley R. Gabe
# withanar@gmail.com
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

	addPointPosition(posData)				3d data
	addBool(attrName, boolData)				1d data
	addInteger(attrName, integerData)			1d data
	addScalar(attrName, scalarData)			1d data
	addVector2(attrName, v2Data)			2d data
	addVector3(attrName, v3Data)			3d data
	addVector4(attrName, v4Data)			4d data
	addQuaternion(attrName, quaternionData)	4d data
	addMatrix3(attrName, matrix3Data)			9d data
	addMatrix4(attrName, matrix4Data)			16d data
	addColor(attrName, colorData)			4d data
	addRotation(attrName, rotData)			4d data
	
USAGE EXAMPLE:

import icecache
nbParticles = 3
ic = icecache.icecache(nbParticles)

posData = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]  #List of 3d data
customIDData = [1, 2, 3]  #1d list of integer data
sizeData = [0.1, 0.2, 0.3]   #1d list of float data
colorData = [[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0], [0.0, 0.0, 1.0, 1.0]]  #List of 4d, RGBA float data

ic.addPointPosition(posData)
ic.addInteger("customID", customIDData)
ic.addScalar("size", sizeData)
ic.addColor("color", colorData)

filename1 = r"C:\temp\testcache.1.icecache"
filename2 = r"C:\temp\testcache.2.icecache"

ic.write(filename1)
ic.write(filename2)

"""


class icecache:
    def __init__(self, nbParticles):
        from struct import pack

        self.nbParticles = nbParticles
        self.attributeData = {}
        self.cacheData = []
        self.DEBUG = 0

        self.DataTypes = {
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

    def addAttribute(self,
                     attributeName,  # attrName:
                     dataType,  # dataType:  1:Bool, 2:Long, 4:Float, 8:Vector2, 16:Vector3, 32:Vector4, 64:Quat, 128:Mat3x3, 256:Mat4x4, 512:Color4, 16384:Rotation
                     structureType,  # structureType:  1:Single data, 2:Array data
                     contextType,  # contextType:  1:Singleton, 2:Component0D, 4:Component1D, 8:Component2D... see SI SDK docs for more
                     category,  # category:  0:Unknown Category, 1:Built-in attribute, 2:User-defined attribute
                     data  # data
                     ):

        attrData = {}
        attrData["dataType"] = dataType
        attrData["structureType"] = structureType
        attrData["contextType"] = contextType
        attrData["category"] = category
        attrData["data"] = data
        self.attributeData[attributeName] = attrData

    def addPointPosition(self, posData):
        self.addAttribute(
            "pointposition",
            16,
            1,
            2,
            1,
            posData
        )

    def addBool(self, attrName, boolData):
        self.addAttribute(
            attrName,
            1,
            1,
            2,
            2,
            boolData
        )

    def addInteger(self, attrName, integerData):
        self.addAttribute(
            attrName,
            2,
            1,
            2,
            2,
            integerData
        )

    def addScalar(self, attrName, scalarData):
        self.addAttribute(
            attrName,
            4,
            1,
            2,
            2,
            scalarData
        )

    def addVector2(self, attrName, v2Data):
        self.addAttribute(
            attrName,
            8,
            1,
            2,
            2,
            v2Data
        )

    def addVector3(self, attrName, v3Data):
        self.addAttribute(
            attrName,
            16,
            1,
            2,
            2,
            v3Data
        )

    def addVector4(self, attrName, v4Data):
        self.addAttribute(
            attrName,
            32,
            1,
            2,
            2,
            v4Data
        )

    def addQuaternion(self, attrName, quaternionData):
        self.addAttribute(
            attrName,
            64,
            1,
            2,
            2,
            quaternionData
        )

    def addMatrix3(self, attrName, matrix3Data):
        self.addAttribute(
            attrName,
            128,
            1,
            2,
            2,
            matrix3Data
        )

    def addMatrix4(self, attrName, matrix4Data):
        self.addAttribute(
            attrName,
            256,
            1,
            2,
            2,
            matrix4Data
        )

    def addColor(self, attrName, colorData):
        self.addAttribute(
            attrName,
            512,
            1,
            2,
            2,
            colorData
        )

    def addRotation(self, attrName, rotData):
        self.addAttribute(
            attrName,
            16384,
            1,
            2,
            2,
            rotData
        )

    def write(self, fileName, ascii=0):
        import gzip
        from struct import pack

        self.__WriteHeader()
        self.__WriteAttributeDefs()
        self.__WriteAttributeData()

        if not ascii:
            text = []
            for elem in self.cacheData:
                if self.DEBUG:
                    Application.LogMessage(elem)
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

            cachefile = gzip.open(fileName, "wb")
            cachefile.write("".join(text))
            cachefile.close()

        else:
            text = []
            for elem in self.cacheData:
                for item in elem[1:]:
                    text.append(str(item))

            cachefile = open(fileName, "w")
            cachefile.write(" ".join(text))
            cachefile.close()

    def __WriteHeader(self):

        self.cacheData += [["8s", "ICECACHE"]]  # header string
        self.cacheData += [["I", 102]]  # version number
        self.cacheData += [["I", 0]]  # object type, pointcloud
        self.cacheData += [["I", self.nbParticles]]  # point count
        self.cacheData += [["I", 0]]  # edge count
        self.cacheData += [["I", 0]]  # polygon count
        self.cacheData += [["I", 0]]  # sample count
        self.cacheData += [["I", 0]]  # don't know this one
        self.cacheData += [["I", len(self.attributeData)]]  # attribute count

    def __WriteAttributeDefs(self):
        attributeList = self.attributeData.keys()
        attributeList.sort()

        for attribute in attributeList:
            data = self.attributeData[attribute]
            nameLength = len(attribute)
            filler = 4 - nameLength % 4
            if filler == 4:
                filler = 0
            attributeName = attribute+"".join(["_"]*filler)

            self.cacheData += [["L", nameLength]]  # attribute name length
            # attribute name
            self.cacheData += [[str(len(attributeName))+"s", attributeName]]
            self.cacheData += [["I", data["dataType"]]]  # self.cacheData type
            self.cacheData += [["I", data["structureType"]]]  # structure type
            self.cacheData += [["I", data["contextType"]]]  # context type
            self.cacheData += [["I", 0]]  # self.cacheDatabase ID, obsolete
            self.cacheData += [["I", data["category"]]]  # category

    def __WriteAttributeData(self):

        attributeList = self.attributeData.keys()
        attributeList.sort()
        for attribute in attributeList:
            data = self.attributeData[attribute]
            dataType = data["dataType"]
            if attribute.lower() == "pointposition":
                self.__WritePositionData(data["data"])
            elif dataType == 1:
                self.__WriteBoolData(data["data"])
            elif dataType == 2:
                self.__WriteLongData(data["data"])
            elif dataType == 4:
                self.__WriteFloatData(data["data"])
            elif dataType == 8:
                self.__WriteVector2Data(data["data"])
            elif dataType == 16:
                self.__WriteVector3Data(data["data"])
            elif dataType == 32:
                self.__WriteVector4Data(data["data"])
            elif dataType == 64:
                self.__WriteVector4Data(data["data"])
            elif dataType == 128:
                self.__WriteMatrix33Data(data["data"])
            elif dataType == 256:
                self.__WriteMatrix44Data(data["data"])
            elif dataType == 512:
                self.__WriteVector4Data(data["data"])
            elif dataType == 16384:
                self.__WriteVector4Data(data["data"])

    def __GetChunks(self, num):
        if num < 4000:
            return [range(num)]

        outlist = []
        chunks = num / 4000
        for i in range(chunks):
            outlist.append(range((i)*4000, (i+1)*4000))
        outlist.append(range((i+1)*4000, (i+1)*4000 + num % 4000))
        return outlist

    def __WritePositionData(self, data):
        self.cacheData += [["I", 0]]  # is constant?
        count = len(data)
        for i in range(count):
            self.cacheData += [["3f"]+data[i][0:3]]

    def __WriteBoolData(self, data):
        chunks = self.__GetChunks(len(data))
        for chunk in chunks:
            self.cacheData += [["I", 0]]  # is constant?
            for i in chunk:
                self.cacheData += [["I"]+[data[i]]]

    def __WriteLongData(self, data):
        chunks = self.__GetChunks(len(data))
        for chunk in chunks:
            self.cacheData += [["I", 0]]  # is constant?
            for i in chunk:
                self.cacheData += [["L"]+[data[i]]]

    def __WriteFloatData(self, data):
        chunks = self.__GetChunks(len(data))
        for chunk in chunks:
            self.cacheData += [["I", 0]]  # is constant?
            for i in chunk:
                self.cacheData += [["1f"]+[data[i]]]

    def __WriteVector2Data(self, data):
        chunks = self.__GetChunks(len(data))
        for chunk in chunks:
            self.cacheData += [["I", 0]]  # is constant?
            for i in chunk:
                self.cacheData += [["2f"]+data[i][0:2]]

    def __WriteVector3Data(self, data):
        chunks = self.__GetChunks(len(data))
        for chunk in chunks:
            self.cacheData += [["I", 0]]  # is constant?
            for i in chunk:
                self.cacheData += [["3f"]+data[i][0:3]]

    def __WriteVector4Data(self, data):
        chunks = self.__GetChunks(len(data))
        for chunk in chunks:
            self.cacheData += [["I", 0]]  # is constant?
            for i in chunk:
                self.cacheData += [["4f"]+data[i][0:4]]

    def __WriteMatrix33Data(self, data):
        chunks = self.__GetChunks(len(data))
        for chunk in chunks:
            self.cacheData += [["I", 0]]  # is constant?
            for i in chunk:
                self.cacheData += [["9f"]+data[i][0:9]]

    def __WriteMatrix44Data(self, data):
        chunks = self.__GetChunks(len(data))
        for chunk in chunks:
            self.cacheData += [["I", 0]]  # is constant?
            for i in chunk:
                self.cacheData += [["16f"]+data[i][0:16]]
