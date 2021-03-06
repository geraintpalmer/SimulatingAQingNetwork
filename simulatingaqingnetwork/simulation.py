from __future__ import division
from random import random, seed, expovariate, uniform, triangular, gammavariate, gauss, lognormvariate, weibullvariate
from datetime import datetime
import os
from csv import writer
import yaml
import shutil
import networkx as nx


class DataRecord:
    """
    A class for a data record
    """
    def __init__(self, arrival_date, service_time, service_start_date, exit_date, node):
        """
        An example of a data record instance.
            >>> r = DataRecord(2, 3, 2, 8, 1)
            >>> r.arrival_date
            2
            >>> r.wait
            0
            >>> r.service_start_date
            2
            >>> r.service_time
            3
            >>> r.service_end_date
            5
            >>> r.blocked
            3
            >>> r.exit_date
            8
            >>> r.node
            1

        Another example of a data record instance.
            >>> r = DataRecord(5.7, 2.1, 8.2, 10.3, 1)
            >>> r.arrival_date
            5.7
            >>> round(r.wait, 5)
            2.5
            >>> r.service_start_date
            8.2
            >>> r.service_time
            2.1
            >>> round(r.service_end_date, 5)
            10.3
            >>> round(r.blocked, 5)
            0.0
            >>> r.exit_date
            10.3
            >>> r.node
            1
        """
        if exit_date < arrival_date:
            raise ValueError('Arrival date should preceed exit date')

        if service_time < 0:
            raise ValueError('Service time should be positive')

        self.arrival_date = arrival_date
        self.service_time = service_time
        self.service_start_date = service_start_date
        self.exit_date = exit_date

        self.service_end_date = service_start_date + service_time
        self.wait = service_start_date - arrival_date
        self.blocked = exit_date - self.service_end_date
        self.node = node


class Individual:
    """
    Class for an individual
    """
    def __init__(self, id_number, customer_class=0):
        """
        Initialise an individual

        An example of an Individual instance.
            >>> i = Individual(22, 3)
            >>> i.arrival_date
            False
            >>> i.service_start_date
            False
            >>> i.service_time
            False
            >>> i.service_end_date
            False
            >>> i.id_number
            22
            >>> i.data_records
            {}
            >>> i.customer_class
            3

        Another example of an individual instance.
            >>> i = Individual(5)
            >>> i.arrival_date
            False
            >>> i.service_start_date
            False
            >>> i.service_time
            False
            >>> i.service_end_date
            False
            >>> i.id_number
            5
            >>> i.data_records
            {}
            >>> i.customer_class
            0
        """
        self.arrival_date = False
        self.service_start_date = False
        self.service_time = False
        self.service_end_date = False
        self.exit_date = False
        self.id_number = id_number
        self.data_records = {}
        self.customer_class = customer_class
        self.is_blocked = False
        self.server = False

    def __repr__(self):
        """
        Represents an Individual instance as a string

        An example of how an intance in represented.
            >>> i = Individual(3, 6)
            >>> i
            Individual 3

        Another example of how an individual is represented.
            >>> i = Individual(93, 2)
            >>> i
            Individual 93

        Although individuals should be represented by unique integers, they can be called anything.
            >>> i = Individual('twelve', 2)
            >>> i
            Individual twelve
        """
        return 'Individual %s' % self.id_number

class Server:
    """
    A class to contain server information
    """
    def __init__(self, node, id_number):
        """
        Initialise the server object
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = Q.transitive_nodes[0] 
            >>> S = Server(N, 1)
            >>> S.node.id_number
            1
            >>> S.id_number
            1
        """
        self.node = node
        self.id_number = id_number
        self.cust = False
        self.busy = False

    def __repr__(self):
        """
        Represents the Server instance as a string

            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = Q.transitive_nodes[0] 
            >>> S = Server(N, 1)
            >>> S
            Server 1 at Node 1

        """
        return 'Server %s at Node %s' % (self.id_number, self.node.id_number)


class Node:
    """
    Class for a node on our network
    """
    def __init__(self, id_number, simulation):
        """
        Initialise a node.

        An example of initialising a node.
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = Node(1, Q)
            >>> N.mu
            [['Exponential', 7.0], ['Exponential', 7.0], ['Deterministic', 0.3]]
            >>> N.c
            9
            >>> N.transition_row
            [[0.1, 0.2, 0.1, 0.4], [0.6, 0.0, 0.0, 0.2], [0.0, 0.0, 0.4, 0.3]]
            >>> N.next_event_date
            'Inf'
            >>> N.individuals
            []
            >>> N.id_number
            1
            >>> N.cum_transition_row
            [[0.1, 0.30000000000000004, 0.4, 0.8], [0.6, 0.6, 0.6, 0.8], [0.0, 0.0, 0.4, 0.7]]
        """

        self.simulation = simulation
        self.mu = [self.simulation.mu[cls][id_number-1] for cls in range(len(self.simulation.mu))]
        self.c = self.simulation.c[id_number-1]
        self.servers = [Server(self, i+1) for i in range(self.c)]
        self.node_capacity = "Inf" if self.simulation.queue_capacities[id_number-1] == "Inf" else self.simulation.queue_capacities[id_number-1] + self.c
        self.transition_row = [self.simulation.transition_matrix[j][id_number-1] for j in range(len(self.simulation.transition_matrix))]
        self.individuals = []
        self.id_number = id_number
        self.cum_transition_row = self.find_cum_transition_row()
        self.next_event_date = "Inf"
        self.blocked_queue = []
        self.simulation.digraph.add_nodes_from([str(s) for s in self.servers])

    def find_cum_transition_row(self):
        """
        Finds the cumulative transition row for the node

        An exmaple of finding the cumulative transition row of a node.
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = Node(1, Q)
            >>> N.cum_transition_row
            [[0.1, 0.30000000000000004, 0.4, 0.8], [0.6, 0.6, 0.6, 0.8], [0.0, 0.0, 0.4, 0.7]]
        """

        cum_transition_row = []
        for cls in range(len(self.transition_row)):
            sum_p = 0
            cum_transition_row.append([])
            for p in self.transition_row[cls]:
                sum_p += p
                cum_transition_row[cls].append(sum_p)
        return cum_transition_row

    def __repr__(self):
        """
        Representation of a node::

        An example of how a node is represented.
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = Node(1, Q)
            >>> N
            Node 1

        A node cannot exist without a simulation.
            >>> N = Node(2, False)
            Traceback (most recent call last):
            ...
            AttributeError: 'bool' object has no attribute 'mu'
        """
        return 'Node %s' % self.id_number

    def attach_server(self, server, individual):
        """
        Attaches a server to an individual, and vice versa
        """
        server.cust = individual
        server.busy = True
        individual.server = server

        for blq in self.blocked_queue:
            inds = [ind for ind in self.simulation.nodes[blq[0]].individuals if ind.id_number==blq[1]]
            ind = inds[0]
            if ind != individual:
                self.simulation.digraph.add_edge(str(ind.server), str(server))


    def detatch_server(self, server, individual):
        """
        Detatches a server from an individual, and vice versa
        """
        server.cust = False
        server.busy = False
        individual.server = False

        self.simulation.digraph.remove_edges_from(self.simulation.digraph.in_edges(str(server)) + self.simulation.digraph.out_edges(str(server)))

    def have_event(self):
        """
        Has an event
        """
        self.finish_service()

    def finish_service(self):
        """
        The next individual finishes service

            >>> seed(4)
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = Q.transitive_nodes[0]
            >>> inds = [Individual(i+1) for i in range(3)]
            >>> for current_time in [0.01, 0.02, 0.03]:
            ...     N.accept(inds[int(current_time*100 - 1)], current_time)
            >>> N.individuals
            [Individual 1, Individual 2, Individual 3]
            >>> N.update_next_event_date(0.03)
            >>> round(N.next_event_date, 5)
            0.03555
            >>> N.finish_service()
            >>> N.individuals
            [Individual 1, Individual 3]
        """
        next_individual_index = [ind.service_end_date for ind in self.individuals[:self.c]].index(self.next_event_date)
        next_individual = self.individuals[next_individual_index]
        next_node = self.next_node(next_individual.customer_class)

        if len(next_node.individuals) < next_node.node_capacity:
            self.release(next_individual_index, next_node, self.next_event_date)
        else:
            self.block_individual(next_individual, next_node)

    def block_individual(self, individual, next_node):
        """
        Blocks the individual from entering the next node

            >>> seed(4)
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> inds = [Individual(i+1) for i in range(7)]
            >>> N1 = Q.transitive_nodes[2]
            >>> N1.individuals = inds[:6]
            >>> N2 = Q.transitive_nodes[3]
            >>> N2.accept(inds[6], 2)
            >>> inds[6].is_blocked
            False
            >>> N1.blocked_queue
            []
            >>> Q.digraph.edges()
            []
            >>> N2.block_individual(inds[6], N1)
            >>> inds[6].is_blocked
            True
            >>> N1.blocked_queue
            [(4, 7)]
            >>> Q.digraph.edges()
            [('Server 1 at Node 4', 'Server 8 at Node 3'), ('Server 1 at Node 4', 'Server 7 at Node 3'), ('Server 1 at Node 4', 'Server 5 at Node 3'), ('Server 1 at Node 4', 'Server 1 at Node 3'), ('Server 1 at Node 4', 'Server 2 at Node 3'), ('Server 1 at Node 4', 'Server 4 at Node 3'), ('Server 1 at Node 4', 'Server 3 at Node 3'), ('Server 1 at Node 4', 'Server 6 at Node 3')]
        """
        individual.is_blocked = True
        self.change_state_block()
        next_node.blocked_queue.append((self.id_number, individual.id_number))

        for svr in next_node.servers:
            self.simulation.digraph.add_edge(str(individual.server), str(svr))


    def release(self, next_individual_index, next_node, current_time):
        """
        Update node when an individual is released.

            >>> seed(4)
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = Q.transitive_nodes[0]
            >>> inds = [Individual(i+1) for i in range(3)]
            >>> for current_time in [0.01, 0.02, 0.03]:
            ...     N.accept(inds[int(current_time*100 - 1)], current_time)
            >>> N.individuals
            [Individual 1, Individual 2, Individual 3]
            >>> N.update_next_event_date(0.03)
            >>> round(N.next_event_date, 5)
            0.03555
            >>> N.individuals[1].exit_date = 0.04 #shouldn't affect the next event date
            >>> N.update_next_event_date(N.next_event_date)
            >>> round(N.next_event_date, 5)
            0.04846
            >>> N.release(1, Q.transitive_nodes[1], N.next_event_date)
            >>> N.individuals
            [Individual 1, Individual 3]
            >>> N.update_next_event_date(N.next_event_date)
            >>> round(N.next_event_date, 5)
            0.10204
        """
        next_individual = self.individuals.pop(next_individual_index)
        next_individual.exit_date = current_time
        self.detatch_server(next_individual.server, next_individual)
        self.write_individual_record(next_individual)
        self.change_state_release(next_individual)
        self.release_blocked_individual(current_time)
        self.begin_service_if_possible_release(current_time)
        next_node.accept(next_individual, current_time)

    def begin_service_if_possible_release(self, current_time):
        """
        Begins the service of the next individual, giving that customer a service time, end date and node

            >>> seed(50)
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> inds = [Individual(i) for i in range(30)]
            >>> Q.transitive_nodes[0].individuals = inds
            >>> ind = Q.transitive_nodes[0].individuals[Q.transitive_nodes[0].c - 1]
            >>> ind.service_time = 3.14
            >>> ind.arrival_date = 100.0
            >>> Q.digraph.nodes()
            ['Server 8 at Node 2', 'Server 8 at Node 3', 'Server 8 at Node 1', 'Server 8 at Node 4', 'Server 2 at Node 4', 'Server 3 at Node 4', 'Server 4 at Node 4', 'Server 6 at Node 4', 'Server 4 at Node 2', 'Server 6 at Node 1', 'Server 6 at Node 2', 'Server 4 at Node 3', 'Server 9 at Node 1', 'Server 5 at Node 3', 'Server 5 at Node 2', 'Server 5 at Node 1', 'Server 4 at Node 1', 'Server 5 at Node 4', 'Server 7 at Node 1', 'Server 7 at Node 3', 'Server 7 at Node 2', 'Server 7 at Node 4', 'Server 1 at Node 4', 'Server 1 at Node 3', 'Server 1 at Node 2', 'Server 1 at Node 1', 'Server 2 at Node 1', 'Server 2 at Node 2', 'Server 2 at Node 3', 'Server 3 at Node 1', 'Server 9 at Node 2', 'Server 3 at Node 3', 'Server 3 at Node 2', 'Server 6 at Node 3', 'Server 10 at Node 2']
            >>> ind.arrival_date
            100.0
            >>> ind.service_time
            3.14
            >>> ind.service_start_date
            False
            >>> ind.service_end_date
            False
            >>> Q.transitive_nodes[0].begin_service_if_possible_release(200.0)
            >>> ind.arrival_date
            100.0
            >>> round(ind.service_time,5)
            3.14
            >>> ind.service_start_date
            200.0
            >>> round(ind.service_end_date,5)
            203.14

        """
        if len(self.individuals) >= self.c:
            for ind in self.individuals[:self.c]:
                if not ind.server:
                    self.attach_server(self.find_free_server(), ind)
                    ind.service_start_date = current_time
                    ind.service_end_date = ind.service_start_date + ind.service_time


    def release_blocked_individual(self, current_time):
        """
        Releases an individual who becomes unblocked when another individual is released

            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N1 = Q.transitive_nodes[0]
            >>> N2 = Q.transitive_nodes[1]
            >>> N1.individuals = [Individual(i) for i in range(N1.c + 3)]
            >>> N2.individuals = [Individual(i + 100) for i in range(N2.c + 4)]

            >>> for ind in N1.individuals[:9]:
            ...     N1.attach_server(N1.find_free_server(), ind)
            >>> for ind in N2.individuals[:10]:
            ...     N2.attach_server(N2.find_free_server(), ind)

            >>> N1.individuals
            [Individual 0, Individual 1, Individual 2, Individual 3, Individual 4, Individual 5, Individual 6, Individual 7, Individual 8, Individual 9, Individual 10, Individual 11]
            >>> N2.individuals
            [Individual 100, Individual 101, Individual 102, Individual 103, Individual 104, Individual 105, Individual 106, Individual 107, Individual 108, Individual 109, Individual 110, Individual 111, Individual 112, Individual 113]
            >>> N1.release_blocked_individual(100)
            >>> N1.individuals
            [Individual 0, Individual 1, Individual 2, Individual 3, Individual 4, Individual 5, Individual 6, Individual 7, Individual 8, Individual 9, Individual 10, Individual 11]
            >>> N2.individuals
            [Individual 100, Individual 101, Individual 102, Individual 103, Individual 104, Individual 105, Individual 106, Individual 107, Individual 108, Individual 109, Individual 110, Individual 111, Individual 112, Individual 113]

            >>> N1.blocked_queue = [(1, 1), (2, 100)]
            >>> rel_ind = N1.individuals.pop(0)
            >>> N1.detatch_server(rel_ind.server, rel_ind)

            >>> N1.release_blocked_individual(110)
            >>> N1.individuals
            [Individual 2, Individual 3, Individual 4, Individual 5, Individual 6, Individual 7, Individual 8, Individual 9, Individual 10, Individual 11, Individual 100, Individual 1]
            >>> N2.individuals
            [Individual 101, Individual 102, Individual 103, Individual 104, Individual 105, Individual 106, Individual 107, Individual 108, Individual 109, Individual 110, Individual 111, Individual 112, Individual 113]

        """
        if len(self.blocked_queue) > 0:
            node_to_receive_from = self.simulation.nodes[self.blocked_queue[0][0]]
            individual_to_receive_index = [ind.id_number for ind in node_to_receive_from.individuals].index(self.blocked_queue[0][1])
            individual_to_receive = node_to_receive_from.individuals[individual_to_receive_index]
            self.blocked_queue.pop(0)
            node_to_receive_from.release(individual_to_receive_index, self, current_time)

    def change_state_release(self, next_individual):
        """
        Changes the state of the system when a customer gets blocked

            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> Q.state = [[0, 0], [0, 0], [2, 1], [0, 0]]
            >>> N = Q.transitive_nodes[2]
            >>> inds = [Individual(i) for i in range(3)]
            >>> N.individuals = inds
            >>> N.change_state_release(inds[0])
            >>> Q.state
            [[0, 0], [0, 0], [1, 1], [0, 0]]
            >>> inds[1].is_blocked = True
            >>> N.change_state_release(inds[1])
            >>> Q.state
            [[0, 0], [0, 0], [1, 0], [0, 0]]

        """
        if next_individual.is_blocked:
            self.simulation.state[self.id_number-1][1] -= 1
        else:
            self.simulation.state[self.id_number-1][0] -= 1

    def change_state_block(self):
        """
        Changes the state of the system when a customer gets blocked

            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> Q.state = [[0, 0], [0, 0], [2, 1], [0, 0]]
            >>> N = Q.transitive_nodes[2]
            >>> N.change_state_block()
            >>> Q.state
            [[0, 0], [0, 0], [1, 2], [0, 0]]
            >>> N.change_state_block()
            >>> Q.state
            [[0, 0], [0, 0], [0, 3], [0, 0]]

        """
        self.simulation.state[self.id_number-1][1] += 1
        self.simulation.state[self.id_number-1][0] -= 1

    def change_state_accept(self):
        """
        Changes the state of the system when a customer gets blocked

            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> Q.state = [[0, 0], [0, 0], [2, 1], [0, 0]]
            >>> N = Q.transitive_nodes[2]
            >>> N.change_state_accept()
            >>> Q.state
            [[0, 0], [0, 0], [3, 1], [0, 0]]
            >>> N.change_state_accept()
            >>> Q.state
            [[0, 0], [0, 0], [4, 1], [0, 0]]

        """
        self.simulation.state[self.id_number-1][0] += 1

    def accept(self, next_individual, current_time):
        """
        Accepts a new customer to the queue

            >>> seed(6)

            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = Q.transitive_nodes[0]
            >>> N.next_event_date = 0.0
            >>> N.individuals
            []
            >>> ind1 = Individual(1)
            >>> ind2 = Individual(2)
            >>> ind3 = Individual(3)
            >>> ind4 = Individual(4)
            >>> ind5 = Individual(5)
            >>> ind6 = Individual(6)
            >>> ind7 = Individual(7)
            >>> ind8 = Individual(8)
            >>> ind9 = Individual(9)
            >>> ind10 = Individual(10)

            >>> N.accept(ind1, 0.01)
            >>> N.individuals
            [Individual 1]
            >>> ind1.arrival_date
            0.01
            >>> ind1.service_start_date
            0.01
            >>> round(ind1.service_time, 5)
            0.22524
            >>> round(ind1.service_end_date, 5)
            0.23524

            >>> N.accept(ind2, 0.02)
            >>> N.accept(ind3, 0.03)
            >>> N.accept(ind4, 0.04)
            >>> N.individuals
            [Individual 1, Individual 2, Individual 3, Individual 4]
            >>> round(ind4.arrival_date, 5)
            0.04
            >>> round(ind4.service_start_date, 5)
            0.04
            >>> round(ind4.service_time, 5)
            0.04333
            >>> round(ind4.service_end_date, 5)
            0.08333

            >>> N.accept(ind5, 0.05)
            >>> N.accept(ind6, 0.06)
            >>> N.accept(ind7, 0.07)
            >>> N.accept(ind8, 0.08)
            >>> N.accept(ind9, 0.09)
            >>> N.accept(ind10, 0.1)
            >>> N.individuals
            [Individual 1, Individual 2, Individual 3, Individual 4, Individual 5, Individual 6, Individual 7, Individual 8, Individual 9, Individual 10]
            >>> round(ind10.arrival_date, 5)
            0.1
            >>> ind10.service_start_date
            False
            >>> round(ind10.service_time, 5)
            0.21004
        """
        next_individual.exit_date = False
        next_individual.is_blocked = False
        self.begin_service_if_possible_accept(next_individual, current_time)
        self.individuals.append(next_individual)
        self.change_state_accept()

    def begin_service_if_possible_accept(self, next_individual, current_time):
        """
        Begins the service of the next individual, giving that customer a service time, end date and node

            >>> seed(50)
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> ind = Individual(1)
            >>> Q.digraph.nodes()
            ['Server 8 at Node 2', 'Server 8 at Node 3', 'Server 8 at Node 1', 'Server 8 at Node 4', 'Server 2 at Node 4', 'Server 3 at Node 4', 'Server 4 at Node 4', 'Server 6 at Node 4', 'Server 4 at Node 2', 'Server 6 at Node 1', 'Server 6 at Node 2', 'Server 4 at Node 3', 'Server 9 at Node 1', 'Server 5 at Node 3', 'Server 5 at Node 2', 'Server 5 at Node 1', 'Server 4 at Node 1', 'Server 5 at Node 4', 'Server 7 at Node 1', 'Server 7 at Node 3', 'Server 7 at Node 2', 'Server 7 at Node 4', 'Server 1 at Node 4', 'Server 1 at Node 3', 'Server 1 at Node 2', 'Server 1 at Node 1', 'Server 2 at Node 1', 'Server 2 at Node 2', 'Server 2 at Node 3', 'Server 3 at Node 1', 'Server 9 at Node 2', 'Server 3 at Node 3', 'Server 3 at Node 2', 'Server 6 at Node 3', 'Server 10 at Node 2']
            >>> ind.arrival_date
            False
            >>> ind.service_time
            False
            >>> ind.service_start_date
            False
            >>> ind.service_end_date
            False
            >>> Q.transitive_nodes[0].begin_service_if_possible_accept(ind, 300)
            >>> ind.arrival_date
            300
            >>> round(ind.service_time,5)
            0.09832
            >>> ind.service_start_date
            300
            >>> round(ind.service_end_date,5)
            300.09832

        """
        next_individual.arrival_date = current_time
        next_individual.service_time = self.simulation.service_times[self.id_number][next_individual.customer_class]()
        if len(self.individuals) < self.c:
            self.attach_server(self.find_free_server(), next_individual)
            next_individual.service_start_date = current_time
            next_individual.service_end_date = current_time + next_individual.service_time

    def find_free_server(self):
        """
        Finds a free server
        """
        free_servers = [svr for svr in self.servers if not svr.busy]
        return free_servers[0]

    def update_next_event_date(self, current_time):
        """
        Finds the time of the next event at this node

            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = Q.transitive_nodes[0]
            >>> N.next_event_date
            'Inf'
            >>> N.individuals
            []
            >>> N.update_next_event_date(0.0)
            >>> N.next_event_date
            'Inf'

            >>> ind1 = Individual(1)
            >>> ind1.arrival_date = 0.3
            >>> ind1.service_time = 0.2
            >>> ind1.service_end_date = 0.5
            >>> N.next_event_date = 0.3
            >>> N.individuals = [ind1]
            >>> N.update_next_event_date(N.next_event_date)
            >>> N.next_event_date
            0.5

            >>> ind2 = Individual(2)
            >>> ind2.arrival_date = 0.4
            >>> ind2.service_time = 0.2
            >>> ind2.service_end_date = 0.6
            >>> ind2.exit_date = False

            >>> N.individuals = [ind1, ind2]
            >>> N.update_next_event_date(N.next_event_date)
            >>> N.next_event_date
            0.6

            >>> ind2.exit_date = 0.9 # shouldn't affect next_event_date

            >>> N.update_next_event_date(N.next_event_date)
            >>> N.next_event_date
            'Inf'
        """
        self.next_event_date = min([ind.service_end_date for ind in self.individuals[:self.c] if not ind.is_blocked if ind.service_end_date>current_time] + ["Inf"])

    def next_node(self, customer_class):
        """
        Finds the next node according the random distribution.

        An example showing a node choosing both nodes and exit node randomly.
            >>> seed(6)
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> node = Q.transitive_nodes[0]
            >>> node.next_node(0)
            Node 4
            >>> node.next_node(0)
            Exit Node
            >>> node.next_node(0)
            Node 4
            >>> node.next_node(0)
            Node 2
            >>> node.next_node(0)
            Node 1
            >>> node.next_node(0)
            Node 4

        Another example.
            >>> seed(54)
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> node = Q.transitive_nodes[2]
            >>> node.next_node(0)
            Node 4
            >>> node.next_node(0)
            Node 2
            >>> node.next_node(0)
            Node 2
            >>> node.next_node(0)
            Node 2
            >>> node.next_node(0)
            Node 4
            >>> node.next_node(0)
            Node 2
            >>> node.next_node(0)
            Node 2
            >>> node.next_node(0)
            Node 2

        """
        rnd_num = random()
        for p in range(len(self.cum_transition_row[customer_class])):
            if rnd_num < self.cum_transition_row[customer_class][p]:
                return self.simulation.transitive_nodes[p]
        return self.simulation.nodes[-1]

    def write_individual_record(self, individual):
        """
        Write a data record for an individual:

        - Arrival date
        - Wait
        - Service start date
        - Service time
        - Service end date
        - Blocked
        - Exit date

        An example showing the data records written; can only write records once an exit date has been determined.
            >>> seed(7)
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = Q.transitive_nodes[0]
            >>> ind = Individual(6)
            >>> N.accept(ind, 3)
            >>> ind.service_start_date = 3.5
            >>> ind.exit_date = 9
            >>> N.write_individual_record(ind)
            >>> ind.data_records[1][0].arrival_date
            3
            >>> ind.data_records[1][0].wait
            0.5
            >>> ind.data_records[1][0].service_start_date
            3.5
            >>> round(ind.data_records[1][0].service_time, 5)
            0.0559
            >>> round(ind.data_records[1][0].service_end_date, 5)
            3.5559
            >>> round(ind.data_records[1][0].blocked, 5)
            5.4441
            >>> ind.data_records[1][0].exit_date
            9
        """
        record = DataRecord(individual.arrival_date, individual.service_time, individual.service_start_date, individual.exit_date, self.id_number)
        if self.id_number in individual.data_records:
            individual.data_records[self.id_number].append(record)
        else:
            individual.data_records[self.id_number] = [record]

        individual.arrival_date = False
        individual.service_time = False
        individual.service_start_date = False
        individual.service_end_date = False
        individual.exit_date = False


class ArrivalNode:
    """
    Class for the arrival node on our network
    """
    def __init__(self, simulation):
        """
        Initialise a node.

        Here is an example::
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = ArrivalNode(Q)
            >>> N.lmbda
            35.5
            >>> N.transition_row_given_class
            [[0.2, 0.4666666666666667, 0.26666666666666666, 0.06666666666666667], [0.13333333333333333, 0.2, 0.4, 0.26666666666666666], [0.36363636363636365, 0.18181818181818182, 0.36363636363636365, 0.09090909090909091]]
            >>> N.next_event_date
            0.0
            >>> N.number_of_individuals
            0
            >>> N.cum_transition_row
            [[0.2, 0.6666666666666667, 0.9333333333333333, 1.0], [0.13333333333333333, 0.33333333333333337, 0.7333333333333334, 1.0], [0.36363636363636365, 0.5454545454545454, 0.9090909090909091, 1.0]]
            >>> N.cum_class_probs
            [0.4225352112676056, 0.8450704225352113, 1.0]
        """

        self.simulation = simulation
        self.lmbda = self.simulation.overall_lmbda
        self.class_probs = self.simulation.class_probs
        self.transition_row_given_class = self.simulation.node_given_class_probs
        self.next_event_date = 0.0
        self.number_of_individuals = 0
        self.cum_transition_row = self.find_cumulative_transition_row()
        self.cum_class_probs = self.find_cumulative_class_probs()

    def find_cumulative_transition_row(self):
        """
        Finds the cumulative transition row for the arrival node

        An example of finding the cumulative transition row of an arrival node.
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = ArrivalNode(Q)
            >>> [[round(pr, 2) for pr in N.cum_transition_row[cls]] for cls in range(len(N.cum_transition_row))]
            [[0.2, 0.67, 0.93, 1.0], [0.13, 0.33, 0.73, 1.0], [0.36, 0.55, 0.91, 1.0]]
        """

        cum_transition_row = []
        for cls in range(len(self.transition_row_given_class)):
            sum_p = 0
            cum_transition_row.append([])
            for p in self.transition_row_given_class[cls]:
                sum_p += p
                cum_transition_row[cls].append(sum_p)
        return cum_transition_row

    def find_cumulative_class_probs(self):
        """
        Returns the cumulative class probs

        An example of finding the cumulative probabilities of a new customer being in each class.
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = ArrivalNode(Q)
            >>> N.find_cumulative_class_probs()
            [0.4225352112676056, 0.8450704225352113, 1.0]
        """

        cum_class_probs = []
        sum_p = 0
        for p in self.class_probs:
            sum_p += p
            cum_class_probs.append(sum_p)
        return cum_class_probs

    def __repr__(self):
        """
        Representation of a node::

        An example showing how an arrival node is represented.
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = ArrivalNode(Q)
            >>> N
            Arrival Node
        """
        return 'Arrival Node'

    def have_event(self):
        """
        Update node when a service happens.

        An example of creating an individual instance, releasing it to a node, and then updating its next event time.
            >>> seed(1)
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> Q.transitive_nodes[0].individuals
            []
            >>> Q.transitive_nodes[1].individuals
            []
            >>> Q.transitive_nodes[2].individuals
            []
            >>> Q.transitive_nodes[3].individuals
            []
            >>> N = ArrivalNode(Q)
            >>> N.lmbda
            35.5
            >>> N.next_event_date
            0.0
            >>> N.have_event()
            >>> Q.transitive_nodes[0].individuals
            []
            >>> Q.transitive_nodes[1].individuals
            []
            >>> Q.transitive_nodes[2].individuals
            [Individual 1]
            >>> Q.transitive_nodes[3].individuals
            []
            >>> round(N.next_event_date,5)
            0.01927

        Another example.
            >>> seed(12)
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> Q.transitive_nodes[0].individuals
            []
            >>> Q.transitive_nodes[1].individuals
            []
            >>> Q.transitive_nodes[2].individuals
            []
            >>> Q.transitive_nodes[3].individuals
            []
            >>> N = ArrivalNode(Q)
            >>> N.next_event_date
            0.0
            >>> N.have_event()
            >>> Q.transitive_nodes[0].individuals
            []
            >>> Q.transitive_nodes[1].individuals
            []
            >>> Q.transitive_nodes[2].individuals
            [Individual 1]
            >>> Q.transitive_nodes[3].individuals
            []
            >>> round(N.next_event_date,5)
            0.00433
        """
        self.number_of_individuals += 1
        next_individual = Individual(self.number_of_individuals, self.choose_class())
        next_node = self.next_node(next_individual.customer_class)
        if len(next_node.individuals) < next_node.node_capacity:
            next_node.accept(next_individual, self.next_event_date)
        self.update_next_event_date()

    def update_next_event_date(self):
        """
        Finds the time of the next event at this node

            >>> seed(1)
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = ArrivalNode(Q)
            >>> N.next_event_date
            0.0
            >>> N.update_next_event_date()
            >>> round(N.next_event_date, 5)
            0.00406
        """
        self.next_event_date += expovariate(self.lmbda)

    def next_node(self, customer_class):
        """
        Finds the next node according the random distribution.

        An example of finding the individual's starting node.
            >>> seed(1)
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = Q.nodes[0]
            >>> N.cum_transition_row
            [[0.2, 0.6666666666666667, 0.9333333333333333, 1.0], [0.13333333333333333, 0.33333333333333337, 0.7333333333333334, 1.0], [0.36363636363636365, 0.5454545454545454, 0.9090909090909091, 1.0]]
            >>> N.next_node(0)
            Node 1
            >>> N.next_node(0)
            Node 3
            >>> N.next_node(0)
            Node 3

        And another example.
            >>> seed(401)
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = Q.nodes[0]
            >>> N.next_node(0)
            Node 2
            >>> N.next_node(0)
            Node 2
            >>> N.next_node(0)
            Node 3
        """
        rnd_num = random()
        for p in range(len(self.cum_transition_row[customer_class])):
            if rnd_num < self.cum_transition_row[customer_class][p]:
                return self.simulation.transitive_nodes[p]

    def choose_class(self):
        """
        Returns the customer's class from the class probabilities

            >>> seed(6)
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = ArrivalNode(Q)
            >>> N.choose_class()
            1
        """
        rnd_num = random()
        for p in range(len(self.cum_class_probs)):
            if rnd_num < self.cum_class_probs[p]:
                return p


class ExitNode:
    """
    Class for the exit node on our network
    """
    def __init__(self, max_simulation_time):
        """
        Initialise a node.

        An example of an exit node instance.
            >>> N = ExitNode(100)
            >>> N.individuals
            []
            >>> N.id_number
            -1
            >>> N.next_event_date
            100

        And another.
            >>> N = ExitNode(4)
            >>> N.id_number
            -1
            >>> N.next_event_date
            4
        """
        self.individuals = []
        self.id_number = -1
        self.next_event_date = max_simulation_time
        self.node_capacity = "Inf"

    def __repr__(self):
        """
        Representation of a node::

        An example of how an exit node is represented.
            >>> N = ExitNode(500)
            >>> N
            Exit Node

        And another.
            >>> N = ExitNode(320)
            >>> N
            Exit Node
        """
        return 'Exit Node'

    def accept(self, next_individual, current_time):
        """
        Accepts a new customer to the queue

        An example of a customer leaving the system (getting accepted to the exit node).
            >>> N = ExitNode(200)
            >>> N.individuals
            []
            >>> N.next_event_date
            200
            >>> next_individual = Individual(5, 1)
            >>> N.accept(next_individual, 1)
            >>> N.individuals
            [Individual 5]
            >>> N.next_event_date
            200

        Another example.
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = Q.nodes[-1]
            >>> N.individuals
            []
            >>> N.next_event_date
            'Inf'
            >>> next_individual = Individual(3)
            >>> N.accept(next_individual, 3)
            >>> N.individuals
            [Individual 3]
            >>> N.next_event_date
            'Inf'
        """
        self.individuals.append(next_individual)

    def update_next_event_date(self):
        """
        Finds the time of the next event at this node

        An example showing that this method does nothing.
            >>> N = ExitNode(25)
            >>> N.next_event_date
            25
            >>> N.update_next_event_date()
            >>> N.next_event_date
            25

        And again.
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> N = Q.nodes[-1]
            >>> N.next_event_date
            'Inf'
            >>> N.update_next_event_date()
            >>> N.next_event_date
            'Inf'

        And again, even when parameters don't make sense.
            >>> N = ExitNode(False)
            >>> N.next_event_date
            False
            >>> N.update_next_event_date()
            >>> N.next_event_date
            False
        """
        pass


class Simulation:
    """
    Overall simulation class
    """
    def __init__(self, directory_name, sffx=None):
        """
        Initialise a queue instance.

        Here is an example::

        An example of creating a simulation instance.
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> Q.lmbda
            [[3.0, 7.0, 4.0, 1.0], [2.0, 3.0, 6.0, 4.0], [2.0, 1.0, 2.0, 0.5]]
            >>> Q.mu
            [[['Exponential', 7.0], ['Exponential', 7.0], ['Gamma', 0.4, 0.6], ['Deterministic', 0.5]], [['Exponential', 7.0], ['Triangular', 0.1, 0.8, 0.85], ['Exponential', 8.0], ['Exponential', 5.0]], [['Deterministic', 0.3], ['Deterministic', 0.2], ['Exponential', 8.0], ['Exponential', 9.0]]]
            >>> Q.c
            [9, 10, 8, 8]
            >>> Q.transition_matrix
            [[[0.1, 0.2, 0.1, 0.4], [0.2, 0.2, 0.0, 0.1], [0.0, 0.8, 0.1, 0.1], [0.4, 0.1, 0.1, 0.0]], [[0.6, 0.0, 0.0, 0.2], [0.1, 0.1, 0.2, 0.2], [0.9, 0.0, 0.0, 0.0], [0.2, 0.1, 0.1, 0.1]], [[0.0, 0.0, 0.4, 0.3], [0.1, 0.1, 0.1, 0.1], [0.1, 0.3, 0.2, 0.2], [0.0, 0.0, 0.0, 0.3]]]
            >>> Q.nodes
            [Arrival Node, Node 1, Node 2, Node 3, Node 4, Exit Node]
            >>> Q.transitive_nodes
            [Node 1, Node 2, Node 3, Node 4]
            >>> Q.max_simulation_time
            2500
        """

        self.root = os.getcwd()
        self.directory = os.path.join(self.root, directory_name)
        self.sffx = sffx
        self.digraph = nx.DiGraph()
        self.parameters = self.load_parameters()
        self.lmbda = [self.parameters['Arrival_rates']['Class ' + str(i)] for i in range(self.parameters['Number_of_classes'])]
        self.overall_lmbda = sum([sum(self.lmbda[i]) for i in range(len(self.lmbda))])
        self.class_probs = [sum(self.lmbda[i])/self.overall_lmbda for i in range(len(self.lmbda))]
        self.node_given_class_probs = [[self.lmbda[j][i]/(self.class_probs[j]*self.overall_lmbda) for i in range(len(self.lmbda[0]))] for j in range(len(self.lmbda))]
        self.mu = [self.parameters['Service_rates']['Class ' + str(i)] for i in range(self.parameters['Number_of_classes'])]
        self.c = self.parameters['Number_of_servers']
        self.queue_capacities = self.parameters['Queue_capacities']
        self.transition_matrix = [self.parameters['Transition_matrices']['Class ' + str(i)] for i in range(self.parameters['Number_of_classes'])]
        self.max_simulation_time = self.parameters['Simulation_time']
        self.transitive_nodes = [Node(i + 1, self) for i in range(len(self.c))]
        self.nodes = [ArrivalNode(self)] + self.transitive_nodes + [ExitNode("Inf")]
        self.number_of_nodes = len(self.transitive_nodes)
        self.service_times = self.find_service_time_dictionary()
        self.order = sum([nd.c for nd in self.transitive_nodes])
        self.state = [[0, 0] for i in range(self.number_of_nodes)]
        initial_state = [[0, 0] for i in range(self.number_of_nodes)]
        self.times_dictionary = {tuple(tuple(initial_state[i]) for i in range(self.number_of_nodes)): 0.0}

        if len(self.lmbda) != len(self.mu) or len(self.lmbda) != len(self.transition_matrix) or len(self.mu) != len(self.transition_matrix):
            raise ValueError('Lambda, Mu and the Transition Matrix should all have the same number of classes')

        if any(len(lmbdacls) != len(self.c) for lmbdacls in self.lmbda):
            raise ValueError('Lambda should have same length as c for every class')

        if any(len(mucls) != len(self.c) for mucls in self.mu):
            raise ValueError('Mu should have same length as c for every class')

        if any(len(transmatrxcls) != len(self.c) for transmatrxcls in self.transition_matrix):
            raise ValueError('Transition matrix should be square matrix of length c for every class')

        if any(len(transmatrxrow) != len(self.c) for transmatrxcls in self.transition_matrix for transmatrxrow in transmatrxcls):
            raise ValueError('Transition matrix should be square matrix of length c for every class')

        if any(l < 0 for lmbdaclass in self.lmbda for l in lmbdaclass):
            raise ValueError('All arrival rates should be positive')

        if any(type(k) is not int or k <= 0 for k in self.c):
            raise ValueError('All servers must be positive integer number')

        if any(tmval < 0 for transmatrxcls in self.transition_matrix for transmatrxrow in transmatrxcls for tmval in transmatrxrow) or any(tmval > 1 for transmatrxcls in self.transition_matrix for transmatrxrow in transmatrxcls for tmval in transmatrxrow) or any(sum(transmatrxrow) > 1 for transmatrxcls in self.transition_matrix for transmatrxrow in transmatrxcls):
            raise ValueError('All transition matrix entries should be probabilities 0<=p<=1 and all transition matrix rows should sum to 1 or less')

        if self.max_simulation_time < 0:
            raise ValueError('Maximum simulation time should be positive')

    def load_parameters(self):
        """
        Loads the parameters into the model
        """
        parameter_file_name = self.directory + 'parameters.yml'
        parameter_file = open(parameter_file_name, 'r')
        parameters = yaml.load(parameter_file)
        parameter_file.close()

        if parameters['Number_of_nodes'] == 1:
            for cls in parameters['Transition_matrices']:
                parameters['Transition_matrices'][cls] = [parameters['Transition_matrices'][cls]]

        return parameters

    def find_next_active_node(self):
        """
        Return the next active node:

        A mock example testing if this method works.
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> i = 0
            >>> for node in Q.nodes[:-1]:
            ...     node.next_event_date = i
            ...     i += 1
            >>> Q.find_next_active_node()
            Arrival Node

        And again.
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> i = 10
            >>> for node in Q.nodes[:-1]:
            ...     node.next_event_date = i
            ...     i -= 1
            >>> Q.find_next_active_node()
            Node 4
        """
        return min(self.nodes, key=lambda x: x.next_event_date)

    def find_service_time(self, n, c):
        """
        Finds the service time function
        """

        if self.mu[c][n][0] == 'Uniform':
            return lambda : uniform(self.mu[c][n][1], self.mu[c][n][2])
        if self.mu[c][n][0] == 'Deterministic':
            return lambda : self.mu[c][n][1]
        if self.mu[c][n][0] == 'Triangular':
            return lambda : triangular(self.mu[c][n][1], self.mu[c][n][2], self.mu[c][n][3])
        if self.mu[c][n][0] == 'Exponential':
            return lambda : expovariate(self.mu[c][n][1])
        if self.mu[c][n][0] == 'Gamma':
            return lambda : gammavariate(self.mu[c][n][1], self.mu[c][n][2])
        if self.mu[c][n][0] == 'Normal':
            return lambda : gauss(self.mu[c][n][1], self.mu[c][n][2])
        if self.mu[c][n][0] == 'Lognormal':
            return lambda : lognormvariate(self.mu[c][n][1], self.mu[c][n][2])
        if self.mu[c][n][0] == 'Weibull':
            return lambda : weibullvariate(self.mu[c][n][1], self.mu[c][n][2])
        return False

    def find_service_time_dictionary(self):
        """
        Finds the dictionary of service time functions for each node for each class
        """
        return {node+1:{customer_class:self.find_service_time(node, customer_class) for customer_class in range(len(self.lmbda))} for node in range(self.number_of_nodes)}

    def simulate_until_max_time(self):
        """
        Run the actual simulation.

            >>> seed(3)
            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> Q.simulate_until_max_time()
        """
        self.nodes[0].update_next_event_date()
        next_active_node = self.find_next_active_node()
        current_time = next_active_node.next_event_date
        while current_time < self.max_simulation_time:
            next_active_node.have_event()
            for node in self.transitive_nodes:
                node.update_next_event_date(current_time)
            next_active_node = self.find_next_active_node()
            current_time = next_active_node.next_event_date

    def simulate_until_deadlock(self):
        """
        Run the actual simulation.

            >>> seed(3)
            >>> Q = Simulation('datafortesting/logs_test_for_deadlock_sim/')
            >>> times = Q.simulate_until_deadlock()
            >>> times[((0, 0), (0, 0))]
            8.699770274666774
        """
        deadlocked = False
        self.nodes[0].update_next_event_date()
        next_active_node = self.find_next_active_node()
        current_time = next_active_node.next_event_date
        while not deadlocked:
            next_active_node.have_event()

            current_state = tuple(tuple(self.state[i]) for i in range(len(self.state)))
            if current_state not in self.times_dictionary:
                self.times_dictionary[current_state] = current_time

            for node in self.transitive_nodes:
                node.update_next_event_date(current_time)
            deadlocked = self.detect_deadlock()

            if deadlocked:
                time_of_deadlock = current_time

            next_active_node = self.find_next_active_node()
            current_time = next_active_node.next_event_date

        return {state: time_of_deadlock - self.times_dictionary[state] for state in self.times_dictionary.keys()}

    def detect_deadlock(self):
        """
        Detects whether the system is in a deadlocked state, that is, is there a knot

        Note that this code is taken and adapted from the NetworkX Developer Zone Ticket #663 knot.py (09/06/2015)

            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> nodes = ['A', 'B', 'C', 'D', 'E']
            >>> connections = [('A', 'D'), ('A', 'B'), ('B', 'E'), ('C', 'B'), ('E', 'C')]
            >>> for nd in nodes:
            ...     Q.digraph.add_node(nd)
            >>> for cnctn in connections:
            ...     Q.digraph.add_edge(cnctn[0], cnctn[1])
            >>> Q.detect_deadlock()
            True

            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> nodes = ['A', 'B', 'C', 'D']
            >>> connections = [('A', 'B'), ('A', 'C'), ('B', 'C'), ('B', 'D')]
            >>> for nd in nodes:
            ...     Q.digraph.add_node(nd)
            >>> for cnctn in connections:
            ...     Q.digraph.add_edge(cnctn[0], cnctn[1])
            >>> Q.detect_deadlock()
            False

            >>> Q = Simulation('datafortesting/logs_test_for_simulation/')
            >>> nodes = ['A', 'B']
            >>> for nd in nodes:
            ...     Q.digraph.add_node(nd)
            >>> Q.detect_deadlock()
            False
            >>> connections = [('A', 'A')]
            >>> for cnctn in connections:
            ...     Q.digraph.add_edge(cnctn[0], cnctn[1])
            >>> Q.detect_deadlock()
            True
        """
        knots = []
        for subgraph in nx.strongly_connected_component_subgraphs(self.digraph):
            nodes = set(subgraph.nodes())
            if len(nodes) == 1:
                n = nodes.pop()
                nodes.add(n)
                if set(self.digraph.successors(n)) == nodes:
                    knots.append(subgraph)
            else:
                for n in nodes:
                    successors = nx.descendants(self.digraph, n)
                    if not successors <= nodes:
                        break
                else:
                    knots.append(subgraph)
        if len(knots) > 0:
            return True
        return False

    def get_all_individuals(self):
        """
        Returns list of all individuals with at least one record
        """
        return [individual for node in self.nodes[1:] for individual in node.individuals if len(individual.data_records) > 0]

    def write_records_to_file(self):
        """
        Writes the records for all individuals to a csv file
        """
        if self.sffx:
            data_file = open('%sdata_' %self.directory + self.sffx + '.csv', 'w')
        else:
            data_file = open('%sdata.csv' % self.directory, 'w')
        csv_wrtr = writer(data_file)
        for individual in self.get_all_individuals():
            for node in individual.data_records:
                for record in individual.data_records[node]:
                    csv_wrtr.writerow([individual.id_number,
                                       individual.customer_class,
                                       node,
                                       record.arrival_date,
                                       record.wait,
                                       record.service_start_date,
                                       record.service_time,
                                       record.service_end_date,
                                       record.blocked,
                                       record.exit_date])
        data_file.close()