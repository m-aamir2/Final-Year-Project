import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings

from ..models import Proposal, Meeting
import json
from adminSection.models import *

logger = logging.getLogger(__name__)
@login_required
def home_supervisors(request):
    # Get counts for the supervisor dashboard
    pending_requests_count = Proposal.objects.filter(
        supervisors=request.user,
        status='pending'
    ).count()
    
    assigned_groups_count = Proposal.objects.filter(
        supervisors=request.user,
        status__in=['supervisor_approved', 'approved']
    ).count()
    
    active_projects_count = Proposal.objects.filter(
        supervisors=request.user,
        status='approved'
    ).count()
    
    # Count actual upcoming meetings
    upcoming_meetings_count = Meeting.objects.filter(
        supervisor=request.user,
        date_time__gte=timezone.now()
    ).count()
    
    # Get ALL deadlines - show everything to supervisor
    proposal_deadline_ann = Announcement.objects.filter(type='Proposal Deadline').order_by('-created_at').first()
    phase1_deadline_ann = Announcement.objects.filter(type='Phase 1').order_by('-created_at').first()
    phase2_deadline_ann = Announcement.objects.filter(type='Phase 2').order_by('-created_at').first()
    
    deadlines = {
        'proposal': proposal_deadline_ann.deadline if proposal_deadline_ann and proposal_deadline_ann.deadline else None,
        'phase1': phase1_deadline_ann.deadline if phase1_deadline_ann and phase1_deadline_ann.deadline else None,
        'phase2': phase2_deadline_ann.deadline if phase2_deadline_ann and phase2_deadline_ann.deadline else None,
    }
    
    context = {
        'pending_requests_count': pending_requests_count,
        'assigned_groups_count': assigned_groups_count,
        'active_projects_count': active_projects_count,
        'upcoming_meetings_count': upcoming_meetings_count,
        'deadlines': deadlines,
        'user_role': 'supervisor',
        'header_title': 'Home',
    }
    return render(request, 'supervisors/home_supervisors.html', context)

@login_required
def assignedProjects(request):
    # Get all projects assigned to this supervisor (both approved and supervisor_approved)
    assigned_projects = Proposal.objects.filter(
        supervisors=request.user,
        status__in=['approved', 'supervisor_approved']
    ).select_related('submitted_by').prefetch_related('group_members', 'supervisors')
    
    # Count projects by status for dashboard
    approved_count = assigned_projects.filter(status='approved').count()
    pending_approval_count = assigned_projects.filter(status='supervisor_approved').count()
    
    context = {
        'assigned_projects': assigned_projects,
        'approved_count': approved_count,
        'pending_approval_count': pending_approval_count,
        'user_role': 'supervisor',
        'header_title': 'Assigned Projects',
    }
    return render(request, 'supervisors/assigned_projects.html', context)

@login_required
def proposal_requests(request):
    proposals = Proposal.objects.filter(
        supervisors=request.user,
        status='pending'  # Only show pending proposals where they're still assigned
    ).select_related('submitted_by').prefetch_related('group_members')
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('supervisor_approved', 'Supervisor Approved'),
        ('approved', 'Fully Approved'),
        ('rejected', 'Rejected'),
    ]
    
    context = {
        'proposals': proposals,
        'user_role': 'supervisor',
        'status_choices': STATUS_CHOICES,
        'header_title': 'Proposal Requests',
    }
    return render(request, 'supervisors/proposal_requests.html', context)

@login_required
def addMeetings(request):
    # Get all meetings for this supervisor
    meetings = Meeting.objects.filter(supervisor=request.user).order_by('-date_time')
    
    if request.method == 'POST':
        # Simple form handling without forms.py
        project_id = request.POST.get('project')
        title = request.POST.get('title')
        date_time = request.POST.get('date_time')
        duration = request.POST.get('duration')
        platform = request.POST.get('platform')
        meeting_link = request.POST.get('meeting_link', '')
        location = request.POST.get('location', '')
        
        try:
            project = Proposal.objects.get(
                id=project_id,
                supervisors=request.user,
                status__in=['approved', 'supervisor_approved']
            )
            
            Meeting.objects.create(
                supervisor=request.user,
                project=project,
                title=title,
                date_time=date_time,
                duration=duration,
                platform=platform,
                meeting_link=meeting_link if platform != 'in_person' else '',
                location=location if platform == 'in_person' else ''
            )
            
            messages.success(request, 'Meeting added successfully!')
            return redirect('add_meetings')
            
        except Exception as e:
            messages.error(request, f'Error adding meeting: {str(e)}')
    
    # Get projects this supervisor can schedule meetings for
    projects = Proposal.objects.filter(
        supervisors=request.user,
        status__in=['approved', 'supervisor_approved']
    )
    
    return render(request, 'supervisors/add_meetings.html', {
        'projects': projects,
        'meetings': meetings,
        'platform_choices': Meeting.PLATFORM_CHOICES,
        'header_title': 'Manage Meetings',

    })

@login_required
def edit_meeting(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id, supervisor=request.user)
    
    if request.method == 'POST':
        # Update meeting details
        meeting.title = request.POST.get('title')
        meeting.date_time = request.POST.get('date_time')
        meeting.duration = request.POST.get('duration')
        meeting.platform = request.POST.get('platform')
        
        if meeting.platform == 'in_person':
            meeting.location = request.POST.get('location', '')
            meeting.meeting_link = ''
        else:
            meeting.meeting_link = request.POST.get('meeting_link', '')
            meeting.location = ''
            
        meeting.save()
        messages.success(request, 'Meeting updated successfully!')
        return redirect('add_meetings')
    
    # Get projects this supervisor can schedule meetings for
    projects = Proposal.objects.filter(
        supervisors=request.user,
        status__in=['approved', 'supervisor_approved']
    )
    
    return render(request, 'supervisors/edit_meeting.html', {
        'meeting': meeting,
        'projects': projects,
        'platform_choices': Meeting.PLATFORM_CHOICES,
        'header_title': 'Edit Meeting',
    })

@login_required
def delete_meeting(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id, supervisor=request.user)
    
    if request.method == 'POST':
        meeting.delete()
        messages.success(request, 'Meeting deleted successfully!')
    
    return redirect('add_meetings')

@login_required
def update_proposal_status(request, proposal_id):
    try:
        profile = request.user.profile
        if profile.user_type == 'supervisor':
            proposal = get_object_or_404(Proposal, id=proposal_id, supervisors=request.user)
            if not proposal.supervisors.filter(id=request.user.id).exists():
                return JsonResponse({'success': False, 'message': 'You are not a supervisor for this proposal.'}, status=403)
            
            # Check if supervisor has reached group limit before accepting
            active_groups_count = Proposal.objects.filter(
                supervisors=request.user,
                status__in=['supervisor_approved', 'approved']
            ).count()
            
        elif profile.user_type == 'coordinator':
            proposal = get_object_or_404(Proposal, id=proposal_id, status='supervisor_approved')
        else:
            return JsonResponse({'success': False, 'message': 'You are not authorized to update this proposal.'}, status=403)
        
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                action = data.get('action')
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'message': 'Invalid JSON format.'}, status=400)
            
            if action == 'accept':
                if profile.user_type == 'supervisor':
                    # Check group limit before accepting
                    if active_groups_count >= 4:
                        return JsonResponse({
                            'success': False, 
                            'message': 'You have reached your maximum limit of 4 groups. Cannot accept more proposals.'
                        }, status=400)
                    
                    # Update the accepted proposal
                    proposal.status = 'supervisor_approved'
                    proposal.rejection_reason = None
                    proposal.coordinator_rejection_reason = None
                    proposal.save()
                    
                    # Get all members of the accepted proposal (submitter + group members)
                    accepted_members = set(proposal.group_members.all()) | {proposal.submitted_by}
                    
                    # Find all other pending proposals involving any of these members
                    other_pending_proposals = Proposal.objects.filter(
                        models.Q(submitted_by__in=accepted_members) | models.Q(group_members__in=accepted_members),
                        status='pending'
                    ).exclude(id=proposal.id).distinct()
                    
                    # Reject all other pending proposals
                    for other_proposal in other_pending_proposals:
                        other_proposal.status = 'rejected'
                        other_proposal.rejection_reason = (
                            'This proposal was automatically rejected because another proposal '
                            'involving one or more of the same students was accepted by a supervisor.'
                        )
                        other_proposal.save()
                        
                        # Send email to group members of rejected proposals
                        group_emails = list(set([member.email for member in other_proposal.group_members.all()] + 
                                              [other_proposal.submitted_by.email]))
                        
                        if group_emails:
                            html_content = f"""
                                <html>
                                <body style="margin: 0; padding: 0; background-color: #f4f4f4;">
                                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px 0;">
                                    <tr>
                                        <td align="center">
                                        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; padding: 40px; font-family: 'Segoe UI', Roboto, Arial, sans-serif; color: #333333; box-shadow: 0 0 10px rgba(0,0,0,0.08);">
                                            <tr>
                                            <td align="center" style="padding-bottom: 20px;">
                                                <h2 style="margin: 0; font-size: 26px; color: #222;">FYPAS Proposal Update</h2>
                                            </td>
                                            </tr>
                                            <tr>
                                            <td style="font-size: 16px; line-height: 1.6;">
                                                <p>Dear Students,</p>
                                                <p>Your proposal titled "<strong>{other_proposal.title}</strong>" has been <strong>rejected</strong>.</p>
                                                <p><strong>Reason for rejection:</strong> {other_proposal.rejection_reason}</p>
                                                <p>Please contact your supervisor or coordinator for further details.</p>
                                                <p style="margin-top: 30px;">Best regards,<br><strong>FYPAS Admin Team</strong></p>
                                            </td>
                                            </tr>
                                            <tr>
                                            <td align="center" style="font-size: 12px; color: #999999; padding-top: 30px;">
                                                <p>© {timezone.now().year} FYPAS. All rights reserved.</p>
                                            </td>
                                            </tr>
                                        </table>
                                        </td>
                                    </tr>
                                    </table>
                                </body>
                                </html>
                            """
                            try:
                                email = EmailMessage(
                                    subject='FYPAS Proposal Automatically Rejected',
                                    body=html_content,
                                    from_email=settings.DEFAULT_FROM_EMAIL,
                                    to=group_emails,
                                )
                                email.content_subtype = "html"
                                email.send()
                            except Exception as e:
                                logger.error(f"Failed to send rejection email for proposal {other_proposal.id}: {str(e)}")
                    
                    # Send email to group members of the accepted proposal
                    group_emails = list(set([member.email for member in proposal.group_members.all()] + 
                                          [proposal.submitted_by.email]))
                    
                    if not group_emails:
                        return JsonResponse({'success': True, 'message': 'Proposal approved by supervisor, but no email addresses found.'})
                    
                    html_content = f"""
                        <html>
                        <body style="margin: 0; padding: 0; background-color: #f4f4f4;">
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px 0;">
                            <tr>
                                <td align="center">
                                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; padding: 40px; font-family: 'Segoe UI', Roboto, Arial, sans-serif; color: #333333; box-shadow: 0 0 10px rgba(0,0,0,0.08);">
                                    <tr>
                                    <td align="center" style="padding-bottom: 20px;">
                                        <h2 style="margin: 0; font-size: 26px; color: #222;">FYPAS Proposal Update</h2>
                                    </td>
                                    </tr>
                                    <tr>
                                    <td style="font-size: 16px; line-height: 1.6;">
                                        <p>Dear Students,</p>
                                        <p>Your proposal titled "<strong>{proposal.title}</strong>" has been <strong>approved by your supervisor</strong>.</p>
                                        <p>It has been forwarded to the coordinator for final approval. You will be notified once the coordinator makes a decision.</p>
                                        <p style="margin-top: 30px;">Best regards,<br><strong>FYPAS Admin Team</strong></p>
                                    </td>
                                    </tr>
                                    <tr>
                                    <td align="center" style="font-size: 12px; color: #999999; padding-top: 30px;">
                                        <p>© {timezone.now().year} FYPAS. All rights reserved.</p>
                                    </td>
                                    </tr>
                                </table>
                                </td>
                            </tr>
                            </table>
                        </body>
                        </html>
                    """
                    try:
                        email = EmailMessage(
                            subject='FYPAS Proposal Approved by Supervisor',
                            body=html_content,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=group_emails,
                        )
                        email.content_subtype = "html"
                        email.send()
                        return JsonResponse({'success': True, 'message': 'Proposal approved by supervisor, other pending proposals rejected, and notifications sent.'})
                    except Exception as e:
                        return JsonResponse({'success': True, 'message': f'Proposal approved by supervisor and other proposals rejected, but failed to send notification email: {str(e)}'})
                
                elif profile.user_type == 'coordinator':
                    proposal.status = 'approved'
                    proposal.coordinator_rejection_reason = None
                    proposal.save()
                    
                    # Send email to group members and supervisors
                    recipient_emails = list(set([member.email for member in proposal.group_members.all()] + 
                                          [proposal.submitted_by.email] + 
                                          [supervisor.email for supervisor in proposal.supervisors.all()]))
                    
                    if not recipient_emails:
                        return JsonResponse({'success': True, 'message': 'Proposal approved, but no email addresses found.'})
                    
                    html_content = f"""
                        <html>
                        <body style="margin: 0; padding: 0; background-color: #f4f4f4;">
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px 0;">
                            <tr>
                                <td align="center">
                                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; padding: 40px; font-family: 'Segoe UI', Roboto, Arial, sans-serif; color: #333333; box-shadow: 0 0 10px rgba(0,0,0,0.08);">
                                    <tr>
                                    <td align="center" style="padding-bottom: 20px;">
                                        <h2 style="margin: 0; font-size: 26px; color: #222;">FYPAS Proposal Update</h2>
                                    </td>
                                    </tr>
                                    <tr>
                                    <td style="font-size: 16px; line-height: 1.6;">
                                        <p>Dear Team,</p>
                                        <p>The proposal titled "<strong>{proposal.title}</strong>" has been <strong>fully approved</strong> by the coordinator.</p>
                                        <p>You may now proceed with the project as outlined. Contact your supervisor for next steps.</p>
                                        <p style="margin-top: 30px;">Best regards,<br><strong>FYPAS Admin Team</strong></p>
                                    </td>
                                    </tr>
                                    <tr>
                                    <td align="center" style="font-size: 12px; color: #999999; padding-top: 30px;">
                                        <p>© {timezone.now().year} FYPAS. All rights reserved.</p>
                                    </td>
                                    </tr>
                                </table>
                                </td>
                            </tr>
                            </table>
                        </body>
                        </html>
                    """
                    try:
                        email = EmailMessage(
                            subject='FYPAS Proposal Fully Approved',
                            body=html_content,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=recipient_emails,
                        )
                        email.content_subtype = "html"
                        email.send()
                        return JsonResponse({'success': True, 'message': 'Proposal fully approved and team notified.'})
                    except Exception as e:
                        return JsonResponse({'success': True, 'message': f'Proposal approved, but failed to send notification email: {str(e)}'})
            
            elif action == 'reject':
                reason = data.get('reason', '')
                if not reason:
                    return JsonResponse({'success': False, 'message': 'Please provide a reason for rejection.'}, status=400)
                
                if profile.user_type == 'supervisor':
                    proposal.status = 'rejected'
                    proposal.rejection_reason = reason
                    proposal.coordinator_rejection_reason = None
                    proposal.save()
                    
                    # Send email to group members
                    group_emails = list(set([member.email for member in proposal.group_members.all()] + [proposal.submitted_by.email]))
                    
                    if not group_emails:
                        return JsonResponse({'success': True, 'message': 'Proposal rejected, but no email addresses found.'})
                    
                    html_content = f"""
                        <html>
                        <body style="margin: 0; padding: 0; background-color: #f4f4f4;">
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px 0;">
                            <tr>
                                <td align="center">
                                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; padding: 40px; font-family: 'Segoe UI', Roboto, Arial, sans-serif; color: #333333; box-shadow: 0 0 10px rgba(0,0,0,0.08);">
                                    <tr>
                                    <td align="center" style="padding-bottom: 20px;">
                                        <h2 style="margin: 0; font-size: 26px; color: #222;">FYPAS Proposal Update</h2>
                                    </td>
                                    </tr>
                                    <tr>
                                    <td style="font-size: 16px; line-height: 1.6;">
                                        <p>Dear Students,</p>
                                        <p>Your proposal titled "<strong>{proposal.title}</strong>" has been <strong>rejected</strong> by your supervisor.</p>
                                        <p><strong>Reason for rejection:</strong> {reason}</p>
                                        <p>Please review the feedback and consider submitting a revised proposal.</p>
                                        <p style="margin-top: 30px;">Best regards,<br><strong>FYPAS Admin Team</strong></p>
                                    </td>
                                    </tr>
                                    <tr>
                                    <td align="center" style="font-size: 12px; color: #999999; padding-top: 30px;">
                                        <p>© {timezone.now().year} FYPAS. All rights reserved.</p>
                                    </td>
                                    </tr>
                                </table>
                                </td>
                            </tr>
                            </table>
                        </body>
                        </html>
                    """
                    try:
                        email = EmailMessage(
                            subject='FYPAS Proposal Rejected',
                            body=html_content,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=group_emails,
                        )
                        email.content_subtype = "html"
                        email.send()
                        return JsonResponse({'success': True, 'message': 'Proposal rejected and students notified with feedback.'})
                    except Exception as e:
                        return JsonResponse({'success': True, 'message': f'Proposal rejected, but failed to send notification email: {str(e)}'})
                
                elif profile.user_type == 'coordinator':
                    proposal.status = 'rejected'
                    proposal.coordinator_rejection_reason = reason
                    proposal.rejection_reason = None
                    proposal.save()
                    
                    # Send email to group members and supervisors
                    recipient_emails = list(set([member.email for member in proposal.group_members.all()] + 
                                            [proposal.submitted_by.email] + 
                                            [supervisor.email for supervisor in proposal.supervisors.all()]))
                    
                    if not recipient_emails:
                        return JsonResponse({'success': True, 'message': 'Proposal rejected, but no email addresses found.'})
                    
                    html_content = f"""
                        <html>
                        <body style="margin: 0; padding: 0; background-color: #f4f4f4;">
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px 0;">
                            <tr>
                                <td align="center">
                                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; padding: 40px; font-family: 'Segoe UI', Roboto, Arial, sans-serif; color: #333333; box-shadow: 0 0 10px rgba(0,0,0,0.08);">
                                    <tr>
                                    <td align="center" style="padding-bottom: 20px;">
                                        <h2 style="margin: 0; font-size: 26px; color: #222;">FYPAS Proposal Update</h2>
                                    </td>
                                    </tr>
                                    <tr>
                                    <td style="font-size: 16px; line-height: 1.6;">
                                        <p>Dear Team,</p>
                                        <p>The proposal titled "<strong>{proposal.title}</strong>" has been <strong>rejected</strong> by the coordinator.</p>
                                        <p><strong>Reason for rejection:</strong> {reason}</p>
                                        <p>Please review the feedback and consider submitting a revised proposal.</p>
                                        <p style="margin-top: 30px;">Best regards,<br><strong>FYPAS Admin Team</strong></p>
                                    </td>
                                    </tr>
                                    <tr>
                                    <td align="center" style="font-size: 12px; color: #999999; padding-top: 30px;">
                                        <p>© {timezone.now().year} FYPAS. All rights reserved.</p>
                                    </td>
                                    </tr>
                                </table>
                                </td>
                            </tr>
                            </table>
                        </body>
                        </html>
                    """
                    try:
                        email = EmailMessage(
                            subject='FYPAS Proposal Rejected by Coordinator',
                            body=html_content,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=recipient_emails,
                        )
                        email.content_subtype = "html"
                        email.send()
                        return JsonResponse({'success': True, 'message': 'Proposal rejected by coordinator and team notified.'})
                    except Exception as e:
                        return JsonResponse({'success': True, 'message': f'Proposal rejected, but failed to send notification email: {str(e)}'})
            
            return JsonResponse({'success': False, 'message': 'Invalid action specified.'}, status=400)
        
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)
    
    except Proposal.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Proposal not found or you are not authorized.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'}, status=500) 

@login_required
def proposal_details(request, proposal_id):
    try:
        profile = request.user.profile
        if profile.user_type == 'supervisor':
            proposal = get_object_or_404(Proposal, id=proposal_id, supervisors=request.user)
        elif profile.user_type == 'coordinator':
            proposal = get_object_or_404(Proposal, id=proposal_id, status='supervisor_approved')
        else:
            return JsonResponse({'success': False, 'message': 'You are not authorized to view this proposal.'}, status=403)
        
        data = {
            'title': proposal.title,
            'description': proposal.description,
            'domain': proposal.domain,
            'status_display': proposal.get_status_display(),
            'rejection_reason': proposal.rejection_reason or proposal.coordinator_rejection_reason or 'N/A',
            'document_url': proposal.document.url,
            'group_members': [
                {'first_name': member.first_name, 'last_name': member.last_name}
                for member in proposal.group_members.all()
            ],
            'supervisors': [
                {'first_name': supervisor.first_name, 'last_name': supervisor.last_name}
                for supervisor in proposal.supervisors.all()
            ]
        }
        return JsonResponse(data)
    except Proposal.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Proposal not found or you are not authorized.'}, status=404)

@login_required
def submitted_documents(request):
    user = request.user
    profile = user.profile

    if profile.user_type != 'supervisor':
        return JsonResponse({'success': False, 'message': 'You are not authorized.'}, status=403)

    # Get all proposals assigned to this supervisor
    assigned_proposals = Proposal.objects.filter(
        supervisors=user,
        status__in=['supervisor_approved', 'approved']
    ).prefetch_related('group_members')

    # Get the students in these proposals (submitter + group members)
    supervised_students = set()
    for proposal in assigned_proposals:
        supervised_students.add(proposal.submitted_by.id)
        supervised_students.update([member.id for member in proposal.group_members.all()])

    # Fetch only documents submitted by these students
    phase1_docs = Phase1Submission.objects.filter(
        submitted_by__id__in=supervised_students
    ).select_related('submitted_by').order_by('-submitted_at')

    phase2_docs = Phase2Submission.objects.filter(
        submitted_by__id__in=supervised_students
    ).select_related('submitted_by').order_by('-submitted_at')

    context = {
        'phase1_docs': phase1_docs,
        'phase2_docs': phase2_docs,
        'head_title': 'View Student Documents',
    }

    return render(request, 'supervisors/submitted_documents.html', context)
