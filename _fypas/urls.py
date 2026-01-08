# _fypas/urls.py
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from adminSection.views.auth_views import signup, user_login, user_logout, password_reset_request, password_reset_confirm, force_password_change, password_change
from adminSection.views.coordinator_views import homePage, manageProposals, manageStudents, manageSupervisors, update_student, update_supervisor, user_delete, supervisor_del, coordinator_proposal_requests,delete_announcement,update_announcement,get_announcement,add_announcement, view_documents,fyp_progress,all_projects_meetings
from adminSection.views.student_views import homeStudents, upload_document, upload_proposal, view_proposals, find_supervisors, announcements
from adminSection.views.supervisor_views import home_supervisors, assignedProjects, proposal_requests,submitted_documents, addMeetings, edit_meeting, delete_meeting, update_proposal_status, proposal_details
from adminSection.views.general_views import landingPage, user_profile, teamMates

urlpatterns = [
    path('', landingPage, name='landingPage'),
    path('login/', user_login, name='login'),
    path('signup/', signup, name='signup'),
    path('user_logout/', user_logout, name='user_logout'),
    path('home/', homePage, name='home'),
    path('manage_proposals/', manageProposals, name='manage_proposals'),
    path('manage_students/', manageStudents, name='manage_students'),
    path('manage_supervisors/', manageSupervisors, name='manage_supervisors'),
    path('home_students/', homeStudents, name='home_students'),
    path('home_supervisors/', home_supervisors, name='home_supervisors'),
    path('admin/', admin.site.urls),
    path('update_student/', update_student, name="update_student"),
    path('update_supervisor/<int:id>/', update_supervisor, name='update_supervisor'),
    path('user_delete/<int:id>/', user_delete, name='user_delete'),
    path('supervisor_del/<int:id>/', supervisor_del, name='supervisor_del'),
    path('user_profile', user_profile, name='user_profile'),
    path('force_password_change/', force_password_change, name='force_password_change'),
    path('password_change/', password_change, name='password_change'),
    path('accounts/password-reset/', password_reset_request, name='password_reset_request'),
    path('accounts/password-reset/confirm/<uidb64>/<token>/', password_reset_confirm, name='password_reset_confirm'),
    path('upload_proposal/', upload_proposal, name='upload_proposal'),
    path('upload_document/', upload_document, name='upload_document'),
    path('view_documents/', view_documents, name='view_documents'),
    path('submitted_documents/', submitted_documents, name='submitted_documents'),
    path('view_proposals/', view_proposals, name='view_proposals'),
    path('find_supervisors/', find_supervisors, name='find_supervisors'),
    path('proposal-requests/', proposal_requests, name='proposal_requests'),
    path('assignedProjects/', assignedProjects, name='assigned_projects'),
    path('add_meetings/', addMeetings, name='add_meetings'),
    path('edit-meeting/<int:meeting_id>/', edit_meeting, name='edit_meeting'),
    path('delete-meeting/<int:meeting_id>/', delete_meeting, name='delete_meeting'),
    path('announcements/', announcements, name='announcements'),
    path('proposal/<int:proposal_id>/update-status/', update_proposal_status, name='update_proposal_status'),
    path('proposal/<int:proposal_id>/details/', proposal_details, name='proposal_details'),
    path('coordinator/proposal-requests/', coordinator_proposal_requests, name='coordinator_proposal_requests'),
    path('team/', teamMates, name='team'),
    path('delete_announcement/<int:ann_id>/', delete_announcement, name='delete_announcement'),
    path('update_announcement/<int:ann_id>/', update_announcement, name='update_announcement'),
    path('get_announcement/<int:ann_id>/', get_announcement, name='get_announcement'),
    path('add_announcement/', add_announcement, name='add_announcement'),
    path('fyp_progress', fyp_progress, name='fyp_progress'),
    path('all-projects-meetings/', all_projects_meetings, name='all_projects_meetings'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)