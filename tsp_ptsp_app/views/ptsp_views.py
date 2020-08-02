
from django.shortcuts import render


def ptsp(request):
    return render(request, 'ptsp/ptsp.html')


def ptsp_file(request):
    return render(request, 'ptsp/ptsp_file.html')


def ptsp_interactive(request):
    return render(request, 'ptsp/ptsp_interactive.html')


def ptsp_game(request):
    return render(request, 'ptsp/ptsp_game.html')