from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from smart_mirror.settings import MEDIA_URL, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER, YOUR_WHATSAPP_NUMBER, NGROK_URL
from users.models import Profile
import random
from django.core.mail import send_mail
import requests
from datetime import datetime
import qrcode
from django.http import HttpResponse
from io import BytesIO
import base64
import uuid
from .models import QRLoginSession, UserProfile
from django.contrib.auth import authenticate, login as auth_login
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.files.storage import default_storage
from twilio.rest import Client
from django.core.cache import cache



def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_superuser:
                return redirect('dashboard')  # Redirect admin
            else:
                return redirect('user_dashboard')  # Redirect user
        else:
            messages.error(request, "Invalid Username or Password")
    return render(request, 'users/login.html')

@login_required
def user_logout(request):
    logout(request)
    return redirect('login')

@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('user_dashboard')  # Prevent non-admin access

    users = User.objects.all()

    # Count users who are superusers (admins)
    total_admins = users.filter(is_superuser=True).count()

    # Count unique locations from user profiles
    total_locations = users.exclude(profile__location='').values_list('profile__location', flat=True).distinct().count()

    context = {
        'users': users,
        'total_admins': total_admins,
        'total_locations': total_locations,
        'total_users': users.count(),
    }
    return render(request, 'users/dashboard.html', context)

@login_required
def user_dashboard(request):
    user = request.user
    # Corrected: Fetch or create Profile instance linked to the user
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        # Handle Profile Picture Upload
        if 'profile_pic' in request.FILES:
            profile.image = request.FILES['profile_pic']
            profile.save()
            messages.success(request, 'Profile picture updated successfully.')
            return redirect('user_dashboard')

        # Handle Profile Info Update
        username = request.POST.get('username')
        location = request.POST.get('location')
        password = request.POST.get('password')

        if username:
            user.username = username
        if location:
            profile.location = location  # Assuming 'location' is in Profile model
        if password:
            user.set_password(password)  # Note: Log user back in after password change

        user.save()
        profile.save()  # Save profile if anything changed
        messages.success(request, 'Profile updated successfully.')
        return redirect('user_dashboard')

    # Example placeholders for mirror preview data (replace with dynamic if needed)
    context = {
        'user': user,
        'profile': profile,
        'profile_image_url': profile.image.url if profile.image else None,
        'current_time': '9:00 AM',
        'weather_info': 'Sunny, 24°C',
        'greeting': f'Hello, {user.first_name}!',
        'quote': 'Stay positive. Work hard. Make it happen.',
        'outfit': 'Light Shirt and Jeans',
    }
    return render(request, 'users/user_dashboard.html', context)

@login_required
def update_user_profile(request):
    if request.method == "POST":
        user = request.user
        user.username = request.POST.get('username')
        user.location = request.POST.get('location')
        password = request.POST.get('password')
        if password:
            user.set_password(password)
        user.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('user_dashboard')

@login_required
def add_user(request):
    if not request.user.is_superuser:
        return redirect('user_dashboard')  # Prevent non-admin access

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        location = request.POST['location']
        phone_number = request.POST['phone_number']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is not Available!")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered!")
        elif UserProfile.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number is already registered!")
        else:
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email
            )
            user.profile.location = location  # Save location in user's profile
            user.profile.phone_number = phone_number
            user.profile.save()
            messages.success(request, "User added successfully!")
            return redirect('add_user')  # Redirect to admin dashboard

    return render(request, 'users/add_user.html')


@login_required
def update_user(request, user_id):
    # if not request.user.is_superuser:
    #     return redirect('user_dashboard')  # Prevent non-admin access

    user = User.objects.get(id=user_id)

    if request.method == 'POST':
        user.username = request.POST['username']
        new_password = request.POST['password']
        location = request.POST['location']
        phone_number = request.POST['phone_number']

        if new_password:  # Update password only if provided
            user.set_password(new_password)

        user.profile.location = location  # Update location
        user.profile.phone_number = phone_number
        user.profile.save()
        user.save()

        messages.success(request, "User updated successfully!")
      

    return render(request, 'users/update_user.html', {'user': user})


@login_required
def delete_user(request, user_id):
    if request.method == "POST":
        user = get_object_or_404(User, id=user_id)
        if request.user.is_superuser:
            user.delete()
            messages.success(request, f"User {user.username} has been deleted successfully!")
        else:
            messages.error(request, "You do not have permission to delete users.")

    return redirect('dashboard')

# Send OTP
def request_otp(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            otp = random.randint(100000, 999999)
            request.session['reset_email'] = email
            request.session['otp'] = str(otp)
            send_mail(
                'Your Password Reset OTP',
                f'Your OTP is: {otp}',
                'your_email@example.com',  # Use your sender email
                [email],
                fail_silently=False,
            )
            messages.success(request, 'OTP sent to your email.')
            return redirect('verify_otp')
        except User.DoesNotExist:
            messages.error(request, 'No user found with that email.')
    return render(request, 'users/request_otp.html')

# Verify OTP
def verify_otp(request):
    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        if otp_entered == request.session.get('otp'):
            return redirect('reset_password')
        else:
            messages.error(request, 'Invalid OTP.')
    return render(request, 'users/verify_otp.html')

# Reset Password
def reset_password(request):
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        email = request.session.get('reset_email')
        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()
        messages.success(request, 'Password reset successfully. Please login.')
        return redirect('login')
    return render(request, 'users/reset_password.html')

def get_user_location(request):
    ip = request.META.get('REMOTE_ADDR', '103.87.197.51')
    try:
        response = requests.get(f'https://ipinfo.io/{ip}?token=ca7bf6e0463fc8')
        data = response.json()
        city = data.get('city', 'Kathmandu')
        return city
    except:
        return 'Kathmandu'

def get_weather(city):
    api_key = '1a29cd579ef841c178fde367966796d2'
    url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'
    response = requests.get(url)
    data = response.json()
    if data.get('main'):
        temperature = data['main']['temp']
        description = data['weather'][0]['description'].capitalize()
        return f'{description}, {temperature}°C'
    return 'Weather data unavailable'

def get_news():
    api_key = 'c572d7a5766442ad9a8c07a94e758173'
    url = f'https://newsapi.org/v2/top-headlines?country=us&apiKey={api_key}'
    response = requests.get(url)
    data = response.json()
    articles = data.get('articles', [])[:5]
    headlines = [article['title'] for article in articles]
    return headlines

@login_required
def mirror_preview(request):
    user = request.user
    profile = Profile.objects.get(user=user)

    # Get user location dynamically
    location = get_user_location(request)

    # Fetch Weather and News
    weather_data = get_weather(location)
    weather_data = 'Clear and sunny, 31°C'
    news_headlines = get_news()
    current_time = datetime.now().strftime('%I:%M %p')
    current_day = datetime.now().strftime('%A')
    current_date = datetime.now().strftime('%B %d, %Y')

    # Default outfit and icon
    outfit = "Dress comfortably."
    weather_icon = 'fas fa-cloud'

    # Extract temperature and description if weather data is available
    if weather_data != 'Weather data unavailable':
        temp_text = weather_data.split(',')[-1].replace('°C', '').strip()
        try:
            temperature = float(temp_text)
            description = weather_data.split(',')[0]
            outfit = get_outfit_recommendation(temperature, description)
            weather_icon = get_weather_icon(description)
        except:
            pass

    face_status = cache.get('face_status')
    face_name = cache.get('face_name')
    emotion = cache.get('emotion')
    unknown_image = cache.get('unknown_image')

    # Emotion-based quote map
    quote_map = {
        'happy': "Keep smiling, you're doing great!",
        'sad': "You look sad!! Tough times never last, tough people do.",
        'angry': "Breathe. Let go. Stay calm.",
    }

    # Dynamic greeting and quote based on recognition
    if face_status == 'known' and face_name:
        greeting = f"Welcome, {face_name.capitalize()}!"
        quote = quote_map.get(emotion, "Stay strong.")
    else:
        greeting = f"Hello! There"
        quote = random.choice(list(quote_map.values()))

    context = {
        'current_time': current_time,
        'current_day': current_day,
        'current_date': current_date,
        'weather_info': weather_data,
        'news_headlines': news_headlines,
        'greeting': greeting,
        'outfit': outfit,
        'quote': quote,
        'weather_icon': weather_icon,
    }
    print("Face:", face_status, face_name, emotion)


    return render(request, 'users/mirror_preview.html', context)

def get_outfit_recommendation(temperature, description):
    if 'snow' in description.lower():
        return "Wear thermal layers, a heavy coat, and boots."
    elif 'rain' in description.lower():
        return "Carry an umbrella and wear waterproof clothing."
    elif temperature >= 30:
        return "Wear lightweight cotton clothes and stay hydrated."
    elif 25 <= temperature < 30:
        return "Opt for breathable fabrics like linen or cotton."
    elif 18 <= temperature < 25:
        return "A light jacket or hoodie would be perfect."
    elif 10 <= temperature < 18:
        return "Wear a warm sweater or light coat."
    else:
        return "Bundle up with a heavy coat, gloves, and a scarf."

def get_weather_icon(description):
    description = description.lower()
    if 'clear' in description:
        return 'fas fa-sun'
    elif 'few clouds' in description or 'scattered clouds' in description:
        return 'fas fa-cloud-sun'
    elif 'cloud' in description:
        return 'fas fa-cloud'
    elif 'rain' in description:
        return 'fas fa-cloud-showers-heavy'
    elif 'snow' in description:
        return 'fas fa-snowflake'
    elif 'storm' in description or 'thunderstorm' in description:
        return 'fas fa-bolt'
    else:
        return 'fas fa-cloud'

def generate_qr(request):
    login_url = NGROK_URL  
    qr = qrcode.make(login_url)
    buffer = BytesIO()
    qr.save(buffer, format='PNG')
    return HttpResponse(buffer.getvalue(), content_type='image/png')

# Simulating auto-login (in production you should use tokens)
def qr_login_action(request):
    user = User.objects.get(username='your_test_user')  
    login(request, user)
    return HttpResponse("You are now logged in. Go check your PC session.")

def qr_login_page(request):
    token = str(uuid.uuid4())
    QRLoginSession.objects.create(token=token)

    public_url = request.build_absolute_uri('/').rstrip('/')
    qr_data = f"{public_url}/qr-scan-login/?token={token}"

    qr = qrcode.make(qr_data)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_image = base64.b64encode(buffer.getvalue()).decode()

    return render(request, 'users/qr_login.html', {'qr_image': qr_image, 'token': token})

def qr_scan_login(request):
    token = request.GET.get('token')
    session = get_object_or_404(QRLoginSession, token=token)

    # Add the redirect URL to the context or pass it in the token
    public_url = request.build_absolute_uri('/').rstrip('/')
    mirror_preview_url = f"{public_url}/mirror-preview/"  # Your mirror_preview URL

    return render(request, 'users/phone_login.html', {
        'token': token,
        'mirror_preview_url': mirror_preview_url
    })


def phone_login_complete(request):
    if request.method == "POST":
        token = request.POST.get('token')
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        
        if user:
            session = get_object_or_404(QRLoginSession, token=token)
            session.user = user
            session.is_authenticated = True
            session.save()
            
            # After login, we show the phone login successful page
            return render(request, 'users/phone_login_success.html')  # This page confirms login was successful.
        else:
            return render(request, 'users/phone_login.html', {'token': token, 'error': 'Invalid credentials'})


def qr_check_status(request):
    token = request.GET.get('token')
    session = get_object_or_404(QRLoginSession, token=token)
    if session.is_authenticated:
        login(request, session.user)  # Login the user
        return JsonResponse({'authenticated': True})
    return JsonResponse({'authenticated': False})

def send_whatsapp_alert(image_url):
    account_sid = TWILIO_ACCOUNT_SID
    auth_token = TWILIO_AUTH_TOKEN
    client = Client(account_sid, auth_token)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message_text = f"⚠️ Unknown person detected at {now}.\nPlease check the image above."

    message = client.messages.create(
        from_='whatsapp:+14155238886',
        body=message_text,
        to='whatsapp:+9779808253241',
        media_url=[image_url]
    )

    print(f"WhatsApp alert sent: SID={message.sid}, Status={message.status}")


@csrf_exempt
def mirror_feed_api(request):
    if request.method == 'POST':
        status = request.POST.get('status')
        emotion = request.POST.get('emotion')
        image = request.FILES.get('image')

        public_url = NGROK_URL # e.g., https://yoursubdomain.loca.lt

        image_url = None  # initialize safely
        if image:
            path = default_storage.save(f'unknown_faces/{image.name}', image)
            cache.set('unknown_image', path)
            image_url = f"{public_url}/media/{path}"

        # Handle known or unknown
        known_names = ['suvan', 'sundar']
        if status in known_names:
            cache.set('face_status', 'known')
            cache.set('face_name', status)
        else:
            cache.set('face_status', 'unknown')
            cache.set('face_name', None)

            # Send WhatsApp only for unknowns and if image URL is available
            if image_url:
                send_whatsapp_alert(image_url)

        cache.set('emotion', emotion)

        return JsonResponse({'success': True})
    
def terms_and_conditions(request):
    return render(request, 'users/terms_and_conditions.html')






