import numpy as np
import networkx as nx
import itertools

import time

from skeleton.cliqueRemoving import removeCliqueEdges
from skeleton.networkxGraphFromarray import getNetworkxGraphFromarray
from metrics.radiusOfNodes import getRadiusByPointsOnCenterline


"""
    write an array to a wavefront obj file - time takes upto 3 minutes for a 512 * 512 * 512 array,
    input array can be either 3D or 2D. Function needs to be called with an array you want to save
    as a .obj file and the location on obj file - primarily written for netmets (comparison of 2 networks)
    Link to the software - http://stim.ee.uh.edu/resources/software/netmets/
"""


def _removeEdgesInVisitedPath(subGraphskeleton, path, cycle):
    """
       given a visited path in variable path, the edges in the
       path are removed in the graph
       if cycle = 1 , the given path belongs to a cycle,
       so an additional edge is formed between the last and the
       first node to form a closed cycle/ path and is removed
    """
    shortestPathedges = []
    if cycle == 0:
        for index, item in enumerate(path):
            if index + 1 != len(path):
                shortestPathedges.append(tuple((item, path[index + 1])))
        subGraphskeleton.remove_edges_from(shortestPathedges)
    else:
        for index, item in enumerate(path):
            if index + 1 != len(path):
                shortestPathedges.append(tuple((item, path[index + 1])))
            else:
                item = path[0]
                shortestPathedges.append(tuple((item, path[-1])))
        subGraphskeleton.remove_edges_from(shortestPathedges)


def getObjWrite(imArray, pathTosave, aspectRatio=None):
    """
       takes in a numpy array and converts it to a obj file and writes it to pathTosave
    """
    startt = time.time()  # for calculating time taken to write to an obj file
    if type(imArray) == np.ndarray:
        networkxGraph = getNetworkxGraphFromarray(imArray)  # converts array to a networkx graph(based on non zero coordinates and the adjacent nonzeros)
        networkxGraph = removeCliqueEdges(networkxGraph)  # remove cliques in the graph
    else:
        networkxGraph = imArray
    objFile = open(pathTosave, "w")  # open a obj file in the given path
    GraphList = nx.to_dict_of_lists(networkxGraph)  # convert the graph to a dictionary with keys as nodes and list of adjacent nodes as the values
    verticesSorted = list(GraphList.keys())  # list and sort the keys so they are geometrically in the same order when writing to an obj file as (l_prefix paths)
    verticesSorted.sort()
    mapping = {}  # initialize variables for writing string of vertex v followed by x, y, x coordinates in the obj file
    #  for each of the sorted vertices
    strsVertices = []
    for index, vertex in enumerate(verticesSorted):
        mapping[vertex] = index + 1  # a mapping to transform the vertices (x, y, z) to indexes (beginining with 1)
        if aspectRatio is not None:
            originalVertex = list(vertex)
            newVertex = [0] * len(vertex)
            newVertex[0] = originalVertex[0] * aspectRatio[0]
            newVertex[1] = originalVertex[2] * aspectRatio[1]
            newVertex[2] = originalVertex[1] * aspectRatio[2]
            vertex = tuple(newVertex)
        strsVertices.append("v " + " ".join(str(vertex[i - 2]) for i in range(0, len(vertex))) + "\n")  # add strings of vertices to obj file
    objFile.writelines(strsVertices)  # write strings to obj file
    networkGraphIntegerNodes = nx.relabel_nodes(networkxGraph, mapping, False)
    strsSeq = []
    # line prefixes for the obj file
    disjointGraphs = list(nx.connected_component_subgraphs(networkGraphIntegerNodes))
    for ithDisjointgraph, subGraphskeleton in enumerate(disjointGraphs):
        nodes = subGraphskeleton.nodes()
        if len(nodes) == 1:
            continue
            """ if there are more than one nodes decide what kind of subgraph it is
                if it has cycles alone, or a straight line or a directed cyclic/acyclic graph"""
        nodes.sort()
        cycleList = nx.cycle_basis(subGraphskeleton)
        cycleCount = len(cycleList)
        nodeDegreedict = nx.degree(subGraphskeleton)
        degreeSet = set(list(nodeDegreedict.values()))
        if degreeSet == {2} and nx.is_biconnected(subGraphskeleton) and cycleCount == 1:
            cycle = cycleList[0]
            # branchAngledict[1, sourceOnCycle] = dirVec
            _removeEdgesInVisitedPath(subGraphskeleton, cycle, 1)
        elif degreeSet == set((1, 2)) or degreeSet == {1}:
            """ straight line or dichtonomous tree"""
            listOfPerms = list(itertools.combinations(nodes, 2))
            if type(nodes[0]) == int:
                modulus = [[start - end] for start, end in listOfPerms]
                dists = [abs(i[0]) for i in modulus]
            else:
                modulus = [[start[dim] - end[dim] for dim in range(0, 3)] for start, end in listOfPerms]
                dists = [sum(modulus[i][dim] * modulus[i][dim] for dim in range(0, 3)) for i in range(0, len(modulus))]
            if len(list(nx.articulation_points(subGraphskeleton))) == 1 and set(dists) != 1:
                """ each node is connected to one or two other nodes which are not a distance of 1 implies there is a
                    one branch point with two end points in a single dichotomous tree"""
                continue
            else:
                endpoints = [k for (k, v) in nodeDegreedict.items() if v == 1]
                sourceOnLine = endpoints[0]
                targetOnLine = endpoints[1]
                simplePaths = list(nx.all_simple_paths(subGraphskeleton, source=sourceOnLine, target=targetOnLine))
                simplePath = simplePaths[0]
                strsSeq.append("l " + " ".join(str(x) for x in simplePath) + "\n")
                edges = subGraphskeleton.edges()
                subGraphskeleton.remove_edges_from(edges)
        else:
            """ cyclic or acyclic tree """
            if len(cycleList) != 0:
                for nthcycle, cycle in enumerate(cycleList):
                    nodeDegreedictFilt = {key: value for key, value in nodeDegreedict.items() if key in cycle}
                    branchpoints = [k for (k, v) in nodeDegreedictFilt.items() if v != 2 and v != 1]
                    branchpoints.sort()
                    listOfPerms = list(itertools.combinations(branchpoints, 2))
                    for sourceOnTree, item in listOfPerms:
                        simplePaths = list(nx.all_simple_paths(subGraphskeleton, source=sourceOnTree, target=item))
                        for simplePath in simplePaths:
                            if nx.has_path(subGraphskeleton, sourceOnTree, item) and sourceOnTree != item:
                                if sum([1 for point in simplePath if point in branchpoints]) == 2:
                                    strsSeq.append("l " + " ".join(str(x) for x in simplePath) + "\n")
                                    _removeEdgesInVisitedPath(subGraphskeleton, simplePath, 0)
            branchpoints = [k for (k, v) in nodeDegreedict.items() if v != 2 and v != 1]
            endpoints = [k for (k, v) in nodeDegreedict.items() if v == 1]
            branchendpoints = branchpoints + endpoints
            branchpoints.sort()
            endpoints.sort()
            listOfPerms = list(itertools.product(branchpoints, endpoints))
            for sourceOnTree, item in listOfPerms:
                if nx.has_path(subGraphskeleton, sourceOnTree, item) and sourceOnTree != item:
                    simplePaths = list(nx.all_simple_paths(subGraphskeleton, source=sourceOnTree, target=item))
                    simplePath = simplePaths[0]
                    if sum([1 for point in simplePath if point in branchendpoints]) == 2:
                        strsSeq.append("l " + " ".join(str(x) for x in simplePath) + "\n")
                        _removeEdgesInVisitedPath(subGraphskeleton, simplePath, 0)
            if subGraphskeleton.number_of_edges() != 0:
                listOfPerms = list(itertools.combinations(branchpoints, 2))
                for sourceOnTree, item in listOfPerms:
                    if nx.has_path(subGraphskeleton, sourceOnTree, item) and sourceOnTree != item:
                        simplePaths = list(nx.all_simple_paths(subGraphskeleton, source=sourceOnTree, target=item))
                        simplePath = simplePaths[0]
                        if sum([1 for point in simplePath if point in branchpoints]) == 2:
                            strsSeq.append("l " + " ".join(str(x) for x in simplePath) + "\n")
                            _removeEdgesInVisitedPath(subGraphskeleton, simplePath, 0)
            cycleList = nx.cycle_basis(subGraphskeleton)
            if subGraphskeleton.number_of_edges() != 0 and len(cycleList) != 0:
                for cycle in cycleList:
                    strsSeq.append("l " + " ".join(str(x) for x in cycle) + "\n")
                    _removeEdgesInVisitedPath(subGraphskeleton, cycle, 1)
        # assert subGraphskeleton.number_of_edges() == 0
        assert subGraphskeleton.number_of_edges() == 0
    objFile.writelines(strsSeq)
    print("obj file write took %0.3f seconds" % (time.time() - startt))
    # Close opend file
    objFile.close()


def getObjWriteWithradius(imArray, pathTosave, dictOfNodesAndRadius, aspectRatio=None):
    """
       takes in a numpy array and converts it to a obj file and writes it to pathTosave
    """
    startt = time.time()  # for calculating time taken to write to an obj file
    if type(imArray) == np.ndarray:
        networkxGraph = getNetworkxGraphFromarray(imArray, True)  # converts array to a networkx graph(based on non zero coordinates and the adjacent nonzeros)
        networkxGraph = removeCliqueEdges(networkxGraph)  # remove cliques in the graph
    else:
        networkxGraph = imArray
    objFile = open(pathTosave, "w")  # open a obj file in the given path
    GraphList = nx.to_dict_of_lists(networkxGraph)  # convert the graph to a dictionary with keys as nodes and list of adjacent nodes as the values
    verticesSorted = list(GraphList.keys())  # list and sort the keys so they are geometrically in the same order when writing to an obj file as (l_prefix paths)
    verticesSorted.sort()
    mapping = {}  # initialize variables for writing string of vertex v followed by x, y, x coordinates in the obj file
    #  for each of the sorted vertices write both v and vy followed by radius
    strsVertices = [0] * (2 * len(verticesSorted))
    for index, vertex in enumerate(verticesSorted):
        mapping[vertex] = index + 1  # a mapping to transform the vertices (x, y, z) to indexes (beginining with 1)
        if aspectRatio is not None:
            originalVertex = list(vertex)
            newVertex = [0] * len(vertex)
            newVertex[0] = originalVertex[0] * aspectRatio[0]
            newVertex[1] = originalVertex[2] * aspectRatio[1]
            newVertex[2] = originalVertex[1] * aspectRatio[2]
            vertex = tuple(newVertex)
        strsVertices[index] = "v " + " ".join(str(vertex[i - 2]) for i in range(0, len(vertex))) + "\n"  # add strings of vertices to obj file
        strsVertices[index + len(verticesSorted)] = "vt " + " " + str(dictOfNodesAndRadius[vertex]) + "\n"
    objFile.writelines(strsVertices)  # write strings to obj file
    networkGraphIntegerNodes = nx.relabel_nodes(networkxGraph, mapping, False)
    strsSeq = []
    # line prefixes for the obj file
    disjointGraphs = list(nx.connected_component_subgraphs(networkGraphIntegerNodes))
    for ithDisjointgraph, subGraphskeleton in enumerate(disjointGraphs):
        nodes = subGraphskeleton.nodes()
        if len(nodes) == 1:
            continue
        """ if there are more than one nodes decide what kind of subgraph it is
            if it has cycles alone, or is a cyclic graph with a tree or an
            acyclic graph with tree """
        nodes.sort()
        cycleList = nx.cycle_basis(subGraphskeleton)
        cycleCount = len(cycleList)
        nodeDegreedict = nx.degree(subGraphskeleton)
        degreeSet = set(list(nodeDegreedict.values()))
        if degreeSet == {2} and nx.is_biconnected(subGraphskeleton) and cycleCount == 1:
            cycle = cycleList[0]
            _removeEdgesInVisitedPath(subGraphskeleton, cycle, 1)
        elif degreeSet == set((1, 2)) or degreeSet == {1}:
            """ straight line or dichtonomous tree"""
            listOfPerms = list(itertools.combinations(nodes, 2))
            if type(nodes[0]) == int:
                modulus = [[start - end] for start, end in listOfPerms]
                dists = [abs(i[0]) for i in modulus]
            else:
                modulus = [[start[dim] - end[dim] for dim in range(0, 3)] for start, end in listOfPerms]
                dists = [sum(modulus[i][dim] * modulus[i][dim] for dim in range(0, 3)) for i in range(0, len(modulus))]
            if len(list(nx.articulation_points(subGraphskeleton))) == 1 and set(dists) != 1:
                """ each node is connected to one or two other nodes which are not a distance of 1 implies there is a
                    one branch point with two end points in a single dichotomous tree"""
                continue
            else:
                endpoints = [k for (k, v) in nodeDegreedict.items() if v == 1]
                sourceOnLine = endpoints[0]
                targetOnLine = endpoints[1]
                simplePaths = list(nx.all_simple_paths(subGraphskeleton, source=sourceOnLine, target=targetOnLine))
                simplePath = simplePaths[0]
                strsSeq.append("l " + " ".join(str(x) for x in simplePath) + "\n")
                edges = subGraphskeleton.edges()
                subGraphskeleton.remove_edges_from(edges)
        else:
            """ cyclic or acyclic tree """
            if len(cycleList) != 0:
                for nthcycle, cycle in enumerate(cycleList):
                    nodeDegreedictFilt = {key: value for key, value in nodeDegreedict.items() if key in cycle}
                    branchpoints = [k for (k, v) in nodeDegreedictFilt.items() if v != 2 and v != 1]
                    branchpoints.sort()
                    listOfPerms = list(itertools.combinations(branchpoints, 2))
                    for sourceOnTree, item in listOfPerms:
                        simplePaths = list(nx.all_simple_paths(subGraphskeleton, source=sourceOnTree, target=item))
                        for simplePath in simplePaths:
                            if nx.has_path(subGraphskeleton, sourceOnTree, item) and sourceOnTree != item:
                                if sum([1 for point in simplePath if point in branchpoints]) == 2:
                                    strsSeq.append("l " + " ".join(str(x) for x in simplePath) + "\n")
                                    _removeEdgesInVisitedPath(subGraphskeleton, simplePath, 0)
            branchpoints = [k for (k, v) in nodeDegreedict.items() if v != 2 and v != 1]
            endpoints = [k for (k, v) in nodeDegreedict.items() if v == 1]
            branchendpoints = branchpoints + endpoints
            branchpoints.sort()
            endpoints.sort()
            listOfPerms = list(itertools.product(branchpoints, endpoints))
            for sourceOnTree, item in listOfPerms:
                if nx.has_path(subGraphskeleton, sourceOnTree, item) and sourceOnTree != item:
                    simplePaths = list(nx.all_simple_paths(subGraphskeleton, source=sourceOnTree, target=item))
                    simplePath = simplePaths[0]
                    if sum([1 for point in simplePath if point in branchendpoints]) == 2:
                        strsSeq.append("l " + " ".join(str(x) for x in simplePath) + "\n")
                        _removeEdgesInVisitedPath(subGraphskeleton, simplePath, 0)
            if subGraphskeleton.number_of_edges() != 0:
                listOfPerms = list(itertools.combinations(branchpoints, 2))
                for sourceOnTree, item in listOfPerms:
                    if nx.has_path(subGraphskeleton, sourceOnTree, item) and sourceOnTree != item:
                        simplePaths = list(nx.all_simple_paths(subGraphskeleton, source=sourceOnTree, target=item))
                        simplePath = simplePaths[0]
                        if sum([1 for point in simplePath if point in branchpoints]) == 2:
                            strsSeq.append("l " + " ".join(str(x) for x in simplePath) + "\n")
                            _removeEdgesInVisitedPath(subGraphskeleton, simplePath, 0)
            cycleList = nx.cycle_basis(subGraphskeleton)
            if subGraphskeleton.number_of_edges() != 0 and len(cycleList) != 0:
                for cycle in cycleList:
                    strsSeq.append("l " + " ".join(str(x) for x in cycle) + "\n")
                    _removeEdgesInVisitedPath(subGraphskeleton, cycle, 1)
        # assert subGraphskeleton.number_of_edges() == 0
        assert subGraphskeleton.number_of_edges() == 0
    objFile.writelines(strsSeq)
    print("obj file write took %0.3f seconds" % (time.time() - startt))
    # Close opend file
    objFile.close()


def getObjBranchPointsWrite(imArray, pathTosave):
    """
       takes in a numpy array and converts it to a obj file and writes it to pathTosave
    """
    if type(imArray) == np.ndarray:
        networkxGraph = getNetworkxGraphFromarray(imArray)  # converts array to a networkx graph(based on non zero coordinates and the adjacent nonzeros)
        networkxGraph = removeCliqueEdges(networkxGraph)  # remove cliques in the graph
    else:
        networkxGraph = imArray
    objFile = open(pathTosave, "w")  # open a obj file in the given path
    nodeDegreedict = nx.degree(networkxGraph)
    branchpoints = [k for (k, v) in nodeDegreedict.items() if v != 2 and v != 1]
    #  for each of the sorted vertices
    strsVertices = []
    for index, vertex in enumerate(branchpoints):
        strsVertices.append("v " + " ".join(str(vertex[i]) for i in [1, 0, 2]) + "\n")  # add strings of vertices to obj file
    objFile.writelines(strsVertices)  # write strings to obj file
    objFile.close()


def getObjPointsWrite(imArray, pathTosave):
    """
       takes in a numpy array and converts it to a obj file and writes it to pathTosave
    """
    if type(imArray) == np.ndarray:
        networkxGraph = getNetworkxGraphFromarray(imArray)  # converts array to a networkx graph(based on non zero coordinates and the adjacent nonzeros)
        networkxGraph = removeCliqueEdges(networkxGraph)  # remove cliques in the graph
    else:
        networkxGraph = imArray
    objFile = open(pathTosave, "w")  # open a obj file in the given path
    nodes = nx.nodes(networkxGraph)
    strsVertices = []
    for index, vertex in enumerate(nodes):
        strsVertices.append("v " + " ".join(str(vertex[i]) for i in [1, 0, 2]) + "\n")  # add strings of vertices to obj file
    objFile.writelines(strsVertices)  # write strings to obj file
    objFile.close()


if __name__ == '__main__':
    # read points into array
    skeletonIm = np.load(input("enter a path to shortest path skeleton volume------"))
    boundaryIm = np.load(input("enter a path to boundary of thresholded volume------"))
    aspectRatio = input("please enter resolution of a voxel in 3D with resolution in z followed by y and x")
    aspectRatio = [float(item) for item in aspectRatio.split(' ')]
    path = input("please enter a path to save resultant obj file with no texture coordinates")
    path2 = input("please enter a path to save resultant obj file with texture coordinates")
    dictOfNodesAndRadius, distTransformedIm = getRadiusByPointsOnCenterline(skeletonIm, boundaryIm)
    getObjWrite(skeletonIm, path, aspectRatio)
    getObjWriteWithradius(skeletonIm, path2, aspectRatio)