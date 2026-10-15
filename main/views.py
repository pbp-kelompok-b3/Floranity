from django.shortcuts import render

# Create your views here.

def show_home(request):
    return render(request, 'home.html')

show_landing_page = show_home
