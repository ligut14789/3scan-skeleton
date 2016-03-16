import numpy as np
import networkx as nx
import itertools
import time

from skeleton.cliqueRemoving import removeCliqueEdges
from skeleton.networkxGraphFromarray import getNetworkxGraphFromarray
from skeleton.segmentLengths import _removeEdgesInVisitedPath


"""
    primarily written for netmets (comparison of 2 networks)
    Link to the software - http://stim.ee.uh.edu/resources/software/netmets/
    Number of edges in the network(n) – unsigned integer
    Number of points on the first edge e1(N)- unsigned integer
    Point1 – float 3
    PointN – float 3
    …. Number of points on the nth edge en
    Number of vertices in the network (m) – unsigned integer
    Position – float 3
    Number of edges attached to it – unsigned integer
    Edge id e1– unsigned integer
    Edge id en – unsigned integer

"""


def _getNetworkClass(imArray):
    """
       takes in a numpy array and convert it to a netowrk class
    """
    startt = time.time()
    if type(imArray) == np.ndarray:
        networkxGraph = getNetworkxGraphFromarray(imArray, True)  # converts array to a networkx graph(based on non zero coordinates and the adjacent nonzeros)
        networkxGraph = removeCliqueEdges(networkxGraph)  # remove cliques in the graph
    else:
        networkxGraph = imArray
    GraphList = nx.to_dict_of_lists(networkxGraph)  # convert the graph to a dictionary with keys as nodes and list of adjacent nodes as the values
    verticesSorted = list(GraphList.keys())  # list and sort the keys so they are geometrically in the same order when writing to an obj file as (l_prefix paths)
    verticesSorted.sort()
    mapping = {}  # initialize variables for writing string of vertex v followed by x, y, x coordinates in the obj file
    mappingReturn = {}
    #  for each of the sorted vertices
    for index, vertex in enumerate(verticesSorted):
        mapping[vertex] = index + 1  # a mapping to transform the vertices (x, y, z) to indexes (beginining with 1)
        mappingReturn[index + 1] = vertex
    networkGraphIntegerNodes = nx.relabel_nodes(networkxGraph, mapping, False)
    # line prefixes for the obj file
    disjointGraphs = list(nx.connected_component_subgraphs(networkGraphIntegerNodes))
    dictBranchPoints = {}
    Fibers = []
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
        degreeList = list(nodeDegreedict.values())
        endPointdegree = min(degreeList)
        branchPointdegree = max(degreeList)
        if endPointdegree == branchPointdegree and nx.is_biconnected(subGraphskeleton) and cycleCount != 0:
            """ if the maximum degree is equal to minimum degree it is a circle"""
            cycle = cycleList[0]
            cycle.append(cycle[0])
            _removeEdgesInVisitedPath(subGraphskeleton, cycle, 1)
        elif set(degreeList) == set((1, 2)) or set(degreeList) == {1}:
            """ each node is connected to one or two other nodes implies and there is a
            one branch point at a distance not equal to one it is a single dichotomous tree"""
            edges = subGraphskeleton.edges()
            subGraphskeleton.remove_edges_from(edges)
        else:
            "acyclic tree characteristics"""
            branchpoints = [k for (k, v) in nodeDegreedict.items() if v > 2]
            endpoints = [k for (k, v) in nodeDegreedict.items() if v == 1]
            branchpoints.sort()
            visitedSources = []
            listOfPerms = list(itertools.product(branchpoints, endpoints))
            for sourceOnTree, item in listOfPerms:
                if nx.has_path(subGraphskeleton, sourceOnTree, item) and sourceOnTree != item:
                    simplePaths = list(nx.all_simple_paths(subGraphskeleton, source=sourceOnTree, target=item))
                    for simplePath in simplePaths:
                        Fibers.append(simplePath)
                        fiberIndex = len(Fibers)
                        if sourceOnTree not in visitedSources:
                            "check if the same source has multiple segments, if it doesn't number of segments is 1"""
                            dictBranchPoints[sourceOnTree] = fiberIndex
                        else:
                            if type(dictBranchPoints[sourceOnTree]) is int:
                                fiberList = [dictBranchPoints[sourceOnTree]]
                            else:
                                fiberList = dictBranchPoints[sourceOnTree]
                            fiberList.append(fiberIndex)
                            dictBranchPoints[sourceOnTree] = fiberList
                        visitedSources.append(sourceOnTree)
                        _removeEdgesInVisitedPath(subGraphskeleton, simplePath, 0)
            if subGraphskeleton.number_of_edges() != 0:
                listOfPerms = list(itertools.permutations(branchpoints, 2))
                for sourceOnTree, item in listOfPerms:
                    if nx.has_path(subGraphskeleton, sourceOnTree, item) and sourceOnTree != item:
                        simplePaths = list(nx.all_simple_paths(subGraphskeleton, source=sourceOnTree, target=item))
                        for simplePath in simplePaths:
                            Fibers.append(simplePath)
                            fiberIndex = len(Fibers)
                            if sourceOnTree not in visitedSources:
                                "check if the same source has multiple segments, if it doesn't number of segments is 1"""
                                dictBranchPoints[sourceOnTree] = fiberIndex
                            else:
                                if type(dictBranchPoints[sourceOnTree]) is int:
                                    fiberList = [dictBranchPoints[sourceOnTree]]
                                else:
                                    fiberList = dictBranchPoints[sourceOnTree]
                                fiberList.append(fiberIndex)
                                dictBranchPoints[sourceOnTree] = fiberList
                            visitedSources.append(sourceOnTree)
                            _removeEdgesInVisitedPath(subGraphskeleton, simplePath, 0)
        assert subGraphskeleton.number_of_edges() == 0
    print("time taken to get network fibers info is %0.3f" % (time.time() - startt), "seconds")
    return Fibers, dictBranchPoints, mappingReturn


def getTextWrite(skeletonIm, pathToSave, aspectRatio=None):
    edge, vertices, mapping = _getNetworkClass(skeletonIm)
    f = open(pathToSave, 'w')
    numEdges = len(edge)
    f.write(str(numEdges) + "\n")
    strsEdges = []
    for pointsOnEdge in edge:
        numPointsOnFiber = len(pointsOnEdge)
        strsEdges.append(str(numPointsOnFiber) + "\n")
        for i in pointsOnEdge:
            if aspectRatio is not None:
                vertex = mapping[i]
                originalVertex = list(vertex)
                newVertex = [0] * len(vertex)
                newVertex[0] = originalVertex[0] * aspectRatio[0]; newVertex[1] = originalVertex[2] * aspectRatio[1]; newVertex[2] = originalVertex[1] * aspectRatio[2]; vertex = tuple(newVertex)
            strsEdges.append(" ".join(str(vertex[i - 2]) for i in range(0, len(vertex))) + "\n")  # add strings of vertices to obj file
    f.writelines(strsEdges)  # write strings to obj file
    numVertices = len(vertices)
    f.write(str(numVertices) + "\n")
    strsVertices = []
    for vertexId, edgeIDs in vertices.items():
        if aspectRatio is not None:
            vertex = mapping[vertexId]
            originalVertex = list(vertex)
            newVertex = [0] * len(vertex)
            newVertex[0] = originalVertex[0] * aspectRatio[0]; newVertex[1] = originalVertex[2] * aspectRatio[1]; newVertex[2] = originalVertex[1] * aspectRatio[2]; vertex = tuple(newVertex)
            strsVertices.append(" ".join(str(vertex[i - 2]) for i in range(0, len(vertex))) + "\n")  # add strings of vertices to obj file
        if type(edgeIDs) is int:
            strsVertices.append(str(1) + "\n")
            strsVertices.append(str(edgeIDs) + "\n")
        else:
            strsVertices.append(str(len(edgeIDs)) + "\n")
            for edgeID in edgeIDs:
                strsVertices.append(str(edgeID) + "\n")
    f.writelines(strsVertices)
    f.close()


def getTextRead(f):
    f = open(f, 'r')
    file_contents = [_ for _ in f]
    f.close()
    numEdges = int(file_contents[0])
    I = int(file_contents[1])
    count = 1; k = 2;
    edges = []; vertices = [];
    for i in range(0, numEdges):
        # pre allocate a position vector p with number of points3d on the edge p
        p = []
        # for each point on the nth edge
        for j in range(k, I + k):
            # split the points3d of floats with separator space and form a float3 position vector out of them
            temp = file_contents[j].replace('\n', '').split(' ')
            temp = [float(item) for item in temp]
            p.append(tuple(temp))
        count += len(p) + 1;  # increment count to point at the next edge in the network
        I = int(file_contents[count]);  # read in the points3d at the next edge and convert it to an integer
        k = count + 1;
        edges.append(p);  # push the edge into the network
    numVertices = int(file_contents[count]);  # this line in the text file gives the number of distinct vertices
    count = count + 1;  # this line of text file gives the first verrtex
    # push each vertex into Vertices
    for i in range(0, numVertices):
        temp = file_contents[count].replace('\n', '').split(' ')
        temp = [float(item) for item in temp]
        vertices.append(tuple(temp))
        count += int(file_contents[count + 1]) + 2;  # Skip number of edge ids + 2 to point to the next vertex
    return edges, vertices


if __name__ == '__main__':
    skeletonIm = np.load(input("please enter a path to your unit width voxelised skeleton"))
    aspectRatio = input("please enter resolution of a voxel in 3D with resolution in z followed by y and x")
    aspectRatio = [float(item) for item in aspectRatio.split(' ')]
    getTextWrite(skeletonIm, "netMetsnetwork.txt", aspectRatio)
