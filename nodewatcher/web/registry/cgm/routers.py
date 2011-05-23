import copy
import inspect

from django.core.exceptions import ImproperlyConfigured

from web.registry import registration

class RouterPort(object):
  """
  An abstract descriptor of a router port.
  """
  def __init__(self, identifier, description):
    """
    Class constructor.
    """
    self.identifier = identifier
    self.description = description

class EthernetPort(RouterPort):
  """
  Describes a router's ethernet port.
  """
  pass

class RouterRadio(object):
  """
  An abstract descriptor of a router radio.
  """
  def __init__(self, identifier, description):
    """
    Class constructor.
    """
    self.identifier = identifier
    self.description = description

class IntegratedRadio(RouterRadio):
  """
  Describes a router's integrated radio.
  """
  pass

class MiniPCIRadio(RouterRadio):
  """
  Describes a router's MiniPCI slot for a radio.
  """
  pass

# A list of attributes that are required to be defined
REQUIRED_ROUTER_ATTRIBUTES = set([
  'identifier',
  'name',
  'architecture',
  'radios',
  'ports',
])

class RouterMeta(type):
  """
  Type for router descriptors.
  """
  def __new__(cls, name, bases, attrs):
    """
    Creates a new RouterBase class.
    """
    new_class = type.__new__(cls, name, bases, attrs)
    
    if name != 'RouterBase':
      # Validate the presence of all attributes
      required_attrs = copy.deepcopy(REQUIRED_ROUTER_ATTRIBUTES)
      for attr in attrs:
        if attr.startswith('_'):
          continue
        
        if isinstance(attrs[attr], staticmethod):
          function = getattr(new_class, attr)
          if not getattr(function, 'cgm_module', False):
            raise ImproperlyConfigured("Function '{0}' is not marked as a CGM module! Only such functions are allowed in router descriptors!".format(attr))
          else:
            continue
        
        if attr not in required_attrs:
          raise ImproperlyConfigured("Attribute '{0}' is not a valid router model attribute!".format(attr))
        
        required_attrs.remove(attr)
      
      if len(required_attrs) > 0:
        raise ImproperlyConfigured("The following attributes are required for router model specification: {0}!".format(
          ", ".join(required_attrs)
        ))
      
      # Router ports and radios cannot both be empty
      if not len(attrs['radios']) and not len(attrs['ports']):
        raise ImproperlyConfigured("A router cannot be without radios and ports!")
      
      # Validate that list of ports only contains RouterPort instances
      if len([x for x in attrs['ports'] if not isinstance(x, RouterPort)]):
        raise ImproperlyConfigured("List of router ports may only contain RouterPort instances!")
      
      # Validate that list of radios only contains RouterRadio instances
      if len([x for x in attrs['radios'] if not isinstance(x, RouterRadio)]):
        raise ImproperlyConfigured("List of router radios may only contain RouterRadio instances!")
    
    return new_class

class RouterBase(object):
  """
  An abstract router hardware descriptor.
  """
  __metaclass__ = RouterMeta
  
  @classmethod
  def register(cls, platform):
    """
    Performs router model registration.
    """
    # Register a new choice in the configuration registry
    registration.point("node.config").register_choice("core.general#router", cls.identifier, cls.name,
      limited_to = ("core.general#platform", platform.name)
    )
    
    # Register a new choice for available router ports
    for port in cls.ports:
      registration.point("node.config").register_choice("core.interfaces#eth_port", port.identifier, port.description,
        limited_to = ("core.general#router", cls.identifier)
      )
    
    # Register a new choice for available router radios
    for radio in cls.radios:
      registration.point("node.config").register_choice("core.interfaces#wifi_radio", radio.identifier, radio.description,
        limited_to = ("core.general#router", cls.identifier)
      )
    
    # Register CGM methods
    for _, function in inspect.getmembers(cls, inspect.isfunction):
      if function.cgm_module_platform is None or function.cgm_module_platform == platform.name:
        platform.register_module(
          function.cgm_module_order,
          function,
          cls.identifier
        )
  
  def __init__(self):
    """
    Prevent instantiation of this class.
    """
    raise TypeError("Router model descriptors are non-instantiable!")
  
  def __setattr__(self, key, value):
    """
    Prevent modification of router model descriptors.
    """
    raise AttributeError("Router model descriptors are immutable!")

def register_module(platform = None, order = 1):
  """
  Marks a method to be registered as a CGM upon router registration.
  """
  def wrapper(f):
    f.cgm_module = True
    f.cgm_module_order = order
    f.cgm_module_platform = platform
    return staticmethod(f)
  
  return wrapper
