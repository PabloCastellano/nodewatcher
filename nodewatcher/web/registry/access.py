from registry import state as registry_state

class UnknownRegistryIdentifier(Exception):
  pass

class RegistryResolver(object):
  """
  Resolves registry identifiers in a hierarchical manner.
  """
  def __init__(self, node, path = None):
    """
    Class constructor.
    
    @param node: Node instance
    @param path: Current path in the hierarhcy
    """
    self._node = node
    self._path = path
  
  def by_path(self, path, create = None, queryset = False):
    """
    Resolves the registry hierarchy.
    """
    if path in registry_state.ITEM_REGISTRY:
      # Determine which class the node is using for configuration
      top_level = registry_state.ITEM_REGISTRY[path]
      cfg = getattr(self._node, "config_{0}_{1}".format(top_level._meta.app_label, top_level._meta.module_name))
      
      if getattr(top_level.RegistryMeta, 'multiple', False):
        # Model supports multiple configuration options of this type
        if create is not None:
          if not issubclass(create, top_level):
            raise TypeError, "Not a valid registry item class for '{0}'!".format(path)
          
          return create(node = self._node)
        elif queryset:
          return cfg.all()
        else:
          return map(lambda x: x.cast(), cfg.all())
      else:
        # Only a single configuration option is supported
        try:
          return cfg.all()[0].cast()
        except (IndexError, top_level.DoesNotExist):
          if create is not None:
            if not issubclass(create, top_level):
              raise TypeError, "Not a valid registry item class for '{0}'!".format(path)
            
            return create(node = self._node)
          else:
            return None
    else:
      raise UnknownRegistryIdentifier
  
  def __getattr__(self, key):
    """
    Constructs hierarchical names by simulating attribute access.
    """
    key = key if self._path is None else "{0}.{1}".format(self._path, key)
    return RegistryResolver(self._node, key)
  
  def __call__(self, **kwargs):
    """
    Resolves the registry hierarchy.
    """
    return self.by_path(self._path, **kwargs)

class Registry(object):
  """
  A convenience class for accessing the registry via Node models.
  """
  def __get__(self, instance, owner):
    return RegistryResolver(instance)
