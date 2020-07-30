
from django.shortcuts import render
context = {}


def home(request):
    context.clear()
    print(request)
    return render(request, 'home.html')


