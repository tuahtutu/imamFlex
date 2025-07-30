from django.urls import path
from . import views

urlpatterns = [
    path("login", views.login, name="login"),
    path('logout', views.logout, name='logout'),

    # Admin Dashboard
    path('admin-dashboard/', views.admin_dashboard, name='adminDash'),
    path('dashboard/leave/', views.admin_leave_list, name='admin_leave_list'),
    path('dashboard/leave/approve/<int:request_id>/', views.approve_leave, name='approve_leave'),
    path('dashboard/leave/reject/<int:request_id>/', views.reject_leave, name='reject_leave'),
    path('send-manual-reminder/', views.send_manual_reminder, name='send_manual_reminder'),
    path('assign-replacement/<int:request_id>/', views.assign_replacement, name='assign_replacement'),
    path('attendance-report/', views.admin_attendance_report, name='attendance_report'),


    # Imam Management
    path('imam-management/', views.imam_management, name='imam_management'),
    path('add_imam/', views.add_imam, name='add_imam'),
    path('edit_imam/<str:imam_id>/', views.edit_imam, name='edit_imam'),
    path('delete_imam/<str:imam_id>/', views.delete_imam, name='delete_imam'),
    path('imam/schedule/', views.imam_schedule, name='imam_schedule'),  # only one
    path('imam/schedule/assign/<str:date>/', views.assign_schedule_ajax, name='assign_schedule'),

    # Muazzin Management
    path('muazzin-management/', views.muazzin_management, name='muazzin_management'),
    path('add_muazzin/', views.add_muazzin, name='add_muazzin'),
    path('edit_muazzin/<str:muazzin_id>/', views.edit_muazzin, name='edit_muazzin'),
    path('delete_muazzin/<str:muazzin_id>/', views.delete_muazzin, name='delete_muazzin'),
    path('muazzin/schedule/', views.muazzin_schedule, name='muazzin_schedule'),
    path('muazzin/schedule/assign/<str:date>/', views.assign_muazzin_schedule_ajax, name='assign_muazzin_schedule'),


    # Siak Management
    path('siak-management/', views.siak_management, name='siak_management'),
    path('add_siak/', views.add_siak, name='add_siak'),
    path('edit_siak/<str:siak_id>/', views.edit_siak, name='edit_siak'),
    path('delete_siak/<str:siak_id>/', views.delete_siak, name='delete_siak'),
    path('siak/schedule/', views.siak_schedule, name='siak_schedule'), 
    path('siak/schedule/assign/<str:date>/', views.assign_siak_schedule_ajax, name='assign_siak_schedule'),

    #Khutbah
    path('khutbah/', views.khutbah_list, name='khutbah_list'),
    path('khutbah/add/', views.add_khutbah, name='add_khutbah'),
    path('khutbah/edit/<int:khutbah_id>/', views.edit_khutbah, name='edit_khutbah'),
    path('khutbah/delete/<int:khutbah_id>/', views.delete_khutbah, name='delete_khutbah'),

    #===IMAM SIDE===#
    path('imam-dashboard/', views.imam_dashboard, name='imamDash'),
    path('imam/profile/', views.imam_profile, name='imam_profile'),
    path('imam-schedule/', views.imam_schedule_side, name='imam_schedule_side'),
    path('apply-leave/', views.apply_leave, name='apply_leave'),
    path('permohonan-cuti/', views.imam_leave_history, name='imam_leave_history'),
    path('imam/kehadiran/', views.imam_attendance, name='imam_attendance'),
    path('imam/kehadiran/mark/', views.mark_attendance, name='mark_attendance'),
    
    #=====MUAZZIN SIDE====
    path('muazzin-dashboard/', views.muazzin_dashboard, name='muazzinDash'),
    path('muazzin-schedule/', views.muazzin_schedule_side, name='muazzin_schedule_side'),
    path('muazzin-apply-leave/', views.apply_leave_muazzin, name='apply_leave_muazzin'),
    path('muazzin-permohonan-cuti/', views.muazzin_leave_history, name='muazzin_leave_history'),
    path('muazzin/attendance/', views.muazzin_attendance, name='muazzin_attendance'),
    path('muazzin/attendance/mark/', views.mark_attendance_muazzin, name='mark_attendance_muazzin'),
    path('muazzin-profile/', views.muazzin_profile, name='muazzin_profile'),

    #=====SIAK SIDE=====
    path('siak-profile/', views.siak_profile, name='siak_profile'),
    path('siak-dashboard/', views.siak_dashboard, name='siakDash'),
    path('siak-schedule/', views.siak_schedule_side, name='siak_schedule_side'),
    path('siak-leave/apply/', views.apply_leave_siak, name='apply_leave_siak'),
    path('siak-leave/history/', views.siak_leave_history, name='siak_leave_history'),
    path('siak-attendance/', views.siak_attendance, name='siak_attendance'),
    path('siak-attendance/mark/', views.mark_attendance_siak, name='mark_attendance_siak'),



    #=====JEMAAH SIDE=====
    path('', views.jemaah_home, name='jemaah_home'),
    path('jemaah/khutbah/', views.jemaah_khutbah, name='jemaah_khutbah'),
    path('jemaah/khutbah/<int:khutbah_id>/', views.khutbah_detail, name='khutbah_detail'),
    path('ajk-info/', views.ajk_info, name='ajk_info')

   
]
