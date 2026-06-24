from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4
import yaml
import os

class PolicyLearningSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # Tabellen-IDs
    TABLE_ACL = 0
    TABLE_GLOBAL = 1
    TABLE_STEERING = 2
    TABLE_HOST_POLICIES = 3
    TABLE_FORWARDING = 4

    def __init__(self, *args, **kwargs):
        super(PolicyLearningSwitch, self).__init__(*args, **kwargs)

        self.mac_to_port = {}
        self.policies = {}
        self.group_counter = 100
        self.load_policies()

    # ------------------------------------------------
    # YAML LADEN
    # ------------------------------------------------
    def load_policies(self):
        print("CWD:", os.getcwd())
        print("__file__:", __file__)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        policy_file = os.path.join(base_dir, '../policies/policies-topo2/policies.yaml')

        with open(policy_file) as f:
            self.policies = yaml.safe_load(f)

    # ------------------------------------------------
    # FLOW INSTALLATION
    # ------------------------------------------------
    def add_flow(self, dp, table, priority, match, actions=None, goto=None, idle_timeout=0):
        parser = dp.ofproto_parser
        ofproto = dp.ofproto
        inst = []

        if actions is not None:
            inst.append(parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions))

        if goto is not None:
            inst.append(parser.OFPInstructionGotoTable(goto))

        mod = parser.OFPFlowMod(
            datapath=dp,
            table_id=table,
            priority=priority,
            match=match,
            instructions=inst,
            idle_timeout=idle_timeout,
            hard_timeout=0)
        
        dp.send_msg(mod)

    # ------------------------------------------------
    # SWITCH CONNECT
    # ------------------------------------------------
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath            # Switch-Objekt
        parser = dp.ofproto_parser      # Parser für OpenFlow-Nachrichten
        ofproto = dp.ofproto            # OpenFlow Konstanten

        # ARP-Pakete gehen direkt an den Controller
        match = parser.OFPMatch(eth_type=0x0806)
        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        self.add_flow(dp, self.TABLE_ACL, 1000, match, actions=actions)

        # Pipeline-Processing: Table 0 -> ... -> Table 4 -> Controller
        self.add_flow(dp, 0, 0, parser.OFPMatch(), goto=1)
        self.add_flow(dp, 1, 0, parser.OFPMatch(), goto=2)
        self.add_flow(dp, 2, 0, parser.OFPMatch(), goto=3)
        self.add_flow(dp, 3, 0, parser.OFPMatch(), goto=4)
        self.add_flow(dp, 4, 0, parser.OFPMatch(), actions=[parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)])

        # Policies installieren
        self.install_acl(dp)
        self.install_global_policies(dp)
        self.install_steering(dp)
        self.install_host_port_policies(dp)

    # ------------------------------------------------
    # ACL (TABLE 0)
    # ------------------------------------------------
    def install_acl(self, dp):
        parser = dp.ofproto_parser

        for rule in self.policies.get("acl", []):
            match = parser.OFPMatch(
                eth_type=0x0800,
                ipv4_src=rule["src_ip"],
                ipv4_dst=rule["dst_ip"])
            
            # Paket wird bei "drop" verworfen 
            if rule["action"] == "drop":
                self.add_flow(dp, 0, 100, match, actions=[])
            # weiter zur nächsten Tabelle
            else:
                self.add_flow(dp, 0, 100, match, goto=1)

    # ------------------------------------------------
    # GLOBAL POLICIES (TABLE 1)
    # ------------------------------------------------
    def install_global_policies(self, dp):
        parser = dp.ofproto_parser
        # Policies auslesen
        for rule in self.policies.get("global", []):
            # Prüfung ob Policy aktiv
            if not rule.get("enabled", True):
                self.logger.info(f"Global policy {rule.get('type')} disabled")
                continue

            policy_type = rule.get("type")
            # 1. HTTP / HTTPS only
            if policy_type == "only_http_https":
                self.logger.info(f"Installing HTTP/HTTPS allow policy for Switch {dp.id}")
                # HTTP Requests
                self.add_flow(
                    dp,
                    table=1,
                    priority=300,
                    match=parser.OFPMatch(eth_type=0x0800, ip_proto=6, tcp_dst=80),
                    goto=2)
                
                # HTTP Responses
                self.add_flow(
                    dp,
                    table=1,
                    priority=300,
                    match=parser.OFPMatch(eth_type=0x0800, ip_proto=6, tcp_src=80),
                    goto=2)

                # HTTPS Requests
                self.add_flow(
                    dp,
                    table=1,
                    priority=300,
                    match=parser.OFPMatch(eth_type=0x0800, ip_proto=6, tcp_dst=443),
                    goto=2)
                
                # HTTPS Responses
                self.add_flow(
                    dp,
                    table=1,
                    priority=300,
                    match=parser.OFPMatch(eth_type=0x0800, ip_proto=6, tcp_src=443),
                    goto=2)
                
                # Block anderer TCP-Traffic
                self.add_flow(
                    dp,
                    table=1,
                    priority=200,
                    match=parser.OFPMatch(eth_type=0x0800, ip_proto=6),
                    actions=[])

            # 2. Restrict SSH
            elif policy_type == "restrict_ssh":
                self.logger.info(f"Installing SSH restriction for Switch {dp.id}")
                admin_hosts = rule.get("admin_host", [])
                # SSH Requests von Admin-Hosts erlauben
                for ip in admin_hosts:
                    self.add_flow(
                        dp,
                        table=1,
                        priority=300,
                        match=parser.OFPMatch(eth_type=0x0800, ip_proto=6, tcp_dst=22, ipv4_src=ip),
                        goto=2)
                    
                # SSH Responses erlauben
                for ip in admin_hosts:
                    self.add_flow(
                        dp,
                        table=1,
                        priority=300,
                        match=parser.OFPMatch(eth_type=0x0800, ip_proto=6, tcp_src=22, ipv4_dst=ip),
                        goto=2)

                # Alle anderen SSH-Verbindungen blockieren
                self.add_flow(
                    dp,
                    table=1,
                    priority=250,
                    match=parser.OFPMatch(eth_type=0x0800, ip_proto=6, tcp_dst=22),
                    actions=[])

    # ------------------------------------------------
    # TRAFFIC STEERING (TABLE 2)
    # ------------------------------------------------
    def install_steering(self, dp):
        parser = dp.ofproto_parser
        dpid = dp.id

        for rule in self.policies.get("steering", []):
            # nur für passenden Switch
            if dpid != rule.get("switch"):
                continue

            in_port = rule["in_port"]
            out_ports = rule["out_ports"]
            group_id = self.group_counter
            self.group_counter += 1

            # 1. Group erstellen
            self.create_select_group(dp, group_id, out_ports)

            # 2. Flow definieren
            match = parser.OFPMatch(in_port=in_port)
            actions = [parser.OFPActionGroup(group_id)]
            self.add_flow(dp, 2, 100, match, actions, 3)

    def create_select_group(self, dp, group_id, ports):
        ofproto = dp.ofproto
        parser = dp.ofproto_parser
        buckets = []

        for port in ports:
            actions = [parser.OFPActionOutput(port)]
            bucket = parser.OFPBucket(
                weight=50,  # gleich verteilt
                watch_port=port,
                watch_group=ofproto.OFPG_ANY,
                actions=actions)
            buckets.append(bucket)

        req = parser.OFPGroupMod(
            dp,
            ofproto.OFPGC_ADD,
            ofproto.OFPGT_SELECT,
            group_id,
            buckets)
        dp.send_msg(req)

    # ------------------------------------------------
    # HOSTSPECIFIC POLICIES (TABLE 3)
    # ------------------------------------------------
    def install_host_port_policies(self, dp):
        parser = dp.ofproto_parser
        
        for rule in self.policies.get("host", []):

            match = parser.OFPMatch(eth_type=0x0800, ipv4_src=rule["src_ip"])
            action = rule.get("action", "drop")

            if action == "drop":
                # Paket wird verworfen
                self.add_flow(dp, 3, 200, match, actions=[], goto=None)

            elif action == "allow":
                # goto next table
                self.add_flow(dp, 3, 200, match, actions=None, goto=4)

            elif action == "redirect":
                actions = [parser.OFPActionSetField(ipv4_dst=rule["to_ip"]), 
                           parser.OFPActionSetField(eth_dst=rule["to_mac"])]
                self.add_flow(dp, 3, 200, match, actions, goto=4)
            
    # ------------------------------------------------
    # PACKET IN HANDLER
    # ------------------------------------------------
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg                    # OFPPacketIn-Nachricht vom Switch
        dp = msg.datapath               # Switch-Objekt
        dpid = dp.id                    # Switch-ID
        parser = dp.ofproto_parser      # Parser für OpenFlow-Nachrichten
        ofproto = dp.ofproto            # OpenFlow Konstanten
        in_port = msg.match['in_port']  # Eingangsport des Pakets

        # MAC Table initialisieren
        self.mac_to_port.setdefault(dpid, {})
        # Paket parsen
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth is None:
            return
        
        # 1. MAC Learning
        self.mac_to_port[dpid][eth.src] = in_port

        # 2. Zielport bestimmen
        if eth.dst in self.mac_to_port[dpid]:
            # Ziel bekannt: Port aus MAC-Tabelle verwenden
            out_port = self.mac_to_port[dpid][eth.dst]
            actions = [parser.OFPActionOutput(out_port)]
            # Flow für IP-Pakete installieren
            if eth.ethertype == 0x0800:
                match = parser.OFPMatch(eth_type=0x0800, eth_dst=eth.dst)
                self.add_flow(dp, 4, 10, match, actions, idle_timeout=30)
        else:
            # Ziel unbekannt: Paket an alle Ports (FLOOD) senden
            out_port = ofproto.OFPP_FLOOD
            actions = [parser.OFPActionOutput(out_port)]

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        # 5. Paket weiterleiten
        out = parser.OFPPacketOut(
            datapath=dp,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data)
        
        dp.send_msg(out)
