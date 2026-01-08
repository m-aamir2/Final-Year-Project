from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from ..decorators import coordinator_required
from django.core.mail import EmailMessage
from django.conf import settings
from django.db.models import Count
from ..models import Profile, Proposal
from adminSection.models import *
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from ..decorators import coordinator_required
from django.core.mail import EmailMessage
from ..models import Profile, Proposal
from adminSection.models import *


@login_required
@coordinator_required
def homePage(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        message_text = request.POST.get('message')
        deadline = request.POST.get('deadline') or None
        ann_type = request.POST.get('type')
        post_date = timezone.now().date()
        # ✅ FIX: Ensure post_date is valid and created_by is always set
        ann = Announcement.objects.create(
            title=title,
            message=message_text,
            post_date=post_date,
            deadline=deadline if deadline else None,
            type=ann_type,
            created_by=request.user, 
        )

        # ✅ Send email to all students (same as before)
        students = Profile.objects.filter(user_type='student').select_related('user')
        student_emails = [s.user.email for s in students if s.user.email]
        if student_emails:
            html_content = f"""
                <html>
                <body style="margin: 0; padding: 0; background-color: #f4f4f4;">
                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px 0;">
                    <tr><td align="center">
                        <table width="600" cellpadding="0" cellspacing="0"
                            style="background-color: #ffffff; border-radius: 8px; padding: 40px;
                            font-family: 'Segoe UI', Roboto, Arial, sans-serif; color: #333333;
                            box-shadow: 0 0 10px rgba(0,0,0,0.08);">
                            <tr><td align="center" style="padding-bottom: 20px;">
                                <h2 style="margin: 0; font-size: 26px; color: #222;">📢 New {ann_type} Announcement</h2>
                            </td></tr>
                            <tr><td style="font-size: 16px; line-height: 1.6;">
                                <p>Dear Students,</p>
                                <p><strong>{title}</strong></p>
                                <p>{message_text}</p>
                                {"<p><strong>Deadline:</strong> " + deadline + "</p>" if deadline else ""}
                                <p style="margin-top: 30px;">Best regards,<br><strong>FYPAS Admin Team</strong></p>
                            </td></tr>
                            <tr><td align="center" style="font-size: 12px; color: #999999; padding-top: 30px;">
                                <p>© {timezone.now().year} FYPAS. All rights reserved.</p>
                            </td></tr>
                        </table>
                    </td></tr></table>
                </body></html>
            """
            email = EmailMessage(
                subject=f'FYPAS Announcement: {ann_type} - {title}',
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                bcc=student_emails,
            )
            email.content_subtype = "html"
            try:
                email.send()
                messages.success(request, f'{ann_type} announcement posted and emails sent successfully.')
            except Exception:
                messages.warning(request, 'Announcement posted, but failed to send emails.')
        else:
            messages.success(request, 'Announcement posted (no students to notify).')

    # --- Dashboard Stats ---
    total_students = Profile.objects.filter(user_type='student').count()
    total_supervisors = Profile.objects.filter(user_type='supervisor').count()
    active_projects_count = Proposal.objects.filter(status='approved').count()
    pending_proposals_count = Proposal.objects.filter(status='supervisor_approved').count()
    announcements = Announcement.objects.all().order_by('-created_at')

    context = {
        'total_students': total_students,
        'total_supervisors': total_supervisors,
        'active_projects_count': active_projects_count,
        'pending_proposals_count': pending_proposals_count,
        'firstname': request.user.first_name,
        'announcements': announcements,
        'header_title': 'Home',
    }
    return render(request, 'coordinators/index.html', context)

@login_required
@coordinator_required
def update_announcement(request, ann_id):
    ann = get_object_or_404(Announcement, id=ann_id)
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        ann.title = data.get('title')
        ann.message = data.get('message')
        ann.deadline = data.get('deadline') or None
        ann.type = data.get('type')
        if 'file' in request.FILES:
            ann.file = request.FILES['file']
        ann.save()
        # send email update
        students = Profile.objects.filter(user_type='student').select_related('user')
        emails = [s.user.email for s in students if s.user.email]

        if emails:
            html_content = f"""
            <html><body style='font-family:Segoe UI, sans-serif;'>
            <h2>📅 {ann.type} Update</h2>
            <p>The announcement <b>{ann.title}</b> has been updated.</p>
            {"<p><b>New Deadline:</b> " + str(ann.deadline) + "</p>" if ann.deadline else ""}
            <p>Please check the portal for updated details.</p>
            <p>Regards,<br><b>FYPAS Team</b></p>
            </body></html>
            """

            email = EmailMessage(
                subject=f'{ann.type} Updated: {ann.title}',
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                bcc=emails,
            )
            email.content_subtype = "html"

            # ✅ Attach uploaded file if present
            if ann.file:
                try:
                    email.attach_file(ann.file.path)
                except Exception as e:
                    print(f"Error attaching file: {e}")

            email.send(fail_silently=True)

        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@login_required
@coordinator_required
def add_announcement(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        message_text = request.POST.get('message')
        post_date = timezone.now().date()
        deadline = request.POST.get('deadline') or None
        ann_type = request.POST.get('type')
        file = request.FILES.get('file')

        ann = Announcement.objects.create(
            title=title,
            message=message_text,
            post_date=post_date,
            deadline=deadline if deadline else None,
            type=ann_type,
            file=file,
            created_by=request.user,
        )

        # ✅ Get all student emails
        students = Profile.objects.filter(user_type='student').select_related('user')
        student_emails = [s.user.email for s in students if s.user.email]

        if student_emails:
            # Email content (HTML)
            html_content = f"""
                <html>
                <body style="margin:0;padding:0;background-color:#f9fafb;font-family:'Segoe UI',Roboto,Arial,sans-serif;">
                    <table width="100%" cellpadding="0" cellspacing="0" style="padding:20px 0;">
                        <tr>
                            <td align="center">
                                <table width="600" cellpadding="0" cellspacing="0" 
                                    style="background-color:#ffffff;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.05);overflow:hidden;">
                                    <tr style="background-color:#2563eb;">
                                        <td align="center" style="padding:25px;">
                                            <h1 style="color:#ffffff;margin:0;font-size:24px;font-weight:600;">📢 New {ann_type} Announcement</h1>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding:30px;color:#374151;font-size:16px;line-height:1.6;">
                                            <p>Dear Students,</p>
                                            <p>A new announcement has been posted on the <strong>FYPAS Portal</strong>.</p>
                                            <div style="border-left:4px solid #2563eb;padding-left:15px;margin:20px 0;">
                                                <p style="font-size:18px;font-weight:600;margin:0 0 10px;">{title}</p>
                                                <p style="margin:0 0 10px;">{message_text}</p>
                                                {"<p style='margin:0 0 10px;'><strong>Deadline:</strong> " + deadline + "</p>" if deadline else ""}
                                            </div>
                                            <p>Please log in to the 
                                            <a href="http://16.171.8.211/" style="color:#2563eb;text-decoration:none;font-weight:500;">FYPAS portal</a> 
                                            for full details and updates.</p>
                                            <p style="margin-top:30px;">Best regards,<br><strong>FYPAS Coordination Team</strong></p>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="center" style="background-color:#f3f4f6;padding:15px;color:#6b7280;font-size:13px;">
                                            <p style="margin:0;">© {timezone.now().year} FYPAS — All Rights Reserved</p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </body>
                </html>
            """

            email = EmailMessage(
                subject=f'📢 FYPAS Announcement: {ann_type} - {title}',
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                bcc=student_emails,
            )
            email.content_subtype = "html"

            if ann.file:
                email.attach_file(ann.file.path)

            try:
                email.send()
                return JsonResponse({'success': True, 'message': 'Announcement posted and emails sent successfully.'})
            except Exception as e:
                return JsonResponse({'success': True, 'message': f'Announcement posted, but email sending failed: {str(e)}'})
        else:
            return JsonResponse({'success': True, 'message': 'Announcement posted (no student emails found).'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)

@login_required
@coordinator_required
def get_announcement(request, ann_id):
    """Get announcement data for updating"""
    ann = get_object_or_404(Announcement, id=ann_id)
    return JsonResponse({
        'success': True,
        'announcement': {
            'id': ann.id,
            'title': ann.title,
            'message': ann.message,
            'deadline': ann.deadline.strftime('%Y-%m-%d') if ann.deadline else None,
            'type': ann.type,
            'file': ann.file.url if ann.file else None,
        }
    })

@login_required
@coordinator_required
def delete_announcement(request, ann_id):
    if request.method == 'POST':
        try:
            ann = get_object_or_404(Announcement, id=ann_id)
            # Remove the created_by check if you want coordinators to delete any announcement
            # ann = get_object_or_404(Announcement, id=ann_id, created_by=request.user)
            ann_title = ann.title
            ann.delete()
            return JsonResponse({'success': True, 'message': f'Announcement "{ann_title}" deleted successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

@login_required
@coordinator_required
def manageProposals(request):
    if request.user.profile.user_type != 'coordinator':
        messages.error(request, 'Only coordinators can view this page.')
        return redirect('/')
    
    proposals = Proposal.objects.exclude(status='pending').select_related('submitted_by').prefetch_related('group_members', 'supervisors')
    has_supervisor_approved = proposals.filter(status='supervisor_approved').exists()
    STATUS_CHOICES = [
        ('supervisor_approved', 'Supervisor Approved'),
        ('approved', 'Fully Approved'),
        ('rejected', 'Rejected'),
    ]
    
    context = {
        'proposals': proposals,
        'user_role': 'coordinator',
        'status_choices': STATUS_CHOICES,
        'header_title': 'Manage Proposals',
        'has_supervisor_approved': has_supervisor_approved,  # ✅ add this flag
    }
    return render(request, 'coordinators/manage_proposals.html', context)

@login_required
@coordinator_required
def manageStudents(request):
    p = Profile.objects.filter(user_type='student')
    context = {'p': p,
               'header_title': 'Manage Students',
               }
    return render(request, 'coordinators/manage_students.html', context)

@login_required
@coordinator_required
def manageSupervisors(request):
    supervisors = Profile.objects.filter(user_type='supervisor')
    context = {
        'supervisors': supervisors,
        'header_title': 'Manage Supervisors',
        }
    return render(request, 'coordinators/manage_supervisors.html', context)

@login_required
@coordinator_required
def coordinator_proposal_requests(request):
    if request.user.profile.user_type != 'coordinator':
        messages.error(request, 'Only coordinators can view this page.')
        return redirect('/')
    
    proposals = Proposal.objects.filter(status='supervisor_approved').select_related('submitted_by').prefetch_related('group_members', 'supervisors')
    STATUS_CHOICES = [
        ('supervisor_approved', 'Supervisor Approved'),
        ('approved', 'Fully Approved'),
        ('rejected', 'Rejected'),
    ]
    
    context = {
        'proposals': proposals,
        'user_role': 'coordinator',
        'status_choices': STATUS_CHOICES,
        'header_title': 'Proposal Requests',
    }
    return render(request, 'coordinators/manage_proposals.html', context)

@login_required
@coordinator_required
def update_student(request):
    if request.method == 'POST':
        student_id = request.POST.get('id')
        name = request.POST.get('name')
        email = request.POST.get('email')
        student_unique_id = request.POST.get('student_id')
        semester = request.POST.get('semester')

        profile = get_object_or_404(Profile, id=student_id)

        user = profile.user
        user.first_name = name
        user.username = email
        user.email = email 
        user.save()

        profile.student_id = student_unique_id
        profile.semester = semester
        profile.save()

        messages.success(request, 'Student updated successfully.')
        return redirect('manage_students')
    else:
        messages.error(request, 'Invalid request method.')
        return redirect('manage_students')

@login_required
@coordinator_required
def update_supervisor(request, id):
    supervisor = get_object_or_404(Profile, id=id)

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        expertise = request.POST.get('expertise')

        supervisor.user.first_name = name
        supervisor.user.username = email
        supervisor.expertise = expertise
        supervisor.user.email = email
        supervisor.user.save()
        supervisor.save()

        messages.success(request, 'Supervisor updated successfully.')
        return redirect('manage_supervisors')
    return redirect('manage_supervisors')
   
@login_required
@coordinator_required
def user_delete(request, id):
    profile = get_object_or_404(Profile, id=id)
    if profile.user:
        profile.user.delete()
    profile.delete()
    messages.success(request, 'User deleted successfully.')
    return redirect('/manage_students/')

@login_required
@coordinator_required
def supervisor_del(request, id):
    profile = get_object_or_404(Profile, id=id)
    profile.delete()
    return redirect('manage_supervisors')

@login_required
@coordinator_required
def view_documents(request):
    phase1_docs = Phase1Submission.objects.select_related('submitted_by').order_by('-submitted_at')
    phase2_docs = Phase2Submission.objects.select_related('submitted_by').order_by('-submitted_at')

    context = {
        'phase1_docs': phase1_docs,
        'phase2_docs': phase2_docs,
        'head_title': 'View Student Documents',
    }
    return render(request, 'coordinators/view_documents.html', context)

@login_required
@coordinator_required
def fyp_progress(request):
    if request.user.profile.user_type != 'coordinator':
        return redirect('home')

    filter_option = request.GET.get('filter', 'all')
    now = timezone.now()

    meetings = Meeting.objects.filter(project__status='approved')

    if filter_option == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        meetings = meetings.filter(date_time__gte=start_date)
    elif filter_option == 'last_week':
        start_date = now - timedelta(days=7)
        meetings = meetings.filter(date_time__gte=start_date)
    elif filter_option == 'last_month':
        start_date = now - timedelta(days=30)
        meetings = meetings.filter(date_time__gte=start_date)

    meetings = meetings.select_related('project', 'supervisor').order_by('-date_time')

    meeting_counts = (
        meetings.values('project__title')
        .annotate(total_meetings=Count('id'))
        .order_by('-total_meetings')
    )

    context = {
        'meetings': meetings,
        'meeting_counts': meeting_counts,
        'filter_option': filter_option,
        'header_title': 'FYP Progress',
    }
    return render(request, 'coordinators/fyp_progress.html', context)


@login_required
@coordinator_required
def all_projects_meetings(request):
    if request.user.profile.user_type != 'coordinator':
        return redirect('home')

    project_meetings = (
        Meeting.objects
        .filter(project__status='approved')
        .select_related('project', 'supervisor')
        .values('project__id', 'project__title', 'supervisor__first_name', 'supervisor__last_name')
        .annotate(total_meetings=Count('id'))
        .order_by('-total_meetings')
    )

    context = {
        'project_meetings': project_meetings,
        'header_title': 'All Projects Meetings Overview',
    }
    return render(request, 'coordinators/all_projects_meetings.html', context)
