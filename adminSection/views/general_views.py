import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from ..models import Proposal, User
import json
from django.db import models
from adminSection.models import *

logger = logging.getLogger(__name__)

def landingPage(request):
    today = timezone.now().date()
    announcements = Announcement.objects.filter(
        deadline__gte=today
    ).order_by('-created_at') | Announcement.objects.filter(deadline__isnull=True).order_by('-created_at')
    return render(request, 'landing.html', {'announcements': announcements})

@login_required
def user_profile(request):
    user = request.user
    profile = user.profile

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        github_account = request.POST.get('github_account')
        bachelors_from = request.POST.get('bachelors_from')
        masters_from = request.POST.get('masters_from')
        phd_from = request.POST.get('phd_from')
        office_location = request.POST.get('office_location')
        office_hours = request.POST.get('office_hours')
        profile_image = request.FILES.get('profile_image')

        # Update user fields
        if name:
            user.first_name = name
        if email:
            user.email = email
            user.username = email
        user.save()

        # Update profile fields
        if phone:
            profile.phone = phone
        if profile_image:
            profile.profile_image = profile_image
        if profile.user_type == 'student' and github_account:
            profile.github_account = github_account
        elif profile.user_type == 'supervisor':
            if bachelors_from:
                profile.bachelors_from = bachelors_from
            if masters_from:
                profile.masters_from = masters_from
            if phd_from:
                profile.phd_from = phd_from
            if office_location:
                profile.office_location = office_location
            if office_hours:
                profile.office_hours = office_hours
        profile.save()

        messages.success(request, 'Profile updated successfully.')
        return redirect('user_profile')
    return render(request, 'profile.html', {'user': user, 'profile': profile, 'head_title': 'Profile'})

@login_required
def teamMates(request):
    user = request.user

    if hasattr(user, 'profile') and hasattr(user.profile, 'user_type'):
        user_role = user.profile.user_type
    elif user.is_staff:
        user_role = 'admin'
    else:
        user_role = 'student'

    # Initialize variables
    active_proposal = None
    group_members = []
    supervisors = []

    if user_role == 'supervisor':
        # Supervisor: get the first approved proposal where they're supervising
        active_proposal = Proposal.objects.filter(
            supervisors=user,
            status__in=['approved', 'supervisor_approved']
        ).first()

        if active_proposal:
            group_members = active_proposal.group_members.all()
            supervisors = active_proposal.supervisors.all()

    else:
        # Student: get their own proposal
        active_proposal = Proposal.objects.filter(
            models.Q(submitted_by=user) | models.Q(group_members=user),
            status__in=['approved', 'supervisor_approved']
        ).first()

        if active_proposal:
            group_members = active_proposal.group_members.all()
            supervisors = active_proposal.supervisors.all()

    context = {
        'user_role': user_role,
        'head_title': 'Team Mates',
        'active_proposal': active_proposal,
        'group_members': group_members,
        'supervisors': supervisors,
    }

    if user_role == 'supervisor':
        return render(request, 'supervisors/team.html', context)
    else:
        return render(request, 'students/team.html', context)


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

