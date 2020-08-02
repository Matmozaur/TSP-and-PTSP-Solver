
from django.shortcuts import render
context = {}


def tsp(request):
    return render(request, 'tsp/tsp.html', context)


def tsp_file(request):
    return render(request, 'tsp/tsp_file.html', context)


def tsp_interactive(request):
    return render(request, 'tsp/tsp_interactive.html', context)


def tsp_file_run(request):
    return render(request, 'tsp/tsp_file.html', context)


def tsp_save(request):
    return render(request, 'tsp/tsp_file.html', context)