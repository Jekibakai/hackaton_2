from django.urls import path
from . import views

urlpatterns = [
    path('', views.overview, name='overview'),
    path('ai/', views.ai_intelligence, name='ai_intelligence'),
    path('gamification/', views.gamification, name='gamification'),
    path('manage/classes/', views.manage_classes, name='manage_classes'),
    path('classrooms/', views.classrooms, name='classrooms'),
    path('api/live/', views.api_live, name='api_live'),
    path('api/ratings/', views.api_ratings, name='api_ratings'),
    path('api/classroom/', views.api_classroom_status, name='api_classroom_status'),
    path('export/anomalies/', views.export_anomalies_csv, name='export_anomalies_csv'),
]
