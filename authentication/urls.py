from django.urls import path
from . import views

app_name = "authentication"

urlpatterns = [
    path('login/', views.login_page, name='login'),
    path('register/', views.register_role, name='register_role'),
    path('register/customer/', views.register_customer, name='register_customer'),
    path('register/organizer/', views.register_organizer, name='register_organizer'),
    path('register/admin/', views.register_admin, name='register_admin'),
]