from django.shortcuts import render


def home(request):
    return render(request, "website/tk_research_consultancy.html")


def work(request):
    return render(request, "website/work.html")


def people(request):
    return render(request, "website/people.html")


def insights(request):
    return render(request, "website/insights.html")


def workflow(request):
    return render(request, "website/workflow.html")


def careers(request):
    return render(request, "website/careers.html")


def contact(request):
    return render(request, "website/contact.html")
