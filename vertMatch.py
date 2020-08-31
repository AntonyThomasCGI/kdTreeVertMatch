# ----------------------------------------------------------------------------------------------------------------------
"""

	VERTMATCH.PY
	Match vertices from one mesh to another to the closest vertex using a k-d tree algorithm.

	Written by Antony Thomas
	antony@thomas-cgi.com

"""
# ----------------------------------------------------------------------------------------------------------------------

from maya.api import OpenMaya as om2
import sys


def buildKdTree(points, depth=0):
	n = len(points)

	if n <= 0:
		return None

	# split tree based on this axis
	axis = depth % 3

	sorted_points = sorted(points, key=lambda point: point[axis])

	return {
		'point': sorted_points[n / 2],
		'negative': buildKdTree(sorted_points[:n / 2], depth + 1),
		'positive': buildKdTree(sorted_points[n / 2 + 1:], depth + 1)
	}
# end def buildKdTree():


def distanceSquare(point1, point2):
	local_p = point1 - point2
	return local_p[0] * local_p[0] + local_p[1] * local_p[1] + local_p[2] * local_p[2]
# end def distanceSquare():


def closerDistance(pivot, p1, p2):
	if p1 is None:
		return p2

	if p2 is None:
		return p1

	d1 = distanceSquare(pivot, p1)
	d2 = distanceSquare(pivot, p2)

	if d1 < d2:
		return p1
	else:
		return p2
# end def closerDistance():


def nearestNeighbor(tree, in_point, depth=0):
	if tree is None:
		return None

	axis = depth % 3

	if in_point[axis] < tree['point'][axis]:
		next_branch = tree['negative']
		opposite_branch = tree['positive']
	else:
		next_branch = tree['positive']
		opposite_branch = tree['negative']

	nearest = closerDistance(in_point, nearestNeighbor(next_branch, in_point, depth + 1), tree['point'])

	if distanceSquare(in_point, nearest) > (in_point[axis] - tree['point'][axis]) ** 2:
		nearest = closerDistance(in_point, nearestNeighbor(opposite_branch, in_point, depth + 1), nearest)

	return nearest
# end def nearestNeighbor():


def maya_useNewAPI():
	pass
# end def maya_useNewAPI():


# plugin meat and potatoes
class vertMatch(om2.MPxCommand):

	kPluginCmdName = "vertMatch"
	mirrorFlag = '-m'
	mirrorFlagLong = '-mirror'

	def __init__(self):
		om2.MPxCommand.__init__(self)

		self.iter_components = None
		self.mirror = 0
		self.initialState = []
	# end def __init__():

	@staticmethod
	def cmdCreator():
		return vertMatch()
	# end def cmdCreator():

	@staticmethod
	def createSyntax():
		syntax = om2.MSyntax()

		syntax.addFlag(vertMatch.mirrorFlag, vertMatch.mirrorFlagLong, om2.MSyntax.kBoolean)

		return syntax
	# end def createSyntax():

	def doIt(self, args):
		sel = om2.MGlobal.getActiveSelectionList()
		self.iter_components = om2.MItSelectionList(sel)

		argDb = om2.MArgDatabase(self.syntax(), args)

		if argDb.isFlagSet(vertMatch.mirrorFlag):
			self.mirror = argDb.flagArgumentBool(vertMatch.mirrorFlag, 0)

		self.redoIt()
	# end def doIt():

	def isUndoable(self):
		return True
	# end def isUndoable():

	def undoIt(self):
		self.iter_components.reset()
		MDagMesh, MObComponent = self.iter_components.getComponent()
		iter_undo = om2.MItMeshVertex(MDagMesh, MObComponent)

		i = 0
		while not iter_undo.isDone():
			iter_undo.setPosition(self.initialState[i], om2.MSpace.kWorld)

			i += 1
			iter_undo.next()
	# end def undoIt():

	def redoIt(self):
		first_iteration = True
		tree_ls = []
		while not self.iter_components.isDone():
			# First iteration is input points, so skip unless mirror flag is True then reverse the x-axis.
			if first_iteration:
				if self.mirror:
					MDagMesh, MObComponent = self.iter_components.getComponent()
					iter_mirror = om2.MItMeshVertex(MDagMesh, MObComponent)

					while not iter_mirror.isDone():
						point = iter_mirror.position(om2.MSpace.kWorld)
						point[0] *= -1
						tree_ls.append(point)
						iter_mirror.next()

				self.iter_components.next()
				first_iteration = False
				continue

			MDagMesh, MObComponent = self.iter_components.getComponent()
			iter_vert = om2.MItMeshVertex(MDagMesh, MObComponent)

			while not iter_vert.isDone():
				tree_ls.append(iter_vert.position(om2.MSpace.kWorld))
				iter_vert.next()

			self.iter_components.next()

		vert_tree = buildKdTree(tree_ls)

		self.iter_components.reset()
		MDagMesh, MObComponent = self.iter_components.getComponent()
		iter_input = om2.MItMeshVertex(MDagMesh, MObComponent)

		while not iter_input.isDone():
			input_point = iter_input.position(om2.MSpace.kWorld)
			# save for undo
			self.initialState.append(input_point)

			if self.mirror:
				if input_point[0] >= 0:
					iter_input.next()
					continue

			closest = nearestNeighbor(vert_tree, input_point)
			iter_input.setPosition(closest, om2.MSpace.kWorld)

			iter_input.next()
	# end def redoIt():


def initializePlugin(plugin):
	pluginFn = om2.MFnPlugin(plugin)
	try:
		pluginFn.registerCommand(
			vertMatch.kPluginCmdName, vertMatch.cmdCreator, vertMatch.createSyntax)
	except:
		sys.stderr.write(
			"Failed to register command: %s\n" % vertMatch.kPluginCmdName
		)
		raise
# end def initializePlugin():


def uninitializePlugin(plugin):
	pluginFn = om2.MFnPlugin(plugin)
	try:
		pluginFn.deregisterCommand(vertMatch.kPluginCmdName)
	except:
		sys.stderr.write(
			"Failed to unregister command: %s\n" % vertMatch.kPluginCmdName
		)
		raise
# end def uninitializePlugin():
