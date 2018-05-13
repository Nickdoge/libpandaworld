from pandac.PandaModules import *
from direct.interval.IntervalGlobal import *
from libpandaworld.WorldCreatorBase import WorldCreatorBase
from libpandaworld.WorldGlobals import HUB_AREAS

class WorldCreator(WorldCreatorBase):
    """
    This is a basic WorldCreator that projects may directly use.
    Alternatively, projects can set up their own WorldCreator.
    """

    notify = directNotify.newCategory('WorldCreator')

    def __init__(self, cr, worldFile, hubManager, district):
        self.objectList = {}
        self.hubAreas = {}
        WorldCreatorBase.__init__(self, cr, worldFile, hubManager, district)

    def destroy(self):
        self.district = None

    def loadObjectsFromFile(self, filename, parent, parentUid=None, dynamic=0, zoneLevel=0, startTime=None, merge=False):
        """
        This overrides the WorldCreatorBase's loadObjectsFromFile, but
        works about the same.
        """

        if filename in self.fileDicts:
            return self.fileDicts
        fileData = self.openFile(filename)
        if parentUid:
            fileDict = {'filename': fileData}
            if merge:
                parentUid = fileData['Objects'].keys()[0]
            self.loadObjectsByUid(parent, parentUid, dynamic=dynamic, fileDict=fileDict, zoneLevel=zoneLevel, startTime=startTime)
        else:
            if parent == self.district:
                self.loadHubData(filename, fileData)
        self.fileDicts[filename] = fileData
        return self.fileDicts

    def loadHubData(self, filename, fileData):
        """
        This will load the hub (location parent) data.
        """

        hubAreas = fileData.get(HUB_AREAS)
        if hubAreas:
            self.hubAreas[filename] = hubAreas

    def getHubData(self, filename):
        """
        Get the hub data.
        """

        return self.hubAreas.get(filename)

    def loadObjectsByUid(self, parent, parentUid, dynamic=0, fileDict=None, zoneLevel=0, startTime=None):
        """
        This will load world objects by the parent's UID.
        """

        if fileDict == None:
            fileDict = self.fileDicts
        objectInfo = self.getObjectDataByUid(parentUid, fileDict)
        if not objectInfo:
            self.notify.error('Data file not found for area being loaded: %s, make sure worldCreator.loadObjectsFromFile is being called.' % parentUid)

        objDict = objectInfo.get('Objects')
        if objDict != None:
            self.loadObjectDict(objDict, parent, parentUid, dynamic, zoneLevel=zoneLevel, startTime=startTime)
            if 'AdditionalData' in objectInfo:
                additionalFiles = objectInfo['AdditionalData']
                for currFile in additionalFiles:
                    if currFile + '.py' in self.fileDicts:
                        altParentUid = self.fileDicts[currFile + '.py']['Objects'].keys()[0]
                        addObjDict = self.fileDicts[currFile + '.py']['Objects'][altParentUid]['Objects']
                        self.loadObjectDict(addObjDict, parent, parentUid, dynamic, zoneLevel=zoneLevel, startTime=startTime)
                        try:
                            self.repository.yieldThread('load object')
                        except Exception:
                            pass

        fileRef = objectInfo.get('File')
        if fileRef:
            self.loadObjectsFromFile(fileRef + '.py', parent, parentUid, dynamic, zoneLevel=zoneLevel, startTime=startTime)

        if 'AdditionalData' in objectInfo:
            additionalFiles = objectInfo['AdditionalData']
            for currFile in additionalFiles:
                self.loadObjectsFromFile(currFile + '.py', parent, parentUid, dynamic, zoneLevel=zoneLevel, startTime=startTime, merge=True)

        return

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
        This inherits the WorldCreatorBase's createObject and uses
        the hubManager to create the necessary objects.
        """

        objType = WorldCreatorBase.createObject(self, obj, parent, parentUid, objKey, dynamic, zoneLevel, startTime, parentIsObj, fileName, actualParentObj)
        if not objType:
            return (None, None)

        newObj = None
        newActualParent = None

        # Should there be something more here?

        self.hubManager.handleObject(obj, objType, parent, parentUid, objKey, dynamic, zoneLevel=0, startTime=None, parentIsObj=False, fileName=None, actualParentObj=None)

        return (newObj, newActualParent)

    def loadDataFile(self, fileName):
        """
        This will call loadObjectsFromFile with a specified fileName,
        using the District (parent of hub).
        """

        self.fileDicts = {}
        self.loadObjectsFromFile(fileName, self.district)

    def loadObject(self, obj, parent, parentUid, objKey, dynamic, zoneLevel=0, startTime=None, parentIsObj=False, fileName=None, actualParentObj=None):
        """
        This overrides WorldCreatorBase's loadObject, doing basically
        the same thing.
        """

        newObj, actualParentObj = self.createObject(obj, parent, parentUid, objKey, dynamic, zoneLevel=zoneLevel, startTime=startTime, fileName=fileName, actualParentObj=actualParentObj)
        objDict = obj.get('Objects')
        if objDict:
            if newObj == None:
                callback = lambda param0=0, param1=objDict, param2=objKey, param3=dynamic, param4=-1: self.loadObjectDictDelayed(param0, param1, param2, param3, param4)
                if hasattr(self.repository, 'uidMgr'):
                    self.repository.uidMgr.addUidCallback(objKey, callback)
            else:
                parentObj = newObj
                newParentUid = objKey
                self.loadObjectDict(objDict, parentObj, newParentUid, dynamic, zoneLevel=zoneLevel, startTime=startTime, actualParentObj=newObj)
        return newObj

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