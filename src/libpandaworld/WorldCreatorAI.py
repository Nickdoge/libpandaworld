from direct.directnotify.DirectNotifyGlobal import directNotify
from libpandaworld.WorldCreatorBase import WorldCreatorBase

class WorldCreatorAI(WorldCreatorBase):
    """
    This is the AI side of the WorldCreator, used by distributed networking servers to load world files.
    """

    notify = directNotify.newCategory('WorldCreatorAI')

    def createObject(self, obj, parent, parentUid, objKey, dynamic, zoneLevel=0, startTime=None, parentIsObj=False, fileName=None, actualParentObj=None):
        """
        This inherits the WorldCreatorBase's createObject and uses
        the hubManager to create the necessary objects.
        """

        objType = WorldCreatorBase.createObject(self, obj, parent, parentUid, objKey, dynamic, zoneLevel, startTime, parentIsObj, fileName, actualParentObj)
        if not objType:
            return

        newObj = None
        newActualParent = None

        if objType == 'Region':
            self.hubManager.setLocationObject(obj)
        elif objType == 'Location':
            loc = self.hubManager.generateLocation(objKey)
            newActualParent = loc
        elif actualParentObj:
            actualParentObj.createObject(obj, objType, parent, parentUid, objKey, dynamic, zoneLevel, startTime, parentIsObj, fileName, actualParentObj)

        return (newObj, newActualParent)