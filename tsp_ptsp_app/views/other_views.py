from .tsp_views import context_tsp
from .ptsp_views import context_ptsp
from tsp_ptsp_app.connector import load_all_tsp, load_all_ptsp
from django.shortcuts import render


def home(request):
    context_tsp.clear()
    context_ptsp.clear()
    return render(request, 'home.html')


def saved(request):
    data_tsp = load_all_tsp()
    data_ptsp = load_all_ptsp()
    context_dic = {'data_tsp': data_tsp, 'data_ptsp': data_ptsp}
    return render(request, 'other/saved.html', context_dic)


def description(request):
    return render(request, 'other/description.html')


def graph_theory(request):
    return render(request, 'other/graph_theory.html')


def gen_desc(request):
    return render(request, 'other/gen_desc.html')


def mcts_desc(request):
    return render(request, 'other/mcts_desc.html')


def tsp_desc(request):
    return render(request, 'other/tsp_desc.html')


def tsp_methods_desc(request):
    return render(request, 'other/tsp_methods_desc.html')


def ptsp_desc(request):
    return render(request, 'other/ptsp_desc.html')


def ptsp_methods_desc(request):
    return render(request, 'other/ptsp_methods_desc.html')
