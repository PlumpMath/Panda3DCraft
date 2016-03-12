from panda3d.core import *
from direct.directbase import DirectStart
from direct.actor.Actor import Actor
from direct.task import Task
from noise import pnoise1, pnoise2, snoise2
import sys
import random
from direct.interval.IntervalGlobal import *

points = 256
span = 5.0
octaves = 1

base.enableParticles()

world = {}

AIR = 0
DIRT = 1

worldSize = 64/2

verboseGeneration = True
paused = False

freq = 16.0 * octaves

class Block():
    def __init__(self, type, x, y, z):
        self.type = type
        if self.type == AIR:
            del self
            return
        self.x = x
        self.y = y
        self.z = z

        self.model = base.loader.loadModel("gfx/block")
        self.model.reparentTo(base.render)
        self.model.setPos(x, y, z)
        self.model.setTag('blockTag', '1')
        self.model.find('**/SideW').setTag('westTag', '2')
        self.model.find('**/SideN').setTag('northTag', '3')
        self.model.find('**/SideE').setTag('eastTag', '4')
        self.model.find('**/SideS').setTag('southTag', '5')
        self.model.find('**/Top').setTag('topTag', '6')
        self.model.find('**/Bottom').setTag('botTag', '7')
    
    def cleanup(self):
        self.model.remove()
        del self

def addBlock(blockType,x,y,z):
    try: 
        world[(x,y,z)].cleanup()
    except:
        pass
    block = Block(blockType, x, y, z)
    world[(x,y,z)] = block
    return

for x in xrange(-worldSize, worldSize):
    for y in xrange(-worldSize, worldSize):
        for z in xrange(-worldSize, worldSize):
            world[(x,y,z)] = Block(AIR, x, y, z)

for x in xrange(0, 16):
    for y in xrange(0, 16):
        amplitude = random.randrange(0.0,5.0)
        blockType = DIRT
        z = int(snoise2(x / freq, y / freq, octaves) * amplitude)
        addBlock(blockType,x,y,z)
        if verboseGeneration: print "Generated block %d at (%d, %d, %d)" % (blockType, x, y, z)

alight = AmbientLight('alight')
alight.setColor(VBase4(0.6, 0.6, 0.6, 1))
alnp = render.attachNewNode(alight)
render.setLight(alnp)
dlight = DirectionalLight('dlight')
dlight.setColor(VBase4(0.8, 0.8, 0.8, 1))
dlnp = render.attachNewNode(dlight)
dlnp.setHpr(0, -45, 0)
render.setLight(dlnp)

traverser = CollisionTraverser()
handler = CollisionHandlerQueue()
        
pickerNode = CollisionNode('mouseRay')
pickerNP = camera.attachNewNode(pickerNode)
pickerNode.setFromCollideMask(GeomNode.getDefaultCollideMask())
pickerRay = CollisionRay()
pickerNode.addSolid(pickerRay)
traverser.addCollider(pickerNP, handler)

def handlePick(right=False):
    if paused:
        return # no
    if base.mouseWatcherNode.hasMouse():
        mpos = base.mouseWatcherNode.getMouse()
        pickerRay.setFromLens(base.camNode, mpos.getX(), mpos.getY())

        traverser.traverse(render)
        if handler.getNumEntries() > 0:
            handler.sortEntries()
            pickedObj = handler.getEntry(0).getIntoNodePath()
            pickedObj = pickedObj.findNetTag('blockTag')
            if not pickedObj.isEmpty():
                if right:
                    handleRightPickedObject(pickedObj, handler.getEntry(0).getIntoNodePath().findNetTag('westTag').isEmpty(),
                        handler.getEntry(0).getIntoNodePath().findNetTag('northTag').isEmpty(), handler.getEntry(0).getIntoNodePath().findNetTag('eastTag').isEmpty(),
                        handler.getEntry(0).getIntoNodePath().findNetTag('southTag').isEmpty(), handler.getEntry(0).getIntoNodePath().findNetTag('topTag').isEmpty(),
                        handler.getEntry(0).getIntoNodePath().findNetTag('botTag').isEmpty())
                else:
                    handlePickedObject(pickedObj)


def save():
    print "Saving..."
    f = open('save.sav', 'wt')
    for key in world:
        f.write(str(key) + ':')
        f.write(str(world[key].type) + '\n')
    f.close()
    print "Saved!"

def load():
    print "Loading..."
    f = open('save.sav', 'r')
    toLoad = f.read().split('\n')
    toLoad.pop() # get rid of newline
    for key in toLoad:
        key = key.split(':')
        posTup = eval(key[0])
        addBlock(int(key[1]), posTup[0], posTup[1], posTup[2])
    f.close()
    print "Loaded!"

def pause():
    global paused
    paused = not paused

base.accept('mouse1', handlePick)
base.accept('mouse3', handlePick, extraArgs=[True])
base.accept('s', save)
base.accept('l', load)
base.accept('escape', pause)

def handlePickedObject(obj):
    print "Picked a block at %d, %d, %d" % (obj.getX(), obj.getY(), obj.getZ())
    addBlock(AIR, obj.getX(), obj.getY(), obj.getZ())

def handleRightPickedObject(obj, west, north, east, south, top, bot):
    print "Picked a block at %d, %d, %d" % (obj.getX(), obj.getY(), obj.getZ())
    if world[(obj.getX()-1, obj.getY(), obj.getZ())].type == AIR and not west:
        addBlock(DIRT, obj.getX()-1, obj.getY(), obj.getZ())
    elif world[(obj.getX()+1, obj.getY(), obj.getZ())].type == AIR and not east:
        addBlock(DIRT, obj.getX()+1, obj.getY(), obj.getZ())
    elif world[(obj.getX(), obj.getY()-1, obj.getZ())].type == AIR and not south:
        addBlock(DIRT, obj.getX(), obj.getY()-1, obj.getZ())
    elif world[(obj.getX(), obj.getY()+1, obj.getZ())].type == AIR and not north:
        addBlock(DIRT, obj.getX(), obj.getY()+1, obj.getZ())
    elif world[(obj.getX(), obj.getY(), obj.getZ()+1)].type == AIR and not top:
        addBlock(DIRT, obj.getX(), obj.getY(), obj.getZ()+1)
    elif world[(obj.getX(), obj.getY(), obj.getZ()-1)].type == AIR and not bot:
        addBlock(DIRT, obj.getX(), obj.getY(), obj.getZ()-1)
 
run()