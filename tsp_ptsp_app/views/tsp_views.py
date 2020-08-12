from django.views.decorators.csrf import ensure_csrf_cookie
from analytics.tsp.main_tsp import TSPController
from django.shortcuts import render
import json

context = {}
tsp_interface = TSPController.get_instance()


def tsp(request):
    context.clear()
    return render(request, 'tsp/tsp.html', context)


def tsp_file(request):
    if request.method == 'POST':
        if 'instance' in request.FILES.keys():
            context.clear()
            uploaded_file = json.load(request.FILES.get('instance'))
            context['instance'] = tsp_interface.generate_graph(uploaded_file)
            tsp_interface.save_graph_image('static/media/temporary.png')
            context['graph_image'] = "/static/media/temporary.png"
        elif 'method' in request.POST.keys():
            method = request.POST.get("method")
            context['method'] = method
            context[method] = True
            if context['method'] == "Random":
                tsp_file_run(request)
        else:
            pass
    return render(request, 'tsp/tsp_file.html', context)


def tsp_interactive(request):
    return render(request, 'tsp/tsp_interactive.html', context)


def tsp_file_run(request):
    if context['method'] == "Random":
        context['solution'] = tsp_interface.get_random_solution()
    elif request.method == 'POST':
        if context['method'] == "HC":
            context['solution'] = tsp_interface.get_hc_solution(float(request.POST.get('time')))
        elif context['method'] == "Genetic":
            context['mutate'] = (request.POST.get('mutate') is True)
            context['solution'] = tsp_interface.get_genetic_solution(float(request.POST.get('time')),
                int(request.POST.get('population')), bool(context['mutate']))
        elif context['method'] == "MCTS":
            context['solution'] = tsp_interface.get_mcts_solution(float(request.POST.get('time')),
                boolean(request.POST.get('simulation')))
        else:
            pass
    context['weight'] = context['solution'].cost
    HC = context['solution'].HC
    context['solution'] = context['solution'].Graph.edge_subgraph(
        [(HC[i], HC[(i+1) % len(HC)]) for i in range(len(HC))]).copy()
    context['solution'] = tsp_interface.relabel(context['solution'])
    tsp_interface.save_graph_image('static/media/temporary_solution.png', context['solution'], True)
    context['solution_image'] = "/static/media/temporary_solution.png"
    return render(request, 'tsp/tsp_file.html', context)


def tsp_save(request):
    return render(request, 'tsp/tsp_file.html', context)
