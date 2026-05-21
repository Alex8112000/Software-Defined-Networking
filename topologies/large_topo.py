from mininet.topo import Topo

class LargeTopo(Topo):
    def build(self):
        host_id = 1

        # Core Layer (4)
        cores = [self.addSwitch(f'c{i}', stp=True, failMode='standalone', dpid='%016x' % (101 + i)) for i in range(4)]

        # Aggregation Layer (6)
        aggs = [self.addSwitch(f'a{i}', stp=True, failMode='standalone', dpid='%016x' % (201 + i)) for i in range(6)]

        # Core - Aggregation (voll vermascht)
        for core in cores:
            for agg in aggs:
                self.addLink(core, agg)

        # Edge Layer (12)
        edges = []
        for i in range(12):
            edge = self.addSwitch(f'e{i}', stp=True, failMode='standalone', dpid='%016x' % (301 + i))
            edges.append(edge)

            # Jeder Edge hängt an 2 Aggregation Switches
            self.addLink(edge, aggs[i % 6])
            self.addLink(edge, aggs[(i + 1) % 6])

        #  Hosts (12 pro Edge)
        for edge in edges:
            for _ in range(12):
                h = self.addHost(f'h{host_id}')
                self.addLink(h, edge)
                host_id += 1

topos = {'largetopo': LargeTopo}

