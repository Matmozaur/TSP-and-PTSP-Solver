"""erteterter URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls import url
from tsp_ptsp_app import views
from django.conf.urls.static import static
from django.conf import settings
# from django.conf.urls.i18n import i18n_patterns
# from django.utils.translation import ugettext_lazy as _


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    # url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^$', views.home, name='home'),
    url(r'^tsp/', views.tsp, name='tsp'),
    url(r'^ptsp/', views.ptsp, name='ptsp'),
    url(r'^saved/', views.saved, name='saved'),
    url(r'^description/', views.description, name='description'),
    url(r'^graph_theory/', views.graph_theory, name='graph_theory'),
    url(r'^gen_desc/', views.gen_desc, name='gen_desc'),
    url(r'^mcts_desc/', views.mcts_desc, name='mcts_desc'),
    url(r'^tsp_desc/', views.tsp_desc, name='tsp_desc'),
    url(r'^tsp_methods_desc/', views.tsp_methods_desc, name='tsp_methods_desc'),
    url(r'^ptsp_desc/', views.ptsp_desc, name='ptsp_desc'),
    url(r'^ptsp_methods_desc/', views.ptsp_methods_desc, name='ptsp_methods_desc'),
    url(r'^tsp_file/', views.tsp_file, name='tsp_file'),
    url(r'^tsp_interactive/', views.tsp_interactive, name='tsp_interactive'),
    url(r'^ptsp_file/', views.ptsp_file, name='ptsp_file'),
    url(r'^ptsp_interactive/', views.ptsp_interactive, name='ptsp_interactive'),
    url(r'^ptsp_game/', views.ptsp_game, name='ptsp_game'),
    url(r'^tsp_file_run/', views.tsp_file_run, name='tsp_file_run'),
    url(r'^tsp_save/', views.tsp_save, name='tsp_save'),
]

urlpatterns+=static(settings.STATIC_URL,document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
