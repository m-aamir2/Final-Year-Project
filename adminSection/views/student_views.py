from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db import models
from adminSection.models import *

from django.utils import timezone
from ..models import Profile, Proposal, Meeting, User

@login_required
def homeStudents(request):
    firstname = request.user.first_name
    email = request.user.username
    
    student_proposals = Proposal.objects.filter(
    models.Q(submitted_by=request.user) |
    models.Q(group_members=request.user)
).order_by('-submitted_at').distinct()


    recent_proposal = student_proposals.first()
    active_proposal = student_proposals.filter(
        status__in=['approved', 'supervisor_approved']
    ).first()

    upcoming_meetings_count = 0
    next_meeting = None
    
    if active_proposal:
        upcoming_meetings = Meeting.objects.filter(
            project=active_proposal,
            date_time__gte=timezone.now()
        ).order_by('date_time')
        
        upcoming_meetings_count = upcoming_meetings.count()
        next_meeting = upcoming_meetings.first() if upcoming_meetings_count > 0 else None
    
    # Determine which deadline to show based on student's progress
    profile = request.user.profile
    semester = profile.semester
    
    relevant_deadline = None
    deadline_type = None
    deadline_description = None
    
    # Check if student has submitted required documents for each phase
    has_submitted_proposal = Proposal.objects.filter(
        models.Q(submitted_by=request.user) | models.Q(group_members=request.user),
        status__in=['supervisor_approved', 'approved']
    ).exists()
    
    has_submitted_phase1 = Phase1Submission.objects.filter(submitted_by=request.user).exists()
    has_submitted_phase2 = Phase2Submission.objects.filter(submitted_by=request.user).exists()
    
    print(f"DEBUG: Semester: {semester}")
    print(f"DEBUG: Has approved proposal: {has_submitted_proposal}")
    print(f"DEBUG: Has submitted Phase 1: {has_submitted_phase1}")
    print(f"DEBUG: Has submitted Phase 2: {has_submitted_phase2}")
    
    # Logic to determine which deadline to show
    if semester == '6':
        # 6th semester students - show proposal deadline if they don't have approved proposal
        if not has_submitted_proposal:
            announcement = Announcement.objects.filter(type='Proposal Deadline').order_by('-created_at').first()
            deadline_type = 'Proposal Submission'
            deadline_description = 'Submit your project proposal'
        else:
            # If they have approved proposal, check if they've submitted Phase 1
            if not has_submitted_phase1:
                announcement = Announcement.objects.filter(type='Phase 1').order_by('-created_at').first()
                deadline_type = 'Phase 1 Submission'
                deadline_description = 'Submit Phase 1 documents'
            else:
                announcement = Announcement.objects.filter(type='Phase 2').order_by('-created_at').first()
                deadline_type = 'Phase 2 Submission'
                deadline_description = 'Submit Phase 2 documents'
    
    elif semester == '7':
        # 7th semester students - show Phase 1 deadline if not submitted
        if not has_submitted_phase1:
            announcement = Announcement.objects.filter(type='Phase 1').order_by('-created_at').first()
            deadline_type = 'Phase 1 Submission'
            deadline_description = 'Submit Phase 1 documents'
        else:
            # If Phase 1 submitted, show Phase 2 deadline
            announcement = Announcement.objects.filter(type='Phase 2').order_by('-created_at').first()
            deadline_type = 'Phase 2 Submission'
            deadline_description = 'Submit Phase 2 documents'
    
    elif semester == '8':
        # 8th semester students - always show Phase 2 deadline
        announcement = Announcement.objects.filter(type='Phase 2').order_by('-created_at').first()
        deadline_type = 'Phase 2 Submission'
        deadline_description = 'Submit Phase 2 documents (Final)'
    
    else:
        announcement = None
    
    # If no specific announcement found for the phase, try to get any relevant one
    if not announcement and semester == '6' and not has_submitted_proposal:
        announcement = Announcement.objects.filter(
            models.Q(type='Proposal Deadline') | 
            models.Q(type__icontains='proposal')
        ).order_by('-created_at').first()
    
    if not announcement and (semester == '7' or (semester == '6' and has_submitted_proposal)) and not has_submitted_phase1:
        announcement = Announcement.objects.filter(
            models.Q(type='Phase 1') | 
            models.Q(type__icontains='phase 1') |
            models.Q(type__icontains='phase1')
        ).order_by('-created_at').first()
    
    if not announcement and (semester == '8' or has_submitted_phase1) and not has_submitted_phase2:
        announcement = Announcement.objects.filter(
            models.Q(type='Phase 2') | 
            models.Q(type__icontains='phase 2') |
            models.Q(type__icontains='phase2')
        ).order_by('-created_at').first()
    
    if announcement and announcement.deadline:
        relevant_deadline = announcement.deadline
    else:
        # Fallback: get any announcement with deadline
        fallback_announcement = Announcement.objects.filter(deadline__isnull=False).order_by('-created_at').first()
        if fallback_announcement:
            relevant_deadline = fallback_announcement.deadline
            deadline_type = fallback_announcement.type
            deadline_description = 'Project deadline'
    
    today = timezone.now().date()
    context = {
        'firstname': firstname,
        'email': email,
        'recent_proposal': recent_proposal,
        'active_proposal': active_proposal,
        'upcoming_meetings_count': upcoming_meetings_count,
        'next_meeting': next_meeting,
        'relevant_deadline': relevant_deadline,
        'deadline_type': deadline_type,
        'deadline_description': deadline_description,
        'semester': semester,
        'has_approved_proposal': has_submitted_proposal,
        'has_submitted_phase1': has_submitted_phase1,
        'has_submitted_phase2': has_submitted_phase2,
        'user_role': 'student',
        'head_title': 'Home',
        'today': today,
    }
    return render(request, 'students/home_students.html', context)

@login_required
def upload_proposal(request):
    profile = request.user.profile

    if profile.user_type != 'student':
        messages.error(request, 'Only students can submit proposals.')
        return redirect('/')

    today = timezone.now().date()
    proposal_deadline_ann = Announcement.objects.filter(type='Proposal Deadline').order_by('-created_at').first()
    proposal_deadline = proposal_deadline_ann.deadline if proposal_deadline_ann and proposal_deadline_ann.deadline else None

    if proposal_deadline and proposal_deadline < today:
        messages.error(request, 'The proposal submission deadline has passed. You cannot submit new proposals at this time.')
        return render(
            request,
            'students/upload_proposal.html',
            {
                'group_members': Profile.objects.filter(user_type='student', semester='6').exclude(user=request.user),
                'supervisors': Profile.objects.filter(user_type='supervisor'),
                'pending_supervisors': User.objects.filter(
                    supervised_proposals__group_members=request.user,
                    supervised_proposals__status='pending'
                ).distinct(),
                'head_title': 'Upload Proposal',
                'proposal_deadline': proposal_deadline,
                'today': today,
            }
        )

    if request.method == 'POST':
        title = request.POST.get('title')
        domain = request.POST.get('domain')
        group_member_ids = request.POST.getlist('group_members', [])
        supervisor_ids = request.POST.getlist('supervisors')
        document = request.FILES.get('document')

        # Check if selected supervisor already has pending proposal
        for sup_id in supervisor_ids:
            supervisor = User.objects.get(pk=sup_id)
            if Proposal.objects.filter(
                models.Q(submitted_by=request.user) | models.Q(group_members=request.user),
                supervisors=supervisor,
                status='pending'
            ).exists():
                messages.error(
                    request,
                    f'You already have a pending proposal with {supervisor.first_name}. '
                    'Please wait for a response or withdraw your current proposal.'
                )
                return redirect('upload_proposal')

        # Validate group members not already in another proposal
        for member_id in group_member_ids:
            member = User.objects.get(pk=member_id)
            if Proposal.objects.filter(
                models.Q(submitted_by=member) | models.Q(group_members=member),
                status__in=['pending', 'supervisor_approved', 'approved']
            ).exists():
                messages.error(
                    request,
                    f'{member.first_name} is already part of another pending or accepted proposal.'
                )
                return redirect('upload_proposal')

        if len(group_member_ids) > 2:
            messages.error(request, 'Maximum 2 additional group members allowed.')
            return redirect('upload_proposal')

        try:
            # CREATE PROPOSAL
            proposal = Proposal.objects.create(
                title=title,
                domain=domain,
                document=document,
                submitted_by=request.user,
                status='pending'
            )

            proposal.group_members.add(request.user)
            for member_id in group_member_ids:
                proposal.group_members.add(User.objects.get(pk=member_id))

            for sup_id in supervisor_ids:
                proposal.supervisors.add(User.objects.get(pk=sup_id))

            proposal.save()

            # ✅ --- BEGIN SIMILARITY CHECK FEATURE ---
            from .utils import extract_text_from_file, compute_embedding, compute_similarity

            temp_path = proposal.document.path
            text = extract_text_from_file(temp_path)

            if not text:
                messages.warning(request, "Could not extract text from the file. Please upload a valid document.")
                return redirect('upload_proposal')

            embedding = compute_embedding(text)
            proposal.extracted_text = text
            proposal.embedding = embedding
            proposal.save()

            # past_proposals = Proposal.objects.filter(status='approved')
            # ✅ Compare with all proposals from same semester AND approved proposals
            past_proposals = Proposal.objects.filter(
                models.Q(status='approved') |
                models.Q(status='supervisor_approved') |
                models.Q(status='pending', submitted_by__profile__semester=profile.semester)
            ).exclude(id=proposal.id)

            max_similarity = 0.0
            similar_title = None

            for past in past_proposals:
                if not past.embedding and past.document:
                    past_text = extract_text_from_file(past.document.path)
                    if past_text:
                        past.embedding = compute_embedding(past_text)
                        past.save()

                if past.embedding:
                    sim = compute_similarity(embedding, past.embedding)
                    if sim > max_similarity:
                        max_similarity = sim
                        similar_title = past.title

            proposal.similarity_score = max_similarity * 100
            similarity_percent = round(max_similarity * 100, 2)
            proposal.similar_to = similar_title
            proposal.save()

            # If similarity > 60% → STOP submission
            if max_similarity >= 0.85:
                messages.error(request,
                    f"❌ This proposal is extremely similar ({similarity_percent}%) to '{similar_title}'. "
                    f"Please submit a completely new and unique idea."
                )
                proposal.delete()
                return redirect('upload_proposal')

            elif max_similarity >= 0.60:
                messages.error(request,
                    f"⚠️ This proposal is {similarity_percent}% similar to '{similar_title}'. "
                    f"Your idea is not unique enough. Please try a new and original idea."
                )
                proposal.delete()
                return redirect('upload_proposal')

            # --- END of SIMILARITY CHECK FEATURE ---

            return redirect('view_proposals')

        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect('upload_proposal')

    unavailable_students = User.objects.filter(
        models.Q(proposals__status__in=['pending', 'supervisor_approved', 'approved']) |
        models.Q(group_proposals__status__in=['pending', 'supervisor_approved', 'approved'])
    ).distinct()

    group_members = Profile.objects.filter(user_type='student') \
        .exclude(user__in=unavailable_students) \
        .exclude(user=request.user)

    supervisors = Profile.objects.filter(user_type='supervisor')

    pending_supervisors = User.objects.filter(
        supervised_proposals__group_members=request.user,
        supervised_proposals__status='pending'
    ).distinct()

    existing_proposal = Proposal.objects.filter(
    models.Q(submitted_by=request.user) | models.Q(group_members=request.user),
    status__in=['pending', 'supervisor_approved', 'approved']
).order_by('-submitted_at').first()


    pending_coordinator = None
    approved_proposal = None

    if existing_proposal:
        if existing_proposal.status == 'supervisor_approved':
            pending_coordinator = existing_proposal
        elif existing_proposal.status == 'approved':
            approved_proposal = existing_proposal

    return render(
        request,
        'students/upload_proposal.html',
        {
            'group_members': group_members,
            'supervisors': supervisors,
            'pending_supervisors': pending_supervisors,
            'head_title': 'Upload',
            'proposal_deadline': proposal_deadline,
            'today': today,
            'existing_proposal': existing_proposal,
            'pending_coordinator': pending_coordinator,
            'approved_proposal': approved_proposal
        }
    )


@login_required
def view_proposals(request):
    # Fetch proposals for students (either submitted by them or they're group members)
    proposals = Proposal.objects.filter(
        models.Q(submitted_by=request.user) | models.Q(group_members=request.user)
    ).distinct()
    return render(
        request,
        'students/view_proposals.html',
        {
            'proposals': proposals,
            'head_title':'View Proposals'
        }
    )

@login_required
def find_supervisors(request):
    supervisors = Profile.objects.filter(user_type='supervisor')
    for supervisor in supervisors:
        # Get only non-rejected proposals
        active_proposals = supervisor.user.supervised_proposals.filter(
            status__in=[ 'supervisor_approved', 'approved']
        )
        supervisor.active_proposals = active_proposals
        supervisor.active_proposals_count = active_proposals.count()
        supervisor.is_available = supervisor.active_proposals_count < 4
    return render(
        request,
        'students/find_supervisors.html',
        {
            'supervisors': supervisors,
            'head_title':'Find Supervisor'
        }
    )

@login_required
def announcements(request):
    # Get all projects where the student is either submitter or group member
    student_projects = Proposal.objects.filter(
        models.Q(submitted_by=request.user) | 
        models.Q(group_members=request.user)
    )
    
    # Get all meetings for these projects
    meetings = Meeting.objects.filter(
        project__in=student_projects,
        date_time__gte=timezone.now()  # Only show upcoming meetings
    ).order_by('date_time')
    
    context = {
        'meetings': meetings,
        'user_role': 'student',
            'head_title':'Annoucements'
    }
    return render(request, 'students/announcements.html', context)

@login_required
def upload_document(request):
    profile = Profile.objects.get(user=request.user)
    semester = profile.semester
    today = timezone.now().date()

    # Determine phase type and related model
    phase_map = {
        "6": ("proposal", "Proposal Deadline", Proposal),
        "7": ("phase1", "Phase 1", Phase1Submission),
        "8": ("phase2", "Phase 2", Phase2Submission),
    }

    phase_type, announcement_type, Model = phase_map.get(semester, (None, None, None))

    if not Model:
        messages.error(request, "Invalid semester configuration.")
        return redirect('/')

    # Get latest announcement and deadline
    announcement = Announcement.objects.filter(type=announcement_type).order_by('-post_date').first()
    deadline = announcement.deadline if announcement else None

    # Get existing uploaded document (if any)
    uploaded_doc = Model.objects.filter(submitted_by=request.user).first()

    # Handle form submission
    if request.method == 'POST':
        document = request.FILES.get('document')

        if not document:
            messages.error(request, "Please select a file before submitting.")
            return redirect('upload_document')

        if not deadline:
            messages.error(request, "No submission deadline set yet.")
            return redirect('upload_document')

        if deadline < today:
            messages.error(request, "Submission deadline has passed.")
            return redirect('upload_document')

        # Replace or create new upload
        if uploaded_doc:
            uploaded_doc.document = document
            uploaded_doc.save()
            messages.success(request, f"{phase_type.title()} document replaced successfully!")
        else:
            uploaded_doc = Model.objects.create(
                title=f"{phase_type.title()} Submission",
                document=document,
                submitted_by=request.user,
            )
            messages.success(request, f"{phase_type.title()} document uploaded successfully!")

        # ✅ Return updated context (so uploaded_doc displays immediately)
        return render(
            request,
            'students/upload_document.html',
            {
                'phase_type': phase_type,
                'announcement': announcement,
                'deadline': deadline,
                'today': today,
                'uploaded_doc': uploaded_doc,  # ✅ important line
                'head_title': 'Upload Document',
            }
        )

    # Initial page load
    context = {
        'phase_type': phase_type,
        'announcement': announcement,
        'deadline': deadline,
        'today': today,
        'uploaded_doc': uploaded_doc,
        'head_title': 'Upload Document',
    }
    return render(request, 'students/upload_document.html', context)
