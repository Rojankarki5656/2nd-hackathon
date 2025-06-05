import json
import logging
import time
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from requests.exceptions import RequestException

from .models import CustomUser, Donation, Product, CommunityReport, Comment

logger = logging.getLogger(__name__)

def index(request):
    if request.user.is_authenticated:
        return redirect('core-dashboard')
    return render(request, 'core/landing.html')

def user_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            if user.is_superuser or user.is_staff:
                return redirect('core-impact_analytics_dashboard')
            next_url = request.GET.get('next', 'core-dashboard')
            return redirect(next_url)
        else:
            return render(request, 'core/login.html', {
                'user_login_error': 'Invalid email or password'
            })
    return render(request, 'core/login.html')

def signup(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        full_name = request.POST.get('full_name')

        if CustomUser.objects.filter(email=email).exists():
            return render(request, 'core/signup.html', {
                'user_signup_error': 'Email already exists',
            })

        user = CustomUser.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=full_name,
        )
        login(request, user)
        next_url = request.GET.get('next', 'core-about-user')
        return redirect(next_url)

    return render(request, 'core/signup.html')

@login_required
def user_about(request):
    if request.method == 'POST':
        gender = request.POST.get('gender')
        dob = request.POST.get('dob')
        medical_conditions = request.POST.getlist('medical_condition')
        request.user.gender = gender
        request.user.dob = dob
        request.user.medical_condition = ', '.join(medical_conditions)
        request.user.save()
        return redirect('core-dashboard')
    return render(request, 'core/about_user.html')

@login_required
def dashboard(request):
    return render(request, 'core/dashboard.html')

@login_required
def community_watch(request):
    if request.method == 'POST':
        CommunityReport.objects.create(
            reporter_name=request.POST.get('reporter_name'),
            item_name=request.POST.get('item_name'),
            location=request.POST.get('location'),
            issue_type=request.POST.get('issue_type'),
            description=request.POST.get('description'),
            photo=request.FILES.get('photo')
        )
        return redirect('core-community_watch')
    reports = CommunityReport.objects.all().order_by('-created_at')
    return render(request, 'core/community_watch.html', {
        'reports': reports,
        'user': request.user,
    })

@login_required
def ingredient_scanner_dashboard(request):
    return render(request, 'core/ingredient_scanner_dashboard.html')

@user_passes_test(lambda u: u.is_superuser or u.is_staff or getattr(u, 'is_admin', False))
def impact_analytics_dashboard(request):
    food_waste_reduced = Product.objects.filter(status='Donated').count()
    donations_matched = Donation.objects.count()
    community_reports = CommunityReport.objects.count()
    safe_ingredients_scanned = 26  # Placeholder

    today = timezone.now().date()
    expiry_trends = [
        Product.objects.filter(expire_date=today - timedelta(days=i)).count()
        for i in reversed(range(7))
    ]

    status_breakdown = {
        'Available': Product.objects.filter(status='Available').count(),
        'Donated': Product.objects.filter(status='Donated').count(),
        'Thrown': Product.objects.filter(status='Thrown').count(),
    }

    flags_by_type = {
        'Expired': Product.objects.filter(expire_date__lt=today, status='Available').count(),
    }

    context = {
        'food_waste_reduced': food_waste_reduced,
        'donations_matched': donations_matched,
        'community_reports': community_reports,
        'safe_ingredients_scanned': safe_ingredients_scanned,
        'expiry_trends': expiry_trends,
        'status_breakdown': status_breakdown,
        'flags_by_type': flags_by_type,
    }
    return render(request, 'core/impact_analytics_dashboard.html', context)

@login_required
def admin_dashboard(request):
    return render(request, 'core/admin_dashboard.html')

def logout_view(request):
    logout(request)
    return redirect('index')

@login_required
def donation_portal_dashboard(request):
    search_query = request.GET.get('search', '')
    if search_query:
        products = Product.objects.filter(
            user=request.user,
            name__icontains=search_query,
            status='Available'
        ).order_by('expire_date')
    else:
        products = Product.objects.filter(
            user=request.user,
            status='Available'
        ).order_by('expire_date')
    total_products = products.count()
    third = total_products // 3
    red_end = third
    yellow_end = third * 2
    expiring_soon_count = red_end
    last_week = timezone.now() - timedelta(days=7)
    donation_count = Donation.objects.filter(
        user=request.user,
        created_at__gte=last_week
    ).count()
    context = {
        'products': products,
        'red_end': red_end,
        'yellow_end': yellow_end,
        'expiring_soon_count': expiring_soon_count,
        'donation_count': donation_count,
    }
    return render(request, 'core/donation_portal_dashboard.html', context)

@login_required
def donation_create(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        try:
            donor_name = request.POST.get('donor_name')
            contact_email = request.POST.get('contact_email')
            contact_number = request.POST.get('contact')
            pickup_address = request.POST.get('address')
            pickup_datetime = request.POST.get('pickup_datetime')
            notes = request.POST.get('notes', '')

            donation = Donation(
                user=request.user,
                product=product,
                donor_name=donor_name,
                contact_email=contact_email,
                contact_number=contact_number,
                pickup_address=pickup_address,
                pickup_datetime=pickup_datetime,
                notes=notes
            )
            donation.full_clean()
            donation.save()

            product.status = 'Donated'
            product.save()

            messages.success(request, f"Donation of {product.name} successfully submitted!")
            return redirect('donation-history')
        except ValidationError as e:
            messages.error(request, f"Error: {', '.join(e.messages)}")
            return render(request, 'core/donation_details.html', {'product': product})
    return render(request, 'core/donation_details.html', {'product': product})

def add_product(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        manufacture_date = request.POST.get('manufacture_date')
        expire_date = request.POST.get('expire_date')
        try:
            Product.objects.create(
                user=request.user,
                name=name,
                manufacture_date=manufacture_date,
                expire_date=expire_date,
                status='Available'
            )
            messages.success(request, 'Product added successfully!')
        except Exception as e:
            messages.error(request, f'Error adding product: {str(e)}')
        return redirect('core-donation_portal_dashboard')
    return redirect('core-donation_portal_dashboard.html')

def throw_product(request, product_id):
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to throw a product.')
        return redirect('login')
    product = get_object_or_404(Product, id=product_id, user=request.user)
    if request.method == 'POST':
        try:
            product.status = 'Thrown'
            product.save()
            messages.success(request, f'{product.name} marked as thrown!')
        except Exception as e:
            messages.error(request, f'Error throwing product: {str(e)}')
        return redirect('core-donation_portal_dashboard')
    return render(request, 'core/confirm_throw.html', {'product': product})

def profile(request):
    user = request.user
    medical_condition_str = getattr(user, "medical_condition", "")
    if medical_condition_str:
        medical_condition_list = [c.strip() for c in medical_condition_str.split(",") if c.strip()]
    else:
        medical_condition_list = []
    context = {
        "user": user,
        "gender": getattr(user, "gender", ""),
        "dob": getattr(user, "dob", ""),
        "medical_condition": medical_condition_str,
        "medical_condition_list": medical_condition_list,
    }
    return render(request, "core/profile.html", context)
@login_required
def ai_waste_dashboard(request):
    return render(request, 'core/ai_waste_dashboard.html')


@login_required
def check_safety(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ingredient = data.get('ingredient')
            expiration = data.get('expiration')
            conditions = data.get('conditions')
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {'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'}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "meta-llama/llama-3.1-8b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a food safety expert. Provide a concise safety assessment for the given product"
                            "based on the user's medical condition. Return JSON with 'status' (Safe, Caution, Risky), "
                            "'score' (0-100), and 'explanation'. Use double quotes for all strings."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Assess the safety of {ingredient} for someone with {conditions}. "
                            f"Expiration date: {expiration or 'not provided'}. "
                            "Return the response in JSON format with 'status', 'score', and 'explanation' fields. "
                            "Use double quotes for all strings."
                        )
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.2,
                "top_p": 0.9
            }
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                result = response.json()
                api_response = result.get('choices', [{}])[0].get('message', {}).get('content', '{}')
                safety_data = json.loads(api_response) if isinstance(api_response, str) else api_response
                safety_data = json.loads(json.dumps(safety_data, ensure_ascii=False))
                safety_response = [safety_data] if isinstance(safety_data, dict) else safety_data
                for item in safety_response:
                    item['ingredient'] = ingredient
                return JsonResponse(safety_response, safe=False)
            except requests.exceptions.RequestException as e:
                return JsonResponse({
                    "error": f"API request failed: {str(e)}"
                }, status=500)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid request data"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request method"}, status=405)

@login_required
def donation_details(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        return redirect('core-donation_portal_dashboard')
    return render(request, 'core/donation_details.html', {'product': product})

def delete_product(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        product.delete()
        messages.success(request, 'Product deleted successfully!')
    return redirect('core-donation_portal_dashboard')

def add_comment(request, report_id):
    if request.method == 'POST':
        report = get_object_or_404(CommunityReport, id=report_id)
        text = request.POST.get('comment')
        if text and request.user.is_authenticated:
            Comment.objects.create(
                report=report,
                user=request.user,
                text=text
            )
    return redirect('core-community_watch')

@login_required
def delete_community_report(request, report_id):
    report = get_object_or_404(CommunityReport, id=report_id)
    if request.user.is_superuser or report.reporter_name == request.user.get_full_name() or report.reporter_name == request.user.username:
        report.delete()
    return redirect('core-community_watch')

@login_required
def donation_history(request):
    donations = Donation.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'core/donation_history.html', {'donations': donations})

@login_required
def get_response(request):
    if request.method == 'POST':
        message = request.POST.get('message', '')
        if not message:
            return JsonResponse({'error': 'No message provided'}, status=400)
        try:
            url = settings.OPENROUTER_API_URL
            logger.info(f"Making request to OpenRouter API: {url}")
            headers = {
                'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
                'HTTP-Referer': request.build_absolute_uri('/'),
                'X-Title': 'FreshGuard+ Food Safety Assistant'
            }
            messages_arr = [
                {
                    "role": "system",
                    "content": """You are a Food Safety Assistant, an expert in food safety, handling, and regulations. 
                    Your role is to provide accurate, helpful information about:
                    - Food handling and storage best practices
                    - Food safety regulations and compliance
                    - Preventing foodborne illnesses
                    - Restaurant food safety guidelines
                    - Home food safety tips
                    - Food waste reduction
                    - Food safety certifications
                    - Food safety training requirements
                    
                    Always provide practical, actionable advice and cite relevant regulations when applicable.
                    If you're unsure about something, acknowledge the limitation and suggest consulting a food safety expert."""
                },
                {
                    "role": "user",
                    "content": message
                }
            ]
            logger.info(f"Request payload: {{'model': 'anthropic/claude-3-opus:beta', 'messages': [{{'role': 'system'}}, {{'role': 'user'}}]}}")
            response = requests.post(
                url,
                headers=headers,
                json={
                    "model": "anthropic/claude-3-opus:beta",
                    "messages": messages_arr,
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                timeout=30
            )
            logger.info(f"API Response Status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            logger.info("Successfully received response from OpenRouter API")
            return JsonResponse(data)
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            logger.error(error_msg)
            if hasattr(e.response, 'text'):
                logger.error(f"Response text: {e.response.text}")
            return JsonResponse({
                'error': 'Failed to get response from AI service. Please try again.'
            }, status=500)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return JsonResponse({
                'error': 'An unexpected error occurred. Please try again.'
            }, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required
def ai_waste_chatbot(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)
    try:
        data = json.loads(request.body)
        message = data.get('message')
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        api_key = settings.OPENROUTER_API_KEY
        api_url = settings.OPENROUTER_API_URL
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': request.build_absolute_uri('/'),
            'X-Title': 'FreshGuard+ Waste Reduction'
        }
        payload = {
            'model': 'openai/gpt-3.5-turbo',
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are a helpful Food Safety and Waste Reduction Assistant. Provide creative recipes and tips for using leftover ingredients and reducing food waste. Format your response with "Recipes:" and "Tips:" sections.'
                },
                {
                    'role': 'user',
                    'content': message
                }
            ],
            'max_tokens': 400,
            'temperature': 0.7
        }
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        ai_response = result['choices'][0]['message']['content']
        return JsonResponse({'response': ai_response})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenRouter API request failed: {str(e)}")
        if hasattr(e.response, 'text'):
            logger.error(f"API response: {e.response.text}")
        return JsonResponse({'error': 'Failed to get response from AI service'}, status=500)
    except Exception as e:
        logger.error(f"Unexpected error in ai_waste_chatbot: {str(e)}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

def call_openrouter_api(messages, model="anthropic/claude-3-opus:beta", max_tokens=200, temperature=0.7, max_retries=3):
    url = settings.OPENROUTER_API_URL
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "FreshGuard+ Food Safety Assistant"
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    retry_count = 0
    base_delay = 1
    while retry_count < max_retries:
        try:
            logger.info(f"Making request to OpenRouter API (attempt {retry_count + 1}/{max_retries})")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 401:
                logger.error("Authentication failed: Invalid or expired API key")
                raise Exception("Authentication failed. Please check your API key configuration.")
            elif response.status_code == 402:
                logger.error("Payment required: Insufficient credits")
                if max_tokens > 100:
                    logger.info(f"Retrying with reduced tokens: {max_tokens - 50}")
                    return call_openrouter_api(messages, model, max_tokens - 50, temperature, max_retries)
                raise Exception("Insufficient credits. Please add credits to your OpenRouter account.")
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded. Retrying with backoff...")
                retry_count += 1
                if retry_count < max_retries:
                    delay = base_delay * (2 ** retry_count)
                    time.sleep(delay)
                    continue
                raise Exception("Rate limit exceeded. Please try again later.")
            response.raise_for_status()
            result = response.json()
            if not result or 'choices' not in result or not result['choices']:
                logger.error("Invalid response format from API")
                raise Exception("Invalid response from AI service")
            return result
        except RequestException as e:
            logger.error(f"API request failed (attempt {retry_count + 1}/{max_retries}): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response text: {e.response.text}")
            retry_count += 1
            if retry_count < max_retries:
                delay = base_delay * (2 ** retry_count)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise Exception("Failed to connect to AI service after multiple attempts. Please try again later.")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise Exception("An unexpected error occurred. Please try again later.")

def get_fallback_response():
    return {
        "choices": [{
            "message": {
                "content": "I apologize, but I'm currently unable to process your request. This could be due to:\n\n" +
                          "1. Temporary service interruption\n" +
                          "2. High server load\n" +
                          "3. Network connectivity issues\n\n" +
                          "Please try again in a few moments. If the problem persists, you can:\n" +
                          "- Check your internet connection\n" +
                          "Contact support if the issue continues"
            }
        }]
    }