from mininet.topo import Topo

class MediumTopo(Topo):
    def build(self):
        # Core
        core1 = self.addSwitch('c0', stp=True, failMode='standalone', dpid='%016x' % 101)
        core2 = self.addSwitch('c1', stp=True, failMode='standalone', dpid='%016x' % 102)

        # Aggregation
        aggs = []
        for i in range(0, 3):
            agg = self.addSwitch(f'a{i}', stp=True, failMode='standalone', dpid='%016x' % (201 + i))
            aggs.append(agg)
            self.addLink(core1, agg)
            self.addLink(core2, agg)

        # Access + Hosts
        host_id = 1
        for i, agg in enumerate(aggs):
            for j in range(2):  # 2 Access Switches pro Aggregation
                access = self.addSwitch(f'e{0 + i*2 + j}', stp=True, failMode='standalone', dpid='%016x' % (301 + i*2 + j))
                self.addLink(agg, access)

                for k in range(5):  # 5 Hosts pro Access
                    h = self.addHost(f'h{host_id}')
                    self.addLink(h, access)
                    host_id += 1

topos = {'mediumtopo': MediumTopo}

