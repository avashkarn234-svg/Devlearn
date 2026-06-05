from django.urls import path
from . import views

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('courses/<int:course_id>/lessons/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('lessons/<int:lesson_id>/complete/', views.mark_lesson_complete, name='mark_lesson_complete'),
    path('pset/<int:lesson_id>/submit/', views.pset_submit, name='pset_submit'),
    path('editor/<int:submission_id>/', views.code_editor, name='code_editor'),
    path('api/execute/', views.execute_code, name='execute_code'),
    path('payment/', views.payment_page, name='payment_page'),
    path('payment/pending/', views.payment_pending, name='payment_pending'),
    path('portfolio/<str:username>/', views.portfolio, name='portfolio'),
    path('my-portfolio/', views.my_portfolio, name='my_portfolio'),
    path('addons/', views.addons, name='addons'),
]