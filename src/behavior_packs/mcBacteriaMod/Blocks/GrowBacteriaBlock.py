# coding=utf-8
from Queue import Queue
import server.extraServerApi as serverApi
from mcBacteriaMod.modCommon.config.const import Const


class GrowBacteriaBlock(object):
    def __init__(self, data, levelId):
        self.__levelId = levelId
        self.blockEntityComp = serverApi.CreateComponent(levelId, "Minecraft", "blockEntityData")
        self.bacteriaDict = {}  # 用于统计当前对应菌群的存活数
        self.bacteriaDictTotal = {}  # 用于统计对应菌群总计感染数
        self.clock = 0

    def ServerPlaceBlockEntityEvent(self, data):
        pass

    def BlockStrengthChangedServerEvent(self, data, playerId):
        # 只在红石信号被激活时执行
        if data["newStrength"] < 2:
            return
        comp = serverApi.CreateComponent(playerId, "Minecraft", "blockInfo")
        posX = data.get("posX")
        posY = data.get("posY")
        posZ = data.get("posZ")
        posId = str(posX) + str(posY) + str(posZ)

        # 获取上面的方块，草方块视为泥土
        upBlock = comp.GetBlockNew((posX, posY + 1, posZ))["name"]
        if upBlock == "minecraft:grass" or upBlock == "minecraft:grass_path":
            upBlock = "minecraft:dirt"
        # 如果上面没有方块或者上面也是GrowBacteria则不执行
        if upBlock == "minecraft:air" or upBlock == Const.GrowBacteria:
            return

        # 获取下面的方块，草方块视为泥土
        downBlock = comp.GetBlockNew((posX, posY - 1, posZ))["name"]
        if downBlock == "minecraft:grass" or upBlock == "minecraft:grass_path":
            downBlock = "minecraft:dirt"
        # 如果下面没有方块或者下面与上面相同则不执行
        if downBlock == "minecraft:air" or downBlock == upBlock:
            return

        # 存储需要感染的目标方块和需要转变的方块
        blockEntityData = self.blockEntityComp.GetBlockEntityData(0, (posX, posY, posZ))
        if blockEntityData:
            blockEntityData["root"] = posId
            blockEntityData["target"] = downBlock
            blockEntityData["change"] = upBlock
        # 增加方块计数
        self.bacteriaDict[posId] = 1
        self.bacteriaDictTotal[posId] = 1

    def ServerBlockEntityTickEvent(self, data, playerId):
        posX = data.get("posX")
        posY = data.get("posY")
        posZ = data.get("posZ")
        comp = serverApi.CreateComponent(playerId, "Minecraft", "blockInfo")
        blockEntityData = self.blockEntityComp.GetBlockEntityData(0, (posX, posY, posZ))
        # 如果root字段存在说明此细菌被激活
        if blockEntityData and blockEntityData["root"]:
            if blockEntityData["root"] not in self.bacteriaDict:
                del blockEntityData
                return

            # 每60帧执行一次
            self.clock = self.clock + 1
            if self.clock < 60:
                return
            self.clock = 0

            target = blockEntityData["target"]
            change = blockEntityData["change"]
            root = blockEntityData["root"]

            # 将周围的目标方块感染成细菌
            if root in self.bacteriaDict and self.bacteriaDict[root] > 0:
                flag = 0
                flag = flag + self.createNew(comp, (posX, posY - 1, posZ), target, change, root)
                flag = flag + self.createNew(comp, (posX, posY + 1, posZ), target, change, root)
                flag = flag + self.createNew(comp, (posX - 1, posY, posZ), target, change, root)
                flag = flag + self.createNew(comp, (posX + 1, posY, posZ), target, change, root)
                flag = flag + self.createNew(comp, (posX, posY, posZ + 1), target, change, root)
                flag = flag + self.createNew(comp, (posX, posY, posZ - 1), target, change, root)
                if flag > 0:
                    # bacteriaDict为负值说明停止增生
                    self.bacteriaDict[root] = -self.bacteriaDict[root]
                    del self.bacteriaDictTotal[root]

            # 将自身变为需要转变的方块
            newBlockDict = {
                'name': change
            }
            comp.SetBlockNew((posX, posY, posZ), newBlockDict)

            # 细菌计数
            # 细菌增生时bacteriaDict为正值
            # 停止增生时bacteriaDict为负值
            # bacteriaDict为0时删除该键值
            if self.bacteriaDict[root] < 0:
                self.bacteriaDict[root] = self.bacteriaDict[root] + 1
            elif self.bacteriaDict[root] > 0:
                self.bacteriaDict[root] = self.bacteriaDict[root] - 1
            if self.bacteriaDict[root] == 0:
                del self.bacteriaDict[root]
                if root in self.bacteriaDictTotal:
                    del self.bacteriaDictTotal["root"]

        # 如果此细菌未被激活则判断是否可激活
        else:
            comp = serverApi.CreateComponent(playerId, "Minecraft", "redStone")
            strength = comp.GetStrength((data["posX"], data["posY"], data["posZ"]))
            if strength > 1:
                data["newStrength"] = strength
                self.BlockStrengthChangedServerEvent(data, playerId)

    def createNew(self, comp, pos, target, change, root):
        blockName = comp.GetBlockNew(pos)["name"]
        # 草方块视为泥土
        if blockName == "minecraft:grass" or blockName == "minecraft:grass_path":
            blockName = "minecraft:dirt"
        if blockName == target:
            newBlockDict = {
                'name': Const.GrowBacteria
            }
            comp.SetBlockNew(pos, newBlockDict)
            blockEntityData = self.blockEntityComp.GetBlockEntityData(0, pos)
            if blockEntityData:
                blockEntityData["root"] = root
                blockEntityData["target"] = target
                blockEntityData["change"] = change
            self.bacteriaDict[root] = self.bacteriaDict[root] + 1
            self.bacteriaDictTotal[root] = self.bacteriaDictTotal[root] + 1
        elif blockName == Const.SterilizeBlock:
            return 1
        return 0

    def clear(self):
        clearCnt = 0
        for key in self.bacteriaDictTotal.keys():
            clearCnt = clearCnt + self.bacteriaDictTotal[key]
            self.bacteriaDict[key] = -self.bacteriaDict[key]
        self.bacteriaDictTotal.clear()
        return clearCnt
