
from django.shortcuts import render


def home(request):
    return render(request, 'home.html')


def saved(request):
    return render(request, 'other/saved.html')


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
