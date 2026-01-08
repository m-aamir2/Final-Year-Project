import datetime
import logging
import smtplib
import socket

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from ..decorators import coordinator_required
from ..models import Profile
from datetime import date
import re 
logger = logging.getLogger(__name__)

def get_auto_updated_semester(initial_semester):
    today = date.today()
    current_month = today.month

    try:
        semester = int(initial_semester)
    except (ValueError, TypeError):
        semester = 6  # Default starting semester

    if current_month not in [2, 10]:
        # If we’re between March–Sep → next update in Oct
        # If we’re between Nov–Jan → next update in Feb
        # (No change on creation)
        return str(semester)
    return str(semester)


@coordinator_required
def signup(request):
    if request.method == 'POST':
        data = request.POST
        firstname = data.get('firstname')
        username = data.get('username')
        user_type = data.get('user_type')
        semester = data.get('semester')
        expertise = data.get('expertise')

        if User.objects.filter(username=username).exists():
            context = {'message': 'User already exists'}
            return render(request, 'accounts/signup.html', context)

        temp_password = get_random_string(10)

        user = User.objects.create_user(
            username=username,
            email=username,
            password=temp_password,
        )
        user.first_name = firstname
        user.save()
        if user_type == 'student':
            semester = get_auto_updated_semester(semester or 6)
        else:
            semester = None
        Profile.objects.create(
            user=user,
            user_type=user_type,
            semester=semester if semester else None,
            expertise=expertise if user_type == 'supervisor' else '',
            must_change_password=True
        )

        expiry_date = (timezone.now() + datetime.timedelta(days=3)).strftime('%Y-%m-%d')

        html_content = f"""
            <html>
            <body style="margin: 0; padding: 0; background-color: #f4f4f4;">
                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px 0;">
                <tr>
                    <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; padding: 40px; font-family: 'Segoe UI', Roboto, Arial, sans-serif; color: #333333; box-shadow: 0 0 10px rgba(0,0,0,0.08);">
                        <tr>
                        <td align="center" style="padding-bottom: 20px;">
                            <h2 style="margin: 0; font-size: 26px; color: #222;">Welcome to FYPAS</h2>
                        </td>
                        </tr>
                        <tr>
                        <td style="font-size: 16px; line-height: 1.6;">
                            <p>Dear <strong>{firstname}</strong>,</p>
                            <p>Your FYPAS account has been successfully created.</p>
                            <p><strong>Temporary Password:</strong> 
                            <span style="display: inline-block; background-color: #f0f0f0; padding: 6px 12px; border-radius: 4px; font-family: monospace; font-size: 15px;">
                                {temp_password}
                            </span>
                            </p>
                            <p>Please log in and change your password immediately. This temporary password will expire after <strong>3 days</strong> (by <strong>{expiry_date}</strong>).</p>
                            <p>If you have any questions, feel free to contact our support team.</p>
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
                subject='FYPAS Account Created',
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[username],
            )
            email.content_subtype = "html"
            email.send()
            messages.success(request, 'User created and email sent successfully.')
        except Exception as e:
            messages.warning(request, 'User created, but failed to send email. Please contact the admin.')

        return redirect('signup')

    return render(request, 'accounts/signup.html')

def user_login(request):
    if request.user.is_authenticated:
        return redirect('landingPage')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Handle empty fields
        if not email or not password:
            return render(request, 'accounts/login.html', {'m': 'Please fill in both email and password.'})

        # Validate email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return render(request, 'accounts/login.html', {'m': 'Please enter a valid email address.'})

        # Check user existence
        try:
            user_obj = User.objects.get(username=email)
        except User.DoesNotExist:
            return render(request, 'accounts/login.html', {'m': 'No account found with this email.'})

        # Authenticate user
        user = authenticate(username=email, password=password)
        if user is None:
            return render(request, 'accounts/login.html', {'m': 'Incorrect password. Please try again.'})

        # Check if suspended
        profile = Profile.objects.get(user=user)
        if profile.is_suspended:
            return render(request, 'accounts/login.html', {'m': 'Your account has been suspended. Please contact admin.'})

        # Login user
        login(request, user)

        # Force password change if required
        if profile.must_change_password:
            return redirect('force_password_change')

        # Redirect by role
        if profile.user_type == 'supervisor':
            return redirect('home_supervisors')
        elif profile.user_type == 'student':
            return redirect('home_students')
        elif profile.user_type == 'coordinator':
            return redirect('home')

    return render(request, 'accounts/login.html')


def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            messages.error(request, 'Please provide an email address.')
            return redirect('password_reset_request')
        
        user = User.objects.filter(email=email).first()
        if user:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = request.build_absolute_uri(f'/accounts/password-reset/confirm/{uid}/{token}/')
            html_content = f"""
                <html>
                <body style="margin: 0; padding: 0; background-color: #f4f4f4;">
                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px 0;">
                    <tr>
                        <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; padding: 40px; font-family: 'Segoe UI', Roboto, Arial, sans-serif; color: #333333; box-shadow: 0 0 10px rgba(0,0,0,0.08);">
                            <tr>
                            <td align="center" style="padding-bottom: 20px;">
                                <h2 style="margin: 0; font-size: 26px; color: #222;">FYPAS Password Reset</h2>
                            </td>
                            </tr>
                            <tr>
                            <td style="font-size: 16px; line-height: 1.6;">
                                <p>Dear <strong>{user.first_name}</strong>,</p>
                                <p>We received a request to reset your FYPAS account password. Click the link below to reset your password:</p>
                                <p>
                                    <a href="{reset_link}" style="display: inline-block; background-color: #28a745; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Reset Password</a>
                                </p>
                                <p>This link will expire in 1 hour.</p>
                                <p>If you did not request a password reset, please ignore this email.</p>
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
                    subject='FYPAS Password Reset Request',
                    body=html_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email],
                )
                email.content_subtype = "html"
                email.send()
                messages.success(request, 'Password reset link has been sent to your email.')
            except smtplib.SMTPAuthenticationError as e:
                messages.error(request, 'Failed to send reset email due to authentication issue. Please contact the admin.')
            except smtplib.SMTPConnectError as e:
                messages.error(request, 'Failed to send reset email due to connection issue. Please check your network and try again.')
            except socket.timeout as e:
                messages.error(request, 'Failed to send reset email due to timeout. Please check your network and try again.')
            except smtplib.SMTPException as e:
                messages.error(request, 'Failed to send reset email due to SMTP issue. Please contact the admin.')
            except OSError as e:
                messages.error(request, 'Failed to send reset email due to network issue. Please check your network and try again.')
            except Exception as e:
                messages.error(request, 'Failed to send reset email. Please contact the admin.')
        else:
            messages.error(request, 'No user found with this email address.')
        return redirect('password_reset_request')
    return render(request, 'accounts/password_reset_request.html')

def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if new_password != confirm_password:
                return render(request, 'accounts/password_reset_confirm.html', {'error': 'Passwords do not match.'})

            if len(new_password) < 8:
                return render(request, 'accounts/password_reset_confirm.html', {'error': 'Password must be at least 8 characters long.'})

            user.set_password(new_password)
            user.save()
            profile = getattr(user, 'profile', None)
            if profile:
                profile.must_change_password = False
                profile.save()
            messages.success(request, 'Password has been reset successfully. Please log in.')
            return redirect('login')
        return render(request, 'accounts/password_reset_confirm.html', {'uidb64': uidb64, 'token': token})
    else:
        messages.error(request, 'The password reset link is invalid or has expired.')
        return redirect('password_reset_request')

@login_required
def force_password_change(request):
    if request.method == 'POST':
        new_pass = request.POST.get('new_password')
        confirm_pass = request.POST.get('confirm_password')

        if new_pass != confirm_pass:
            return render(request, 'accounts/force_password_change.html', {'error': 'Passwords do not match.'})

        user = request.user
        user.set_password(new_pass)
        user.save()
        update_session_auth_hash(request, user)

        profile = getattr(user, 'profile', None)
        if profile:
            profile.must_change_password = False
            profile.save()

            if profile.user_type == 'supervisor':
                return redirect('/home_supervisors/')
            elif profile.user_type == 'student':
                return redirect('/home_students/')
            elif profile.user_type == 'coordinator':
                return redirect('/home/')
            else:
                return redirect('/')

        messages.success(request, 'Password updated successfully.')
        return redirect('/')

    return render(request, 'accounts/force_password_change.html')

@login_required
def password_change(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        user = request.user
        if not user.check_password(old_password):
            return render(request, 'accounts/password-change.html', {'error': 'Incorrect old password.'})

        if new_password != confirm_password:
            return render(request, 'accounts/password-change.html', {'error': 'New passwords do not match.'})

        if len(new_password) < 8:
            return render(request, 'accounts/password-change.html', {'error': 'New password must be at least 8 characters long.'})

        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)

        return render(request, 'accounts/password-change.html', {'success': 'Password changed successfully.'})

    return render(request, 'accounts/password-change.html')

def user_logout(request):
    messages.get_messages(request).used = True 
    logout(request)
    return redirect('/')