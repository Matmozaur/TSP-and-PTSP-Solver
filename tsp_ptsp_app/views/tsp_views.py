from django.views.decorators.csrf import ensure_csrf_cookie
from analytics.tsp.main_tsp import TSPController
from tsp_ptsp_app.connector import save_tsp
from django.shortcuts import render
import json

context_tsp = {}
tsp_interface = TSPController.get_instance()


def tsp_file(request):
    if request.method == 'POST':
        if 'instance' in request.FILES.keys():
            context_tsp.clear()
            context_tsp['uploaded_file'] = json.load(request.FILES.get('instance'))
            context_tsp['instance'] = tsp_interface.generate_graph(context_tsp['uploaded_file'])
            tsp_interface.save_graph_image('static/media/temporary.png')
            context_tsp['graph_image'] = "/static/media/temporary.png"
        elif 'method' in request.POST.keys():
            method = request.POST.get("method")
            context_tsp['method'] = method
            context_tsp[method] = True
            if context_tsp['method'] == "Random":
                tsp_file_run(request)
        else:
            pass
    return render(request, 'tsp/tsp_file.html', context_tsp)


def tsp_file_run(request):
    if context_tsp['method'] == "Random":
        context_tsp['solution'] = tsp_interface.get_random_solution()
    elif request.method == 'POST':
        if context_tsp['method'] == "HC":
            context_tsp['solution'] = tsp_interface.get_hc_solution(float(request.POST.get('time')))
        elif context_tsp['method'] == "Genetic":
            context_tsp['mutate'] = (request.POST.get('mutate') is True)
            context_tsp['solution'] = tsp_interface.get_genetic_solution(float(request.POST.get('time')),
                int(request.POST.get('population')), bool(context_tsp['mutate']))
        elif context_tsp['method'] == "MCTS":
            context_tsp['solution'] = tsp_interface.get_mcts_solution(float(request.POST.get('time')),
                request.POST.get('simulation'))
        else:
            pass
    context_tsp['weight'] = context_tsp['solution'].cost
    context_tsp['core solution'] = HC = context_tsp['solution'].HC
    context_tsp['solution'] = context_tsp['solution'].Graph.edge_subgraph(
        [(HC[i], HC[(i+1) % len(HC)]) for i in range(len(HC))]).copy()
    context_tsp['solution'] = tsp_interface.relabel(context_tsp['solution'])
    tsp_interface.save_graph_image('static/media/temporary_solution.png', context_tsp['solution'], True)
    context_tsp['solution_image'] = "/static/media/temporary_solution.png"
    return render(request, 'tsp/tsp_file.html', context_tsp)


def tsp_save(request):
    if request.method == 'POST':
        try:
            save_tsp(context_tsp['uploaded_file'], context_tsp['core solution'], request.POST.get('Name'),
                     request.POST.get('Description'))
        except:
            context_tsp['nunique'] = True
    return render(request, 'tsp/tsp_file.html', context_tsp)
