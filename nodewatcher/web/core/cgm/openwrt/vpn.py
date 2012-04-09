from django.utils.translation import ugettext as _

from web.registry.cgm import base as cgm_base
from web.registry import registration

@cgm_base.register_platform_module("openwrt", 50)
def openvpn(node, cfg):
  """
  Generates configuration for OpenVPN.
  """
  # TODO
  pass

# Add OpenVPN to list of supported VPN solutions
registration.point("node.config").register_choice("core.vpn.server#protocol", "openvpn", _("OpenVPN"))
