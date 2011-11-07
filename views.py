import os

from django.conf import settings
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.shortcuts import redirect
from django.shortcuts import get_list_or_404
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.utils import simplejson

def example(req):
    return render_to_response('example.html', {})

def index(req):
    #return render_to_response('index.html', {})
    return redirect('/gentlemens_gt/standings')

#
# cheating static content handlers
#
def css(req, filename):
    return HttpResponse(
            open('%scss/%s' % (settings.MEDIA_ROOT, filename), 'rb').read(),
            mimetype='text/css'
        )

def js(req, filename):
    return HttpResponse(
            open('%sjs/%s' % (settings.MEDIA_ROOT, filename), 'rb').read(),
            mimetype='application/x-javascript'
        )

def gif(req, filename):
    return HttpResponse(
            open('%simg/%s.gif' % (settings.MEDIA_ROOT, filename), 'rb').read(),
            mimetype='image/gif'
        )

def png(req, filename):
    return HttpResponse(
            open('%simg/%s.png' % (settings.MEDIA_ROOT, filename), 'rb').read(),
            mimetype='image/png'
        )

def jpeg(req, filename, extension):
    return HttpResponse(
            open('%simg/%s.%s' % (settings.MEDIA_ROOT, filename, extension), 'rb').read(),
            mimetype='image/jpeg'
        )

def jquery_ui_images(req, theme, filename):
    return HttpResponse(
            open('%scss/%s/images/%s.png' % (settings.MEDIA_ROOT, theme, filename), 'rb').read(),
            mimetype='image/png'
        )
