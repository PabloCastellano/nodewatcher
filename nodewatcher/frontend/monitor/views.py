import os

from celery.exceptions import TimeoutError

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, Http404
from django.views.decorators.cache import cache_control
from django.views.static import serve

from frontend.monitor import tasks as monitor_tasks

@cache_control(max_age = 300)
def graph_image(request, graph_id, timespan):
  """
  Serves the graph image, requesting graph redraw when necessary.
  """
  if timespan not in settings.GRAPH_TIMESPANS:
    raise Http404
  
  graph_file = '{0}-{1}.png'.format(graph_id, timespan)
  if not settings.ENABLE_GRAPH_DISPLAY:
    # When graph display is disabled, we show some default image
    graph_file = 'graphs-disabled.png'
  elif not cache.get('nodewatcher.graphs.drawn.{0}.{1}'.format(graph_id, timespan)):
    # First ensure that the graph is actually drawn
    try:
      monitor_tasks.draw_graph.delay(graph_id, timespan).get(timeout = 1)
    except TimeoutError:
      pass
  
  # Send the proper file
  if settings.DEBUG:
    return serve(request, os.path.join(settings.GRAPH_DIR, graph_file), '/')
  else:
    response = HttpResponse()
    response['X-Sendfile'] = os.path.join(settings.GRAPH_DIR, graph_file)
    response['X-Accel-Redirect'] = '/_graphs/{0}'.format(graph_file)
    response['Content-Type'] = 'image/png'
    return response

