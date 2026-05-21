from mininet.topo import Topo

class SmallTopo(Topo):
    def build(self):
        core = self.addSwitch('c0', stp=True, failMode='standalone', dpid='%016x' % 101)

        e0 = self.addSwitch('e0', stp=True, failMode='standalone', dpid='%016x' % 201)
        e1 = self.addSwitch('e1', stp=True, failMode='standalone', dpid='%016x' % 202)

        self.addLink(core, e0)
        self.addLink(core, e1)

        for i in range(1, 4):
            h = self.addHost(f'h{i}')
            self.addLink(h, e0)

        for i in range(4, 7):
            h = self.addHost(f'h{i}')
            self.addLink(h, e1)

topos = {'smalltopo': SmallTopo}

