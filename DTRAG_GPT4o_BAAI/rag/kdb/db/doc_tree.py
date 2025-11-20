class DocTree:
    def __init__(self):
        self.nodes = {}
        self.masterNode = None
        self.rootNodes = {}

    def addNode(self, treeNode, isMaster=False):
        """
        添加树的节点
        """

        if treeNode.id in self.nodes:
            return

        self.nodes[treeNode.id] = treeNode
        if isMaster:
            treeNode.isMaster = True
            treeNode.enable = True
            self.masterNode = treeNode

    def buildTree(self):
        """
        构建树
        """
        # mock 缺失的父节点
        mockNodes = []
        for node in self.nodes.values():
            if node.parentID not in self.nodes and node.parentID > 0:
                mockNodes.append(DocTreeNode(node.parentID, 0, 1, '', True))
        for one in mockNodes:
            self.addNode(one)

        for node in self.nodes.values():
            if node.parentID <= 0:
                self.rootNodes[node.getUniqID()] = node
            elif not node.isMock:
                node.setParentNode(self.nodes[node.parentID])
                self.nodes[node.parentID].addChildNode(node)

    def cropTree(self, sameLayerMaxSize=-1, parentLayerMaxSize=-1, childLayerMaxSize=-1):
        """
        裁剪树
        """
        if sameLayerMaxSize > 0:
            self._cropSameLayer(sameLayerMaxSize)

        if parentLayerMaxSize > 0:
            self._cropParentLayer(parentLayerMaxSize)

        if childLayerMaxSize > 0:
            self._cropChildLayer(childLayerMaxSize)

    def _cropNode(self, maxSize, nodes, masterNode=None):
        """
        根据尺寸裁剪节点
        """
        if nodes is None or len(nodes) == 0 or maxSize == 0:
            return 0, 0

        nodeIndex = 0
        if masterNode is not None:
            try:
                nodeIndex = nodes.index(masterNode)
            except:
                pass

        beforeIndex = nodeIndex
        afterIndex = nodeIndex + 1
        if self._calSize(nodes[beforeIndex:afterIndex], masterNode) > maxSize:
            return 0, 0

        step = 0
        retainNum = 0
        beforeIndexCanMove = True
        afterIndexCanMove = True
        while beforeIndexCanMove or afterIndexCanMove:
            step += 1
            if step % 2 == 1:
                if beforeIndex > 0 and self._calSize(nodes[beforeIndex-1:afterIndex], masterNode) <= maxSize:
                    beforeIndex -= 1
                    retainNum += 1
                else:
                    beforeIndexCanMove = False

            else:
                if afterIndex <= len(nodes) and self._calSize(nodes[beforeIndex:afterIndex+1], masterNode) <= maxSize:
                    afterIndex += 1
                    retainNum += 1
                else:
                    afterIndexCanMove = False

        for one in nodes[beforeIndex:afterIndex]:
            one.enable = True

        return retainNum, self._calSize(nodes[beforeIndex:afterIndex], masterNode)

    def _cropSameLayer(self, maxSize):
        if self.masterNode.parentNode is None:
            self._cropNode(maxSize, None, self.masterNode)
        else:
            self._cropNode(
                maxSize, self.masterNode.parentNode.childs, self.masterNode)

    def _cropParentLayer(self, maxSize):
        if self.masterNode.parentNode is None:
            return

        parentNode = self.masterNode.parentNode
        leftSize = maxSize
        step = 0
        while True:
            step += 1
            if step % 2 == 1:
                retainNum, usedSize = self._cropNode(leftSize, [parentNode])
                if retainNum == 1:
                    leftSize -= usedSize
                else:
                    break

            else:
                if parentNode.parentNode is not None:
                    retainNum, usedSize = self._cropNode(
                        leftSize, parentNode.parentNode.childs, parentNode)
                    if retainNum == len(parentNode.parentNode.childs):
                        parentNode = parentNode.parentNode
                        leftSize -= usedSize
                    else:
                        break
                else:
                    break

    def _cropChildLayer(self, maxSize, node=None):
        childs = [self.masterNode]
        while True:
            childs_temp = []
            for one in childs:
                childs_temp = childs_temp + one.childs

            retainNum, usedSize = self._cropNode(maxSize, childs_temp)
            if retainNum == 0 or retainNum != len(childs_temp) or usedSize == maxSize:
                break
            else:
                maxSize -= usedSize
                childs = childs_temp

    def _calSize(self, nodes, masterNode):
        size = 0
        for one in nodes:
            if masterNode is None:
                size += one.size
            elif one.id != masterNode.id:
                size += one.size

        return size

    def printTree(self, treeNode=None, layer=0, justPrintEnable=False):
        if treeNode is None:
            for key in sorted(self.rootNodes):
                one = self.rootNodes[key]

                one.printNode(layer, justPrintEnable)
                for oneChild in one.childs:
                    self.printTree(oneChild, layer+1, justPrintEnable)
        else:
            treeNode.printNode(layer, justPrintEnable)
            for oneChild in treeNode.childs:
                self.printTree(oneChild, layer+1, justPrintEnable)

    def toStr(self, treeNode=None):
        rs = ""
        if treeNode is None:
            for key in sorted(self.rootNodes):
                one = self.rootNodes[key]
                if one.enable and not one.isMock:
                    rs += one.content
                for oneChild in one.childs:
                    rs += self.toStr(oneChild)
        else:
            if treeNode.enable and not treeNode.isMock:
                rs += treeNode.content
            for oneChild in treeNode.childs:
                rs += self.toStr(oneChild)

        return rs


class DocTreeNode:
    def __init__(self, id, parentID, seq, content, isMock=False):
        self.id = id
        self.parentID = parentID
        self.seq = seq
        self.content = content
        self.size = len(content)
        self.childs = []
        self.parentNode = None
        self.isMaster = False
        self.enable = False
        self.isMock = isMock

    def getUniqID(self):
        return self.parentID * 1000000000000 + self.id * 10000 + self.seq

    def setParentNode(self, node):
        self.parentNode = node

    def addChildNode(self, node):
        self.childs.append(node)
        self.childs.sort(key=lambda node: node.seq)

    def printNode(self, layer, justPrintEnable=True):
        if justPrintEnable and not self.enable:
            return

        for i in range(layer):
            print("--", end="")

        if self.isMaster:
            print("***", end="")
        print(self.id, self.parentID, self.seq, self.content)
