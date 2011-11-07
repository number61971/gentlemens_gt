from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^gentlemens_gt/', include('gentlemens_gt.foo.urls')),
    (r'^gentlemens_gt/?$', 'gentlemens_gt.views.index'),
    (r'^gentlemens_gt/example.html$', 'gentlemens_gt.views.example'),

    (r'^gentlemens_gt/static/css/(?P<theme>[^/]+)/images/(?P<filename>[^.]+).png$', 'gentlemens_gt.views.jquery_ui_images'),
    (r'^gentlemens_gt/static/css/(?P<filename>.+)$', 'gentlemens_gt.views.css'),
    (r'^gentlemens_gt/static/js/(?P<filename>.+)$', 'gentlemens_gt.views.js'),
    (r'^gentlemens_gt/static/img/(?P<filename>[^.]+)\.gif$', 'gentlemens_gt.views.gif'),
    (r'^gentlemens_gt/static/img/(?P<filename>[^.]+)\.png$', 'gentlemens_gt.views.png'),
    (r'^gentlemens_gt/static/img/(?P<filename>[^.]+)\.(?P<extension>jpe?g)$', 'gentlemens_gt.views.jpeg'),

    (r'^gentlemens_gt/', include('gentlemens_gt.gt.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)
