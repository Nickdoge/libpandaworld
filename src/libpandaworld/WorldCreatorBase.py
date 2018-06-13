from pandac.PandaModules import *
from direct.showbase.DirectObject import DirectObject
from libpandaworld.WorldGlobals import WORLD_TYPE
from importlib import import_module
import os, re, imp, types

class WorldCreatorBase(DirectObject):
    """
    This is the base world creation class, inherited by either
    a server or client sided world creator.
    """

    def __init__(self, repository, worldFile, hubManager):
        self.repository = repository
        self.worldFile = worldFile
        self.hubManager = hubManager

        self.creatingInstance = False
        self.creatingInstanceParams = None
        self.fileDicts = {}
        self.objectList = {}
        self.postLoadCalls = []

    def makeRegion(self):
        """
        This method takes the main region world file and loads
        all of the objects from the file.
        """

        self.worldType = WORLD_TYPE
        if self.worldFile:
            self.loadObjectsFromFile(self.worldFile, self.repository)
        self.worldType = None

    def setHubManager(self, hubManager):
        """
        Set the hub manager.
        """

        self.hubManager = hubManager

    def getHubManager(self):
        """
        Get the hub manager.
        """

        return self.hubManager

    def loadObjectsFromFile(self, filename, parent, zoneLevel=0, startTime=None, parentIsObj=False):
        """
        This method opens a world data module and loads all of the
        objects from the object dictionary.
        """

        fileDict = self.openFile(filename)
        objDict = fileDict.get('Objects')
        parentUid = None
        if hasattr(parent, 'getUniqueId'):
            parentUid = parent.getUniqueId()
        objects = self.loadObjectDict(objDict,
            parent,
            parentUid,
            dynamic=0,
            zoneLevel=zoneLevel,
            startTime=startTime,
            parentIsObj=parentIsObj,
            fileName=re.sub('.py', '', filename))
        return [fileDict, objects]

    def loadObjectDict(self, objDict, parent, parentUid, dynamic, zoneLevel=0, startTime=None, parentIsObj=False, fileName=None, actualParentObj=None):
        """
        This method will take every key in an object dict and then
        load each object and return a list of the objects.
        """

        objects = []
        for objKey in objDict.keys():
            newObj = self.loadObject(objDict[objKey],
                parent,
                parentUid,
                objKey,
                dynamic,
                zoneLevel=zoneLevel,
                startTime=startTime,
                parentIsObj=parentIsObj,
                fileName=fileName,
                actualParentObj=actualParentObj)
            if newObj:
                objects.append(newObj)

        return objects

    def loadInstancedObject(self, obj, parent, parentUid, objKey, instanceParams=[]):
        self.creatingInstance = True
        self.creatingInstanceParams = instanceParams
        newObj = self.loadObject(obj, parent, parentUid, objKey, False)
        self.creatingInstance = False
        self.creatingInstanceParams = None
        return newObj

    def loadObject(self, obj, parent, parentUid, objKey, dynamic, zoneLevel=0, startTime=None, parentIsObj=False, fileName=None, actualParentObj=None):
        """
        This method will create new object info and return either
        a new object from the new info or None if there is no new info.
        """

        newObjInfo = self.createObject(obj,
            parent,
            parentUid,
            objKey,
            dynamic,
            zoneLevel=zoneLevel,
            startTime=startTime,
            parentIsObj=parentIsObj,
            fileName=fileName,
            actualParentObj=actualParentObj)
        if newObjInfo:
            newObj, newActualParent = newObjInfo
        else:
            return
        instanced = obj.get('Instanced')
        objDict = obj.get('Objects')
        if objDict:
            if newObj == None:
                newObj = parent
                if hasattr(newObj, 'getUniqueId'):
                    objKey = newObj.getUniqueId()
            self.loadObjectDict(objDict,
                newObj,
                objKey,
                dynamic,
                zoneLevel=zoneLevel,
                startTime=startTime,
                fileName=fileName,
                actualParentObj=newActualParent)
        return newObj

    def appendObjectList(self, key, value):
        """
        Append a key/value to the object list.
        """

        self.objectList[key] = value

    def findObjectCategory(self, objectType):
        """
        Find an object category in the object list.
        """

        cats = self.objectList.keys()
        for currCat in cats:
            types = self.objectList[currCat].keys()
            if objectType in types:
                return currCat

        return

    def createObject(self, obj, parent, parentUid, objKey, dynamic, zoneLevel=0, startTime=None, parentIsObj=False, fileName=None, actualParentObj=None):
        """
        This method will return an object type if it exists.
        This is meant to be inherited and then the actual object
        in the world will be created.
        """

        objType = obj.get('Type')
        self.notify.debug('createObject: type = %s' % objType)
        if dynamic and obj.get('ExtUid'):
            return objType
        childFilename = obj.get('File')
        if childFilename and obj['Type'] != 'Location Area':
            self.loadObjectsFromFile(childFilename + '.py',
                parent,
                zoneLevel=zoneLevel,
                startTime=startTime)
            return
        return objType

    def openFile(self, filename):
        """
        This method imports Python world data modules.
        The directory of world data files can be specified in the
        config string 'world-data-dir'. By default, it is just
        'worldData'.
        """

        objectStruct = None
        if '.py' in filename:
            moduleName = filename[:-3]
        else:
            moduleName = filename

        directory = config.GetString('world-data-dir', 'worldData')

        try:
            obj = import_module(directory + '.' + moduleName)
        except Exception as e:
            self.notify.error('Got a %s when loading %s' % (e, moduleName))

        dirl = directory.split('.')
        dirl.append(moduleName)
        dirl.append('objectStruct')

        newObj = None

        for symbol in dirl:
            if obj:
                newObj = getattr(obj, symbol, None)

        if newObj is not None:
            return newObj

    def getObjectDataByUid(self, uid, fileDict=None):
        """
        This will take a UID and look in all of the file data
        for the UID and return the object data if the UID is detected
        as a key.
        """

        if fileDict is None:
            fileDict = self.fileDicts
        objectInfo = None
        for name in fileDict:
            fileData = fileDict[name]
            if not uid in fileData['ObjectIds']:
                continue

            # TODO: Secure this:
            getSyntax = 'objectInfo = fileData' + fileData['ObjectIds'][uid]
            exec getSyntax

            if not 'File' in objectInfo or objectInfo.get('File') == '':
                break

        return objectInfo

    def getObjectDataFromFileByUid(self, uid, fileName):
        """
        This will take a UID and look in the passed fileName for the
        UID and return the object data if the UID is detected as a key.
        """

        objectInfo = None
        if fileName:
            if '.py' not in fileName:
                fileName += '.py'
            if self.isObjectDefined(uid, fileName):
                fileData = self.fileDicts[fileName]
                # TODO: Secure this:
                getSyntax = 'objectInfo = fileData' + fileData['ObjectIds'][uid]
                exec getSyntax
        return objectInfo

    def getFilelistByUid(self, uid, fileDict = None):
        """
        This will take a UID and optionally a passed file dictionary
        and return the filelist that the UID is in.
        """

        objectInfo = None
        if not fileDict:
            fileDict = self.fileDicts

        fileList = set()
        for name in fileDict:
            fileData = fileDict[name]
            if not uid in fileData['ObjectIds']:
                continue
            # TODO: Replace this:
            getSyntax = 'objectInfo = fileData' + fileData['ObjectIds'][uid]
            exec getSyntax
            fileList.add(name)
            objects = objectInfo.get('Objects')
            if objects:
                for obj in objects.values():
                    visual = obj.get('Visual')
                    if visual:
                        model = visual.get('Model')
                        if model:
                            if type(model) is types.ListType:
                                for currModel in model:
                                    fileList.add(currModel + '.bam')
                            else:
                                fileList.add(model + '.bam')
            objects = fileData.get('Objects')
            if objects:
                for obj in objects.values():
                    visual = obj.get('Visual')
                    if visual:
                        model = visual.get('Model')
                        if model:
                            fileList.add(model + '.bam')
            if not 'File' in objectInfo or objectInfo.get('File') == '':
                break
        return list(fileList)

    def getObjectLocationUid(self, objUid, fileDict=None):
        """
        This will take an object's UID and optionally a passed file
        dictionary and return the current object's location's UID.
        """

        if not fileDict:
            fileDict = self.fileDicts
        found = False
        curUid = objUid
        isPrivate = False
        while curUid:
            curFile = None
            for name in fileDict:
                fileData = fileDict[name]
                if not str(curUid) in fileData['ObjectIds']:
                    continue

                if str(curUid) in fileData['Objects']:
                    if fileData['Objects'][str(curUid)].get('Type') == 'Location':
                        return (str(curUid), isPrivate)
                    continue

                objData = fileData['Objects'].values()[0]['Objects']
                if str(curUid) in objData:
                    if objData[str(curUid)].get('Type') == 'Location':
                        return str(curUid)
                curFile = fileData
                break

            if not curFile:
                return
            else:
                curUid = curFile.get('Objects', {}).keys()[0]
                if curFile['Objects'][str(curUid)].get('Type') == 'Location':
                    return curUid

        return

    def isObjectDefined(self, objUid, fileName):
        """
        This checks if an object is defined in the file data or not.
        """

        fileDict = self.fileDicts
        fileData = fileDict.get(fileName)
        if fileData and objUid in fileData['ObjectIds']:
            return True
        else:
            return False

    def loadObjectDictDelayed(self, parentObj, objDict, parentUid, dynamic, zoneLevel=0):
        """
        This will call loadObjectDict with delayed time.
        (up to applications to use startTime)
        """

        if hasattr(parentObj, 'loadZoneObjects'):
            parentObj.loadZoneObjects(zoneLevel)
        else:
            startTime = globalClock.getRealTime()
            self.loadObjectDict(objDict, parentObj, parentUid, dynamic, zoneLevel=zoneLevel, startTime=startTime)

    def registerPostLoadCall(self, funcCall):
        """
        This registers a function to call after something
        in the world is loaded.
        """

        self.postLoadCalls.append(funcCall)

    def processPostLoadCalls(self):
        """
        This calls functions in the list after something in the world
        is loaded.
        """

        functionsCalled = []
        for currObj in self.postLoadCalls:
            if currObj not in functionsCalled:
                functionsCalled.append(currObj)
                currObj()

        self.postLoadCalls = []