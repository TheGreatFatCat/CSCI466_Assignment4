import queue
import threading
import json

## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.in_queue = queue.Queue(maxsize)
        self.out_queue = queue.Queue(maxsize)

    ##get packet from the queue interface
    # @param in_or_out - use 'in' or 'out' interface
    def get(self, in_or_out):
        try:
            if in_or_out == 'in':
                pkt_S = self.in_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the IN queue')
                return pkt_S
            else:
                pkt_S = self.out_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the OUT queue')
                return pkt_S
        except queue.Empty:
            return None

    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        if in_or_out == 'out':
            # print('putting packet in the OUT queue')
            self.out_queue.put(pkt, block)
        else:
            # print('putting packet in the IN queue')
            self.in_queue.put(pkt, block)


## Implements a network layer packet.
class NetworkPacket:
    ## packet encoding lengths 
    dst_S_length = 5
    prot_S_length = 1

    ##@param dst: address of the destination host
    # @param data_S: packet payload
    # @param prot_S: upper layer protocol for the packet (data, or control)
    def __init__(self, dst, prot_S, data_S):
        self.dst = dst
        self.data_S = data_S
        self.prot_S = prot_S

    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()

    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst).zfill(self.dst_S_length)
        if self.prot_S == 'data':
            byte_S += '1'
        elif self.prot_S == 'control':
            byte_S += '2'
        else:
            raise ('%s: unknown prot_S option: %s' % (self, self.prot_S))
        byte_S += self.data_S
        return byte_S

    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst = byte_S[0: NetworkPacket.dst_S_length].strip('0')
        prot_S = byte_S[NetworkPacket.dst_S_length: NetworkPacket.dst_S_length + NetworkPacket.prot_S_length]
        if prot_S == '1':
            prot_S = 'data'
        elif prot_S == '2':
            prot_S = 'control'
        else:
            raise ('%s: unknown prot_S field: %s' % (self, prot_S))
        data_S = byte_S[NetworkPacket.dst_S_length + NetworkPacket.prot_S_length:]
        return self(dst, prot_S, data_S)


## Implements a network host for receiving and transmitting data
class Host:

    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False  # for thread termination

    ## called when printing the object
    def __str__(self):
        return self.addr

    ## create a packet and enqueue for transmission
    # @param dst: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst, data_S):
        p = NetworkPacket(dst, 'data', data_S)
        print('%s: sending packet "%s"' % (self, p))
        self.intf_L[0].put(p.to_byte_S(), 'out')  # send packets always enqueued successfully

    ## receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.intf_L[0].get('in')
        if pkt_S is not None:
            print('%s: received packet "%s"' % (self, pkt_S))

    ## thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            # receive data arriving to the in interface
            self.udt_receive()
            # terminate
            if (self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return


## Implements a multi-interface router
class Router:

    ##@param name: friendly router name for debugging
    # @param cost_D: cost table to neighbors {neighbor: {interface: cost}}
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, cost_D, max_queue_size):
        self.stop = False  # for thread termination
        self.name = name
        # create a list of interfaces
        self.intf_L = [Interface(max_queue_size) for _ in range(len(cost_D))]
        # save neighbors and interfeces on which we connect to them
        self.cost_D = cost_D  # {neighbor: {interface: cost}}
        # TODO: set up the routing table for connected hosts
        self.rt_tbl_D = {dest: {self.name: cost for key, cost in cost_D[dest].items()} for dest in cost_D}
        self.rt_tbl_D[self.name] = {self.name: 0}
        # Setting up routers table to look like below comment
        # {destination: {router: cost}}
        print('%s: Initialized routing table' % self)
        self.print_routes()

    ## Print routing table
    def print_routes(self):

        #  Printing top line
        top = ''
        for dst in self.rt_tbl_D.keys():
            top += '--------' #printing starting lines
        print(top + "--")
        # printing starting row (destinations)
        destination = "|" + self.name + "   |   "
        for dst in self.rt_tbl_D.keys():
            destination += dst + " |   "
        print(destination)

        body = ''
        for key in self.rt_tbl_D[self.name].keys():
            for _ in range(len(self.rt_tbl_D) + 1):
                body += "------|"
            body += "\n|"

            body += key + "   |   "
            for _, v in self.rt_tbl_D.items():
                if key in v:
                    val = v[key]
                    if val == 1000:
                        val = 'X'
                body += str(val) + "  |   "
            body += "\n"
        print(body, end='')
        print(top + "--")

    # print(self.rt_tbl_D)

    ## called when printing the object
    def __str__(self):
        return self.name

    ## look through the content of incoming interfaces and
    # process data and control packets
    def process_queues(self):
        for i in range(len(self.intf_L)):
            pkt_S = None
            # get packet from interface i
            pkt_S = self.intf_L[i].get('in')
            # if packet exists make a forwarding decision
            if pkt_S is not None:
                p = NetworkPacket.from_byte_S(pkt_S)  # parse a packet out
                if p.prot_S == 'data':
                    self.forward_packet(p, i)
                elif p.prot_S == 'control':
                    self.update_routes(p, i)
                else:
                    raise Exception('%s: Unknown packet type in packet %s' % (self, p))

    ## forward the packet according to the routing table
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def forward_packet(self, p, i):
        try:
            # TODO: Here you will need to implement a lookup into the
            # forwarding table to find the appropriate outgoing interface
            # for now we assume the outgoing interface is 1
            p_dst = ''  # destination for packet
            best_cost = 1000  # setting our best cost var
            # finding our packets destination
            if p.dst not in self.cost_D:
                router_list = []  # list of routers to check in second loop
                for key in self.cost_D:  # getting our "keys" from our cost list to get routers to check
                    if key.startswith("R"):
                        router_list.append(key)
                for router in router_list:  # checking our routers to get route from routing table
                    route_cost = self.rt_tbl_D[router][self.name] + self.rt_tbl_D[p.dst][router]  # getting route cost
                    if route_cost < best_cost:
                        best_cost = route_cost
                        p_dst = router
            else:  # p.dst is in self cost so it must be our neighbor
                p_dst = p.dst
            # getting output interface
            output_interface = list(self.cost_D[p_dst].keys())[0]
            self.intf_L[output_interface].put(p.to_byte_S(), 'out', True)
            print('%s: forwarding packet "%s" from interface %d to %d' % \
                  (self, p, i, output_interface))
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass

    ## send out route update
    # @param i Interface number on which to send out a routing update
    def send_routes(self, i):
        # TODO: Send out a routing table update
        # create a routing table update packet
        # Serialize routing table  with json's .dumps command.  (See https://docs.python.org/3/library/json.html)
        routes = json.dumps(self.rt_tbl_D)
        # send out packet with name and our table
        # may need below var if self.name + routes bugs out when sending
        data = self.name + routes
        p = NetworkPacket(0, 'control', data)
        try:
            print('%s: sending routing update "%s" from interface %d' % (self, p, i))
            self.intf_L[i].put(p.to_byte_S(), 'out', True)
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass

    ## forward the packet according to the routing table
    #  @param p Packet containing routing information
    def update_routes(self, p, i):
        # TODO: add logic to update the routing tables and
        # possibly send out routing updates
        # get the packet
        packet = str(p) # setting to string to use startswith on keys later
        source_start = NetworkPacket.prot_S_length + NetworkPacket.dst_S_length
        source_end = source_start + 2
        # getting the router our packet was sent from
        source_router = packet[source_start : source_end]
        # get our vector to be used in updating routes (list being sent in)
        vector = json.loads(packet[source_end:])  # de-serialize using the json.loads method
        # get list of keys (routers) from our stored list
        keys = self.rt_tbl_D.keys() | vector.keys()
        # list of routers to be used for vectoring in a later loop
        router_list = []

        for key in keys:
            # add routers found in packet to list
            if key.startswith("R"):  # if starts with R is router
                router_list.append(key)
        for key in keys:
            if key not in vector:
                vector[key] = {source_router: 9999}  # setting arbitrary high value
            if key not in self.rt_tbl_D:
                self.rt_tbl_D[key] = {self.name: 9999} # setting self value high
            # set our tables distance to our vectors
            self.rt_tbl_D[key][source_router] = vector[key][source_router]

        # doing bellman ford stuff
        for dest_key in keys:
            for router in router_list:
                route_vector = self.rt_tbl_D[router]
                dest_vector = self.rt_tbl_D[dest_key]

                if router == dest_key:
                    continue
                # if no connection from router to destination set vector to 9999
                if router not in dest_vector:
                    dest_vector[router] = 9999
                # doing bellman ford stuff
                bellman_ford = route_vector[self.name] + dest_vector[router]
                if bellman_ford < dest_vector[self.name]:
                    dest_vector[self.name] = bellman_ford
                    for p in range(len(self.intf_L)): # sending router updates to all ports
                        self.send_routes(p)
        print('%s: Received routing update %s from interface %d' % (self, p, i))

    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return
