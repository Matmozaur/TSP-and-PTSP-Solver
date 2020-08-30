from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render
from analytics.ptsp.main_ptsp import PTSPController
import json

context_ptsp = {}
ptsp_interface = PTSPController.get_instance()


def ptsp(request):
    if request.method == 'POST':
        if 'instance' in request.FILES.keys():
            context_ptsp.clear()
            context_ptsp['uploaded_file'] = json.load(request.FILES.get('instance'))
            context_ptsp['map'] = ptsp_interface.generate_map(context_ptsp['uploaded_file']['map'])
            context_ptsp['config'] = ptsp_interface.generate_config(context_ptsp['uploaded_file']['config'])
            ptsp_interface.save_map_image('static/media/temporary.png')
            context_ptsp['map_image'] = "/static/media/temporary.png"
        else:
            pass
    return render(request, 'ptsp/ptsp.html', context_ptsp)


def ptsp_solver(request):
    if request.method == 'POST':
        if 'method' in request.POST.keys():
            method = request.POST.get("method")
            context_ptsp['method'] = method
            context_ptsp[method] = True
        else:
            pass
    return render(request, 'ptsp/ptsp_solver.html', context_ptsp)


def ptsp_file_run(request):
    if request.method == 'POST':
        if context_ptsp['method'] == "HC":
            context_ptsp['solution'] = ptsp_interface.get_hc_solution(float(request.POST.get('time')),
                                                        request.POST.get('sol_metric'))
        elif context_ptsp['method'] == "Genetic":
            context_ptsp['mutate'] = (request.POST.get('mutate') is True)
            context_ptsp['solution'] = ptsp_interface.get_genetic_solution(float(request.POST.get('time')),
                request.POST.get('sol_metric'), int(request.POST.get('population')))
        elif context_ptsp['method'] == "MCTS":
            context_ptsp['solution'] = ptsp_interface.get_mcts_solution(float(request.POST.get('time')),
                request.POST.get('sol_metric'), request.POST.get('simulation'))
        else:
            pass
        context_ptsp['length'] = len(context_ptsp['solution'].moves)
        ptsp_interface.save_sol_image('static/media/temporary_solution.png', context_ptsp['solution'])
        context_ptsp['solution_image'] = "/static/media/temporary_solution.png"
    return render(request, 'ptsp/ptsp_solver.html', context_ptsp)


def ptsp_game(request):
    return render(request, 'ptsp/ptsp_game.html', context_ptsp)
