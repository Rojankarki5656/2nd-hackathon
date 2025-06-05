from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.user_login, name='core-login'), 
    path('signup/', views.signup, name='core-signup'),
    path('user-about/', views.user_about, name='core-about-user'),
    path('dashboard/', views.dashboard, name='core-dashboard'),
    path('community-watch/', views.community_watch, name='core-community_watch'),
    path('ai-waste-dashboard/', views.ai_waste_dashboard, name='core-ai_waste_dashboard'),
    path('ai_waste_chatbot/', views.ai_waste_chatbot, name='core-ai_waste_chatbot'),
    path('ingredient-scanner-dashboard/', views.ingredient_scanner_dashboard, name='core-ingredient_scanner_dashboard'),
    path('donation-portal-dashboard/', views.donation_portal_dashboard, name='core-donation_portal_dashboard'),
    path('impact-analytics-dashboard/', views.impact_analytics_dashboard, name='core-impact_analytics_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='core-admin_dashboard'),
    path('logout/', views.logout_view, name='core-logout'),
    path('product/add/', views.add_product, name='add-product'),
    path('profile/', views.profile, name='core-profile'),
    path('ingredient_scanner_dashboard/', views.check_safety, name='core-check_safety'),
    path('donation/details/<int:product_id>/', views.donation_details, name='donation-details'),
    path('product/delete/<int:product_id>/', views.delete_product, name='delete-product'),
    path('donation/<int:product_id>/', views.donation_create, name='donation-create'),
    path('community-watch/comment/<int:report_id>/', views.add_comment, name='add-comment'),
    path('community-watch/delete/<int:report_id>/', views.delete_community_report, name='delete-community-report'),
    path('donation-history/', views.donation_history, name='donation-history'),
]