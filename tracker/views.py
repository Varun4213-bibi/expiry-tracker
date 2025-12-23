from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import datetime
from django.utils import timezone
from datetime import timedelta
from .models import Item, Product, UserProfile
from .forms import ItemForm
import easyocr
from PIL import Image
import re
import base64
from io import BytesIO
import cv2
import numpy as np
import calendar
from urllib.parse import urlencode, quote
from dateutil.parser import parse as date_parser

def correct_ocr_text(text):
    """
    Correct common OCR misreads in expiry date text for medicine, groceries, and food labels.
    Includes context-aware replacements.
    """
    # Normalize and clean
    cleaned = text.replace('\n',' ').replace('\r',' ').upper()

    # Expanded corrections dictionary
    corrections = {
        # Month corrections
        "5EP": "SEP",
        "0CT": "OCT",
        "N0V": "NOV",
        "JULY": "JUL",
        "AUGUST": "AUG",
        "SEPTEMBER": "SEP",
        "NOVEMBER": "NOV",
        "DECEMBER": "DEC",
        "JAN1": "JAN",
        # Expiry prefixes
        "E3P": "EXP",
        "EXR": "EXP",
        "EXPIRY": "EXP",
        "EXPIRES": "EXP",
        "BEST BEFORE": "BB",
        "USE BY": "UB",
        "MFG": "MFG",
        "LOT": "LOT",
        # Numbers and symbols
        "O": "0",  # Use with caution
        "S": "5",  # For 5 in dates
        "Z": "2",  # For 2
        "B": "8",  # For 8
        "I": "1",  # For 1
        # Separators
        "|": "/",
        "·": ".",
        # Additional common misreads
        "EXPIRY DATE": "EXP",
        "BEST BY DATE": "BB",
        "USE BY DATE": "UB",
        "MANUFACTURED": "MFG",
        "BATCH": "LOT",
        "PRODUCED": "MFG",
        "PACKED": "MFG",
    }

    # Apply general corrections
    for wrong, right in corrections.items():
        cleaned = cleaned.replace(wrong, right)

    # Context-aware replacements: only replace if near date-related words
    date_keywords = ["EXP", "BB", "UB", "MFG", "LOT"]
    for keyword in date_keywords:
        if keyword in cleaned:
            # Replace numbers only in proximity to keywords (within 10 chars)
            start = cleaned.find(keyword)
            if start != -1:
                end = start + len(keyword) + 10
                segment = cleaned[start:end]
                # Apply number corrections in this segment
                segment = segment.replace("O", "0").replace("S", "5").replace("Z", "2").replace("B", "8").replace("I", "1")
                cleaned = cleaned[:start] + segment + cleaned[end:]

    return cleaned

def ocr_expiry_view(request):
    expiry_date = None
    extracted_text = None
    error_message = None

    barcode = request.POST.get('barcode', request.GET.get('barcode', ''))
    product_name = request.POST.get('product_name', request.GET.get('product_name', ''))

    if request.method == "POST":
        if request.POST.get('confirm_date'):
            # Handle confirmation
            confirmed_expiry = request.POST.get('confirmed_expiry', '').strip()
            if confirmed_expiry:
                params = {
                    'barcode': request.POST.get('barcode', ''),
                    'product_name': request.POST.get('product_name', ''),
                    'expiry_date': confirmed_expiry
                }
                redirect_url = reverse('add_item') + '?' + urlencode(params)
                return redirect(redirect_url)
            else:
                error_message = "Please provide a confirmed expiry date."
        else:
            # Handle scanning
            b64_image = request.POST.get('captured_image')
            if b64_image and b64_image.startswith('data:image'):
                try:
                    # Decode and preprocess image for OCR
                    b64_image = b64_image.split(',', 1)[1]
                    img_data = base64.b64decode(b64_image)
                    pil_img = Image.open(BytesIO(img_data))

                    # Enhanced preprocessing: convert to grayscale, resize, noise reduction, thresholding
                    img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

                    # Mobile-specific preprocessing (detect based on image dimensions or EXIF if available)
                    height, width = img_cv.shape[:2]
                    is_mobile = width > height  # Mobile cameras often have landscape orientation

                    if is_mobile:
                        # For mobile images: enhance contrast and sharpness
                        # Convert to LAB color space for better contrast adjustment
                        lab = cv2.cvtColor(img_cv, cv2.COLOR_BGR2LAB)
                        l, a, b = cv2.split(lab)
                        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
                        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
                        l = clahe.apply(l)
                        lab = cv2.merge([l, a, b])
                        img_cv = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

                    # Resize to smaller resolution for faster processing
                    img_cv = cv2.resize(img_cv, (400, 300))
                    # Convert to grayscale
                    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

                    if is_mobile:
                        # Additional mobile-specific preprocessing
                        # Sharpen the image
                        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                        gray = cv2.filter2D(gray, -1, kernel)
                        # Increase contrast
                        gray = cv2.convertScaleAbs(gray, alpha=1.2, beta=10)

                    # Noise reduction with Gaussian blur
                    gray = cv2.GaussianBlur(gray, (3, 3), 0)
                    # Adaptive thresholding for binarization
                    gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

                    # OCR extraction using EasyOCR with GPU if available for faster processing
                    reader = easyocr.Reader(['en'], gpu=True)
                    result = reader.readtext(gray)
                    extracted_text = " ".join([res[1] for res in result])

                    print("=== RAW OCR OUTPUT ===")
                    print(repr(extracted_text))

                    # Use the new correct_ocr_text function for normalization and corrections
                    corrected = correct_ocr_text(extracted_text)
                    print("=== CLEANED FOR REGEX ===")
                    print(repr(corrected))

                    # Expanded patterns for medicine, groceries, food packets, including full dates, 2/4-digit years
                    patterns = [
                        # Prioritize EXP with YYYY-MM-DD
                        r'(EXP|BB|UB)[\s\:\.\-]*([1-2][0-9]{3})[\/\-\.][0-1][0-9][\/\-\.][0-3][0-9]',  # EXP 2025-09-10
                        # General YYYY-MM-DD full dates (e.g., MFG 2025-09-10)
                        r'([1-2][0-9]{3})[\/\-\.][0-1][0-9][\/\-\.][0-3][0-9]',  # 2025-09-10
                        # Added: Prefix + MM/DD/YYYY (e.g., EXP 09/10/2025)
                        r'(EXP|BB|UB)\s*([0-1][0-9])\/([0-3][0-9])\/([1-2][0-9]{3})',  # EXP 09/10/2025
                        # Added: Prefix + DD/MM/YYYY (e.g., EXP 10/09/2025)
                        r'(EXP|BB|UB)\s*([0-3][0-9])\/([0-1][0-9])\/([1-2][0-9]{3})',  # EXP 10/09/2025
                        # New: Prefix + MM/DD/YYYY (e.g., EXP 09/10/2025) with words allowed
                        r'(EXP|BB|UB)[\s\w]*([0-1][0-9])\/([0-3][0-9])\/([1-2][0-9]{3})',  # EXP 09/10/2025 (allow words like DATE between)
                        # New: Prefix + DD/MM/YYYY (e.g., EXP 10/09/2025) with words allowed
                        r'(EXP|BB|UB)[\s\w]*([0-3][0-9])\/([0-1][0-9])\/([1-2][0-9]{3})',  # EXP 10/09/2025
                        # Added: Prefix + MM/DD/YY (e.g., EXP 04/30/26)
                        r'(EXP|BB|UB)\s*([0-1][0-9])\/([0-3][0-9])\/([0-9]{2})',  # EXP 04/30/26
                        # Added: Prefix + DD/MM/YY (e.g., EXP 30/04/26)
                        r'(EXP|BB|UB)\s*([0-3][0-9])\/([0-1][0-9])\/([0-9]{2})',  # EXP 30/04/26
                        # Prefixes with 3-letter month and year
                        r'(EXP|BB|UB)[\s\:\.\-]*([A-Z]{3})[\s\.\:,]*([1-2][0-9]{3})\b',  # EXP/BB/UB SEP 2025 (fixed to 4-digit)
                        r'\b([A-Z]{3})[\.\s\:\-,]*([1-2][0-9]{3})\b',                     # SEP.2025
                        # Prefixes with numeric month and 4-digit year
                        r'(EXP|BB|UB)[\s\:\.\-]*([01][0-9])[\/\.:\-\s]*([1-2][0-9]{3})',  # EXP 09/2025
                        r'([01][0-9])[\/\.:\-\s]*([1-2][0-9]{3})',                         # 09/2025
                        r'([1-2][0-9]{3})[\/\.:\-\s]*([01][0-9])',                         # 2025/09
                        # Full dates DD/MM/YYYY or MM/DD/YYYY
                        r'([0-3][0-9])[\/\-\.][0-1][0-9][\/\-\.][1-2][0-9]{3}',           # 25/04/2025 or 04/25/2025 (fixed year)
                        r'([0-1][0-9])[\/\-\.][0-3][0-9][\/\-\.][1-2][0-9]{3}',           # 04/25/2025
                        # Space-separated full dates DD MM YYYY (common on labels)
                        r'([0-3][0-9])\s+([0-1][0-9])\s+([1-2][0-9]{3})',                # 19 04 2025
                        r'([0-1][0-9])\s+([0-3][0-9])\s+([1-2][0-9]{3})',                # 04 19 2025
                        # Prefixes with 3-letter month and 2-digit year
                        r'(EXP|BB|UB)[\s\:\.\-]*([A-Z]{3})[\s\.\:,]*([0-9]{2})\b',           # EXP SEP 25
                        r'\b([A-Z]{3})[\.\s\:\-,]*([0-9]{2})\b',                              # SEP.25
                        # Prefixes with numeric month and 2-digit year
                        r'(EXP|BB|UB)[\s\:\.\-]*([01][0-9])[\/\.:\-\s]*([0-9]{2})',          # EXP 09/25
                        r'([01][0-9])[\/\.:\-\s]*([0-9]{2})',                                 # 09/25
                        r'([0-9]{2})[\/\.:\-\s]*([01][0-9])',                                 # 25/09
                        # Full dates with 2-digit year
                        r'([0-3][0-9])[\/\-\.][0-1][0-9][\/\-\.][0-9]{2}',                   # 25/04/25
                        r'([0-1][0-9])[\/\-\.][0-3][0-9][\/\-\.][0-9]{2}',                   # 04/25/25
                        # Space-separated full dates with 2-digit year
                        r'([0-3][0-9])\s+([0-1][0-9])\s+([0-9]{2})',                         # 19 04 25
                        r'([0-1][0-9])\s+([0-3][0-9])\s+([0-9]{2})',                         # 04 19 25
                        # Other common formats
                        r'(EXP|BB|UB)[\s\:\.\-]*([1-2][0-9]{3})',                         # EXP 2025 (year only, rare)
                        # DD.MM.YYYY (European) - PRIORITIZE THIS PATTERN - FIXED
                        r'([0-3][0-9])\.([0-1][0-9])\.([1-2][0-9]{3})',                  # 15.09.2025
                        r'([0-3][0-9])\.([0-1][0-9])\s+([1-2][0-9]{3})',                # 15.09 2025 (space separator)
                        # DD,MM,YYYY (with commas - common in some regions)
                        r'([0-3][0-9])\,([0-1][0-9])\,([1-2][0-9]{3})',                  # 25,04,2025
                        # EXP: DD.MM,YYYY (specific pattern from your example)
                        r'(EXP|BB|UB)\:\s*([0-3][0-9])\.([0-1][0-9])\,([1-2][0-9]{3})',  # EXP: 15.09,2025
                        # Aggressive/fuzzy for 4-digit (moved lower to avoid false positives like PAT 2024)
                        r'\b([5S][EP][F])[\.\s\:\-\,]*([1-2][0-9]{3})\b',                 # Accept OCR errors like 5EP 2025
                        r'[E3][XK][P8][\s\:\.\-]*([A-Z0-9]{3})[\.\s\:\-\,]*([1-2][0-9]{3})\b', # E3P SEP 2025
                        # Fuzzy for 2-digit
                        r'\b([5S][EP][F])[\.\s\:\-\,]*([0-9]{2})\b',                         # SEP.25 fuzzy
                        r'[E3][XK][P8][\s\:\.\-]*([A-Z0-9]{3})[\.\s\:\-\,]*([0-9]{2})\b',    # E3P SEP 25
                        # Fuzzy full dates (last resort)
                        r'([0-3]?[0-9]?)[\/\-\.\,]?([0-1]?[0-9]?)[\/\-\.\,]?([0-9]{2,4})',       # Loose match for partial dates
                    ]
                    current_year = datetime.datetime.now().year
                    current_two_digit = current_year % 100

                    valid_months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
                    possible_dates_with_scores = []  # List of (date, score) tuples
                    today = datetime.date.today()

                    for pattern in patterns:
                        for match in re.finditer(pattern, corrected, re.IGNORECASE):
                            groups = match.groups()
                            if len(groups) >= 2:
                                candidate_date = None
                                score = 0  # Score based on completeness and specificity

                                # Handle prefixed 4-group patterns (prefix + date parts)
                                if len(groups) == 4 and groups[0] and groups[0].upper() in ['EXP', 'BB', 'UB']:
                                    prefix, g1, g2, g3 = groups
                                    score = 12  # High score for prefixed full dates
                                    try:
                                        if g3.isdigit():  # year last (MM/DD/YYYY, DD/MM/YYYY, or with 2-digit YY)
                                            part1_str, part2_str, year_str = g1, g2, g3
                                            p1 = int(part1_str)
                                            p2 = int(part2_str)
                                            if len(year_str) == 4:
                                                year_int = int(year_str)
                                                if current_year - 2 <= year_int <= current_year + 10:
                                                    if p1 <= 12 and p1 >= 1:
                                                        month_int, day_int = p1, p2
                                                    else:
                                                        month_int, day_int = p2, p1
                                                    if 1 <= month_int <= 12 and 1 <= day_int <= 31:
                                                        candidate_date = datetime.date(year_int, month_int, day_int)
                                            elif len(year_str) == 2:
                                                year_int = int(year_str)
                                                base_year = 2000 + year_int
                                                if year_int < (current_year % 100) - 10:
                                                    base_year = 1900 + year_int
                                                full_year = base_year
                                                if current_year - 2 <= full_year <= current_year + 10:
                                                    if p1 <= 12 and p1 >= 1:
                                                        month_int, day_int = p1, p2
                                                    else:
                                                        month_int, day_int = p2, p1
                                                    if 1 <= month_int <= 12 and 1 <= day_int <= 31:
                                                        candidate_date = datetime.date(full_year, month_int, day_int)
                                                        score = 10  # Slightly lower for 2-digit year
                                        else:  # year first (YYYY-MM-DD)
                                            year_str, month_str, day_str = g1, g2, g3
                                            year_int = int(year_str)
                                            month_int = int(month_str)
                                            day_int = int(day_str)
                                            if 1 <= month_int <= 12 and 1 <= day_int <= 31 and current_year - 2 <= year_int <= current_year + 10:
                                                candidate_date = datetime.date(year_int, month_int, day_int)
                                    except ValueError:
                                        continue
                                # Handle full date patterns (3 groups)
                                elif len(groups) == 3:
                                    g1, g2, g3 = groups
                                    if g1 and g2 and g3:
                                        score = 10  # High score for full dates
                                        try:
                                            # Special handling for European date format with space: DD.MM YYYY
                                            if len(g1) == 2 and len(g2) == 2 and len(g3) == 4 and g1.isdigit() and g2.isdigit() and g3.isdigit():
                                                # This is likely DD.MM YYYY format
                                                day_int = int(g1)
                                                month_int = int(g2)
                                                year_int = int(g3)
                                                if 1 <= day_int <= 31 and 1 <= month_int <= 12 and current_year - 2 <= year_int <= current_year + 10:
                                                    candidate_date = datetime.date(year_int, month_int, day_int)
                                                    score = 15  # Very high score for European date format
                                            # Check if first group is 4-digit year (YYYY-MM-DD or YYYY MM DD)
                                            elif len(g1) == 4 and g1.isdigit() and 2000 <= int(g1) <= 2035:
                                                year_str, month_str, day_str = g1, g2, g3
                                                year_int = int(year_str)
                                                month_int = int(month_str)
                                                day_int = int(day_str)
                                                if 1 <= month_int <= 12 and 1 <= day_int <= 31 and current_year - 2 <= year_int <= current_year + 10:
                                                    candidate_date = datetime.date(year_int, month_int, day_int)
                                            # Otherwise, assume day/month/year or month/day/year (existing logic)
                                            else:
                                                p1 = int(g1)
                                                p2 = int(g2)
                                                year_int = int(g3)
                                                if len(g3) == 2:
                                                    base_year = 2000 + year_int
                                                    if year_int < (current_year % 100) - 10:
                                                        base_year = 1900 + year_int
                                                    full_year = base_year
                                                    score = 8  # Lower score for 2-digit year
                                                else:
                                                    full_year = year_int
                                                if current_year - 2 <= full_year <= current_year + 10:
                                                    if p1 <= 12 and p1 >= 1:
                                                        month, day = p1, p2
                                                    else:
                                                        month, day = p2, p1
                                                    if 1 <= month <= 12 and 1 <= day <= 31:
                                                        candidate_date = datetime.date(full_year, month, day)
                                        except ValueError:
                                            continue
                                else:
                                    # Month/year or year/month patterns (2+ groups, take first two digits)
                                    digit_groups = [g for g in groups if g and g.isdigit()]
                                    if len(digit_groups) >= 2:
                                        g1, g2 = digit_groups[0], digit_groups[1]
                                        if g1 and g2:
                                            score = 5  # Medium score for month/year patterns
                                            # Check for year-month (4-digit year first, 2-digit month)
                                            if len(g1) == 4 and 2000 <= int(g1) <= 2035 and len(g2) == 2 and 1 <= int(g2) <= 12:
                                                try:
                                                    candidate_date = datetime.date(int(g1), int(g2), 1)
                                                except ValueError:
                                                    pass
                                            # Check for month-year (2-digit month first, 4-digit year)
                                            elif len(g1) == 2 and 1 <= int(g1) <= 12 and len(g2) == 4 and 2000 <= int(g2) <= 2035:
                                                try:
                                                    candidate_date = datetime.date(int(g2), int(g1), 1)
                                                except ValueError:
                                                    pass
                                            # Check for 2-digit year-month (e.g., 25-09 as 2025-09)
                                            elif len(g1) == 2 and len(g2) == 2 and 1 <= int(g2) <= 12:
                                                year_int = int(g1)
                                                month_int = int(g2)
                                                if year_int >= current_two_digit - 2 and year_int <= current_two_digit + 10:
                                                    full_year = 2000 + year_int
                                                    try:
                                                        candidate_date = datetime.date(full_year, month_int, 1)
                                                        score = 4  # Lower score for ambiguous 2-digit patterns
                                                    except ValueError:
                                                        pass
                                            # Check for 2-digit month-year (09-25 as 2025-09)
                                            elif len(g1) == 2 and 1 <= int(g1) <= 12 and len(g2) == 2:
                                                year_int = int(g2)
                                                month_int = int(g1)
                                                if year_int >= current_two_digit - 2 and year_int <= current_two_digit + 10:
                                                    full_year = 2000 + year_int
                                                    try:
                                                        candidate_date = datetime.date(full_year, month_int, 1)
                                                        score = 4  # Lower score for ambiguous 2-digit patterns
                                                    except ValueError:
                                                        pass
                                    # 3-letter month + year
                                    month_str = next((g for g in groups if g and len(g) <= 3 and g.isalpha()), None)
                                    if month_str:
                                        month = month_str.upper()
                                        year_str = next((g for g in groups if g and g.isdigit()), None)
                                        if year_str:
                                            score = 6  # Medium-high score for month names
                                            try:
                                                year_int = int(year_str)
                                                if len(year_str) == 2:
                                                    if year_int >= current_two_digit - 2 and year_int <= current_two_digit + 10:
                                                        full_year = 2000 + year_int
                                                    else:
                                                        full_year = 2000 + year_int
                                                else:
                                                    full_year = year_int
                                                if current_year - 2 <= full_year <= current_year + 10 and month in valid_months:
                                                    month_num = valid_months.index(month) + 1
                                                    candidate_date = datetime.date(full_year, month_num, 1)
                                            except (ValueError, IndexError):
                                                pass

                                if candidate_date:
                                    # Collect all plausible dates with their scores
                                    if candidate_date > today or current_year - 2 <= candidate_date.year <= current_year + 10:
                                        possible_dates_with_scores.append((candidate_date, score))

                    # Select the date with highest score (completeness/specificity)
                    if possible_dates_with_scores:
                        # Sort by score (descending) then by date (latest first)
                        possible_dates_with_scores.sort(key=lambda x: (-x[1], x[0]))
                        best_date, best_score = possible_dates_with_scores[0]
                        expiry_date = best_date.strftime("%Y-%m-%d")
                        print(f"=== SELECTED DATE: {expiry_date} (score: {best_score}) ===")
                    else:
                        error_message = "Expiry not found or year looks unrealistic. Try again with a close, bright expiry region."
                except Exception as e:
                    error_message = f"Error processing image: {e}"
            else:
                error_message = "No image captured."

    # AJAX or normal response
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == "POST" and expiry_date and is_ajax:
        parsed = parse_expiry_date_string(expiry_date)
        if parsed:
            return JsonResponse({'success': True, 'expiry_date': parsed.isoformat()})
        else:
            return JsonResponse({'success': False, 'error': 'Could not parse the detected date'})

    return render(request, 'ocr_expiry.html', {
        'expiry_date': expiry_date,
        'extracted_text': extracted_text,
        'error_message': error_message,
        'barcode': barcode,
        'product_name': product_name,
    })


from django.contrib.auth.decorators import login_required

@login_required
def view_items(request):
    items = Item.objects.filter(user=request.user).order_by('expiry_date')
    today_date = datetime.date.today()

    # Initialize counters
    expired_count = 0
    expiring_soon_count = 0
    safe_count = 0

    for item in items:
        if item.expiry_date:
            item.days_left = (item.expiry_date - today_date).days
            item.abs_days_left = abs(item.days_left)
        else:
            item.days_left = None
            item.abs_days_left = None

        if item.days_left is not None:
            if item.days_left < 0:
                item.expiry_status = 'Expired'
                expired_count += 1
            elif item.days_left == 0:
                item.expiry_status = 'Expires Today'
                expiring_soon_count += 1
            elif item.days_left <= 14:
                item.expiry_status = 'Expiring Soon'
                expiring_soon_count += 1
            elif item.days_left <= 30:
                item.expiry_status = 'Expiring in 30 Days'
                expiring_soon_count += 1  # Fixed: items expiring in 30 days should count as expiring soon
            else:
                item.expiry_status = 'Safe'
                safe_count += 1
        else:
            item.expiry_status = 'Unknown'

    context = {
        'items': items,
        'today_date': today_date,
        'expired_count': expired_count,
        'expiring_soon_count': expiring_soon_count,
        'safe_count': safe_count,
    }

    return render(request, 'view_items.html', context)

def home(request):
    return render(request, 'home.html')


# Helper to parse expiry string to proper date
def parse_expiry_date_string(date_str):
    # Full date formats first (keep day)
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y/%m", "%m/%d/%Y", "%d/%m/%Y", "%m/%Y", "%m-%Y", "%b %Y"):
        try:
            parsed = datetime.datetime.strptime(date_str, fmt)
            if fmt in ["%Y-%m", "%Y/%m", "%m/%Y", "%m-%Y", "%b %Y"]:
                return parsed.replace(day=1).date()
            return parsed.date()
        except ValueError:
            continue
    # Fallback to dateutil parser for more flexible parsing
    try:
        parsed = date_parser(date_str)
        return parsed.date()
    except (ValueError, TypeError):
        return None

@login_required
def add_item(request):
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            return redirect('view_items')
        else:
            # Form invalid, render with errors
            pass  # fall through to render
    else:
        barcode = request.GET.get('barcode', '').strip()
        product_name = request.GET.get('product_name', '').strip()
        expiry_date_raw = request.GET.get('expiry_date', '').strip()

        initial_data = {'barcode': barcode}
        if product_name:
            initial_data['name'] = product_name
        if expiry_date_raw:
            parsed = parse_expiry_date_string(expiry_date_raw)
            if parsed:
                initial_data['expiry_date'] = parsed.isoformat()
            else:
                initial_data['expiry_date'] = expiry_date_raw  # fallback if can't parse

        form = ItemForm(initial=initial_data)

        today_date = datetime.date.today().isoformat()
        context = {'form': form, 'today_date': today_date}
        if barcode:
            context['barcode'] = barcode
            context['product_name'] = product_name
            return render(request, 'add_item_with_barcode.html', context)
        else:
            return render(request, 'add_item.html', context)

def scan_product(request):
    today_date = datetime.date.today().isoformat()
    return render(request, 'scan.html', {'today_date': today_date})

def product_list(request):
    products_qs = Product.objects.all().values()
    return JsonResponse(list(products_qs), safe=False)

def lookup_product(request):
    barcode = request.GET.get('barcode', '').strip()
    try:
        product = Product.objects.get(barcode=barcode)
        return JsonResponse({
            'exists': True,
            'product_name': product.product_name,
        })
    except Product.DoesNotExist:
        return JsonResponse({
            'exists': False,
            'product_name': None,
        })

@login_required
def delete_item(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(Item, id=item_id, user=request.user)
        item.delete()
    return redirect('view_items')

@login_required
def donate_item(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(Item, id=item_id, user=request.user)
        if item.category == 'Medicine' and not item.is_expired():
            item.donated = True
            item.save()
    return redirect('donate_to_ngo')

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def donate_to_ngo(request):
    """Enhanced donation view with both integrated and manual options"""
    donated_items = Item.objects.filter(user=request.user, donated=True, category='Medicine').exclude(expiry_date__lt=datetime.date.today())

    # Get verified NGOs for integrated donation system
    from .models import NGOProfile
    verified_ngos = NGOProfile.objects.filter(verified=True).order_by('city', 'organization_name')

    ngo_list = []
    selected_ngo = None

    # Hardcoded NGO data for Kerala districts
    ngo_data = {
        'Palakkad': [
            {'name': 'Palakkad Medical Trust', 'address': 'Palakkad, Kerala', 'email': 'info@palakkadmedicaltrust.org', 'phone': '+91-491-1234567'},
            {'name': 'Kerala Health NGO', 'address': 'Palakkad District, Kerala', 'email': 'contact@keralahealthngo.in', 'phone': '+91-491-7654321'},
            {'name': 'Medicine Donation Center Palakkad', 'address': 'Central Palakkad, Kerala', 'email': 'donate@mdc-palakkad.com', 'phone': '+91-491-9876543'},
        ],
        'Thrissur': [
            {'name': 'Thrissur Charity Hospital', 'address': 'Thrissur, Kerala', 'email': 'help@thrissurcharity.org', 'phone': '+91-487-1234567'},
            {'name': 'Kerala Medicine Aid', 'address': 'Thrissur District, Kerala', 'email': 'aid@keralamedicineaid.com', 'phone': '+91-487-7654321'},
            {'name': 'Thrissur Health Foundation', 'address': 'Central Thrissur, Kerala', 'email': 'foundation@thrissurhealth.org', 'phone': '+91-487-9876543'},
        ],
        'Kozhikode': [
            {'name': 'Kozhikode Medical Relief', 'address': 'Kozhikode, Kerala', 'email': 'relief@kozhikodemedical.org', 'phone': '+91-495-1234567'},
            {'name': 'Calicut Health NGO', 'address': 'Kozhikode District, Kerala', 'email': 'info@calicuthealthngo.in', 'phone': '+91-495-7654321'},
            {'name': 'Medicine Donation Hub Kozhikode', 'address': 'Central Kozhikode, Kerala', 'email': 'hub@mdc-kozhikode.com', 'phone': '+91-495-9876543'},
        ],
        'Ernakulam': [
            {'name': 'Ernakulam Medical Trust', 'address': 'Ernakulam, Kerala', 'email': 'trust@ernakulammedical.org', 'phone': '+91-484-1234567'},
            {'name': 'Kochi Health Aid', 'address': 'Ernakulam District, Kerala', 'email': 'aid@kochihealth.com', 'phone': '+91-484-7654321'},
            {'name': 'Ernakulam Charity Foundation', 'address': 'Central Ernakulam, Kerala', 'email': 'foundation@ernakulamcharity.org', 'phone': '+91-484-9876543'},
        ],
        'Trivandrum': [
            {'name': 'Trivandrum Health NGO', 'address': 'Trivandrum, Kerala', 'email': 'ngo@trivandrumhealth.org', 'phone': '+91-471-1234567'},
            {'name': 'Kerala Capital Medicine Aid', 'address': 'Trivandrum District, Kerala', 'email': 'aid@keralacapital.com', 'phone': '+91-471-7654321'},
            {'name': 'Trivandrum Donation Center', 'address': 'Central Trivandrum, Kerala', 'email': 'center@trivandrumdonation.org', 'phone': '+91-471-9876543'},
        ],
    }

    # Handle GET request for location selection (old method)
    location = request.GET.get('location')
    if location:
        ngo_list = ngo_data.get(location, [])
        # Prepare email body with donated items for GET requests
        user_name = request.user.get_full_name() or request.user.username
        user_email = request.user.email
        email_body = f"Dear NGO,\n\nI have the following medicines available for donation:\n\n"
        for item in donated_items:
            email_body += f"- {item.name}, Expiry: {item.expiry_date}, Notes: {item.notes or 'None'}\n"
        email_body += f"\nPlease contact me to arrange pickup. I will provide prescriptions of these medicines.\n\nBest regards,\n{user_name}\nEmail: {user_email}"
        subject = "Medicine Donation Offer"

        # Use Gmail compose URL for direct Gmail opening
        for ngo in ngo_list:
            # Use Gmail compose URL to open Gmail directly with prefilled fields
            # This works for both desktop and mobile browsers
            ngo['gmail_link'] = f"https://mail.google.com/mail/?view=cm&fs=1&to={quote(ngo['email'])}&su={quote(subject)}&body={quote(email_body)}"
            # Fallback mailto link for devices where Gmail web doesn't work
            ngo['mailto_link'] = f"mailto:{quote(ngo['email'])}?subject={quote(subject)}&body={quote(email_body)}"

    if request.method == 'POST':
        donation_type = request.POST.get('donation_type')
        location = request.POST.get('location')

        # If location is provided but no donation_type, treat as manual (old method)
        if not donation_type and location:
            donation_type = 'manual'

        if donation_type == 'integrated':
            # Integrated donation system
            ngo_id = request.POST.get('ngo_id')
            pickup_address = request.POST.get('pickup_address', '').strip()
            contact_number = request.POST.get('contact_number', '').strip()
            notes = request.POST.get('notes', '').strip()

            if ngo_id and pickup_address and contact_number:
                try:
                    ngo_profile = NGOProfile.objects.get(id=ngo_id, verified=True)
                    from .models import Donation

                    # Create donation request
                    donation = Donation.objects.create(
                        user=request.user,
                        ngo_profile=ngo_profile,
                        ngo=ngo_profile.organization_name,
                        ngo_email=ngo_profile.user.email,
                        pickup_address=pickup_address,
                        contact_number=contact_number,
                        notes=notes,
                        status='pending'
                    )

                    # Link donated items to this donation
                    for item in donated_items:
                        item.donation_request = donation
                        item.save()

                    # Send notification email to NGO
                    from django.core.mail import send_mail
                    from django.conf import settings

                    subject = f"New Medicine Donation Request - {donation.ngo}"
                    message = f"""Dear {ngo_profile.contact_person},

A new medicine donation request has been submitted to {ngo_profile.organization_name}.

Donor Details:
- Name: {request.user.get_full_name() or request.user.username}
- Contact: {contact_number}
- Pickup Address: {pickup_address}

Medicines Available:
"""
                    for item in donated_items:
                        message += f"- {item.name} (Expiry: {item.expiry_date})\n"

                    if notes:
                        message += f"\nAdditional Notes: {notes}\n"

                    message += f"""
Please log in to your NGO dashboard to review and accept this donation request.

Best regards,
Smart Expiry Tracker Team
"""

                    try:
                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            [ngo_profile.user.email],
                            fail_silently=True
                        )
                    except:
                        pass

                    return redirect('donation_success')

                except NGOProfile.DoesNotExist:
                    pass

        elif donation_type == 'manual':
            # Manual Gmail process (existing functionality)
            location = request.POST.get('location')
            # Hardcoded NGO data for Kerala districts
            ngo_data = {
                'Palakkad': [
                    {'name': 'Palakkad Medical Trust', 'address': 'Palakkad, Kerala', 'email': 'info@palakkadmedicaltrust.org', 'phone': '+91-491-1234567'},
                    {'name': 'Kerala Health NGO', 'address': 'Palakkad District, Kerala', 'email': 'contact@keralahealthngo.in', 'phone': '+91-491-7654321'},
                    {'name': 'Medicine Donation Center Palakkad', 'address': 'Central Palakkad, Kerala', 'email': 'donate@mdc-palakkad.com', 'phone': '+91-491-9876543'},
                ],
                'Thrissur': [
                    {'name': 'Thrissur Charity Hospital', 'address': 'Thrissur, Kerala', 'email': 'help@thrissurcharity.org', 'phone': '+91-487-1234567'},
                    {'name': 'Kerala Medicine Aid', 'address': 'Thrissur District, Kerala', 'email': 'aid@keralamedicineaid.com', 'phone': '+91-487-7654321'},
                    {'name': 'Thrissur Health Foundation', 'address': 'Central Thrissur, Kerala', 'email': 'foundation@thrissurhealth.org', 'phone': '+91-487-9876543'},
                ],
                'Kozhikode': [
                    {'name': 'Kozhikode Medical Relief', 'address': 'Kozhikode, Kerala', 'email': 'relief@kozhikodemedical.org', 'phone': '+91-495-1234567'},
                    {'name': 'Calicut Health NGO', 'address': 'Kozhikode District, Kerala', 'email': 'info@calicuthealthngo.in', 'phone': '+91-495-7654321'},
                    {'name': 'Medicine Donation Hub Kozhikode', 'address': 'Central Kozhikode, Kerala', 'email': 'hub@mdc-kozhikode.com', 'phone': '+91-495-9876543'},
                ],
                'Ernakulam': [
                    {'name': 'Ernakulam Medical Trust', 'address': 'Ernakulam, Kerala', 'email': 'trust@ernakulammedical.org', 'phone': '+91-484-1234567'},
                    {'name': 'Kochi Health Aid', 'address': 'Ernakulam District, Kerala', 'email': 'aid@kochihealth.com', 'phone': '+91-484-7654321'},
                    {'name': 'Ernakulam Charity Foundation', 'address': 'Central Ernakulam, Kerala', 'email': 'foundation@ernakulamcharity.org', 'phone': '+91-484-9876543'},
                ],
                'Trivandrum': [
                    {'name': 'Trivandrum Health NGO', 'address': 'Trivandrum, Kerala', 'email': 'ngo@trivandrumhealth.org', 'phone': '+91-471-1234567'},
                    {'name': 'Kerala Capital Medicine Aid', 'address': 'Trivandrum District, Kerala', 'email': 'aid@keralacapital.com', 'phone': '+91-471-7654321'},
                    {'name': 'Trivandrum Donation Center', 'address': 'Central Trivandrum, Kerala', 'email': 'center@trivandrumdonation.org', 'phone': '+91-471-9876543'},
                ],
            }
            ngo_list = ngo_data.get(location, [])
            # Prepare email body with donated items
            user_name = request.user.get_full_name() or request.user.username
            user_email = request.user.email
            email_body = f"Dear NGO,\n\nI have the following medicines available for donation:\n\n"
            for item in donated_items:
                email_body += f"- {item.name}, Expiry: {item.expiry_date}, Notes: {item.notes or 'None'}\n"
            email_body += f"\nPlease contact me to arrange pickup. I will provide prescriptions of these medicines.\n\nBest regards,\n{user_name}\nEmail: {user_email}"
            subject = "Medicine Donation Offer"
            for ngo in ngo_list:
                # Use Gmail compose URL for browser-based Gmail opening
                ngo['gmail_link'] = f"https://mail.google.com/mail/?view=cm&fs=1&to={quote(ngo['email'])}&su={quote(subject)}&body={quote(email_body)}"

    return render(request, 'donate_to_ngo.html', {
        'ngo_list': ngo_list,
        'donated_items': donated_items,
        'verified_ngos': verified_ngos,
        'selected_ngo': selected_ngo
    })


@login_required
def donation_success(request):
    """Success page after donation submission"""
    return render(request, 'donation_success.html')

@login_required
def profile(request):
    from .forms import UserProfileForm
    from .models import UserProfile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile, user=request.user)
    return render(request, 'profile.html', {'form': form})


# NGO Views
def ngo_register(request):
    """NGO Registration View"""
    if request.method == 'POST':
        user_form = NGORegistrationForm(request.POST)
        ngo_form = NGOProfileForm(request.POST)

        if user_form.is_valid() and ngo_form.is_valid():
            # Create user account
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password1'])
            user.save()

            # Create NGO profile
            ngo_profile = ngo_form.save(commit=False)
            ngo_profile.user = user
            ngo_profile.save()

            # Create UserProfile with NGO type
            from .models import UserProfile
            UserProfile.objects.create(user=user, user_type='ngo')

            # Log the user in
            from django.contrib.auth import login
            login(request, user)

            return redirect('ngo_dashboard')
    else:
        user_form = NGORegistrationForm()
        ngo_form = NGOProfileForm()

    return render(request, 'ngo_register.html', {
        'user_form': user_form,
        'ngo_form': ngo_form
    })


def ngo_login(request):
    """NGO Login View"""
    if request.method == 'POST':
        form = NGOLoginForm(request.POST)
        if form.is_valid():
            from django.contrib.auth import authenticate, login
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(username=username, password=password)
            if user is not None:
                # Check if user is NGO
                try:
                    profile = user.userprofile
                    if profile.user_type == 'ngo':
                        login(request, user)
                        return redirect('ngo_dashboard')
                    else:
                        form.add_error(None, "This login is for NGOs only.")
                except:
                    form.add_error(None, "Invalid NGO account.")
            else:
                form.add_error(None, "Invalid username or password.")
    else:
        form = NGOLoginForm()

    return render(request, 'ngo_login.html', {'form': form})


@login_required
def ngo_dashboard(request):
    """NGO Dashboard - Shows donation requests and inventory"""
    try:
        ngo_profile = request.user.ngoprofile
        if not ngo_profile.verified:
            return render(request, 'ngo_pending_verification.html')
    except:
        return redirect('ngo_login')

    # Get pending donation requests (using email-based filtering like old system)
    from .models import Donation
    donation_requests = Donation.objects.filter(
        ngo_email=request.user.email,
        status='pending'
    ).order_by('-donation_date')

    # Get NGO inventory with expiry alerts
    from .models import NGOInventory
    inventory = NGOInventory.objects.filter(
        ngo=ngo_profile
    ).order_by('expiry_date')

    # Add expiry status to inventory items
    for item in inventory:
        days_left = item.days_until_expiry()
        if days_left < 0:
            item.expiry_status = 'Expired'
            item.status_class = 'danger'
        elif days_left <= 30:
            item.expiry_status = f'Expires in {days_left} days'
            item.status_class = 'warning'
        else:
            item.expiry_status = 'Safe'
            item.status_class = 'success'

    # Get completed donations (using email-based filtering like old system)
    completed_donations = Donation.objects.filter(
        ngo_email=request.user.email,
        status='completed'
    ).order_by('-completed_date')[:10]

    context = {
        'ngo_profile': ngo_profile,
        'donation_requests': donation_requests,
        'inventory': inventory,
        'completed_donations': completed_donations,
        'pending_count': donation_requests.count(),
        'inventory_count': inventory.count(),
        'expiring_soon_count': sum(1 for item in inventory if item.days_until_expiry() <= 30 and item.days_until_expiry() >= 0),
    }

    return render(request, 'ngo_dashboard.html', context)


@login_required
def update_donation_status(request, donation_id):
    """Update donation request status (Accept/Reject/Complete)"""
    try:
        ngo_profile = request.user.ngoprofile
    except:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    from .models import Donation, NGOInventory
    donation = get_object_or_404(Donation, id=donation_id, ngo_email=request.user.email)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['confirmed', 'completed', 'cancelled']:
            donation.status = new_status

            if new_status == 'confirmed':
                donation.confirmed_date = timezone.now()
                # Create NGO inventory records
                for item in donation.items_donated.all():
                    NGOInventory.objects.create(
                        ngo=ngo_profile,
                        item_name=item.name,
                        category=item.category,
                        barcode=item.barcode,
                        expiry_date=item.expiry_date,
                        quantity=1,
                        batch_number=item.barcode or '',
                        source_donation=donation,
                        notes=item.notes
                    )
                    # Mark donor's item as donated
                    item.donation_status = 'donated'
                    item.save()

            elif new_status == 'completed':
                donation.completed_date = timezone.now()

            donation.save()

            # Send email notification to donor
            from django.core.mail import send_mail
            from django.conf import settings

            if new_status == 'confirmed':
                subject = f"Donation Confirmed - {donation.ngo}"
                message = f"Your donation request to {donation.ngo} has been accepted. They will contact you at {donation.contact_number} for pickup arrangements."
            elif new_status == 'completed':
                subject = f"Donation Completed - {donation.ngo}"
                message = f"Your donation to {donation.ngo} has been successfully completed. Thank you for your generosity!"
            elif new_status == 'cancelled':
                subject = f"Donation Declined - {donation.ngo}"
                message = f"Your donation request to {donation.ngo} was declined. You can try donating to another NGO."

            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [donation.user.email],
                    fail_silently=True
                )
            except:
                pass  # Email sending failure shouldn't break the flow

            return JsonResponse({'success': True, 'status': new_status})

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def ngo_inventory(request):
    """NGO Inventory Management View"""
    try:
        ngo_profile = request.user.ngoprofile
    except:
        return redirect('ngo_login')

    from .models import NGOInventory
    inventory = NGOInventory.objects.filter(ngo=ngo_profile).order_by('expiry_date')

    # Add expiry status
    for item in inventory:
        days_left = item.days_until_expiry()
        if days_left < 0:
            item.expiry_status = 'Expired'
            item.status_class = 'danger'
        elif days_left <= 30:
            item.expiry_status = f'Expires in {days_left} days'
            item.status_class = 'warning'
        else:
            item.expiry_status = 'Safe'
            item.status_class = 'success'

    return render(request, 'ngo_inventory.html', {
        'inventory': inventory,
        'ngo_profile': ngo_profile
    })


@login_required
def ngo_profile(request):
    """NGO Profile Management"""
    try:
        ngo_profile = request.user.ngoprofile
    except:
        return redirect('ngo_login')

    if request.method == 'POST':
        form = NGOProfileForm(request.POST, instance=ngo_profile)
        if form.is_valid():
            form.save()
            return redirect('ngo_profile')
    else:
        form = NGOProfileForm(instance=ngo_profile)

    return render(request, 'ngo_profile.html', {
        'form': form,
        'ngo_profile': ngo_profile
    })
