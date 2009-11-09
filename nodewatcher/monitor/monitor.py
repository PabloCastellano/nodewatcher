#!/usr/bin/python
#
# WiFi Mesh Monitoring Daemon
#
# Copyright (C) 2009 by Jernej Kos <kostko@unimatrix-one.org>
#

# First parse options (this must be done here since they contain import paths
# that must be parsed before Django models can be imported)
import sys, os
from optparse import OptionParser

print "============================================================================"
print "                  Ljubljana WiFi Mesh Monitoring Daemon"
print "============================================================================"

parser = OptionParser()
parser.add_option('--path', dest = 'path', help = 'Path that contains "wlanlj" nodewatcher installation')
parser.add_option('--settings', dest = 'settings', help = 'Django settings to use')
options, args = parser.parse_args()

if not options.path:
  print "ERROR: Path specification is required!\n"
  parser.print_help()
  exit(1)
elif not options.settings:
  print "ERROR: Settings specification is required!\n"
  parser.print_help()
  exit(1)

# Setup import paths, since we are using Django models
sys.path.append(options.path)
os.environ['DJANGO_SETTINGS_MODULE'] = options.settings

# Import our models
from wlanlj.nodes.models import Node, NodeStatus, Subnet, SubnetStatus, APClient, Link, GraphType, GraphItem, Event, EventSource, EventCode, IfaceType, InstalledPackage, NodeType
from django.db import transaction, models
from django.conf import settings

# Import other stuff
from lib.wifi_utils import OlsrParser, PingParser
from lib import nodewatcher
from lib.rra import RRA, RRAIface, RRAClients, RRARTT, RRALinkQuality, RRASolar, RRALoadAverage, RRANumProc, RRAMemUsage, RRALocalTraffic, RRANodesByStatus, RRAWifiCells, RRAOlsrPeers
from lib.topology import DotTopologyPlotter
from lib.local_stats import fetch_traffic_statistics
from lib import ipcalc
from time import sleep
from datetime import datetime, timedelta
from traceback import format_exc, print_exc
import pwd
import logging
import time
import multiprocessing

RRA_CONF_MAP = {
  GraphType.RTT         : RRARTT,
  GraphType.LQ          : RRALinkQuality,
  GraphType.Clients     : RRAClients,
  GraphType.Traffic     : RRAIface,
  GraphType.LoadAverage : RRALoadAverage,
  GraphType.NumProc     : RRANumProc,
  GraphType.MemUsage    : RRAMemUsage,
  GraphType.Solar       : RRASolar,
  GraphType.WifiCells   : RRAWifiCells,
  GraphType.OlsrPeers   : RRAOlsrPeers
}
WORKER_POOL = None

def safe_int_convert(integer):
  """
  A helper method for converting a string to an integer.
  """
  try:
    return int(integer)
  except:
    return None

def safe_loadavg_convert(loadavg):
  """
  A helper method for converting a string to a loadavg tuple.
  """
  try:
    loadavg = loadavg.split(' ')
    la1min, la5min, la15min = (float(x) for x in loadavg[0:3])
    nproc = int(loadavg[3].split('/')[1])
    return la1min, la5min, la15min, nproc
  except:
    return None, None, None, None

def safe_uptime_convert(uptime):
  """
  A helper method for converting a string to an uptime integer.
  """
  try:
    return int(float(uptime.split(' ')[0]))
  except:
    return None

def safe_date_convert(timestamp):
  """
  A helper method for converting a string timestamp into a datetime
  object.
  """
  try:
    return datetime.fromtimestamp(int(timestamp))
  except:
    return None

def add_graph(node, name, type, conf, title, filename, *values, **attrs):
  """
  A helper function for generating graphs.
  """
  if hasattr(settings, 'MONITOR_DISABLE_GRAPHS') and settings.MONITOR_DISABLE_GRAPHS:
    return
  
  rra = str(os.path.join(settings.MONITOR_WORKDIR, 'rra', '%s.rrd' % filename))
  try:
    RRA.update(node, conf, rra, *values)
  except:
    pass
  RRA.graph(conf, title, '%s.png' % filename, *[rra for i in xrange(len(values))])
  
  # Get parent instance (toplevel by default)
  parent = attrs.get('parent', None)

  try:
    graph = GraphItem.objects.get(node = node, name = name, type = type, parent = parent)
  except GraphItem.DoesNotExist:
    graph = GraphItem(node = node, name = name, type = type, parent = parent)
    graph.rra = '%s.rrd' % filename
    graph.graph = '%s.png' % filename
  
  graph.title = title
  graph.last_update = datetime.now()
  graph.dead = False
  graph.save()
  return graph

@transaction.commit_on_success
def check_events():
  """
  Check events that need resend.
  """
  transaction.set_dirty()
  Event.post_events_that_need_resend()

@transaction.commit_on_success
def check_global_statistics():
  """
  Graph some global statistics.
  """
  transaction.set_dirty()

  try:
    stats = fetch_traffic_statistics()
    rra = os.path.join(settings.MONITOR_WORKDIR, 'rra', 'global_replicator_traffic.rrd')
    RRA.update(None, RRALocalTraffic, rra,
      stats['statistics:to-inet'],
      stats['statistics:from-inet'],
      stats['statistics:internal']
    )
    RRA.graph(RRALocalTraffic, 'replicator - Traffic', 'global_replicator_traffic.png', rra, rra, rra)
  except:
    logging.warning("Unable to process local server traffic information, skipping!")

  # Nodes by status
  nbs = {}
  for s in Node.objects.exclude(node_type = NodeType.Test).values('status').annotate(count = models.Count('ip')):
    nbs[s['status']] = s['count']

  rra = os.path.join(settings.MONITOR_WORKDIR, 'rra', 'global_nodes_by_status.rrd')
  RRA.update(None, RRANodesByStatus, rra,
    nbs.get(NodeStatus.Up, 0),
    nbs.get(NodeStatus.Down, 0),
    nbs.get(NodeStatus.Visible, 0),
    nbs.get(NodeStatus.Invalid, 0),
    nbs.get(NodeStatus.Pending, 0),
    nbs.get(NodeStatus.Duped, 0)
  )
  RRA.graph(RRANodesByStatus, 'Nodes By Status', 'global_nodes_by_status.png', *([rra] * 6))

  # Global client count
  client_count = len(APClient.objects.all())
  rra = os.path.join(settings.MONITOR_WORKDIR, 'rra', 'global_client_count.rrd')
  RRA.update(None, RRAClients, rra, client_count)
  RRA.graph(RRAClients, 'Global Client Count', 'global_client_count.png', rra)

@transaction.commit_on_success
def check_dead_graphs():
  """
  Checks for dead graphs.
  """
  transaction.set_dirty()

  for graph in GraphItem.objects.filter(dead = False, last_update__lt = datetime.now() - timedelta(minutes = 10)):
    # Mark graph as dead
    graph.dead = True
    graph.save()

    # Redraw the graph with dead status attached
    pathArchive = str(os.path.join(settings.MONITOR_WORKDIR, 'rra', graph.rra))
    pathImage = graph.graph
    conf = RRA_CONF_MAP[graph.type]
    
    try:
      RRA.graph(conf, str(graph.title), pathImage, end_time = int(time.mktime(graph.last_update.timetuple())), dead = True,
                *[pathArchive for i in xrange(len(conf.sources))])
    except OSError:
      logging.warning("Skipping dead non-existant graph '%s'!" % graph.rra)

@transaction.commit_on_success
def process_node(node_ip, ping_results, is_duped, peers):
  """
  Processes a single node.

  @param node_ip: Node's IP address
  @param ping_results: Results obtained from ICMP ECHO tests
  @param is_duped: True if duplicate echos received
  @param peers: Peering info from routing daemon
  """
  transaction.set_dirty()
  n = Node.objects.get(ip = node_ip)
  oldStatus = n.status

  # Determine node status
  if ping_results is not None:
    n.status = NodeStatus.Up
    n.rtt_min, n.rtt_avg, n.rtt_max, n.pkt_loss = ping_results
    
    # Add RTT graph
    add_graph(n, '', GraphType.RTT, RRARTT, 'Latency', 'latency_%s' % node_ip, n.rtt_avg)

    # Add uptime credit
    if n.uptime_last:
      n.uptime_so_far = (n.uptime_so_far or 0) + (datetime.now() - n.uptime_last).seconds
    
    n.uptime_last = datetime.now()
  else:
    n.status = NodeStatus.Visible

  if is_duped:
    n.status = NodeStatus.Duped
    n.warnings = True

  # Generate status change events
  if oldStatus in (NodeStatus.Down, NodeStatus.Pending, NodeStatus.New) and n.status in (NodeStatus.Up, NodeStatus.Visible):
    if oldStatus in (NodeStatus.New, NodeStatus.Pending):
      n.first_seen = datetime.now()

    Event.create_event(n, EventCode.NodeUp, '', EventSource.Monitor)
  elif oldStatus != NodeStatus.Duped and n.status == NodeStatus.Duped:
    Event.create_event(n, EventCode.PacketDuplication, '', EventSource.Monitor)
  
  # Add olsr peer count graph
  add_graph(n, '', GraphType.OlsrPeers, RRAOlsrPeers, 'Routing Peers', 'olsrpeers_%s' % node_ip, n.peers)

  # Add LQ/ILQ graphs
  if n.peers > 0:
    lq_avg = ilq_avg = 0.0
    for peer in peers:
      lq_avg += float(peer[1])
      ilq_avg += float(peer[2])
    
    lq_graph = add_graph(n, '', GraphType.LQ, RRALinkQuality, 'Average Link Quality', 'lq_%s' % node_ip, lq_avg / n.peers, ilq_avg / n.peers)

    for peer in n.src.all():
      add_graph(n, peer.dst.ip, GraphType.LQ, RRALinkQuality, 'Link Quality to %s' % peer.dst, 'lq_peer_%s_%s' % (node_ip, peer.dst.ip), peer.lq, peer.ilq, parent = lq_graph)

  n.last_seen = datetime.now()

  # Check if we have fetched nodewatcher data
  info = nodewatcher.fetch_node_info(node_ip)
  if info is not None:
    try:
      oldUptime = n.uptime or 0
      oldChannel = n.channel or 0
      oldVersion = n.firmware_version
      n.firmware_version = info['general']['version']
      n.local_time = safe_date_convert(info['general']['local_time'])
      n.bssid = info['wifi']['bssid']
      n.essid = info['wifi']['essid']
      n.channel = nodewatcher.frequency_to_channel(info['wifi']['frequency'])
      n.clients = 0
      n.uptime = safe_uptime_convert(info['general']['uptime'])

      if oldVersion != n.firmware_version:
        Event.create_event(n, EventCode.VersionChange, '', EventSource.Monitor, data = 'Old version: %s\n  New version: %s' % (oldVersion, n.firmware_version))

      if oldUptime > n.uptime:
        Event.create_event(n, EventCode.UptimeReset, '', EventSource.Monitor, data = 'Old uptime: %s\n  New uptime: %s' % (oldUptime, n.uptime))

      if oldChannel != n.channel and oldChannel != 0:
        Event.create_event(n, EventCode.ChannelChanged, '', EventSource.Monitor, data = 'Old channel: %s\n  New channel %s' % (oldChannel, n.channel))

      if n.has_time_sync_problems():
        n.warnings = True
      
      # Parse nodogsplash client information
      oldNdsStatus = n.captive_portal_status
      if 'nds' in info:
        if 'down' in info['nds'] and info['nds']['down'] == '1':
          n.captive_portal_status = False
          n.warnings = True
        else:
          for cid, client in info['nds'].iteritems():
            if not cid.startswith('client'):
              continue

            try:
              c = APClient.objects.get(node = n, ip = client['ip'])
            except APClient.DoesNotExist:
              c = APClient(node = n)
              n.clients_so_far += 1
            
            n.clients += 1
            c.ip = client['ip']
            c.connected_at = safe_date_convert(client['added_at'])
            c.uploaded = safe_int_convert(client['up'])
            c.downloaded = safe_int_convert(client['down'])
            c.last_update = datetime.now()
            c.save()
      else:
        n.captive_portal_status = True
      
      # Check for captive portal status change
      if oldNdsStatus and not n.captive_portal_status:
        Event.create_event(n, EventCode.CaptivePortalDown, '', EventSource.Monitor)
      elif not oldNdsStatus and n.captive_portal_status:
        Event.create_event(n, EventCode.CaptivePortalUp, '', EventSource.Monitor)

      # Generate a graph for number of wifi cells
      if 'cells' in info['wifi']:
        add_graph(n, '', GraphType.WifiCells, RRAWifiCells, 'Nearby Wifi Cells', 'wificells_%s' % node_ip, safe_int_convert(info['wifi']['cells']) or 0)

      # Update node's MAC address on wifi iface
      if 'mac' in info['wifi']:
        n.wifi_mac = info['wifi']['mac']

      # Check for VPN statistics
      if 'vpn' in info:
        n.vpn_mac = info['vpn']['mac']

      # Generate a graph for number of clients
      add_graph(n, '', GraphType.Clients, RRAClients, 'Connected Clients', 'clients_%s' % node_ip, n.clients)

      # Check for IP shortage
      wifiSubnet = n.subnet_set.filter(gen_iface_type = IfaceType.WiFi, allocated = True)
      if len(wifiSubnet) and n.clients >= ipcalc.Network(wifiSubnet[0].subnet, wifiSubnet[0].cidr).size() - 4:
        Event.create_event(n, EventCode.IPShortage, '', EventSource.Monitor, data = 'Subnet: %s\n  Clients: %s' % (wifiSubnet[0], n.clients))

      # Record interface traffic statistics for all interfaces
      for iid, iface in info['iface'].iteritems():
        if iid not in ('wifi0', 'wmaster0'):
          add_graph(n, iid, GraphType.Traffic, RRAIface, 'Traffic - %s' % iid, 'traffic_%s_%s' % (node_ip, iid), iface['up'], iface['down'])
      
      # Generate load average statistics
      if 'loadavg' in info['general']:
        n.loadavg_1min, n.loadavg_5min, n.loadavg_15min, n.numproc = safe_loadavg_convert(info['general']['loadavg'])
        add_graph(n, '', GraphType.LoadAverage, RRALoadAverage, 'Load Average', 'loadavg_%s' % node_ip, n.loadavg_1min, n.loadavg_5min, n.loadavg_15min)
        add_graph(n, '', GraphType.NumProc, RRANumProc, 'Number of Processes', 'numproc_%s' % node_ip, n.numproc)

      # Generate free memory statistics
      if 'memfree' in info['general']:
        n.memfree = safe_int_convert(info['general']['memfree'])
        buffers = safe_int_convert(info['general'].get('buffers', 0))
        cached = safe_int_convert(info['general'].get('cached', 0))
        add_graph(n, '', GraphType.MemUsage, RRAMemUsage, 'Memory Usage', 'memusage_%s' % node_ip, n.memfree, buffers, cached)

      # Generate solar statistics when available
      if 'solar' in info and all([x in info['solar'] for x in ('batvoltage', 'solvoltage', 'charge', 'state', 'load')]):
        states = {
          'boost'       : 1,
          'equalize'    : 2,
          'absorption'  : 3,
          'float'       : 4
        }

        add_graph(n, '', GraphType.Solar, RRASolar, 'Solar Monitor', 'solar_%s' % node_ip,
          info['solar']['batvoltage'],
          info['solar']['solvoltage'],
          info['solar']['charge'],
          states.get(info['solar']['state'], 1),
          info['solar']['load']
        )

      # Check for installed package versions (every hour)
      try:
        last_pkg_update = n.installedpackage_set.all()[0].last_update
      except:
        last_pkg_update = None

      if not last_pkg_update or last_pkg_update < datetime.now() - timedelta(hours = 1):
        packages = nodewatcher.fetch_installed_packages(n.ip) or {}

        # Remove removed packages and update existing package versions
        for package in n.installedpackage_set.all():
          if package.name not in packages:
            package.delete()
          else:
            package.version = packages[package.name]
            package.last_update = datetime.now()
            package.save()
            del packages[package.name]

        # Add added packages
        for packageName, version in packages.iteritems():
          package = InstalledPackage(node = n)
          package.name = packageName
          package.version = version
          package.last_update = datetime.now()
          package.save()
      
      # Check if DNS works
      if 'dns' in info:
        old_dns_works = n.dns_works
        n.dns_works = info['dns']['local'] == '0' and info['dns']['remote'] == '0'
        if not n.dns_works:
          n.warnings = True

        if old_dns_works != n.dns_works:
          # Generate a proper event when the state changes
          if n.dns_works:
            Event.create_event(n, EventCode.DnsResolverRestored, '', EventSource.Monitor)
          else:
            Event.create_event(n, EventCode.DnsResolverFailed, '', EventSource.Monitor)
    except:
      logging.warning(format_exc())

  n.save()

@transaction.commit_manually
def check_mesh_status():
  """
  Performs a mesh status check.
  """
  # Remove all invalid nodes and mark subnets as not visible
  Node.objects.filter(status = NodeStatus.Invalid).delete()
  Subnet.objects.all().update(visible = False)
  APClient.objects.filter(last_update__lt = datetime.now() -  timedelta(minutes = 11)).delete()
  GraphItem.objects.filter(last_update__lt = datetime.now() - timedelta(days = 30)).delete()

  # Mark all nodes as down
  Node.objects.all().update(warnings = False, conflicting_subnets = False)
  Link.objects.all().delete()

  # Fetch routing tables from OLSR
  nodes, hna = OlsrParser.getTables(settings.MONITOR_OLSR_HOST)

  # Create a topology plotter
  topology = DotTopologyPlotter()

  # Ping nodes present in the database and visible in OLSR
  dbNodes = {}
  nodesToPing = []
  for nodeIp in nodes.keys():
    try:
      # Try to get the node from the database
      dbNodes[nodeIp] = Node.objects.get(ip = nodeIp)
      dbNodes[nodeIp].peers = len(nodes[nodeIp].links)

      # If we have succeeded, add to list
      nodesToPing.append(nodeIp)
    except Node.DoesNotExist:
      # Node does not exist, create an invalid entry for it
      n = Node(ip = nodeIp, status = NodeStatus.Invalid, last_seen = datetime.now())
      n.node_type = NodeType.Unknown
      n.warnings = True
      n.peers = len(nodes[nodeIp].links)
      n.save()
      dbNodes[nodeIp] = n
  
  # Mark invisible nodes as down
  for node in Node.objects.exclude(status = NodeStatus.Invalid):
    oldStatus = node.status

    if node.ip not in dbNodes:
      if node.status == NodeStatus.New:
        node.status = NodeStatus.Pending
      elif node.status != NodeStatus.Pending:
        node.status = NodeStatus.Down
      node.save()

    if oldStatus in (NodeStatus.Up, NodeStatus.Visible, NodeStatus.Duped) and node.status == NodeStatus.Down:
      Event.create_event(node, EventCode.NodeDown, '', EventSource.Monitor)
      
      # Invalidate uptime credit for this node
      node.uptime_last = None
      node.save()
  
  # Setup all node peerings
  for nodeIp, node in nodes.iteritems():
    n = dbNodes[nodeIp]
    oldRedundancyLink = n.redundancy_link
    n.redundancy_link = False

    for peerIp, lq, ilq, etx in node.links:
      l = Link(src = n, dst = dbNodes[peerIp], lq = float(lq), ilq = float(ilq), etx = float(etx))
      l.save()

      # Check if we have a peering with any border routers
      if l.dst.border_router:
        n.redundancy_link = True
    
    if not n.is_invalid():
      if oldRedundancyLink and not n.redundancy_link:
        Event.create_event(n, EventCode.RedundancyLoss, '', EventSource.Monitor)
      elif not oldRedundancyLink and n.redundancy_link:
        Event.create_event(n, EventCode.RedundancyRestored, '', EventSource.Monitor)

    if n.redundancy_req and not n.redundancy_link:
      n.warnings = True

    n.save()
  
  # Add nodes to topology map and generate output
  for node in dbNodes.values():
    topology.addNode(node)

  topology.save(os.path.join(settings.GRAPH_DIR, 'mesh_topology.png'))

  # Update valid subnet status in the database
  for nodeIp, subnets in hna.iteritems():
    if nodeIp not in dbNodes:
      continue

    for subnet in subnets:
      subnet, cidr = subnet.split("/")

      try:
        s = Subnet.objects.get(node__ip = nodeIp, subnet = subnet, cidr = int(cidr))
        s.last_seen = datetime.now()
        s.visible = True
        
        if s.status == SubnetStatus.Subset:
          pass
        elif s.status in (SubnetStatus.AnnouncedOk, SubnetStatus.NotAnnounced):
          s.status = SubnetStatus.AnnouncedOk
        elif not s.node.border_router or s.status == SubnetStatus.Hijacked:
          s.node.warnings = True
          s.node.save()

        s.save()
      except Subnet.DoesNotExist:
        # Subnet does not exist, prepare one
        s = Subnet(node = dbNodes[nodeIp], subnet = subnet, cidr = int(cidr), last_seen = datetime.now())
        s.visible = True

        # Check if this is a more specific prefix announce for an allocated prefix
        if Subnet.objects.ip_filter(ip_subnet__contains = '%s/%s' % (subnet, cidr)).filter(node = s.node, allocated = True).count() > 0:
          s.status = SubnetStatus.Subset
        else:
          s.status = SubnetStatus.NotAllocated
        s.save()

        # Check if this is a hijack
        n = dbNodes[nodeIp]
        try:
          origin = Subnet.objects.get(subnet = subnet, cidr = int(cidr), status__in = (SubnetStatus.AnnouncedOk, SubnetStatus.NotAnnounced))
          s.status = SubnetStatus.Hijacked
          s.save()

          # Generate an event
          Event.create_event(n, EventCode.SubnetHijacked, '', EventSource.Monitor,
                             data = 'Subnet: %s/%s\n  Allocated to: %s' % (s.subnet, s.cidr, origin.node))
        except Subnet.DoesNotExist:
          pass
        
        # Flag node entry with warnings flag (if not a border router)
        if s.status != SubnetStatus.Subset and (not n.border_router or s.status == SubnetStatus.Hijacked):
          n.warnings = True
          n.save()
      
      # Detect subnets that cause conflicts and raise warning flags for all involved
      # nodes
      if s.is_conflicting():
        s.node.warnings = True
        s.node.conflicting_subnets = True
        s.node.save()
        
        for cs in s.get_conflicting_subnets():
          cs.node.warnings = True
          cs.node.conflicting_subnets = True
          cs.node.save()
  
  # Remove (or change their status) subnets that are not visible
  Subnet.objects.filter(status__in = (SubnetStatus.NotAllocated, SubnetStatus.Subset), visible = False).delete()
  Subnet.objects.filter(status = SubnetStatus.AnnouncedOk, visible = False).update(status = SubnetStatus.NotAnnounced)

  # Remove subnets that were hijacked but are not visible anymore
  for s in Subnet.objects.filter(status = SubnetStatus.Hijacked, visible = False):
    Event.create_event(s.node, EventCode.SubnetRestored, '', EventSource.Monitor, data = 'Subnet: %s/%s' % (s.subnet, s.cidr))
    s.delete()
  
  # Ping the nodes to prepare information for later node processing
  results, dupes = PingParser.pingHosts(10, nodesToPing)
  
  if hasattr(settings, 'MONITOR_DISABLE_MULTIPROCESSING') and settings.MONITOR_DISABLE_MULTIPROCESSING:
    # Multiprocessing is disabled (the MONITOR_DISABLE_MULTIPROCESSING option is usually
    # used for debug purpuses where a single process is prefered)
    for node_ip in nodesToPing:
      process_node(node_ip, results.get(node_ip), node_ip in dupes, nodes[node_ip].links)
    
    # Commit the transaction here since we do everything in the same session
    transaction.commit()
  else:
    # We MUST commit the current transaction here, because we will be processing
    # some transactions in parallel and must ensure that this transaction that has
    # modified the nodes is commited. Otherwise this will deadlock!
    transaction.commit()
    
    worker_results = []
    for node_ip in nodesToPing:
      worker_results.append(
        WORKER_POOL.apply_async(process_node, (node_ip, results.get(node_ip), node_ip in dupes, nodes[node_ip].links))
      )
    
    # Wait for all workers to finish processing
    ex = None
    for result in worker_results:
      try:
        result.get()
      except Exception, e:
        ex = e
    
    if ex is not None:
      raise ex

if __name__ == '__main__':
  # Configure logger
  logging.basicConfig(level = logging.DEBUG,
                      format = '%(asctime)s %(levelname)-8s %(message)s',
                      datefmt = '%a, %d %b %Y %H:%M:%S',
                      filename = settings.MONITOR_LOGFILE,
                      filemode = 'a')
  
  try:
    info = getpwnam(settings.MONITOR_USER)
    
    # Change ownership of RRA directory
    os.chown(os.path.join(settings.MONITOR_WORKDIR, 'rra'), info.pw_uid, info.pw_gid)
    
    # Drop user privileges
    #os.setgid(info.pw_gid)
    #os.setuid(info.pw_uid)
  except:
    logging.warning("Failed to chown monitor RRA storage directory!")
  
  # Output warnings when debug mode is enabled
  if settings.DEBUG:
    logging.warning("Debug mode is enabled, monitor will leak memory!")
  
  if hasattr(settings, 'MONITOR_DISABLE_MULTIPROCESSING') and settings.MONITOR_DISABLE_MULTIPROCESSING:
    logging.warning("Multiprocessing mode disabled.")
  
  if hasattr(settings, 'MONITOR_DISABLE_GRAPHS') and settings.MONITOR_DISABLE_GRAPHS:
    logging.warning("Graph generation disabled.")
  
  # Create worker pool and start processing
  logging.info("wlan ljubljana mesh monitoring system is initializing...")
  WORKER_POOL = multiprocessing.Pool(processes = settings.MONITOR_WORKERS)
  try:
    while True:
      # Perform all processing
      try:
        check_mesh_status()
        check_dead_graphs()
        check_global_statistics()
        check_events()
      except:
        logging.warning(format_exc())
      
      # Go to sleep for a while
      sleep(settings.MONITOR_POLL_INTERVAL)
  except:
    logging.warning("Terminating workers...")
    WORKER_POOL.terminate()

