from panda3d.core import *
from direct.directbase import DirectStart
from direct.actor.Actor import Actor
from direct.task import Task
from direct.gui.DirectGui import *
from noise import pnoise1, pnoise2, snoise2
import sys
import random
import os
from direct.interval.IntervalGlobal import *

points = 256
span = 5.0
octaves = 1
freq = 16.0 * octaves

world = {}

AIR = 0
DIRT = 1

worldSize = 64/2

verboseGeneration = True
paused = False

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


def pause():
    global paused
    paused = not paused

    if paused:
        base.disableMouse()
        pauseScreen.showPause()
    else:
        base.enableMouse()
        pauseScreen.hide()

class PauseScreen():
    def __init__(self):
        self.pauseScr = aspect2d.attachNewNode("pause") # This is used so that everything can be stashed at once... except for dim, which is on render2d
        self.loadScr = aspect2d.attachNewNode("load") # It also helps for flipping between screens
        self.saveScr = aspect2d.attachNewNode("save")
        
        cm = CardMaker('card')
        self.dim = render2d.attachNewNode(cm.generate()) # On render2d because I don't know a way to cover the entire screen on aspect2d
        self.dim.setPos(-1, 0, -1)
        self.dim.setScale(2)
        self.dim.setTransparency(1)
        self.dim.setColor(0, 0, 0, 0.5)

        buttonModel = loader.loadModel('gfx/button')
        inputTexture = loader.loadTexture('gfx/tex/button_press.png')

        # Pause Screen
        self.unpauseButton = DirectButton(geom = (buttonModel.find('**/button_up'), buttonModel.find('**/button_press'), buttonModel.find('**/button_over'), buttonModel.find('**/button_disabled')),
            relief = None, parent = self.pauseScr, scale = 0.75, pos = (0, 0, 0.75), text = "Resume Game", text_fg = (1,1,1,1), text_scale = 0.15, text_pos = (0, -0.04), command = pause)
        self.saveButton = DirectButton(geom = (buttonModel.find('**/button_up'), buttonModel.find('**/button_press'), buttonModel.find('**/button_over'), buttonModel.find('**/button_disabled')),
            relief = None, parent = self.pauseScr, scale = 0.75, pos = (0, 0, 0.5), text = "Save Game", text_fg = (1,1,1,1), text_scale = 0.15, text_pos = (0, -0.04), command = self.showSave)
        self.loadButton = DirectButton(geom = (buttonModel.find('**/button_up'), buttonModel.find('**/button_press'), buttonModel.find('**/button_over'), buttonModel.find('**/button_disabled')),
            relief = None, parent = self.pauseScr, scale = 0.75, pos = (0, 0, -0.5), text = "Load Game", text_fg = (1,1,1,1), text_scale = 0.15, text_pos = (0, -0.04), command = pause, state = DGG.DISABLED)
        self.exitButton = DirectButton(geom = (buttonModel.find('**/button_up'), buttonModel.find('**/button_press'), buttonModel.find('**/button_over'), buttonModel.find('**/button_disabled')),
            relief = None, parent = self.pauseScr, scale = 0.75, pos = (0, 0, -0.75), text = "Quit Game", text_fg = (1,1,1,1), text_scale = 0.15, text_pos = (0, -0.04), command = exit)

        #Save Screen
        self.saveText = DirectLabel(text = "Type in a name for your world:", text_fg = (1,1,1,1), frameColor = (0,0,0,0), parent = self.saveScr, scale = 0.1, pos = (0,0,0.1))
        self.saveText2 = DirectLabel(text = "", text_fg = (1,1,1,1), frameColor = (0,0,0,0), parent = self.saveScr, scale = 0.06, pos = (0,0,-0.3))
        self.saveName = DirectEntry(text = "", scale= .15, command=self.save, initialText="My World", numLines = 1, focus=1, frameTexture = inputTexture, parent = self.saveScr, text_fg = (1,1,1,1),
            pos = (-0.75, 0, -0.1))
        self.saveGameBtn = DirectButton(geom = (buttonModel.find('**/button_up'), buttonModel.find('**/button_press'), buttonModel.find('**/button_over'), buttonModel.find('**/button_disabled')),
            relief = None, parent = self.saveScr, scale = 0.75, pos = (0, 0, -0.5), text = "Save", text_fg = (1,1,1,1), text_scale = 0.15, text_pos = (0, -0.04), command = self.save)
        self.backButton = DirectButton(geom = (buttonModel.find('**/button_up'), buttonModel.find('**/button_press'), buttonModel.find('**/button_over'), buttonModel.find('**/button_disabled')),
            relief = None, parent = self.saveScr, scale = 0.75, pos = (0, 0, -0.75), text = "Back", text_fg = (1,1,1,1), text_scale = 0.15, text_pos = (0, -0.04), command = self.showPause)
        

        self.hide()

    def showPause(self):
        self.saveScr.stash()
        self.pauseScr.unstash()
        self.dim.unstash()

    def showSave(self):
        self.pauseScr.stash()
        self.saveScr.unstash()

    def save(self, worldName = None):
        if worldName == None:
            worldName = self.saveName.get(True)
        self.saveText2['text'] = "Saving..."
        print "Saving %s..." % worldName
        dest = 'saves/%s.sav' % worldName
        dir = os.path.dirname(dest)
        if not os.path.exists(dir):
            os.makedirs(dir)
        try:
            f = open(dest, 'wt')
        except IOError:
            self.saveText2['text'] = "Could not save. Make sure the world name does not contain the following characters: \\ / : * ? \" < > |"
            print "Failed!"
            return
        for key in world:
            f.write(str(key) + ':')
            f.write(str(world[key].type) + '\n')
        f.close()
        self.saveText2['text'] = "Saved!"
        print "Saved!"

    def hide(self):
        self.pauseScr.stash()
        self.loadScr.stash()
        self.saveScr.stash()
        self.dim.stash()

pauseScreen = PauseScreen()

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

base.accept('mouse1', handlePick)
base.accept('mouse3', handlePick, extraArgs=[True])
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