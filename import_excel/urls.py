from django.urls import path
from . import views

urlpatterns = [
    path('modele-approvisionnement/', views.download_template, name='download_template'),
    path('import-approvisionnement/', views.import_approvisionnement, name='import_approvisionnement'),
    path('modele-articles/', views.download_template_articles, name='download_template_articles'),
    path('import-articles/', views.import_articles, name='import_articles'),
    path('modele-sortie/', views.download_template_sortie, name='download_template_sortie'),
    path('import-sortie/', views.import_sortie, name='import_sortie'),
]
