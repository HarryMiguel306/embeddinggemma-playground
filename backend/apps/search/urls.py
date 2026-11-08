from django.urls import path

from . import views

urlpatterns = [
    path('text/', views.SearchTextView.as_view(), name='search-text'),
    path('image/', views.SearchImageView.as_view(), name='search-image'),
]
