from django.urls import path
from . import views

urlpatterns = [
    path('', views.overview, name='overview'),
    path('ai/', views.ai_intelligence, name='ai_intelligence'),
    path('gamification/', views.gamification, name='gamification'),
    path('api/live/', views.api_live, name='api_live'),
]