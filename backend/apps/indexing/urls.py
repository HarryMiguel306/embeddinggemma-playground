from django.urls import path

from . import views

urlpatterns = [
    path('', views.IndexingTaskListView.as_view(), name='indexing-task-list'),
    path('run/', views.IndexingRunView.as_view(), name='indexing-run'),
]
