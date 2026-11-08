from django.urls import path

from . import views

urlpatterns = [
    path('', views.EmbeddingListView.as_view(), name='embedding-list'),
    path('generate/', views.EmbeddingGenerateView.as_view(), name='embedding-generate'),
]
