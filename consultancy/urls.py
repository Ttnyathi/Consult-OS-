from django.urls import path

from . import views


app_name = "consultancy"

urlpatterns = [
    path("", views.home, name="home"),
    path("work/", views.work, name="work"),
    path("people/", views.people, name="people"),
    path("insights/", views.insights, name="insights"),
    path("workflow/", views.workflow, name="workflow"),
    path("careers/", views.careers, name="careers"),
    path("contact/", views.contact, name="contact"),
]
