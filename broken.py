from typing import List, Optional, Dict
from decimal import Decimal
import networkx as nx
import pydot
import copy
import os
import sys


class CommunicationCoefficients:
    """
    CommunicationCoefficients helper class for extracting
    communication coefficients from a file and exposing
    helper functions to calculate latency.
    """

    def __init__(self):
        with open('communicationCoefficients', 'r') as file:
            for line in file:
                tokens: List[str] = line.split()
                self.slope: Decimal = Decimal(tokens[0])
                self.y_intercept: Decimal = Decimal(tokens[1])

    def latency(self, size: int) -> Decimal:
        return (size * self.slope) + self.y_intercept


class MessageID:
    """
    MessageID class represents a Message object.
    MessageID helper class to store message specifications extracted
    from the log file for an MPI node. Standardizes the creation of
    message signatures for matching message passing edges while
    constructing the networkx graph
    """

    def __init__(self, tokens: List[str], sender_id: int) -> None:
        self.sender_id: int = sender_id
        self.count: int = int(tokens[5])
        self.type_size: int = int(tokens[6])
        self.src: int = int(tokens[7])
        self.dst: int = int(tokens[8])
        self.tag: int = int(tokens[9])
        self.bytes: int = self.type_size * self.count
        self.id: str = self.update_id()

    def update_sender(self, sender_id) -> None:
        self.sender_id = sender_id
        self.id = self.update_id()

    def get_id(self) -> str:
        return self.id

    def update_id(self) -> str:
        return "_".join([str(self.sender_id), str(self.src), str(self.dst),
                        str(self.tag), str(self.type_size), str(self.count)])


class MPINode:
    """
    MPINode class represents an MPI Node object parsed from a log file
    and saved in the networkx graph.
    """

    def __init__(self, tokens: List[str], rank: int) -> None:
        self.command: str = tokens[0]
        self.call_id: int = int(tokens[1])
        self.meta_val: int = int(tokens[2])
        self.begin_time: Decimal = Decimal(tokens[3])
        self.end_time: Decimal = Decimal(tokens[4])
        self.rank: int = rank
        self.msg: Optional[MessageID] = None

    # get the label format representing the MPI node in the DOT file.
    def get_label(self) -> str:
        return "{}: {}".format(0 if self.rank == -1 else self.rank, self.command)

    # get the label format representing the MPI node in the critPath.out file.
    def get_crit_path_label(self) -> str:
        return "{} {}\n".format(self.command, self.rank)

    # update begin and end times for the current MPI node.
    def set_time(self, new: 'MPINode') -> None:
        self.begin_time = new.begin_time
        self.end_time = new.end_time


class GraphFactory:
    """
    GraphFactory helper class for constructing the MPI Task graph from a log file
    using networkx and pydot.
    """

    def __init__(self) -> None:
        # networkx graph representing the Task graph
        self.G: nx.MultiDiGraph = nx.MultiDiGraph()
        self.init_node: Optional[MPINode] = None
        self.final_node: Optional[MPINode] = None
        self.prev_node: Optional[MPINode] = None
        # A map indexing all collective nodes parsed ordered by invocation time.
        self.collective: Dict[str, Dict[int, MPINode]] = dict()
        # map of request pointers to Irecv/Isend/Wait for matching MPI_Wait
        self.non_blocking_requests: Dict[str, MPINode] = dict()
        # A map of sends, recv and wait nodes that need to be linked with nodes sharing unique message signatures.
        self.message_pass: Dict[str, MPINode] = dict()
        self.cc: CommunicationCoefficients = CommunicationCoefficients()

    # initialize the shared collective init MPI node.
    def handle_mpi_init(self, cur_node: MPINode) -> None:
        if self.init_node is None:
            cur_node.rank = self.get_collective_rank()
            self.init_node = cur_node
            self.G.add_node(self.init_node, label=self.init_node.get_label())
        self.prev_node = cur_node

    # initialize the shared collective finalize MPI node.
    def handle_finalize(self, cur_node: MPINode) -> None:
        if self.final_node is None:
            cur_node.rank = self.get_collective_rank()
            self.final_node = cur_node
            self.G.add_node(self.final_node, label=self.final_node.get_label())

    # handle tracking all collectives apart from finalize and init.
    def handle_collectives(self, cur_node: MPINode) -> MPINode:
        if cur_node.command in self.collective:
            if cur_node.meta_val in self.collective[cur_node.command]:
                self.collective[cur_node.command][cur_node.meta_val].set_time(cur_node)
                return self.collective[cur_node.command][cur_node.meta_val]
            else:
                cur_node.rank = self.get_collective_rank()
                self.collective[cur_node.command][cur_node.meta_val] = cur_node
        else:
            cur_node.rank = self.get_collective_rank()
            self.collective[cur_node.command] = dict({cur_node.meta_val: cur_node})
        return cur_node

    # track and create send message edges from Isend/send to Recv/Wait
    # when the current node is a node with the outgoing message edge.
    def handle_send(self, cur_node: MPINode, tokens: List[str]) -> None:
        cur_node.msg = MessageID(tokens, cur_node.call_id)
        if cur_node.msg.get_id() in self.message_pass:
            msg_latency: Decimal = self.cc.latency(cur_node.msg.bytes)
            self.G.add_edge(cur_node, self.message_pass[cur_node.msg.get_id()],
                            label="{:.3f} ({})".format(msg_latency, cur_node.msg.bytes),
                            weight=msg_latency, latency_edge=True)
        else:
            self.message_pass[cur_node.msg.get_id()] = cur_node

    # track and create send message edges from Isend/send to Recv/Wait
    # when the current node is a node with the incoming message edge.
    def handle_receive(self, cur_node: MPINode, tokens: List[str]) -> None:
        if cur_node.command == 'MPI_Wait':
            # get matching Irecv for the wait.
            cur_node.msg = self.non_blocking_requests[tokens[len(tokens) - 1]].msg
            cur_node.msg.update_sender(cur_node.meta_val)
        else:
            cur_node.msg = MessageID(tokens, cur_node.meta_val)
        if cur_node.msg.get_id() in self.message_pass:
            msg_latency: Decimal = self.cc.latency(cur_node.msg.bytes)
            self.G.add_edge(self.message_pass[cur_node.msg.get_id()], cur_node,
                            label="{:.3f} ({})".format(msg_latency, cur_node.msg.bytes),
                            weight=msg_latency, latency_edge=True)
        else:
            self.message_pass[cur_node.msg.get_id()] = cur_node

    # process a line of tokens read from the log file representing a node and add them to the networkx graph.
    def process_line(self, line: str, rank: int) -> None:
        tokens: List[str] = line.split()
        cur_node: MPINode = MPINode(tokens, rank)

        if cur_node.command == 'MPI_Init':
            self.handle_mpi_init(cur_node)
            return

        # get the elapsed time for the sequential task edge between the previous node and current node.
        elapsed_time: Decimal = cur_node.begin_time - self.prev_node.end_time

        if cur_node.command in ('MPI_Barrier', 'MPI_Alltoall', 'MPI_Allreduce'):
            cur_node = self.handle_collectives(cur_node)

        if cur_node.command == 'MPI_Finalize':
            self.handle_finalize(cur_node)
        else:
            self.G.add_node(cur_node, label=cur_node.get_label())

        # track request pointers of non blocking receives
        if cur_node.command == 'MPI_Irecv':
            # request pointer is always stored as the last token in the log.
            cur_node.msg = MessageID(tokens, cur_node.meta_val)
            self.non_blocking_requests[tokens[len(tokens)-1]] = cur_node

        # match Recv/Wait to send/Isend
        # Meta_val will be negative only for Waits that match to Isend. We can ignore these.
        if cur_node.command in ('MPI_Wait', 'MPI_Recv') and cur_node.meta_val >= 0:
            self.handle_receive(cur_node, tokens)

        # match send/Isend to Recv/Wait
        if cur_node.command in ('MPI_Send', 'MPI_Isend'):
            self.handle_send(cur_node, tokens)

        # add a sequential task edge from the previous MPI node to the current MPI node.
        self.G.add_edge(self.init_node if self.prev_node.command == 'MPI_Init' else self.prev_node,
                        self.final_node if cur_node.command == 'MPI_Finalize' else cur_node,
                        label="{:.3f}".format(elapsed_time),
                        weight=elapsed_time, latency_edge=False)
        self.prev_node = cur_node
        return

    # create a dot file for the networkx graph and generate a png file representing the dot file.
    def draw_dot(self) -> None:
        nx.drawing.nx_pydot.write_dot(self.G, os.getcwd() + '/dotOutput.gv')
        (graph, ) = pydot.graph_from_dot_file(os.getcwd() + '/dotOutput.gv')
        graph.write_png(os.getcwd() + '/dotOutput.png')

    # a class method to get the rank representing collective nodes.
    @classmethod
    def get_collective_rank(cls) -> int:
        return -1

    # find the edge with the maximum weight between the two vertex nodes node1 and node2.
    def find_max_edge(self, node1, node2) -> int:
        if len(self.G[node1][node2]) == 1:
            return 0
        max_val: Decimal = self.G[node1][node2][0]['weight']
        max_index: int = 0
        for i in range(len(self.G[node1][node2])):
            if self.G[node1][node2][i]['weight'] > max_val:
                max_val = self.G[node1][node2][i]['weight']
                max_index = i
        return max_index

    # marks the edges of the networkx graph that form the critical path as red and log them in a file.
    def mark_critical_path(self) -> None:
        critical_path = multigraph_dag_longest_path(self.G)
        with open("critPath.out", "w") as file:
            file.write(critical_path[0].get_crit_path_label())
            for i in range(len(critical_path)-1):
                self.G[critical_path[i]][critical_path[i+1]][0]['color'] = 'red'
                if self.G[critical_path[i]][critical_path[i + 1]][0]['latency_edge']:
                    file.write("{}\n".format(critical_path[i].msg.bytes))
                else:
                    file.write("{}\n".format(
                        round(Decimal(self.G[critical_path[i]][critical_path[i + 1]][0]['label']))))
                file.write(critical_path[i+1].get_crit_path_label())


def multigraph_dag_longest_path(G: nx.MultiDiGraph, weight='weight', default_weight=1):
    if not G:
        return []
    dist = {}  # stores {v : (length, u)}
    for v in nx.topological_sort(G):
        us = [(dist[u][0] + data[0].get(weight, default_weight), u)
              for u, data in G.pred[v].items()]
        # Use the best predecessor if there is one and its distance is
        # non-negative, otherwise terminate.
        maxu = max(us, key=lambda x: x[0]) if us else (0, v)
        dist[v] = maxu if maxu[0] >= 0 else (0, v)
    u = None
    v = max(dist, key=lambda x: dist[x][0])
    path = []
    while u != v:
        path.append(v)
        u = v
        v = dist[v][1]
    path.reverse()
    return path


# create a networkx graph for the given input log files and dump a critical path file and dot file.
def main() -> None:
    print("starting critical path analyzer...")
    process_count: int = int(sys.argv[1])
    g: GraphFactory = GraphFactory()
    for rank in range(process_count):
        with open('mpi_rank_' + str(rank) + '.txt', "r") as file:
            for line in file:
                g.process_line(line, rank)
    g.mark_critical_path()
    g.draw_dot()


if __name__ == "__main__":
    main()
