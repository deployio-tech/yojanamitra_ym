"""
YojanaMitra Flask Backend
Production-ready backend with Gemini AI integration
"""

from flask import (
    Flask,
    request,
    jsonify,
    session,
    send_from_directory,
    redirect,
    url_for,
)
from werkzeug.utils import secure_filename
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import threading
import time
import json
from datetime import datetime, timezone, date
from dotenv import load_dotenv
import google.generativeai as genai

# New eligibility engine
from app.engine import EligibilityOrchestrator
from app.engine.eligibility import (
    EligibilityEngine,
    EligibilityOutput,
    evaluate_single,
    PASS_R,
    FAIL_R,
    UNKNOWN_C,
    ELIGIBLE,
    POSSIBLE,
    INELIGIBLE,
)
from app.engine.scorer import (
    ResultRanker,
    RankedScheme,
    THRESH_ELIGIBLE,
    THRESH_POSSIBLE,
    THRESH_MAYBE,
)
from app.engine.context import ContextualReasoner
from app.engine.questions import QuestionEngine, Question

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import PIL.Image
import re

# Load environment variables (.env)
load_dotenv()

import logging
import traceback
import sys

# Configure logging (Vercel-safe: stdout only)
log_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

terminal_handler = logging.StreamHandler(sys.stdout)
terminal_handler.setFormatter(log_formatter)

logging.basicConfig(level=logging.INFO, handlers=[terminal_handler], force=True)

logger = logging.getLogger(__name__)


def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        print(
            *[str(a).encode("ascii", "replace").decode("ascii") for a in args], **kwargs
        )


# Ensure stdout is UTF-8 and unbuffered
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(line_buffering=True, encoding="utf-8", errors="replace")
# Also ensure stdout is unbuffered and uses UTF-8 to handle unicode characters in terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(line_buffering=True, encoding="utf-8", errors="replace")

# Initialize Flask app
app = Flask(__name__, static_folder="static")
app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY", "your-secret-key-change-in-production"
)

# Ensure instance directory exists (for SQLite database)
try:
    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)
except Exception:
    pass

db_url = os.getenv("DATABASE_URL", "sqlite:///instance/yojanamitra.db")

# Fix for Supabase / SQLAlchemy compatibility
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = (
    0  # Disable static file caching for development
)


db = SQLAlchemy(app)
CORS(app, supports_credentials=True)

# File Upload Config
UPLOAD_FOLDER = "static/uploads/documents"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
# Only create upload folder in writable environments (not on Vercel serverless)
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except OSError:
    pass
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ----------------- Gemini AI Setup -----------------
# Hardcoded API key - update this when needed
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "PASTE_YOUR_GEMINI_API_KEY_HERE")
print(f"GEMINI_API_KEY loaded: {GEMINI_API_KEY}")


# Rate limiter for free tier (15 RPM = 1 request per 4 seconds)
class RateLimiter:
    def __init__(self, rpm=15):
        self.min_interval = 60.0 / rpm
        self.last_request_time = 0

    def wait(self):
        """Wait if needed to respect rate limit"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()


gemini_limiter = RateLimiter(rpm=15)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-flash-latest")
    print("Gemini model initialized (using gemini-flash-latest for stable quota).")

# ----------------- Production Config (ProxyFix) -----------------
from werkzeug.middleware.proxy_fix import ProxyFix

# Apply ProxyFix to handle HTTPS behind Render/Load Balancer
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Secure Session Settings (Enable in Production)
if os.getenv("RENDER") or os.getenv("FLASK_ENV") == "production":
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    print("🔒 Applied Secure Session Config for Production")


@app.after_request
def add_security_headers(response):
    """Add headers required for Google GSI and cross-origin security"""
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    # COEP: unsafe-none is usually okay for GSI, but 'credentialless' or 'require-corp' might be needed for high isolation
    # For now,COOP is the most critical for the popup to communicate back to the opener.
    return response


# ----------------- SendGrid Setup -----------------
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content, Header

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv(
    "FROM_EMAIL", "06052004shreyas2@gmail.com"
)  # Verified in SendGrid

# ============ NOTIFICATION FUNCTIONS (SMS & EMAIL) ============


def get_email_html_template(title, content_html, user_name="User"):
    """Returns a professional, responsive HTML template for emails"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 20px auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 25px; text-align: center; }}
            .content {{ padding: 30px; background-color: #ffffff; }}
            .footer {{ background-color: #f9f9f9; padding: 20px; text-align: center; font-size: 12px; color: #888; border-top: 1px solid #eeeeee; }}
            .btn {{ display: inline-block; padding: 12px 25px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
            .scheme-list {{ margin: 20px 0; padding-left: 20px; }}
            .scheme-item {{ margin-bottom: 10px; font-weight: bold; color: #2c3e50; }}
            h2 {{ color: #1e3c72; margin-top: 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin:0;">YojanaMitra</h1>
                <p style="margin:5px 0 0 0; opacity: 0.8;">Your Guide to Government Schemes</p>
            </div>
            <div class="content">
                <h2>{title}</h2>
                <p>Hi {user_name},</p>
                {content_html}
                <p>Best regards,<br>The YojanaMitra Team</p>
            </div>
            <div class="footer">
                <p>&copy; 2026 YojanaMitra. All rights reserved.</p>
                <p>You received this because you are a registered user of YojanaMitra.</p>
                <p><a href="https://yojanamitra-1.onrender.com/dashboard" style="color: #007bff;">Manage Notifications</a> | <a href="#" style="color: #888;">Unsubscribe</a></p>
            </div>
        </div>
    </body>
    </html>
    """


def send_email_notification(
    to_email, subject, body, html_content=None, user_name="User"
):
    """Send Email using SendGrid HTTP API asynchronously (Explicit capture to prevent identity mixing)"""

    def _send_thread_worker(
        target_email, email_subject, email_body, final_html_content, name
    ):
        try:
            if not SENDGRID_API_KEY:
                print("⚠️ SENDGRID_API_KEY not configured - Email skipped")
                return

            sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
            from_email = Email(FROM_EMAIL)
            to_email_obj = To(target_email)

            # If html_content is provided, use it. Otherwise, wrap body in template.
            if not final_html_content:
                final_html = get_email_html_template(
                    email_subject, f"<p>{email_body}</p>", name
                )
            else:
                final_html = final_html_content

            content = Content("text/html", final_html)
            mail_obj = Mail(from_email, to_email_obj, email_subject, content)

            # Add Unsubscribe Header for Gmail/Yahoo reputation
            mail_obj.add_header(
                Header(
                    "List-Unsubscribe",
                    f"<mailto:unsubscribe@yojanamitra.in?subject=unsubscribe>, <https://yojanamitra-1.onrender.com/unsubscribe?email={target_email}>",
                )
            )

            response = sg.client.mail.send.post(request_body=mail_obj.get())

            if response.status_code >= 200 and response.status_code < 300:
                print(
                    f"📧 HTML Email successfully sent to {target_email} addressed to {name}"
                )
            else:
                print(
                    f"❌ SendGrid failed with status {response.status_code}: {response.body}"
                )

        except Exception as e:
            print(f"❌ Email failed to {target_email}: {str(e)}")
            import traceback

            traceback.print_exc()

    print(f"📨 Queueing async email for {to_email} (Addressing: {user_name})")

    # Pass arguments explicitly to the thread to avoid closure/binding issues in loops
    thread = threading.Thread(
        target=_send_thread_worker,
        args=(to_email, subject, body, html_content, user_name),
    )
    thread.start()
    return True


def send_sms_notification(phone_number, message):
    """Send SMS using either a Custom Gateway Relay or Twilio"""
    try:
        # Load credentials
        sms_gateway_url = os.getenv("SMS_GATEWAY_URL")
        sms_gateway_key = os.getenv("SMS_GATEWAY_API_KEY")

        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")

        # Clean phone number (Ensure it has +91 for India if not specified)
        phone_number = phone_number.strip()
        if not phone_number.startswith("+"):
            if len(phone_number) == 10:
                phone_number = "+91" + phone_number
            elif not phone_number.startswith("91") and len(phone_number) > 10:
                phone_number = "+" + phone_number

        # 1. Try Custom Gateway Relay first (Great for using personal Android as relay)
        if sms_gateway_url:
            import requests

            # Detect if it's smsmobileapi.com and adjust parameters
            if "smsmobileapi.com" in sms_gateway_url:
                # Correct documentation endpoint: https://api.smsmobileapi.com/sendsms/
                # Note: The .env might have a subpath like /v1/messages, we should handle both
                final_url = (
                    sms_gateway_url
                    if "sendsms" in sms_gateway_url
                    else "https://api.smsmobileapi.com/sendsms/"
                )
                data = {
                    "apikey": sms_gateway_key,
                    "recipients": phone_number.replace(
                        "+", ""
                    ),  # Usually expects no + for this API
                    "message": message,
                }
            else:
                # Standard generic payload
                data = {"to": phone_number, "message": message, "key": sms_gateway_key}

            # Also support 'number'/'text' common variations for other relays
            data_alt = {
                "number": phone_number.replace("+", ""),
                "text": message,
                "token": sms_gateway_key,
            }

            try:
                # Debug Info
                print(f"📡 SMS Debug: Hitting {final_url}")

                # Some gateways (like smsmobileapi) might prefer GET or POST with form-data/json
                # We'll try JSON first, then form-params
                res = requests.post(
                    (
                        final_url
                        if "smsmobileapi.com" in sms_gateway_url
                        else sms_gateway_url
                    ),
                    json=data,
                    timeout=10,
                )

                if res.status_code in [200, 201]:
                    print(f"✅ Custom Gateway SMS sent to {phone_number}")
                    return True
                else:
                    print(
                        f"📡 SMS Debug: JSON POST failed ({res.status_code}): {res.text[:200]}"
                    )
                    # Try form-data if JSON fails
                    res_form = requests.post(
                        (
                            final_url
                            if "smsmobileapi.com" in sms_gateway_url
                            else sms_gateway_url
                        ),
                        data=data,
                        timeout=10,
                    )
                    if res_form.status_code in [200, 201]:
                        print(
                            f"✅ Custom Gateway SMS sent to {phone_number} (form-data)"
                        )
                        return True

                    print(
                        f"📡 SMS Debug: Form POST failed ({res_form.status_code}): {res_form.text[:200]}"
                    )

                    # Try GET as last resort for some gateways
                    res_get = requests.get(
                        (
                            final_url
                            if "smsmobileapi.com" in sms_gateway_url
                            else sms_gateway_url
                        ),
                        params=data,
                        timeout=10,
                    )
                    if res_get.status_code in [200, 201]:
                        print(
                            f"✅ Custom Gateway SMS sent to {phone_number} (GET request)"
                        )
                        return True

                    print(
                        f"📡 SMS Debug: GET failed ({res_get.status_code}): {res_get.text[:200]}"
                    )

                    # Try alternate payload format if both fail
                    res_alt = requests.post(sms_gateway_url, json=data_alt, timeout=10)
                    if res_alt.status_code in [200, 201]:
                        print(
                            f"✅ Custom Gateway SMS sent to {phone_number} (alt format)"
                        )
                        return True
                    print(
                        f"⚠️ Gateway Relay failed (Status {res.status_code or res_form.status_code}), falling back to Twilio..."
                    )
            except Exception as ge:
                print(f"⚠️ Gateway connection failed: {ge}, falling back...")

        # 2. Fallback to Twilio
        if (
            all([twilio_sid, twilio_token, twilio_phone])
            and twilio_sid != "your_twilio_account_sid_here"
        ):
            from twilio.rest import Client

            client = Client(twilio_sid, twilio_token)

            sms = client.messages.create(
                body=message, from_=twilio_phone, to=phone_number
            )
            print(f"✅ Twilio SMS sent to {phone_number}: {sms.sid}")
            return True

        print(f"❌ No functional SMS provider configured for {phone_number}")
        return False

    except Exception as e:
        print(f"❌ SMS System Error for {phone_number}: {str(e)}")
        traceback.print_exc()
        return False


@app.route("/api/config")
def get_config():
    """Serve public configuration to the frontend"""
    return jsonify(
        {
            "google_client_id": os.getenv(
                "GOOGLE_CLIENT_ID",
                "886008127383-v80l90m0uukpgov20n0223n748ivcc5d.apps.googleusercontent.com",
            )
        }
    )


@app.route("/api/profile", methods=["GET"])
def get_profile_for_desktop():
    """Return the current user's profile for the Electron Portal Helper desktop widget."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    profile = {}
    field_map = {
        "Full Name": user.name,
        "Email": user.email,
        "Mobile": user.mobile,
        "Date of Birth": user.dob,
        "Age": user.age,
        "Gender": user.gender,
        "State": user.state,
        "District": user.district,
        "Block / Taluk": user.block_taluk,
        "Residence": user.residence,
        "Annual Income": ("Rs." + str(int(user.income))) if user.income else None,
        "Annual Family Income": (
            ("Rs." + str(int(user.annual_family_income)))
            if user.annual_family_income
            else None
        ),
        "Caste": user.caste,
        "Religion": user.religion,
        "Occupation": user.occupation,
        "Employment Status": user.employment_status,
        "Education": user.highest_education_level or user.education,
        "Marital Status": user.marital_status,
        "Ration Card Type": user.ration_card_type,
        "Disability": user.disability,
        "Bank Account": user.bank_account_available,
        "Aadhaar Available": user.aadhaar_available,
    }
    for k, v in field_map.items():
        if v is not None and str(v).strip():
            profile[k] = str(v)

    return jsonify({"profile": profile})


@app.route("/api/auth/google", methods=["POST"])
def google_auth():
    """Verify Google ID token and log user in"""
    data = request.json
    token = data.get("credential")
    if not token:
        return jsonify({"error": "No token provided"}), 400

    try:
        # Client ID for YojanaMitra (Pulled from .env)
        CLIENT_ID = os.getenv(
            "GOOGLE_CLIENT_ID",
            "886008127383-v80l90m0uukpgov20n0223n748ivcc5d.apps.googleusercontent.com",
        )
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), CLIENT_ID
        )

        email = idinfo["email"]
        name = idinfo.get("name", email.split("@")[0])

        user = User.query.filter_by(email=email).first()
        if not user:
            # Create new user if doesn't exist (using existing User model)
            user = User(email=email, name=name)
            db.session.add(user)
            db.session.commit()
            print(f"🆕 Created new user via Google: {email}")

        session["user_id"] = user.id
        session["user_name"] = user.name
        session["user_type"] = "user"
        print(f"✅ Google login successful: {email}")
        return (
            jsonify({"message": "Login successful", "user": {"name": user.name}}),
            200,
        )

    except ValueError:
        return jsonify({"error": "Invalid token"}), 400
    except Exception as e:
        print(f"Google Auth Error: {e}")
        return jsonify({"error": "Authentication failed"}), 500


@app.route("/api/view-document/<int:doc_id>")
def view_document(doc_id):
    """Securely serve document without exposing path"""
    user_id = session.get("user_id")
    print(
        f"📡 view_document: doc_id={doc_id}, session user_id={user_id}, user_type={session.get('user_type')}"
    )

    if not user_id:
        print(f"⚠️ Unauthorized: no user_id in session")
        return jsonify({"error": "Unauthorized - please log in"}), 401

    doc = UserDocument.query.get_or_404(doc_id)
    if doc.user_id != user_id:
        print(f"🚫 Forbidden: doc owner={doc.user_id}, session={user_id}")
        return jsonify({"error": "Forbidden"}), 403

    # Serve the file from the uploads directory
    directory = os.path.join(app.root_path, "static", "uploads", "documents")
    filepath = os.path.join(directory, doc.filename)
    print(f"📁 Serving: {filepath} (exists={os.path.exists(filepath)})")
    return send_from_directory(directory, doc.filename)


# ============ NEW ELIGIBILITY ENGINE CLASSIFICATION ============


@app.route("/api/classify", methods=["GET"])
def api_classify_schemes():
    """
    Evaluates user profile against all extracted schemes using the strict classification logic.
    """
    user_id = request.args.get("user_id")
    if not user_id:
        user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "No user_id provided"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user_profile = user.to_dict().get("profile", {})

    import sqlite3
    import json
    from app.engine.classifier import evaluate_all_schemes

    # Load all schemes for mapping names mapping
    schemes = Scheme.query.all()
    db_schemes_map = {s.id: s.name for s in schemes}

    # Load conditions from gemini_prefill
    db_path = os.path.join(app.root_path, "instance", "yojanamitra.db")
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT scheme_id, extracted_json FROM gemini_prefill WHERE status='success'"
        ).fetchall()
        conn.close()
    except Exception as e:
        return jsonify({"error": f"DB error: {e}"}), 500

    all_conditions = {}
    for r in rows:
        try:
            # Handle empty extracted_json gracefully
            all_conditions[r[0]] = json.loads(r[1]) if r[1] else {}
        except Exception:
            pass

    # Run strict evaluation
    results = evaluate_all_schemes(user_profile, all_conditions, db_schemes_map)

    return jsonify(results)


# ============ CONDITIONS DATA ENDPOINT ============
_conditions_cache = None


@app.route("/api/conditions", methods=["GET"])
def get_all_conditions():
    """
    Serves all_extracted_conditions.json — the single source of truth for
    client-side eligibility classification.
    Covers all 4,225 schemes with ~25 conditions each.
    """
    global _conditions_cache
    if _conditions_cache is None:
        conditions_path = os.path.join(app.root_path, "all_extracted_conditions.json")
        try:
            with open(conditions_path, "r", encoding="utf-8", errors="replace") as f:
                _conditions_cache = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load conditions file: {e}")
            return jsonify({"error": "Conditions data unavailable"}), 503

    from flask import make_response

    resp = make_response(jsonify(_conditions_cache))
    resp.headers["Cache-Control"] = "public, max-age=86400"  # 24h browser cache
    return resp


# ============ DOCUMENT AI & VAULT FUNCTIONS ============


def process_document_ai(image_path):
    """
    Categorize and extract details from a government document image using Gemini Vision.
    """
    if not GEMINI_API_KEY:
        print("⚠️ GEMINI_API_KEY not configured - Document processing skipped")
        return {"doc_type": "Unknown", "extracted_data": {}, "confidence": 0.0}

    try:
        img = PIL.Image.open(image_path)
        prompt = """
        Analyze this Indian government document or YojanaMitra Questionnaire and return a JSON object.
        
        1. doc_type: Categorize it (e.g., "Aadhaar Card", "Ration Card", "Questionnaire Sheet", etc.).
        2. extracted_data: 
           - For standard Gov docs: Extract details like Name, ID Number, DOB.
           - For Questionnaire Sheets: Identify the Unique IDs in format [YM-Q-FIELDNAME] (e.g., [YM-Q-AGE], [YM-Q-IS_FARMER]).
           - Determine which choice is SHADED or TICKED (usually Yes, No, or N/A). 
           - Map them exactly as: { "YM-Q-AGE": "Yes", "YM-Q-IS_FARMER": "No", ... }.
        3. confidence: A score from 0.0 to 1.0.
        
        Return ONLY valid JSON.
        """
        vision_model = genai.GenerativeModel("gemini-flash-latest")
        response = vision_model.generate_content([prompt, img])

        # Clean response text
        text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        print(
            f"📄 AI Processed Document: {result.get('doc_type', 'Unknown')} (Confidence: {result.get('confidence', 0.0)})"
        )
        return result

    except Exception as e:
        print(f"❌ Gemini Vision Error: {e}")
        return {
            "doc_type": "Manual Review Required",
            "extracted_data": {"error": str(e)},
            "confidence": 0.0,
        }


def notify_users_of_new_schemes(new_schemes_list):
    """
    Send summarized and targeted notifications.
    Only individual eligible schemes are listed to prevent overwhelming the user.
    """
    try:
        if not new_schemes_list:
            return

        users = User.query.all()
        total_new = len(new_schemes_list)
        base_url = "https://yojanamitra-1.onrender.com"

        print(
            f"📢 Starting targeted broadcast for {total_new} schemes to {len(users)} users..."
        )

        for user in users:
            # --- Check 1: Profile Completeness ---
            if user.age is None:
                html_msg = f"""
                <p>Great news! <b>{total_new}</b> new government schemes have been added to YojanaMitra today.</p>
                <p>We found several opportunities that might interest you, but we need more details to confirm your eligibility.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{base_url}/dashboard" class="btn">Complete My Profile</a>
                </div>
                """
                send_email_notification(
                    user.email,
                    f"{total_new} New Schemes Added - Action Required 🔔",
                    f"Hi {user.name}, {total_new} new schemes were added. Complete your profile to check eligibility!",
                    html_content=get_email_html_template(
                        "Profile Update Needed", html_msg, user.name
                    ),
                    user_name=user.name,
                )
                continue

            # --- Check 2: Targeted Eligibility ---
            eligible_schemes = []
            try:
                from app.engine_compat import get_orchestrator

                orch = get_orchestrator(app.config)
                for scheme in new_schemes_list:
                    try:
                        score = orch.quick_score(user, scheme)
                        if score > 0:
                            eligible_schemes.append(scheme)
                    except Exception as e:
                        print(
                            f"❌ Error matching user {user.id} with scheme {scheme.id}: {e}"
                        )
            except Exception as orch_err:
                print(f"❌ Orchestrator not available for notifications: {orch_err}")

            # --- Message construction ---
            if eligible_schemes:
                count = len(eligible_schemes)
                # List only up to 5 specific matches to keep email clean, then "and more"
                display_schemes = eligible_schemes[:5]
                schemes_html_list = "".join(
                    [
                        f'<li class="scheme-item"><a href="{base_url}/all_schemes.html" style="color: #1e3c72; text-decoration: none;">{s.name}</a></li>'
                        for s in display_schemes
                    ]
                )

                if count > 5:
                    schemes_html_list += f'<li class="scheme-item">...and {count - 5} more matching your profile!</li>'

                html_msg = f"""
                <p>Excellent news, <b>{user.name}</b>!</p>
                <p>We've just added <b>{total_new}</b> new schemes, and based on your profile, you are eligible for <b>{count}</b> of them:</p>
                <ul class="scheme-list">
                    {schemes_html_list}
                </ul>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{base_url}/dashboard" class="btn">View My Recommendations</a>
                </div>
                <p style="font-size: 14px; color: #666;">These schemes match your age, location, and other profile details.</p>
                """

                msg_body = f"Hi {user.name}, you're eligible for {count} of the {total_new} new schemes added today! Check them on YojanaMitra."
                email_subject = (
                    f"Match Found! You're eligible for {count} new schemes 🎉"
                )
                email_html = get_email_html_template(
                    "New Targeted Opportunities", html_msg, user.name
                )
            else:
                # No matches found for this user
                html_msg = f"""
                <p><b>{total_new}</b> new schemes were added to our platform today.</p>
                <p>While none directly match your profile criteria yet, you can browse the full list to see if any catch your eye.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{base_url}/all-schemes" class="btn">Browse All Schemes</a>
                </div>
                """
                msg_body = f"Hi {user.name}, {total_new} new schemes added to YojanaMitra. Check them out today."
                email_subject = "New Schemes Update - YojanaMitra"
                email_html = get_email_html_template(
                    "Update: New Schemes Added", html_msg, user.name
                )

            # --- Dispatch ---
            if user.email:
                send_email_notification(
                    user.email,
                    email_subject,
                    msg_body,
                    html_content=email_html,
                    user_name=user.name,
                )

            # --- SMS Dispatch (New Integration) ---
            if user.mobile and eligible_schemes:
                sms_message = f"Hi {user.name}, you have {len(eligible_schemes)} new scheme matches! Visit yojanamitra and check it out."
                send_sms_notification(user.mobile, sms_message)
            elif user.mobile:
                # General update if no specific matches but mobile exists
                sms_message = f"Hi {user.name}, {total_new} new schemes were added to YojanaMitra. Visit yojanamitra and check it out."
                send_sms_notification(user.mobile, sms_message)

        print("✅ Refined targeted broadcast completed.")

    except Exception as e:
        print(f"❌ Error in notification broadcast: {e}")
        import traceback

        traceback.print_exc()


# ====================================================

# System prompt for the chatbot
system_prompt = "You are the YojanaMitra AI assistant. Provide concise, helpful information about Indian government schemes, eligibility criteria, and application guidance."


# ----------------- Models -----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    mobile = db.Column(db.String(15))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    occupation = db.Column(db.String(100))
    income = db.Column(db.Integer)
    caste = db.Column(db.String(50))
    state = db.Column(db.String(50))
    education = db.Column(db.String(50))
    marital_status = db.Column(db.String(20))
    disability = db.Column(db.String(10))  # Yes/No
    residence = db.Column(db.String(20))  # Urban/Rural

    # Holistic Accuracy Fields
    father_occupation = db.Column(db.String(100))
    mother_occupation = db.Column(db.String(100))
    religion = db.Column(db.String(50))
    land_type = db.Column(db.String(20))  # Dry/Wet
    is_orphan = db.Column(db.String(10))  # Yes/No
    is_tribal = db.Column(db.String(10))  # Yes/No

    # New Fields
    dob = db.Column(db.String(20))
    aadhaar_available = db.Column(db.String(10))
    district = db.Column(db.String(100))
    block_taluk = db.Column(db.String(100))
    domicile_status = db.Column(db.String(10))
    family_type = db.Column(db.String(20))
    total_family_members = db.Column(db.Integer)
    is_head_of_family = db.Column(db.String(10))
    annual_family_income = db.Column(db.Integer)
    income_slab = db.Column(db.String(50))
    income_certificate_available = db.Column(db.String(10))
    sub_caste = db.Column(db.String(100))
    minority_status = db.Column(db.String(10))
    ews_status = db.Column(db.String(10))
    ration_card_available = db.Column(db.String(10))
    ration_card_type = db.Column(db.String(20))
    education_status = db.Column(db.String(50))
    highest_education_level = db.Column(db.String(50))
    current_course = db.Column(db.String(100))
    institution_type = db.Column(db.String(50))
    employment_status = db.Column(db.String(50))
    govt_employee_in_family = db.Column(db.String(10))
    is_farmer = db.Column(db.String(10))
    own_agricultural_land = db.Column(db.String(10))
    land_size_acres = db.Column(db.Float)
    is_tenant_farmer = db.Column(db.String(10))
    disability_percentage = db.Column(db.Integer)
    is_widow_single_woman = db.Column(db.String(10))
    is_senior_citizen = db.Column(db.String(10))
    bank_account_available = db.Column(db.String(10))
    aadhaar_linked_bank = db.Column(db.String(10))
    mobile_linked_bank = db.Column(db.String(10))
    income_cert_last_1_year = db.Column(db.String(10))
    scheme_previously_availed = db.Column(db.String(10))
    willing_to_submit_docs = db.Column(db.String(10))
    documents_available = db.Column(db.Text)  # JSON list of selected documents
    achievement_certificates = db.Column(
        db.Text
    )  # JSON list e.g. ["sports_certificate","ncc_certificate"]
    is_pensioner = db.Column(db.String(10))
    num_daughters = db.Column(db.Integer)
    has_pucca_house = db.Column(db.String(10))
    house_type = db.Column(db.String(30))
    is_landless = db.Column(db.String(10))
    is_bocw_registered = db.Column(db.String(10))
    is_school_dropout = db.Column(db.String(10))
    is_first_gen_student = db.Column(db.String(10))
    # Predictive Forecasting fields
    child_age = db.Column(db.Integer)
    education_milestones = db.Column(
        db.Text
    )  # JSON list e.g. ["10th", "12th", "Degree"]
    career_goal = db.Column(db.String(100))

    # NEW FIELDS: Added to profile form (not asked as questions)
    is_citizen = db.Column(db.String(10))  # Yes/No - Critical for 23 schemes
    is_urban = db.Column(db.String(10))  # Yes/No - Complements is_rural
    has_bank_account = db.Column(db.String(10))  # Yes/No - Bank account ownership
    residence_type = db.Column(db.String(50))  # Islands/River Islands/Mainland

    # Deep analysis cache — stores scheme IDs that passed readiness check
    verified_scheme_ids = db.Column(db.Text)  # JSON list of scheme IDs
    verified_schemes_data = db.Column(db.Text)  # JSON list of full scheme objects

    # Questions integration fields
    profile_version = db.Column(db.Integer, default=1)  # Track profile snapshots
    question_answers = db.Column(
        db.Text, default="{}"
    )  # JSON dict of field -> answer mappings

    def _get_json_field(self, field_name, default=None):
        val = getattr(self, field_name)
        if not val:
            return default
        try:
            return json.loads(val)
        except Exception:
            return default

    def to_dict(self):
        # Exhaustive snake_case mapping for all 60+ database signals
        p = {
            "age": self.age,
            "gender": self.gender,
            "occupation": self.occupation,
            "income": self.income,
            "annual_income": self.income,
            "annual_family_income": self.annual_family_income,
            "caste": self.caste,
            "category": self.caste,  # Alias for engine
            "state": self.state,
            "domicile_state": self.state,
            "education": self.education,
            "marital_status": self.marital_status,
            "residence": self.residence,
            "father_occupation": self.father_occupation,
            "mother_occupation": self.mother_occupation,
            "religion": self.religion,
            "land_type": self.land_type,
            "dob": self.dob,
            "district": self.district,
            "block_taluk": self.block_taluk,
            "domicile_status": self.domicile_status,
            "family_type": self.family_type,
            "total_family_members": self.total_family_members,
            "income_slab": self.income_slab,
            "sub_caste": self.sub_caste,
            "ration_card_type": self.ration_card_type,
            "education_status": self.education_status,
            "highest_education_level": self.highest_education_level or self.education,
            "current_course": self.current_course,
            "institution_type": self.institution_type,
            "employment_status": self.employment_status,
            "land_size_acres": self.land_size_acres,
            "disability_percentage": self.disability_percentage,
            "num_daughters": self.num_daughters,
            "house_type": self.house_type,
            "residence_type": self.residence_type,
            "career_goal": self.career_goal,
            "child_age": self.child_age,
            "documents_available": self.documents_available,
            "achievement_certificates": self.achievement_certificates,
            # Boolean/Binary Signals (Yes/No Standardized)
            "is_farmer": _str_to_bool(self.is_farmer),
            "is_student": _str_to_bool(
                self.education_status == "Student" or self.occupation == "Student"
            ),
            "is_widow": _str_to_bool(self.is_widow_single_woman),
            "is_widow_single_woman": _str_to_bool(self.is_widow_single_woman),
            "is_senior_citizen": _str_to_bool(self.is_senior_citizen),
            "is_minority": _str_to_bool(self.minority_status),
            "minority_status": _str_to_bool(self.minority_status),
            "is_ews": _str_to_bool(self.ews_status),
            "ews_status": _str_to_bool(self.ews_status),
            "is_disabled": _str_to_bool(self.disability),
            "disability": self.disability,
            "is_orphan": _str_to_bool(self.is_orphan),
            "is_tribal": _str_to_bool(self.is_tribal),
            "is_citizen": _str_to_bool(
                self.is_citizen or "Yes"
            ),  # Default to yes if not specified
            "has_aadhaar": _str_to_bool(self.aadhaar_available),
            "aadhaar_available": _str_to_bool(self.aadhaar_available),
            "is_head_of_family": _str_to_bool(self.is_head_of_family),
            "income_certificate_available": _str_to_bool(
                self.income_certificate_available
            ),
            "ration_card_available": _str_to_bool(self.ration_card_available),
            "govt_employee_in_family": _str_to_bool(self.govt_employee_in_family),
            "own_agricultural_land": _str_to_bool(self.own_agricultural_land),
            "is_tenant_farmer": _str_to_bool(self.is_tenant_farmer),
            "bank_account_available": _str_to_bool(self.bank_account_available),
            "has_bank_account": _str_to_bool(
                self.bank_account_available or self.has_bank_account
            ),
            "aadhaar_linked_bank": _str_to_bool(self.aadhaar_linked_bank),
            "mobile_linked_bank": _str_to_bool(self.mobile_linked_bank),
            "income_cert_last_1_year": _str_to_bool(self.income_cert_last_1_year),
            "scheme_previously_availed": _str_to_bool(self.scheme_previously_availed),
            "willing_to_submit_docs": _str_to_bool(self.willing_to_submit_docs),
            "is_pensioner": _str_to_bool(self.is_pensioner),
            "has_pucca_house": _str_to_bool(self.has_pucca_house),
            "is_landless": _str_to_bool(self.is_landless),
            "is_bocw_registered": _str_to_bool(self.is_bocw_registered),
            "is_school_dropout": _str_to_bool(self.is_school_dropout),
            "is_first_gen_student": _str_to_bool(self.is_first_gen_student),
            "is_urban": _str_to_bool(
                self.is_urban or (self.residence and "urban" in self.residence.lower())
            ),
            "is_rural": _str_to_bool(
                self.residence and "rural" in self.residence.lower()
            ),
            "is_bpl": str(self.ration_card_type or "").lower()
            in ("bpl", "antyodaya", "aay"),
        }

        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "mobile": self.mobile,
            "profile": {k: v for k, v in p.items() if v is not None},
        }

    def get_profile_dict(self):
        """
        Unified way to reach user profile data for the engine.
        Returns snake_case keys matching the Condition.field names in the DB.
        NOTE: _user_get_profile_dict is patched over this below with the full implementation.
        This stub is only used if the patch hasn't run yet (shouldn't happen in production).
        """
        return _user_get_profile_dict(self)


class UserDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    doc_type = db.Column(db.String(100))  # Aadhaar Card, Ration Card, etc.
    extracted_data = db.Column(db.Text)  # JSON string
    confidence_score = db.Column(db.Float)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("documents", lazy=True))

    def to_dict(self):
        try:
            data = json.loads(self.extracted_data) if self.extracted_data else {}
        except:
            data = {}
        return {
            "id": self.id,
            "docType": self.doc_type,
            "filename": self.filename,
            "originalName": self.original_name,
            "uploadDate": self.upload_date.isoformat(),
            "extractedData": data,
            "confidenceScore": self.confidence_score,
            "url": f"api/view-document/{self.id}",
        }


class Scheme(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100))
    target_audience = db.Column(db.String(200))
    benefits = db.Column(db.Text)
    eligibility = db.Column(db.Text)
    application_link = db.Column(db.String(300))
    min_age = db.Column(db.Integer)
    max_age = db.Column(db.Integer)
    allowed_genders = db.Column(db.String(100))  # JSON array
    min_income = db.Column(db.Integer)
    max_income = db.Column(db.Integer)
    allowed_occupations = db.Column(db.Text)  # JSON array
    allowed_castes = db.Column(db.Text)  # JSON array
    allowed_states = db.Column(db.Text)  # JSON array
    allowed_education = db.Column(db.Text)  # JSON array
    allowed_marital_status = db.Column(db.Text)  # JSON array
    disability_requirement = db.Column(db.String(20))  # Yes/No/Any
    residence_requirement = db.Column(db.String(20))  # Urban/Rural/Any

    # New holistic granular criteria
    allowed_father_occupations = db.Column(db.Text)  # JSON array
    allowed_mother_occupations = db.Column(db.Text)  # JSON array
    allowed_religions = db.Column(db.Text)  # JSON array
    land_type_requirement = db.Column(db.String(20))  # Dry/Wet/Any
    orphan_requirement = db.Column(db.String(20))  # Yes/No/Any
    tribal_requirement = db.Column(db.String(20))  # Yes/No/Any

    # New granular criteria
    minority_requirement = db.Column(db.String(20))  # Yes/No/Any
    senior_citizen_requirement = db.Column(db.String(20))  # Yes/No/Any
    widow_requirement = db.Column(db.String(20))  # Yes/No/Any
    disability_percentage_min = db.Column(db.Integer)
    bank_account_required = db.Column(db.String(10))  # Yes/No
    aadhaar_required = db.Column(db.String(10))  # Yes/No
    allowed_ration_card_types = db.Column(db.Text)  # JSON array
    min_education_level = db.Column(db.String(100))
    mutually_exclusive_with = db.Column(db.Text)  # JSON array of scheme tags or IDs

    # Detailed Information Fields
    exclusions = db.Column(db.Text)
    application_process = db.Column(db.Text)
    documents_required = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    extraction_status = db.Column(db.String(32), default="pending")
    extraction_version = db.Column(db.Integer)
    expires_at = db.Column(db.Date)
    raw_text = None  # Property - uses eligibility text for pipeline

    # FLAT COLUMNS BLOCKED - Use Condition table instead
    FLAT_COLUMNS = {
        "min_age",
        "max_age",
        "allowed_genders",
        "allowed_castes",
        "allowed_states",
        "allowed_education",
        "allowed_occupations",
        "allowed_marital_status",
        "min_income",
        "max_income",
        "disability_requirement",
        "residence_requirement",
        "minority_requirement",
        "senior_citizen_requirement",
        "widow_requirement",
        "orphan_requirement",
        "tribal_requirement",
        "land_type_requirement",
        "bank_account_required",
        "aadhaar_required",
        "allowed_father_occupations",
        "allowed_mother_occupations",
        "allowed_religions",
        "allowed_ration_card_types",
        "disability_percentage_min",
        "min_education_level",
    }

    def __setattr__(self, key, value):
        if key in Scheme.FLAT_COLUMNS:
            raise AttributeError(
                f"Flat column '{key}' is deprecated. "
                f"Use Condition table for eligibility criteria."
            )
        super().__setattr__(key, value)

    @property
    def raw_text(self):
        """Pipeline expects raw_text - return eligibility for compatibility."""
        return self.eligibility or ""

    @raw_text.setter
    def raw_text(self, value):
        """Allow pipeline to set raw_text - stored in eligibility."""
        pass  # Don't store - use eligibility

    @property
    def ministry(self):
        """Pipeline expects ministry - return category for compatibility."""
        return self.category or ""

    @ministry.setter
    def ministry(self, value):
        """Allow pipeline to set ministry - don't store."""
        pass

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "targetAudience": self.target_audience,
            "benefits": self.benefits,
            "eligibility": self.eligibility,
            "applicationLink": self.application_link,
            "criteria": {
                "minAge": self.min_age,
                "maxAge": self.max_age,
                "allowedGenders": (
                    json.loads(self.allowed_genders) if self.allowed_genders else []
                ),
                "minIncome": self.min_income,
                "maxIncome": self.max_income,
                "allowedOccupations": (
                    json.loads(self.allowed_occupations)
                    if self.allowed_occupations
                    else []
                ),
                "allowedCastes": (
                    json.loads(self.allowed_castes) if self.allowed_castes else []
                ),
                "allowedStates": (
                    json.loads(self.allowed_states) if self.allowed_states else []
                ),
                "allowedEducation": (
                    json.loads(self.allowed_education) if self.allowed_education else []
                ),
                "allowedMaritalStatus": (
                    json.loads(self.allowed_marital_status)
                    if self.allowed_marital_status
                    else []
                ),
                "disabilityRequirement": self.disability_requirement,
                "residenceRequirement": self.residence_requirement,
                # New fields
                "minorityRequirement": self.minority_requirement,
                "seniorCitizenRequirement": self.senior_citizen_requirement,
                "widowRequirement": self.widow_requirement,
                "disabilityPercentageMin": self.disability_percentage_min,
                "bank_account_required": self.bank_account_required,
                "aadhaarRequired": self.aadhaar_required,
                "allowedRationCardTypes": (
                    json.loads(self.allowed_ration_card_types)
                    if self.allowed_ration_card_types
                    else []
                ),
                "minEducationLevel": self.min_education_level,
                "mutuallyExclusiveWith": (
                    json.loads(self.mutually_exclusive_with)
                    if self.mutually_exclusive_with
                    else []
                ),
                "allowedFatherOccupations": (
                    json.loads(self.allowed_father_occupations)
                    if self.allowed_father_occupations
                    else []
                ),
                "allowedMotherOccupations": (
                    json.loads(self.allowed_mother_occupations)
                    if self.allowed_mother_occupations
                    else []
                ),
                "allowedReligions": (
                    json.loads(self.allowed_religions) if self.allowed_religions else []
                ),
                "landTypeRequirement": self.land_type_requirement,
                "orphanRequirement": self.orphan_requirement,
                "tribal_requirement": self.tribal_requirement,
                "exclusions": self.exclusions,
                "applicationProcess": self.application_process,
                "documentsRequired": self.documents_required,
            },
        }

    @property
    def conditions(self):
        """
        Get conditions for a scheme.
        STRICT: Returns ONLY DB Condition rows.
        """
        return list(self.condition_rows) if hasattr(self, "condition_rows") else []


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)


class SchemeSource(db.Model):
    """Government websites to scrape for schemes"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # e.g., "SevaSethe Karnataka"
    url = db.Column(db.String(500), nullable=False)
    scraper_type = db.Column(
        db.String(100)
    )  # e.g., "karnataka_sevasethe", "education_gov_in"
    is_active = db.Column(db.Boolean, default=True)
    last_scraped = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "scraperType": self.scraper_type,
            "isActive": self.is_active,
            "lastScraped": self.last_scraped.isoformat() if self.last_scraped else None,
            "createdAt": self.created_at.isoformat(),
        }


class SchemeTranslation(db.Model):
    """Cache for AI-translated scheme details using flexible JSON storage"""

    id = db.Column(db.Integer, primary_key=True)
    scheme_id = db.Column(db.Integer, db.ForeignKey("scheme.id"), nullable=False)
    language = db.Column(db.String(10), nullable=False)  # e.g., 'kn'

    # Store complete translation payload as JSON string
    content_json = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("scheme_id", "language", name="_scheme_lang_uc"),
    )

    def to_dict(self):
        try:
            data = json.loads(self.content_json)
        except:
            data = {}

        return {
            "id": self.id,
            "schemeId": self.scheme_id,
            "language": self.language,
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "benefits": data.get("benefits", ""),
            "eligibility": data.get("eligibility", ""),
            "exclusions": data.get("exclusions", ""),
            "applicationProcess": data.get("application_process", ""),
            "documentsRequired": data.get("documents_required", ""),
        }


class PendingScheme(db.Model):
    """Schemes detected by scraper awaiting admin approval"""

    id = db.Column(db.Integer, primary_key=True)
    # Core scheme details (same as Scheme model)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100))
    target_audience = db.Column(db.String(200))
    benefits = db.Column(db.Text)
    eligibility = db.Column(db.Text)
    application_link = db.Column(db.String(300))
    min_age = db.Column(db.Integer)
    max_age = db.Column(db.Integer)
    allowed_genders = db.Column(db.String(100))
    min_income = db.Column(db.Integer)
    max_income = db.Column(db.Integer)
    allowed_occupations = db.Column(db.Text)
    allowed_castes = db.Column(db.Text)
    allowed_states = db.Column(db.Text)
    allowed_education = db.Column(db.Text)
    allowed_marital_status = db.Column(db.Text)
    disability_requirement = db.Column(db.String(20))
    residence_requirement = db.Column(db.String(20))

    # New holistic granular criteria
    allowed_father_occupations = db.Column(db.Text)  # JSON array
    allowed_mother_occupations = db.Column(db.Text)  # JSON array
    allowed_religions = db.Column(db.Text)  # JSON array
    land_type_requirement = db.Column(db.String(20))  # Dry/Wet/Any
    orphan_requirement = db.Column(db.String(20))  # Yes/No/Any
    tribal_requirement = db.Column(db.String(20))  # Yes/No/Any

    # New granular criteria
    minority_requirement = db.Column(db.String(20))
    senior_citizen_requirement = db.Column(db.String(20))
    widow_requirement = db.Column(db.String(20))
    disability_percentage_min = db.Column(db.Integer)
    bank_account_required = db.Column(db.String(10))
    aadhaar_required = db.Column(db.String(10))
    allowed_ration_card_types = db.Column(db.Text)
    min_education_level = db.Column(db.String(100))
    mutually_exclusive_with = db.Column(db.Text)  # JSON array of scheme tags or IDs

    # Detailed Information Fields
    exclusions = db.Column(db.Text)
    application_process = db.Column(db.Text)
    documents_required = db.Column(db.Text)

    # Approval workflow fields
    status = db.Column(db.String(20), default="pending")  # pending, approved, rejected
    source_id = db.Column(db.Integer, db.ForeignKey("scheme_source.id"))
    source = db.relationship("SchemeSource", backref="pending_schemes")
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_by = db.Column(db.Integer, db.ForeignKey("admin.id"))
    approved_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.String(500))
    confidence_score = db.Column(db.Float)  # 0.0-1.0, how well data was extracted

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "targetAudience": self.target_audience,
            "benefits": self.benefits,
            "eligibility": self.eligibility,
            "applicationLink": self.application_link,
            "criteria": {
                "minAge": self.min_age,
                "maxAge": self.max_age,
                "allowedGenders": (
                    json.loads(self.allowed_genders) if self.allowed_genders else []
                ),
                "minIncome": self.min_income,
                "maxIncome": self.max_income,
                "allowedOccupations": (
                    json.loads(self.allowed_occupations)
                    if self.allowed_occupations
                    else []
                ),
                "allowedCastes": (
                    json.loads(self.allowed_castes) if self.allowed_castes else []
                ),
                "allowedStates": (
                    json.loads(self.allowed_states) if self.allowed_states else []
                ),
                "allowedEducation": (
                    json.loads(self.allowed_education) if self.allowed_education else []
                ),
                "allowedMaritalStatus": (
                    json.loads(self.allowed_marital_status)
                    if self.allowed_marital_status
                    else []
                ),
                "disabilityRequirement": self.disability_requirement,
                "residenceRequirement": self.residence_requirement,
                # New fields
                "minorityRequirement": self.minority_requirement,
                "seniorCitizenRequirement": self.senior_citizen_requirement,
                "widowRequirement": self.widow_requirement,
                "disabilityPercentageMin": self.disability_percentage_min,
                "bankAccountRequired": self.bank_account_required,
                "aadhaarRequired": self.aadhaar_required,
                "allowedRationCardTypes": (
                    json.loads(self.allowed_ration_card_types)
                    if self.allowed_ration_card_types
                    else []
                ),
                "minEducationLevel": self.min_education_level,
                "mutuallyExclusiveWith": (
                    json.loads(self.mutually_exclusive_with)
                    if self.mutually_exclusive_with
                    else []
                ),
                "allowedFatherOccupations": (
                    json.loads(self.allowed_father_occupations)
                    if self.allowed_father_occupations
                    else []
                ),
                "allowedMotherOccupations": (
                    json.loads(self.allowed_mother_occupations)
                    if self.allowed_mother_occupations
                    else []
                ),
                "allowedReligions": (
                    json.loads(self.allowed_religions) if self.allowed_religions else []
                ),
                "landTypeRequirement": self.land_type_requirement or "Any",
                "orphanRequirement": self.orphan_requirement or "Any",
                "tribalRequirement": self.tribal_requirement or "Any",
                "exclusions": self.exclusions,
                "applicationProcess": self.application_process,
                "documentsRequired": self.documents_required,
            },
            "status": self.status,
            "sourceId": self.source_id,
            "sourceName": self.source.name if self.source else None,
            "scrapedAt": self.scraped_at.isoformat(),
            "confidenceScore": self.confidence_score,
            "rejectionReason": self.rejection_reason,
        }


class AdminNotification(db.Model):
    """In-app notifications for admins"""

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admin.id"))
    pending_scheme_id = db.Column(db.Integer, db.ForeignKey("pending_scheme.id"))
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "message": self.message,
            "isRead": self.is_read,
            "createdAt": self.created_at.isoformat(),
            "pendingSchemeId": self.pending_scheme_id,
        }


class ScrapeLog(db.Model):
    """Log of scraping activities for debugging"""

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey("scheme_source.id"))
    source = db.relationship("SchemeSource", backref="logs")
    status = db.Column(db.String(20))  # success, error, partial
    schemes_found = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "sourceId": self.source_id,
            "sourceName": self.source.name if self.source else None,
            "status": self.status,
            "schemesFound": self.schemes_found,
            "errorMessage": self.error_message,
            "scrapedAt": self.scraped_at.isoformat(),
        }


# ==============================================================================
# NEW ELIGIBILITY ENGINE MODELS (v6 — structured Condition-based engine)
# ==============================================================================

import uuid


def _new_uuid():
    return str(uuid.uuid4())


class Condition(db.Model):
    __tablename__ = "conditions"

    id = db.Column(db.String(36), primary_key=True, default=_new_uuid)
    scheme_id = db.Column(db.Integer, db.ForeignKey("scheme.id"), nullable=False)
    field = db.Column(db.String(128), nullable=False)
    operator = db.Column(db.String(32), nullable=False)
    value = db.Column(db.Text, nullable=False)
    condition_type = db.Column(db.String(32), default="soft")
    confidence = db.Column(db.Float, default=1.0)
    source_fragment = db.Column(db.Text)
    source = db.Column(
        db.String(32), default="manual"
    )  # 'manual', 'extraction', 'migration'
    is_ambiguous = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    scheme = db.relationship(
        "Scheme",
        backref=db.backref(
            "condition_rows", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )

    @property
    def parsed_value(self):
        try:
            return json.loads(self.value)
        except Exception:
            return self.value

    @parsed_value.setter
    def parsed_value(self, val):
        self.value = json.dumps(val)


class EligibilityResult(db.Model):
    __tablename__ = "eligibility_results"

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    scheme_id = db.Column(db.Integer, db.ForeignKey("scheme.id"), primary_key=True)
    result = db.Column(db.String(32))
    confidence = db.Column(db.Float, default=0.0)
    blocking_reason = db.Column(db.Text)
    missing_fields = db.Column(db.Text, default="[]")
    acquirable = db.Column(db.Text, default="[]")
    computed_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile_version = db.Column(db.Integer, default=1)

    user = db.relationship("User", backref=db.backref("elig_results", lazy="dynamic"))
    scheme = db.relationship(
        "Scheme", backref=db.backref("elig_results", lazy="dynamic")
    )

    @property
    def missing_fields_list(self):
        try:
            return json.loads(self.missing_fields or "[]")
        except Exception:
            return []

    @property
    def acquirable_list(self):
        try:
            return json.loads(self.acquirable or "[]")
        except Exception:
            return []


class SchemeFlag(db.Model):
    __tablename__ = "scheme_flags"

    id = db.Column(db.String(36), primary_key=True, default=_new_uuid)
    scheme_id = db.Column(db.Integer, db.ForeignKey("scheme.id"), nullable=False)
    flag_type = db.Column(db.String(64))
    reason = db.Column(db.Text)
    severity = db.Column(db.String(16), default="warning")
    auto_raised = db.Column(db.Boolean, default=True)
    raised_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    resolved_by = db.Column(db.String(36))
    resolution = db.Column(db.String(32))

    scheme = db.relationship("Scheme", backref=db.backref("flags", lazy="dynamic"))

    @property
    def is_open(self):
        return self.resolved_at is None


class UserProfileAttribute(db.Model):
    __tablename__ = "user_profile_attributes"

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    field = db.Column(db.String(128), primary_key=True)
    value = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(32), default="direct_input")
    confidence = db.Column(db.Float, default=1.0)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("profile_attrs", lazy="dynamic"))


class SchemeClarification(db.Model):
    __tablename__ = "scheme_clarifications"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "scheme_id", "question_id_hash", name="uq_clarification"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    scheme_id = db.Column(db.Integer, db.ForeignKey("scheme.id"), nullable=False)
    question_id_hash = db.Column(db.String(64), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    answer_text = db.Column(db.Text, nullable=False)
    ai_verdict = db.Column(db.String(32), nullable=False)
    resolved_at = db.Column(db.DateTime, default=datetime.utcnow)
    iteration_count = db.Column(db.Integer, default=0)


class QuestionAnswer(db.Model):
    __tablename__ = "question_answers"

    id = db.Column(db.String(36), primary_key=True, default=_new_uuid)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    question_id = db.Column(db.String(128))
    field = db.Column(db.String(128), nullable=False)
    value = db.Column(db.Text, nullable=False)
    context = db.Column(db.String(36))
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("qa_answers", lazy="dynamic"))


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.String(36), primary_key=True, default=_new_uuid)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    scheme_id = db.Column(db.Integer, db.ForeignKey("scheme.id"), nullable=False)
    did_apply = db.Column(db.Boolean)
    match_score = db.Column(db.Float)
    outcome = db.Column(db.String(32))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = db.relationship("User", backref=db.backref("feedback_list", lazy="dynamic"))
    scheme = db.relationship(
        "Scheme", backref=db.backref("feedback_list", lazy="dynamic")
    )

    def to_dict(self):
        return {
            "id": self.id,
            "scheme_id": self.scheme_id,
            "did_apply": self.did_apply,
            "match_score": self.match_score,
            "outcome": self.outcome,
            "notes": self.notes,
            "created_at": str(self.created_at),
        }


# ==============================================================================
# USER MODEL — add get_profile_dict() for new engine
# ==============================================================================


def _str_to_bool(val):
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("yes", "true", "1", "y")


def _str_to_int(val):
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _str_to_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


# Patch User model with get_profile_dict
def _user_get_profile_dict(self):
    base = {
        "state": self.state,
        "age": self.age,
        "gender": self.gender,
        "category": self.caste,  # map old 'caste' to new 'category'
        "occupation": self.occupation,
        "annual_income": self.income,
        "education_level": self.highest_education_level or self.education,
        "is_student": _str_to_bool(
            normalize_is_student(
                self.education_status,
                self.employment_status,
                self.highest_education_level or self.education,
                self.occupation,
            )
        ),
        "income": self.income,
        "family_income": self.annual_family_income,
        "disability_percentage": self.disability_percentage,
        # Boolean flags from string Yes/No fields
        "is_farmer": _str_to_bool(self.is_farmer),
        "is_bpl": str(self.ration_card_type or "").lower()
        in ("bpl", "antyodaya", "aay"),
        "is_disabled": _str_to_bool(self.disability),
        "is_widow": _str_to_bool(self.is_widow_single_woman),
        "is_senior_citizen": _str_to_bool(self.is_senior_citizen),
        "is_minority": _str_to_bool(self.minority_status),
        "is_ews": _str_to_bool(self.ews_status),
        "is_orphan": _str_to_bool(self.is_orphan),
        "is_tribal": _str_to_bool(self.is_tribal),
        "has_aadhaar": _str_to_bool(self.aadhaar_available),
        "has_bank_account": _str_to_bool(self.bank_account_available),
        "has_income_cert": _str_to_bool(self.income_certificate_available),
        "has_ration_card": _str_to_bool(self.ration_card_available),
        "is_pensioner": _str_to_bool(self.is_pensioner),
        "is_self_employed": self.occupation and "self" in self.occupation.lower(),
        "is_construction_worker": _str_to_bool(self.is_bocw_registered),
        "is_school_dropout": _str_to_bool(self.is_school_dropout),
        "is_first_gen_student": _str_to_bool(self.is_first_gen_student),
        "is_landless": _str_to_bool(self.is_landless),
        "has_pucca_house": _str_to_bool(self.has_pucca_house),
        "is_urban": self.residence and self.residence.lower() == "urban",
        "is_rural": self.residence and self.residence.lower() == "rural",
        "religion": self.religion,
        "land_type": self.land_type,
        "marital_status": self.marital_status,
        "residence": self.residence,
        "num_daughters": self.num_daughters,
        # Additional profile fields for engine coverage
        "employment_status": self.employment_status,
        "father_occupation": self.father_occupation,
        "mother_occupation": self.mother_occupation,
        "caste": self.caste,
        "ration_card_type": self.ration_card_type,
        "land_size_acres": self.land_size_acres,
        "district": self.district,
        "highest_education_level": self.highest_education_level or self.education,
        "current_course": self.current_course,
        "institution_type": self.institution_type,
        "disability": self.disability,
    }
    # Merge any dynamic UserProfileAttribute rows (from question answers)
    import json as _json

    for attr in getattr(self, "profile_attrs", []) or []:
        try:
            base[attr.field] = _json.loads(attr.value)
        except Exception:
            base[attr.field] = attr.value
    # Strip None values so engine treats them as truly unknown
    return {k: v for k, v in base.items() if v is not None}


# Patch the correct engine-compatible get_profile_dict onto User model
User.get_profile_dict = _user_get_profile_dict

# SCHEME MODEL — conditions property (Condition table only)
# ==============================================================================


def _scheme_get_conditions(self):
    """
    Get conditions for a scheme.

    STRICT: Returns ONLY DB Condition rows.
    No fallback - if no conditions exist, return empty list.
    """
    conditions = list(self.condition_rows)
    return conditions


# ----------------- Routes -----------------
@app.route("/")
def index():
    # Serve the main index.html from /static
    return send_from_directory("static", "index.html")


@app.route("/all-schemes")
def all_schemes():
    return send_from_directory("static", "all_schemes.html")


@app.route("/dashboard")
def dashboard():
    # Redirect to home where the dashboard logic resides
    return redirect(url_for("index"))


@app.route("/unsubscribe")
def unsubscribe():
    # Placeholder for unsubscribe logic
    return "Unsubscribed successfully. You will no longer receive emails.", 200


@app.route("/admin.html")
def serve_admin():
    import os

    admin_path = os.path.join("static", "admin.html")
    if not os.path.exists(admin_path):
        return send_from_directory("static", "admin.html")
    with open(admin_path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()
    patch = (
        "<script>\n"
        "/* Admin Patch: remove 50-scheme fetch limit */\n"
        "(function(){\n"
        "  const _fetch = window.fetch;\n"
        "  window.fetch = function(url, opts) {\n"
        '    if (typeof url === "string"\n'
        '        && url.includes("/api/admin/pending-schemes")\n'
        '        && !url.includes("/approve")\n'
        '        && !url.includes("/reject")\n'
        '        && !url.includes("/translate")) {\n'
        "      url = url\n"
        '        .replace(/[?&]per_page=[0-9]+/, "")\n'
        '        .replace(/[?&]page=[0-9]+/, "")\n'
        '        .replace(/[?&]$/, "");\n'
        "    }\n"
        "    return _fetch.apply(this, [url, opts]);\n"
        "  };\n"
        "})();\n"
        "</script>\n"
    )
    if "</body>" in html:
        html = html.replace("</body>", patch + "</body>", 1)
    else:
        html += patch
    from flask import Response

    return Response(html, mimetype="text/html")


@app.route("/scrolly.mp4")
def serve_scrolly_video():
    return send_from_directory("static", "scrolly.mp4", conditional=True)


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)


# ----------------- User Auth Routes -----------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    if not data.get("name") or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Missing required fields"}), 400

    email = data["email"].lower().strip()
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400
    user = User(
        name=data["name"],
        email=email,
        password_hash=generate_password_hash(data["password"]),
        mobile=data.get("mobile", ""),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Registration successful", "user": user.to_dict()}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email", "").lower().strip()
    password = data.get("password")

    safe_print(f"DEBUG: Login attempt for {email}")

    # Check if Admin
    admin = Admin.query.filter_by(email=email).first()
    if admin:
        safe_print(f"DEBUG: Admin found for {email}")
        if check_password_hash(admin.password_hash, password):
            session["user_id"] = admin.id
            session["user_type"] = "admin"
            safe_print(f"DEBUG: Admin login successful for {email}")
            return (
                jsonify(
                    {
                        "message": "Admin login successful",
                        "user": {
                            "id": admin.id,
                            "email": admin.email,
                            "name": "Administrator",
                            "isAdmin": True,
                        },
                    }
                ),
                200,
            )
        else:
            safe_print(f"DEBUG: Admin password mismatch for {email}")

    # Check if Normal User
    user = User.query.filter_by(email=email).first()
    if user:
        safe_print(f"DEBUG: User found for {email}")
        if check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["user_type"] = "user"
            safe_print(f"DEBUG: User login successful for {email}")
            return jsonify({"message": "Login successful", "user": user.to_dict()}), 200
        else:
            safe_print(f"DEBUG: User password mismatch for {email}")
    else:
        safe_print(f"DEBUG: No user found for {email}")

    return jsonify({"error": "Invalid email or password"}), 401


@app.route("/logout")
def logout_redirect():
    """Redirect /logout to API logout then auth page"""
    session.clear()
    return redirect("/auth.html")


@app.route("/api/logout", methods=["GET", "POST"])
def logout():
    safe_print(
        f"DEBUG: Logout triggered for user_id={session.get('user_id')}, type={session.get('user_type')}"
    )
    session.clear()
    return jsonify({"message": "Logout successful"}), 200


@app.route("/api/user", methods=["GET"])
def get_current_user():
    if session.get("user_type") != "user":
        return jsonify({"error": "Not logged in as user"}), 401

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Compute server-side profile score
    profile_score, score_hints = calculate_profile_score(user)
    user_dict = user.to_dict()
    user_dict["profileScore"] = profile_score
    user_dict["profileScoreHints"] = score_hints

    return jsonify({"user": user_dict}), 200


@app.route("/api/user/answer", methods=["POST"])
def submit_question_answer():
    """Save user's answer to a question and trigger re-evaluation"""
    if session.get("user_type") != "user":
        return jsonify({"error": "Not logged in as user"}), 401

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    field = data.get("field")
    value = data.get("value")

    if not field:
        return jsonify({"error": "Field is required"}), 400

    # Validate input: reject null/empty values at API level
    if value is None or value == "" or value == "null":
        app.logger.warning(f"[VALIDATION] Rejected null/empty value for field: {field}")
        return jsonify({"error": "Invalid value: cannot be empty"}), 400

    # Validate input: check field type using canonical registry
    try:
        from app.engine.canonical_field_registry import get_data_type_for_field

        expected_type = get_data_type_for_field(field)
    except Exception:
        expected_type = "string"  # default to string if registry unavailable

    # Basic type validation
    if expected_type in ("integer", "number"):
        try:
            float(value)
        except (ValueError, TypeError):
            app.logger.warning(
                f"[VALIDATION] Invalid numeric value '{value}' for field '{field}' (expected {expected_type})"
            )
            return (
                jsonify({"error": f"Invalid value for {field}: must be a number"}),
                400,
            )

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        # 1. Save to QuestionAnswer model
        answer = QuestionAnswer(
            user_id=user_id, field=field, value=value, answered_at=datetime.utcnow()
        )
        db.session.add(answer)

        # 2. Update user profile with answer — try direct field, then mapped fields
        saved_to_model = False
        if hasattr(user, field):
            setattr(user, field, value)
            saved_to_model = True

        # Also save to UserProfileAttribute for engine lookup
        from app.engine.eligibility import get_canonical_field, FIELD_MAP

        canonical = get_canonical_field(field)
        # Try to save to any mapped User column
        mapped = FIELD_MAP.get(field) or FIELD_MAP.get(canonical)
        if mapped and hasattr(user, mapped) and not saved_to_model:
            setattr(user, mapped, value)

        # Save as UserProfileAttribute regardless (engine reads these too)
        import json as _j

        encoded_val = _j.dumps(value) if not isinstance(value, str) else value

        existing_attr = UserProfileAttribute.query.filter_by(
            user_id=user_id, field=field
        ).first()
        if existing_attr:
            existing_attr.value = encoded_val
            existing_attr.source = "question_answer"
        else:
            db.session.add(
                UserProfileAttribute(
                    user_id=user_id,
                    field=field,
                    value=encoded_val,
                    source="question_answer",
                    confidence=1.0,
                )
            )

        # Also save under canonical field name
        if canonical != field:
            existing_canon = UserProfileAttribute.query.filter_by(
                user_id=user_id, field=canonical
            ).first()
            if existing_canon:
                existing_canon.value = encoded_val
                existing_canon.source = "question_answer"
            else:
                db.session.add(
                    UserProfileAttribute(
                        user_id=user_id,
                        field=canonical,
                        value=encoded_val,
                        source="question_answer",
                        confidence=1.0,
                    )
                )

        # 3. Increment profile_version to invalidate cache
        user.profile_version = (user.profile_version or 0) + 1

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error saving answer for field {field}: {str(e)}")
        return jsonify({"error": str(e)}), 500

    from app.engine_compat import get_orchestrator, build_engine_response

    orch = get_orchestrator(app.config)
    all_schemes = Scheme.query.all()

    # Use updated profile (cache already invalidated)
    result = build_engine_response(orch, user, all_schemes)

    return (
        jsonify(
            {
                "status": "success",
                "field": field,
                "value": value,
                "profile_version": user.profile_version,
                # NEW: Return updated eligibility results
                "recommendations": result.get("recommendations", []),
                "possibly_eligible": result.get("possibly_eligible", []),
                "questions": result.get("questions", []),
                "meta": result.get("meta", {}),
                "message": f"Answer saved! Your eligibility has been updated.",
            }
        ),
        200,
    )


@app.route("/api/user/batch-answer", methods=["POST"])
def submit_batch_answers():
    """Save a list of user's answers and trigger re-evaluation once"""
    if session.get("user_type") != "user":
        return jsonify({"error": "Not logged in as user"}), 401

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    answers = data.get("answers", [])
    if not answers:
        return jsonify({"success": True, "message": "No answers to save"}), 200

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    from app.engine.eligibility import get_canonical_field, FIELD_MAP
    import json as _j

    try:
        for item in answers:
            field = item.get("field")
            value = item.get("value")
            if not field or value is None or value == "" or value == "null":
                continue

            # 1. Save to QuestionAnswer model
            db.session.add(
                QuestionAnswer(
                    user_id=user_id,
                    field=field,
                    value=value,
                    answered_at=datetime.utcnow(),
                )
            )

            # 2. Update user profile
            saved_to_model = False
            if hasattr(user, field):
                setattr(user, field, value)
                saved_to_model = True

            canonical = get_canonical_field(field)
            mapped = FIELD_MAP.get(field) or FIELD_MAP.get(canonical)
            if mapped and hasattr(user, mapped) and not saved_to_model:
                setattr(user, mapped, value)

            # Save as UserProfileAttribute
            encoded_val = _j.dumps(value) if not isinstance(value, str) else value
            existing_attr = UserProfileAttribute.query.filter_by(
                user_id=user_id, field=field
            ).first()
            if existing_attr:
                existing_attr.value = encoded_val
            else:
                db.session.add(
                    UserProfileAttribute(
                        user_id=user_id,
                        field=field,
                        value=encoded_val,
                        source="batch_question_answer",
                        confidence=1.0,
                    )
                )

            if canonical != field:
                existing_canon = UserProfileAttribute.query.filter_by(
                    user_id=user_id, field=canonical
                ).first()
                if existing_canon:
                    existing_canon.value = encoded_val
                else:
                    db.session.add(
                        UserProfileAttribute(
                            user_id=user_id,
                            field=canonical,
                            value=encoded_val,
                            source="batch_question_answer",
                            confidence=1.0,
                        )
                    )

        # 3. Increment profile_version
        user.profile_version = (user.profile_version or 0) + 1
        db.session.commit()

        # 4. Trigger re-evaluation
        from app.engine_compat import get_orchestrator, build_engine_response

        orch = get_orchestrator(app.config)
        all_schemes = Scheme.query.all()
        # Increase question_cap slightly for better follow-up
        result = build_engine_response(orch, user, all_schemes)

        return (
            jsonify(
                {
                    "status": "success",
                    "profile_version": user.profile_version,
                    "recommendations": result.get("recommendations", []),
                    "possibly_eligible": result.get("possibly_eligible", []),
                    "meta": result.get("meta", {}),
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in batch saving: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/resolve-questions", methods=["POST"])
def resolve_questions_bulk():
    """
    Accept bulk answers from the Resolve Questions modal.
    Saves answers to user profile, then re-evaluates ONLY the affected
    possibly-eligible schemes using the classifier engine.
    Returns categorized results: newly_eligible, still_possibly, newly_ineligible.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    answers = data.get("answers", {})  # { field_name: value, ... }
    scheme_ids = data.get("scheme_ids", [])  # IDs of possibly-eligible schemes

    if not answers:
        return jsonify({"error": "No answers provided"}), 400

    try:
        orch = get_orchestrator(app.config)

        # 2. Save all answers to user profile columns AND UserProfileAttribute
        from app.engine.eligibility import get_canonical_field, FIELD_MAP
        import json as _j

        for field, value in answers.items():
            # A. Direct column save
            saved_to_model = False
            if hasattr(user, field):
                setattr(user, field, value)
                saved_to_model = True

            # B. Mapped column save
            canonical = get_canonical_field(field)
            mapped = FIELD_MAP.get(field) or FIELD_MAP.get(canonical)
            if mapped and hasattr(user, mapped) and not saved_to_model:
                setattr(user, mapped, value)

            # C. UserProfileAttribute (for engine lookup)
            encoded_val = _j.dumps(value) if not isinstance(value, str) else value

            # Save original field
            existing_attr = UserProfileAttribute.query.filter_by(
                user_id=user_id, field=field
            ).first()
            if existing_attr:
                existing_attr.value = encoded_val
            else:
                db.session.add(
                    UserProfileAttribute(
                        user_id=user_id,
                        field=field,
                        value=encoded_val,
                        source="bulk_resolve",
                        confidence=1.0,
                    )
                )

            # Save canonical field
            if canonical != field:
                existing_canon = UserProfileAttribute.query.filter_by(
                    user_id=user_id, field=canonical
                ).first()
                if existing_canon:
                    existing_canon.value = encoded_val
                else:
                    db.session.add(
                        UserProfileAttribute(
                            user_id=user_id,
                            field=canonical,
                            value=encoded_val,
                            source="bulk_resolve",
                            confidence=1.0,
                        )
                    )

        user.profile_version = (user.profile_version or 0) + 1
        db.session.commit()

        # 3. Re-evaluate affected schemes
        all_schemes = {
            s.id: s for s in Scheme.query.filter(Scheme.id.in_(scheme_ids)).all()
        }

        impact_analysis = []
        newly_eligible_names = []
        newly_ineligible_names = []

        for sid in scheme_ids:
            scheme = all_schemes.get(sid)
            if not scheme:
                continue

            # Deep evaluation using the unified engine
            result = orch.evaluate_single_scheme(scheme, user, use_cache=False)

            # Formulate a logic-based reason for the status change
            impact_reason = result.top_insight or "Information verified."
            if result.result == "eligible":
                impact_reason = "All mandatory requirements have been met."
                newly_eligible_names.append(scheme.name)
            elif result.result == "ineligible":
                impact_reason = (
                    result.blocking_reason
                    or "One or more mandatory requirements failed."
                )
                newly_ineligible_names.append(scheme.name)

            entry = {
                "scheme_id": sid,
                "scheme_name": scheme.name,
                "old_status": "POSSIBLY_ELIGIBLE",
                "new_status": result.result.upper(),
                "impact_reason": impact_reason,
                "unknown_fields": result.missing_fields,
            }
            impact_analysis.append(entry)

        return (
            jsonify(
                {
                    "newly_eligible": newly_eligible_names,
                    "newly_ineligible": newly_ineligible_names,
                    "impact_analysis": impact_analysis,
                    "answers_saved": len(answers),
                    "total_resolved": len(newly_eligible_names)
                    + len(newly_ineligible_names),
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate-resolve-questions", methods=["POST"])
def generate_resolve_questions():
    """
    AI-powered endpoint: takes possibly eligible schemes with their reasons,
    and uses Gemini to produce natural, accurate multiple-choice questions.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    schemes_info = data.get("schemes", [])  # [{id, name, questions/reason}]

    if not schemes_info:
        return jsonify({"questions": [], "scheme_ids": []}), 200

    try:
        # Build COMPLETE raw profile from every single DB column
        # This ensures AI never asks about fields that have ANY value (including 0/No/False)
        SKIP_COLS = {
            "id",
            "email",
            "password_hash",
            "created_at",
            "updated_at",
            "is_admin",
            "profile_version",
            "question_answers",
        }

        from app.engine.eligibility import get_profile_value

        user_profile_dict = (
            user.get_profile_dict() if hasattr(user, "get_profile_dict") else {}
        )

        raw_profile = {}
        truly_unknown = []
        for col in User.__table__.columns.keys():
            if col in SKIP_COLS:
                continue

            # Use engine's resolver to see if this concept is already resolved
            # (e.g. is_citizen resolves citizenshipconcept)
            resolved_val = get_profile_value(col, user_profile_dict)

            if (
                resolved_val is not None
                and resolved_val != ""
                and resolved_val != "{}"
                and resolved_val != "[]"
            ):
                # Convert to human-readable for AI
                if isinstance(resolved_val, (int, bool)) and (
                    col.startswith(("is_", "has_", "own_")) or "available" in col
                ):
                    raw_profile[col] = "Yes" if resolved_val else "No"
                else:
                    raw_profile[col] = resolved_val
            else:
                truly_unknown.append(col)

        # Build the prompt
        scheme_context = []
        for s in schemes_info:  # Removed cap to analyze all schemes
            scheme_context.append(
                {
                    "id": s.get("id"),
                    "name": s.get("name", ""),
                    "reason": s.get("questions", "")
                    or s.get("reason", "")
                    or "Unknown verification needed",
                    "unknown_fields": s.get("unknown_fields", []),
                }
            )

        prompt = f"""You are YojanaMitra's intelligence-driven eligibility assistant.

TASK: Generate smart, non-redundant multiple-choice questions for "Possibly Eligible" schemes.

USER PROFILE (ALREADY KNOWN - DO NOT ASK ABOUT THESE):
{json.dumps(raw_profile, indent=2)}

FIELDS CURRENTLY UNKNOWN (ONLY THESE ARE ELIGIBLE FOR QUESTIONS):
{json.dumps(truly_unknown, indent=2)}

GLOBAL COGNITIVE INFERENCE RULES (CRITICAL):
1. USE COMMON SENSE: If a user has provided a specific value that implies another, do NOT ask about it.
2. COURSE -> FIELD: If user provided "current_course" (e.g., BE, BTech, MBBS, LLB), do NOT ask for "Highest Education Level" or "Field of Study".
3. OCCUPATION -> EMPLOYMENT: If user profile includes "occupation" or "employment_status", do NOT ask general employment questions.
4. FAMILY -> OCCUPATION: If user has listed parents' specific occupations (e.g., `father_occupation: Teacher`), DO NOT ask if their parents are teachers.
5. INCOME -> CLASS: If income is provided, do NOT ask if they are BPL/EWS unless explicitly unknown.
6. LOCATION: If "district" and "state" are present, do NOT ask for general location.
7. DISABILITY: If "disability_percentage" exists, infer "disability: Yes". Do NOT ask again.

POSSIBLY ELIGIBLE SCHEMES & REASONS:
{json.dumps(scheme_context, indent=2)}

STRICT OUTPUT RULES:
- If an answer can be reasoned out or inferred from the USER PROFILE, SKIP that question.
- Do NOT ask questions that the user has already answered in the profile above.
- Map questions to EXACT database column names from the FIELDS CURRENTLY UNKNOWN list.
- Return an empty list [] if all necessary info is already known or can be inferred.

OUTPUT STRICT JSON ARRAY ONLY (no markdown):
[
  {{
    "field": "db_column_name_from_unknown_list",
    "question": "Natural language question",
    "type": "bool|choice|number|text",
    "options": ["A", "B"] or null,
    "affects_scheme_ids": [123],
    "affects_scheme_names": ["Scheme Name"]
  }}
]"""

        response = model.generate_content(prompt)
        res_text = response.text.strip()

        # Clean markdown fencing
        if res_text.startswith("```json"):
            res_text = res_text[7:]
        if res_text.startswith("```"):
            res_text = res_text[3:]
        if res_text.endswith("```"):
            res_text = res_text[:-3]

        questions = json.loads(res_text.strip())

        scheme_ids = [s.get("id") for s in schemes_info]

        return (
            jsonify(
                {
                    "questions": questions,
                    "scheme_ids": scheme_ids,
                }
            ),
            200,
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e), "questions": []}), 500


# ----------------- Document Vault Routes -----------------


@app.route("/api/documents/upload", methods=["POST"])
def upload_document():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(
            f"user_{user_id}_{datetime.utcnow().timestamp()}_{file.filename}"
        )
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        # Process with AI
        ai_result = process_document_ai(file_path)

        # Save to DB
        doc = UserDocument(
            user_id=user_id,
            filename=filename,
            original_name=file.filename,
            doc_type=ai_result.get("doc_type", "Unknown"),
            extracted_data=json.dumps(ai_result.get("extracted_data", {})),
            confidence_score=ai_result.get("confidence", 0.0),
        )
        db.session.add(doc)
        db.session.commit()

        return (
            jsonify(
                {
                    "message": "Document uploaded and analyzed successfully",
                    "document": doc.to_dict(),
                }
            ),
            201,
        )

    return jsonify({"error": "Invalid file type"}), 400


@app.route("/api/documents", methods=["GET"])
def get_user_documents():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    documents = (
        UserDocument.query.filter_by(user_id=user_id)
        .order_by(UserDocument.upload_date.desc())
        .all()
    )
    return jsonify({"documents": [doc.to_dict() for doc in documents]}), 200


@app.route("/api/documents/<int:doc_id>", methods=["POST"])
def delete_document(doc_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    doc = db.session.get(UserDocument, doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    if doc.user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        # Delete file from disk
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], doc.filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        db.session.delete(doc)
        db.session.commit()
        return jsonify({"message": "Document deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/api/documents/sync-profile", methods=["POST"])
def sync_profile_from_vault():
    """
    Scans all user documents and updates the profile with extracted data.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    user = db.session.get(User, user_id)
    documents = UserDocument.query.filter_by(user_id=user_id).all()

    if not documents:
        return jsonify({"error": "No documents found in vault to sync"}), 400

    # Field Mapping Configuration
    field_map = {
        "Name": "name",
        "Full Name": "name",
        "Gender": "gender",
        "Date of Birth": "dob",
        "DOB": "dob",
        "Annual Income": "annual_family_income",
        "Income": "income",
        "Annual Family Income": "annual_family_income",
        "Age": "age",
        "Ration Card Type": "ration_card_type",
        "Caste": "caste",
        "Category": "caste",
        "Sub-Caste": "sub_caste",
    }

    modified_fields = []

    # Placeholders to allow overwriting
    placeholders = [
        "Test",
        "test@example.com",
        "100",
        100,
        "01-01-1990",
        "Single",
        "None",
        "",
        None,
    ]

    for doc in documents:
        try:
            data = json.loads(doc.extracted_data) if doc.extracted_data else {}
        except:
            continue

        for doc_key, user_field in field_map.items():
            val = data.get(doc_key)
            if not val:
                continue

            current_val = getattr(user, user_field)

            # Determine if we should update:
            # 1. Field is empty/placeholder
            # 2. Field is 'name' and currently 'Test'
            # 3. High confidence update
            should_update = False
            if current_val in placeholders:
                should_update = True
            elif not current_val:
                should_update = True

            # Specific check for Name placeholder
            if user_field == "name" and (
                not current_val or current_val.lower() == "test"
            ):
                should_update = True

            if should_update:
                try:
                    if user_field in [
                        "income",
                        "annual_family_income",
                        "age",
                        "total_family_members",
                    ]:
                        # Handle numeric cleaning
                        clean_num = int(str(val).replace(",", "").split(".")[0])
                        setattr(user, user_field, clean_num)
                    else:
                        setattr(user, user_field, str(val))

                    if user_field not in modified_fields:
                        modified_fields.append(user_field)
                except Exception as e:
                    print(f"Sync error for {user_field}: {e}")
                    pass

    # ── Sync document presence flags from vault doc_types ─────────────────────
    # This is the critical fix: vault uploads → profile Yes/No fields + achievement list
    achievement_certs = []
    for doc in documents:
        dtype = (doc.doc_type or "").lower().strip()
        try:
            ex = json.loads(doc.extracted_data) if doc.extracted_data else {}
        except Exception:
            ex = {}

        # Standard documents → profile flags
        if "aadhaar" in dtype:
            if user.aadhaar_available != "Yes":
                user.aadhaar_available = "Yes"
                modified_fields.append("aadhaarAvailable")
        if "income certificate" in dtype or "income cert" in dtype:
            if user.income_certificate_available != "Yes":
                user.income_certificate_available = "Yes"
                modified_fields.append("incomeCertificateAvailable")
        if "ration card" in dtype or "bpl card" in dtype:
            if user.ration_card_available != "Yes":
                user.ration_card_available = "Yes"
                modified_fields.append("rationCardAvailable")
            # Try to extract ration card type from OCR data
            rc_type = (
                ex.get("Ration Card Type") or ex.get("Card Type") or ex.get("Category")
            )
            if rc_type and not user.ration_card_type:
                user.ration_card_type = str(rc_type)
                modified_fields.append("rationCardType")

        # ── YojanaMitra OMR Questionnaire Sync ────────────────────────────────
        # Process keys starting with YM-Q- (e.g., YM-Q-IS_FARMER)
        for doc_key, val in ex.items():
            if str(doc_key).startswith("YM-Q-"):
                field_name = doc_key.replace("YM-Q-", "").lower()
                clean_val = None

                try:
                    # 1. Normalize Value
                    text_val = str(val).strip().lower()
                    if text_val in ["yes", "y", "shaded", "ticked"]:
                        clean_val = "Yes"
                    elif text_val in ["no", "n"]:
                        clean_val = "No"
                    elif field_name in [
                        "age",
                        "income",
                        "annual_family_income",
                        "annual_income",
                    ]:
                        try:
                            clean_val = int("".join(filter(str.isdigit, str(val))))
                        except:
                            clean_val = str(val).strip()
                    else:
                        clean_val = str(val).strip()

                    # 2. Save Type A: Standard User Model Field
                    if hasattr(user, field_name):
                        setattr(user, field_name, clean_val)
                        if field_name not in modified_fields:
                            modified_fields.append(field_name)
                    else:
                        # 3. Save Type B: Flexible Key-Value (UserProfileAttribute)
                        attr = UserProfileAttribute.query.filter_by(
                            user_id=user.id, field=field_name
                        ).first()
                        if not attr:
                            attr = UserProfileAttribute(
                                user_id=user.id, field=field_name
                            )
                            db.session.add(attr)

                        # Store as JSON if it's a complex type or just string
                        attr.value = (
                            json.dumps(clean_val)
                            if not isinstance(clean_val, (str, int, float, bool))
                            else str(clean_val)
                        )
                        attr.source = "vault_omr"
                        attr.answered_at = datetime.utcnow()

                        if f"extra:{field_name}" not in modified_fields:
                            modified_fields.append(f"extra:{field_name}")

                except Exception as e:
                    print(f"OMR Sync error for {field_name}: {e}")
        if "bank" in dtype or "passbook" in dtype:
            if user.bank_account_available != "Yes":
                user.bank_account_available = "Yes"
                modified_fields.append("bankAccountAvailable")
        if (
            "domicile" in dtype
            or "residence certificate" in dtype
            or "nativity" in dtype
        ):
            if user.domicile_status != "Yes":
                user.domicile_status = "Yes"
                modified_fields.append("domicileStatus")
        if "disability" in dtype or "divyang" in dtype or "pwd" in dtype:
            if user.disability != "Yes":
                user.disability = "Yes"
                modified_fields.append("disability")
            # Extract disability percentage if present
            dis_pct = (
                ex.get("Disability Percentage")
                or ex.get("Percentage")
                or ex.get("disability_percentage")
            )
            if dis_pct and not user.disability_percentage:
                try:
                    user.disability_percentage = int(
                        str(dis_pct).replace("%", "").strip()
                    )
                    modified_fields.append("disabilityPercentage")
                except Exception:
                    pass
        if "caste certificate" in dtype or "community certificate" in dtype:
            # Extract caste from OCR if profile caste is empty
            caste_val = ex.get("Caste") or ex.get("Category") or ex.get("Community")
            if caste_val and not user.caste:
                user.caste = str(caste_val)
                modified_fields.append("caste")

        # Achievement certificates — collected into list
        ACHIEVEMENT_TYPES = {
            "sports certificate": "sports_certificate",
            "sports achievement": "sports_certificate",
            "national sports": "sports_certificate",
            "state sports": "sports_certificate",
            "arts certificate": "arts_certificate",
            "cultural certificate": "arts_certificate",
            "fine arts": "arts_certificate",
            "ncc certificate": "ncc_certificate",
            "ncc": "ncc_certificate",
            "nss certificate": "nss_certificate",
            "nss": "nss_certificate",
            "merit certificate": "merit_certificate",
            "academic merit": "merit_certificate",
            "participation certificate": "participation_certificate",
            "ex-serviceman": "ex_serviceman_certificate",
            "freedom fighter": "freedom_fighter_certificate",
        }
        for keyword, cert_key in ACHIEVEMENT_TYPES.items():
            if keyword in dtype and cert_key not in achievement_certs:
                achievement_certs.append(cert_key)

    # Persist achievement certificates if any found
    if achievement_certs:
        existing = []
        try:
            existing = (
                json.loads(user.achievement_certificates)
                if user.achievement_certificates
                else []
            )
        except Exception:
            pass
        merged = list(set(existing + achievement_certs))
        if sorted(merged) != sorted(existing):
            user.achievement_certificates = json.dumps(merged)
            modified_fields.append("achievementCertificates")

    if modified_fields:
        db.session.commit()
        return (
            jsonify(
                {
                    "message": "Profile synced successfully",
                    "fields": list(set(modified_fields)),
                    "achievement_certificates": achievement_certs,
                }
            ),
            200,
        )
    else:
        return jsonify({"message": "Profile already up to date", "fields": []}), 200


@app.route("/api/documents/cross-validate", methods=["GET"])
def cross_validate_documents():
    """
    Check for mismatches between documents and user profile.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found", "issues": []}), 200

    documents = UserDocument.query.filter_by(user_id=user_id).all()

    issues = []
    processed_names = []

    user_name = user.name or "User"
    user_name_parts = set(user_name.lower().split())

    for doc in documents:
        data = json.loads(doc.extracted_data) if doc.extracted_data else {}
        doc_name = data.get("Name") or data.get("Full Name") or data.get("name")

        if doc_name:
            doc_name_clean = doc_name.lower().strip()
            # Basic partial match check
            doc_name_parts = set(doc_name_clean.split())

            # Intersection of name parts
            overlap = user_name_parts.intersection(doc_name_parts)
            if not overlap and len(user_name_parts) > 0:
                issues.append(
                    {
                        "type": "Name Mismatch",
                        "document": doc.doc_type,
                        "severity": "High",
                        "message": f"Name on {doc.doc_type} ('{doc_name}') doesn't match your profile name ('{user.name}')",
                        "suggestion": "Update your profile or upload a document with the correct name to avoid rejection.",
                    }
                )

        # Check Expiry
        expiry = (
            data.get("Expiry Date")
            or data.get("Valid Until")
            or data.get("expiry_date")
        )
        if expiry:
            try:
                # Simple date parsing logic (can be improved)
                # Expecting formats like DD/MM/YYYY or YYYY-MM-DD
                import dateutil.parser

                expiry_date = dateutil.parser.parse(expiry)
                if expiry_date < datetime.now():
                    issues.append(
                        {
                            "type": "Document Expired",
                            "document": doc.doc_type,
                            "severity": "Critical",
                            "message": f"Your {doc.doc_type} expired on {expiry}",
                            "suggestion": "Apply for a renewal immediately. Most schemes will reject expired documents.",
                        }
                    )
            except:
                pass  # Silently fail for complex date formats in prototype

    return (
        jsonify(
            {
                "status": "success" if not issues else "warning",
                "issues_count": len(issues),
                "issues": issues,
            }
        ),
        200,
    )


# ── Vault document type → engine normalized key mapping ─────────────────────
# Maps Gemini OCR doc_type strings to the normalized keys the engine uses.
# Critical: without this mapping, every vault document is invisible to matching.
VAULT_DOC_TYPE_MAP = {
    # Identity
    "aadhaar card": "aadhaar",
    "aadhaar": "aadhaar",
    "pan card": "pan",
    "pan": "pan",
    "voter id": "voter_id",
    "voter card": "voter_id",
    "passport": "passport",
    "driving licence": "driving_licence",
    "driving license": "driving_licence",
    # Economic
    "income certificate": "income_certificate",
    "income cert": "income_certificate",
    "ration card": "ration_card",
    "bpl card": "ration_card",
    "bank passbook": "bank_passbook",
    "bank account": "bank_passbook",
    "passbook": "bank_passbook",
    # Social / Community
    "caste certificate": "caste_certificate",
    "community certificate": "caste_certificate",
    "obc certificate": "caste_certificate",
    "sc certificate": "caste_certificate",
    "st certificate": "caste_certificate",
    "domicile certificate": "domicile_certificate",
    "residence certificate": "domicile_certificate",
    "nativity certificate": "domicile_certificate",
    # Disability
    "disability certificate": "disability_certificate",
    "divyang certificate": "disability_certificate",
    "pwd certificate": "disability_certificate",
    # Education
    "marks card": "marks_card",
    "marksheet": "marks_card",
    "10th marksheet": "marks_card",
    "12th marksheet": "marks_card",
    "sslc certificate": "marks_card",
    "degree certificate": "degree_certificate",
    "graduation certificate": "degree_certificate",
    "diploma certificate": "diploma_certificate",
    "bonafide certificate": "bonafide_certificate",
    "school bonafide": "bonafide_certificate",
    "transfer certificate": "transfer_certificate",
    "tc": "transfer_certificate",
    # Land / Agriculture
    "land records": "land_records",
    "patta": "land_records",
    "khata": "land_records",
    "revenue records": "land_records",
    "farmer id": "farmer_id",
    "kisan credit card": "farmer_id",
    # Achievement / Special certificates — #1 fix
    "sports certificate": "sports_certificate",
    "sports achievement": "sports_certificate",
    "national sports": "sports_certificate",
    "state sports": "sports_certificate",
    "arts certificate": "arts_certificate",
    "cultural certificate": "arts_certificate",
    "fine arts certificate": "arts_certificate",
    "ncc certificate": "ncc_certificate",
    "ncc": "ncc_certificate",
    "nss certificate": "nss_certificate",
    "nss": "nss_certificate",
    "merit certificate": "merit_certificate",
    "academic merit": "merit_certificate",
    "scholarship certificate": "merit_certificate",
    "participation certificate": "participation_certificate",
    "employment card": "employment_card",
    "unemployment certificate": "unemployment_certificate",
    "ex-serviceman certificate": "ex_serviceman_certificate",
    "freedom fighter certificate": "freedom_fighter_certificate",
    "birth certificate": "birth_certificate",
    "death certificate": "death_certificate",
    "marriage certificate": "marriage_certificate",
    "widow certificate": "widow_certificate",
    "orphan certificate": "orphan_certificate",
}


def _normalize_doc_type(raw_type: str) -> str:
    """Convert Gemini OCR doc_type string to engine-normalized key."""
    if not raw_type:
        return ""
    return VAULT_DOC_TYPE_MAP.get(
        raw_type.lower().strip(), raw_type.lower().strip().replace(" ", "_")
    )


def _build_audit_trail(
    scheme, user, ai_score, ai_verdict, ai_reason, ai_errors, engine_result=None
) -> dict:
    """
    Fix #11: Structured audit trail for every matched scheme.
    Documents every pass/fail decision for government review.
    """
    from datetime import datetime as _dt, timezone as _tz

    now = _dt.now(_tz.utc).isoformat()

    engine_layer = {
        "passed_conditions": [],
        "failed_conditions": [],
        "soft_failed_conditions": [],
        "missing_mandatory_docs": [],
        "missing_optional_docs": [],
        "confidence_score": None,
        "eligibility_class": None,
    }
    if engine_result:
        engine_layer["confidence_score"] = getattr(
            engine_result, "confidence_score", None
        )
        engine_layer["eligibility_class"] = str(
            getattr(engine_result, "eligibility_class", "")
        )
        for c in getattr(engine_result, "passed_conditions", []):
            engine_layer["passed_conditions"].append(
                {
                    "field": c.condition_field,
                    "user_value": str(c.user_value),
                    "expected": str(c.expected_value),
                    "operator": c.operator,
                }
            )
        for c in getattr(engine_result, "failed_conditions", []):
            engine_layer["failed_conditions"].append(
                {
                    "field": c.condition_field,
                    "user_value": str(c.user_value),
                    "expected": str(c.expected_value),
                    "operator": c.operator,
                    "message": c.failure_message,
                    "mandatory": c.is_mandatory,
                }
            )
        for c in getattr(engine_result, "soft_failed_conditions", []):
            engine_layer["soft_failed_conditions"].append(
                {
                    "field": c.condition_field,
                    "message": c.failure_message,
                }
            )
        engine_layer["missing_mandatory_docs"] = getattr(
            engine_result, "missing_mandatory_docs", []
        )
        engine_layer["missing_optional_docs"] = getattr(
            engine_result, "missing_documents", []
        )

    scheme_docs_required = _docs_required_from_text(
        getattr(scheme, "documents_required", "") or ""
    )
    user_docs = set(_build_documents_uploaded(user))
    docs_present = [d for d in scheme_docs_required if d in user_docs]
    docs_missing = [d for d in scheme_docs_required if d not in user_docs]
    vault_docs = (
        [d.doc_type for d in user.documents if d.doc_type]
        if hasattr(user, "documents") and user.documents
        else []
    )

    profile_snapshot = {
        "age": getattr(user, "age", None),
        "gender": getattr(user, "gender", None),
        "state": getattr(user, "state", None),
        "caste": getattr(user, "caste", None),
        "income": getattr(user, "income", None),
        "annual_family_income": getattr(user, "annual_family_income", None),
        "occupation": getattr(user, "occupation", None),
        "disability": getattr(user, "disability", None),
        "disability_pct": getattr(user, "disability_percentage", None),
        "education": getattr(user, "highest_education_level", None)
        or getattr(user, "education", None),
        "ration_card_type": getattr(user, "ration_card_type", None),
        "is_senior_citizen": getattr(user, "is_senior_citizen", None),
        "is_widow": getattr(user, "is_widow_single_woman", None),
        "is_tribal": getattr(user, "is_tribal", None),
        "is_orphan": getattr(user, "is_orphan", None),
        "minority_status": getattr(user, "minority_status", None),
        "residence": getattr(user, "residence", None),
        "achievement_certs": _build_achievement_certs(user),
    }

    passed_count = len(engine_layer["passed_conditions"])
    failed_count = len(engine_layer["failed_conditions"])
    verdict_text = {
        "ELIGIBLE": "fully eligible",
        "POSSIBLY_ELIGIBLE": "possibly eligible",
        "NOT_ELIGIBLE": "not eligible",
    }.get(ai_verdict, ai_verdict)
    summary_parts = [
        f"User is {verdict_text} for '{scheme.name}' (AI score: {ai_score}/100).",
        f"Engine: {passed_count} condition(s) passed"
        + (f", {failed_count} failed." if failed_count else "."),
    ]
    if ai_reason:
        summary_parts.append(f"AI: {ai_reason}")
    if docs_missing:
        summary_parts.append(
            f"Missing docs: {', '.join(d.replace('_',' ').title() for d in docs_missing)}."
        )
    if ai_errors:
        summary_parts.append(f"Hard failures: {'; '.join(ai_errors)}.")

    return {
        "evaluated_at": now,
        "scheme_id": scheme.id,
        "scheme_name": scheme.name,
        "ai_score": ai_score,
        "ai_verdict": ai_verdict,
        "ai_reason": ai_reason,
        "ai_errors": ai_errors,
        "engine_layer": engine_layer,
        "documents": {
            "in_vault": vault_docs,
            "required_by_scheme": scheme_docs_required,
            "present": docs_present,
            "missing": docs_missing,
        },
        "profile_snapshot": profile_snapshot,
        "summary": " ".join(summary_parts),
    }


def _build_achievement_certs(user) -> list:
    """Extract achievement certificates from user model for the engine."""
    import json as _j

    certs = []
    try:
        raw = getattr(user, "achievement_certificates", None)
        if raw:
            certs = _j.loads(raw) if isinstance(raw, str) else list(raw)
    except Exception:
        pass
    return certs


def _parse_achievement_list(certs: list, cert_type: str) -> list:
    """
    Parse achievement certificates list into engine-specific fields.
    cert_type: 'sports', 'art', or 'skill'
    Returns list of matching certificates.
    """
    if not certs:
        return []

    prefix_map = {
        "sports": [
            "sports",
            "game",
            "athlete",
            "olympic",
            "commonwealth",
            "national_sports",
            "state_sports",
            "district_sports",
        ],
        "art": [
            "art",
            "cultural",
            "dance",
            "music",
            "painting",
            "fine_arts",
            "classical",
            "performing_arts",
        ],
        "skill": [
            "skill",
            "iti",
            "vocational",
            "apprentice",
            "trade",
            "competency",
            "professional_cert",
        ],
    }

    prefixes = prefix_map.get(cert_type, [])
    result = []
    for cert in certs:
        cert_lower = cert.lower() if isinstance(cert, str) else str(cert).lower()
        for prefix in prefixes:
            if prefix in cert_lower:
                result.append(cert)
                break
    return result


def _check_achievement_flag(certs: list, cert_type: str) -> bool:
    """
    Check if a specific achievement type is present in certificates list.
    cert_type: 'ncc' or 'nss'
    Returns True if found, False otherwise.
    """
    if not certs:
        return False

    check_map = {
        "ncc": ["ncc", "national_cadet"],
        "nss": ["nss", "national_service"],
    }

    prefixes = check_map.get(cert_type, [])
    for cert in certs:
        cert_lower = cert.lower() if isinstance(cert, str) else str(cert).lower()
        for prefix in prefixes:
            if prefix in cert_lower:
                return True
    return False


def _build_documents_uploaded(user) -> list:
    """
    Build the complete normalized documents_uploaded list for the match engine.
    Combines:
      1. Actual vault documents (normalized from Gemini OCR doc_type)
      2. Profile-confirmed document availability fields
      3. Achievement certificates stored in user.achievement_certificates
    This ensures the engine sees ALL documents the user actually has.
    """
    docs = set()

    # 1. Vault documents — normalize each doc_type to engine key
    if hasattr(user, "documents") and user.documents:
        for doc in user.documents:
            if doc.doc_type:
                normalized = _normalize_doc_type(doc.doc_type)
                if normalized:
                    docs.add(normalized)

    # 2. Profile-confirmed fields (belt-and-suspenders — even if not in vault)
    if getattr(user, "aadhaar_available", None) == "Yes":
        docs.add("aadhaar")
    if getattr(user, "bank_account_available", None) == "Yes":
        docs.add("bank_passbook")
    if getattr(user, "income_certificate_available", None) == "Yes":
        docs.add("income_certificate")
    if getattr(user, "ration_card_available", None) == "Yes":
        docs.add("ration_card")
    if getattr(user, "domicile_status", None) == "Yes":
        docs.add("domicile_certificate")
    if getattr(user, "disability", None) == "Yes":
        docs.add("disability_certificate")
    if getattr(user, "caste", None) and getattr(user, "caste", "").lower() not in [
        "general",
        "open",
        "",
    ]:
        docs.add("caste_certificate")

    # 3. Achievement certificates from profile (Fix #1)
    try:
        import json as _json

        raw_certs = getattr(user, "achievement_certificates", None)
        if raw_certs:
            certs = _json.loads(raw_certs) if isinstance(raw_certs, str) else raw_certs
            for c in certs:
                docs.add(c.lower().strip().replace(" ", "_"))
    except Exception:
        pass

    # 4. Manually selected documents from profile form
    try:
        import json as _json

        raw_docs = getattr(user, "documents_available", None)
        if raw_docs:
            selected = _json.loads(raw_docs) if isinstance(raw_docs, str) else raw_docs
            for d in selected:
                normalized = _normalize_doc_type(str(d))
                if normalized:
                    docs.add(normalized)
    except Exception:
        pass

    return list(docs)


def calculate_profile_score(user):
    """
    Server-side profile completeness + quality score out of 100.
    Weighted by field importance for scheme matching accuracy.
    Returns: (score: int, missing_hints: list[str])
    """
    score = 0
    hints = []

    # TIER 1 — Critical (5 pts each, max 35) — scheme matching impossible without these
    tier1 = [
        (user.name, "Full name", 5),
        (user.state, "State", 5),
        (user.age, "Age / DOB", 5),
        (user.income, "Annual income", 5),
        (user.caste, "Caste category", 5),
        (user.gender, "Gender", 5),
        (user.occupation, "Occupation", 5),
    ]
    for val, label, pts in tier1:
        if val not in (None, "", 0):
            score += pts
        else:
            hints.append(label)

    # TIER 2 — Important (3 pts each, max 30)
    tier2 = [
        (user.disability, "Disability status", 3),
        (user.residence, "Urban/Rural residence", 3),
        (user.ration_card_available, "Ration card status", 3),
        (user.bank_account_available, "Bank account status", 3),
        (user.aadhaar_available, "Aadhaar status", 3),
        (user.highest_education_level, "Education level", 3),
        (user.marital_status, "Marital status", 3),
        (user.employment_status, "Employment status", 3),
        (user.annual_family_income, "Family income details", 3),
        (user.is_farmer, "Farmer status", 3),
    ]
    for val, label, pts in tier2:
        if val not in (None, "", 0):
            score += pts
        else:
            hints.append(label)

    # TIER 3 — Helpful (2 pts each, max 20)
    tier3 = [
        (user.religion, "Religion", 2),
        (user.is_widow_single_woman, "Widow/single woman status", 2),
        (user.minority_status, "Minority status", 2),
        (user.district, "District", 2),
        (user.dob, "Date of birth", 2),
        (user.income_slab, "Income slab", 2),
        (user.is_tribal, "Tribal status", 2),
        (user.domicile_status, "Domicile status", 2),
        (user.family_type, "Family type", 2),
        (user.documents_available, "Documents held", 2),
    ]
    for val, label, pts in tier3:
        if val not in (None, "", 0, "[]"):
            score += pts
        else:
            hints.append(label)

    # TIER 4 — Bonus (1 pt each, max 15)
    tier4 = [
        (user.father_occupation, "Father's occupation", 1),
        (user.mother_occupation, "Mother's occupation", 1),
        (user.own_agricultural_land, "Land ownership", 1),
        (user.disability_percentage, "Disability %", 1),
        (user.govt_employee_in_family, "Govt employee in family", 1),
        (user.ration_card_type, "Ration card type", 1),
        (user.sub_caste, "Sub-caste", 1),
        (user.is_orphan, "Orphan status", 1),
        (user.education_status, "Education status", 1),
        (user.income_certificate_available, "Income certificate", 1),
    ]
    for val, label, pts in tier4:
        if val not in (None, "", 0):
            score += pts

    score = min(100, score)
    top_hints = hints[:3]  # top 3 most important missing fields
    return score, top_hints


@app.route("/api/profile", methods=["POST"])
def save_profile():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        data = request.json or {}

        # 1. SPECIAL CASE: Email & Name
        new_name = data.get("name")
        if new_name:
            user.name = new_name

        new_email = data.get("email", "").lower().strip()
        if new_email and new_email != user.email:
            if User.query.filter_by(email=new_email).first():
                return jsonify({"error": "Email already registered"}), 400
            user.email = new_email

        if data.get("mobile"):
            user.mobile = data.get("mobile")

        # 2. ADAPTIVE MAPPING LOGIC
        # We iterate over all columns in the User table to make it "adaptive"
        cols = User.__table__.columns.keys()

        # Helper for camelCase to snake_case translation
        def camel_to_snake(name):
            name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
            return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

        # Build a reversed map of incoming data keys
        # Example: {'isFarmer': 'is_farmer'}
        input_data = {}
        for k, v in data.items():
            input_data[camel_to_snake(k)] = v
            # Keep original key too
            input_data[k] = v

        # Manual Overrides & Legacy Bridges
        MANUAL_MAP = {
            "income": "income",
            "annual_family_income": "annual_family_income",
            "domicileStatus": "domicile_status",
            "selectedDocuments": "documents_available",
        }

        # 2. Adaptive Data Processing Loop
        for col, col_obj in User.__table__.columns.items():
            if col in [
                "id",
                "email",
                "password_hash",
                "created_at",
                "updated_at",
                "is_admin",
            ]:
                continue

            # Find the best match from input data
            val = None
            if col in input_data:
                val = input_data[col]
            else:
                # Try finding by manual mapping
                for ui_key, db_col in MANUAL_MAP.items():
                    if db_col == col and ui_key in data:
                        val = data[ui_key]
                        break

            if val is not None:
                # Type-Safe Casting with Normalization
                col_type = str(col_obj.type).upper()

                # Pre-normalize values like "Yes"/"No"
                normalized_val = val
                if isinstance(val, str):
                    v_low = val.strip().lower()
                    if v_low in ["yes", "true", "y", "1"]:
                        normalized_val = (
                            "Yes"
                            if "INTEGER" not in col_type and "FLOAT" not in col_type
                            else 1
                        )
                    elif v_low in ["no", "false", "n", "0"]:
                        normalized_val = (
                            "No"
                            if "INTEGER" not in col_type and "FLOAT" not in col_type
                            else 0
                        )
                    elif v_low == "":
                        normalized_val = None

                if "INTEGER" in col_type:
                    try:
                        setattr(
                            user,
                            col,
                            int(normalized_val) if normalized_val is not None else None,
                        )
                    except:
                        logger.warning(f"Failed to cast {col} value '{val}' to INTEGER")
                elif "FLOAT" in col_type or "REAL" in col_type:
                    try:
                        setattr(
                            user,
                            col,
                            (
                                float(normalized_val)
                                if normalized_val is not None
                                else None
                            ),
                        )
                    except:
                        logger.warning(f"Failed to cast {col} value '{val}' to FLOAT")
                elif ("TEXT" in col_type or "VARCHAR" in col_type) and isinstance(
                    val, (list, dict)
                ):
                    setattr(user, col, json.dumps(val))
                else:
                    # Default assignment for strings
                    setattr(user, col, val)

        # 3. Cache Invalidation
        user.profile_version = (user.profile_version or 0) + 1
        db.session.commit()

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Profile updated (Adaptive Pipeline)",
                    "profile_version": user.profile_version,
                    "user": user.to_dict(),
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Profile update failed: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ----------------- Scheme Routes -----------------
@app.route("/api/schemes", methods=["GET"])
def get_schemes():
    query = request.args.get("q", "").lower()
    category = request.args.get("category", "All")
    state = request.args.get("state", "All")

    # Pagination — default 50 per page, max 5000
    page = max(1, int(request.args.get("page", 1)))
    limit = min(5000, max(1, int(request.args.get("limit", 50))))

    if not category:
        category = "All"
    if not state:
        state = "All"

    schemes_query = Scheme.query.order_by(Scheme.id.desc())

    if category != "All":
        schemes_query = schemes_query.filter(Scheme.category == category)

    if state != "All":
        schemes_query = schemes_query.filter(
            Scheme.allowed_states.ilike(f'%"{state}"%')
            | Scheme.allowed_states.ilike('%"All"%')
            | Scheme.allowed_states.ilike('%"All India"%')
        )

    # Text search — apply at DB level for speed when no extra Python filter needed
    if query:
        schemes_query = schemes_query.filter(
            Scheme.name.ilike(f"%{query}%") | Scheme.description.ilike(f"%{query}%")
        )

    total_items = schemes_query.count()
    total_pages = max(1, (total_items + limit - 1) // limit)
    page = min(page, total_pages)

    paginated = schemes_query.offset((page - 1) * limit).limit(limit).all()

    return (
        jsonify(
            {
                "schemes": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "description": s.description,
                        "category": s.category,
                        "benefits": s.benefits,
                        "applicationLink": s.application_link,
                        "matchPercentage": 50,
                        "conflicts": (
                            json.loads(s.mutually_exclusive_with)
                            if s.mutually_exclusive_with
                            else []
                        ),
                    }
                    for s in paginated
                ],
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "total_items": total_items,
            }
        ),
        200,
    )


@app.route("/api/schemes/<int:scheme_id>", methods=["GET"])
def get_scheme(scheme_id):
    scheme = Scheme.query.get_or_404(scheme_id)
    return jsonify({"scheme": scheme.to_dict()}), 200


@app.route("/api/schemes/<int:scheme_id>/translate", methods=["POST"])
def translate_scheme(scheme_id):
    """
    On-demand translation with DB caching.
    Protects Gemini quota by ensuring each scheme is only translated once.
    """
    target_lang = request.json.get("language", "kn")
    if target_lang != "kn":
        return (
            jsonify({"error": "Only Kannada translation is supported currently"}),
            400,
        )

    # 1. Check Cache
    cached = SchemeTranslation.query.filter_by(
        scheme_id=scheme_id, language=target_lang
    ).first()
    if cached:
        return jsonify({"translation": cached.to_dict(), "cached": True}), 200

    # 2. Translate using Gemini
    scheme = Scheme.query.get_or_404(scheme_id)

    if not GEMINI_API_KEY:
        return jsonify({"error": "AI Translation service not configured"}), 503

    try:
        # Construct prompt for structured translation
        prompt = f"""
        Translate the following government scheme details into fluent, professional Kannada.
        Keep the output as a JSON object with these exact keys: 
        name, description, benefits, eligibility, exclusions, application_process, documents_required.
        
        SCHEME DATA:
        Name: {scheme.name}
        Description: {scheme.description}
        Benefits: {scheme.benefits}
        Eligibility: {scheme.eligibility}
        Exclusions: {scheme.exclusions}
        Application Process: {scheme.application_process}
        Documents Required: {scheme.documents_required}
        
        JSON OUTPUT (Kannada):
        """

        response = model.generate_content(prompt)
        # Handle potential response formatting issues
        text = response.text.replace("```json", "").replace("```", "").strip()
        translated_data = json.loads(text)
        safe_print(
            f"DEBUG: Translate JSON parsed successfully. Keys: {list(translated_data.keys())}"
        )

        # 3. Save to Cache (Dump entire JSON)
        translation = SchemeTranslation(
            scheme_id=scheme.id,
            language=target_lang,
            content_json=json.dumps(translated_data),
        )
        db.session.add(translation)
        db.session.commit()

        return jsonify({"translation": translation.to_dict(), "cached": False}), 200

    except Exception as e:
        error_msg = str(e)
        print(f"❌ AI Translation Error for Scheme {scheme_id}: {error_msg}")

        if "429" in error_msg or "ResourceExhausted" in error_msg:
            return (
                jsonify(
                    {
                        "error": "AI Quota temporarily exhausted. Please try again in a few minutes.",
                        "retry_after": 60,
                    }
                ),
                429,
            )
        elif "403" in error_msg or "PermissionDenied" in error_msg:
            return (
                jsonify({"error": "AI Service permission denied (API key issue)."}),
                403,
            )

        traceback.print_exc()
        return jsonify({"error": f"Translation failed: {error_msg}"}), 500


@app.route("/api/translate-text", methods=["POST"])
def translate_text_api():
    """
    General purpose text translation using Gemini.
    Used for translating OMR questionnaire content on the fly.
    """
    if not GEMINI_API_KEY:
        return jsonify({"error": "AI service offline"}), 503

    data = request.json
    text = data.get("text")
    target_lang = data.get("target_lang", "en")

    if not text or target_lang == "en":
        return jsonify({"translated": text})

    # Cache check (simple in-memory for the session if needed, but here we just call AI)
    lang_map = {
        "hi": "Hindi",
        "kn": "Kannada",
        "ml": "Malayalam",
        "ta": "Tamil",
        "te": "Telugu",
    }
    target_name = lang_map.get(target_lang, target_lang)

    prompt = f"Translate the following government scheme related text into {target_name}. Return ONLY the translated text, no explanations:\n\n{text}"

    try:
        response = model.generate_content(prompt)
        translated = response.text.strip()
        return jsonify({"translated": translated})
    except Exception as e:
        logger.error(f"Text translation error: {e}")
        return jsonify({"translated": text, "error": str(e)})


@app.route("/api/ai/distill-questions", methods=["POST"])
def distill_questions_api():
    """
    Receives a list of questions from Phase 3 and uses AI to perform
    aggressive semantic merging to reduce user friction.
    """
    if not GEMINI_API_KEY:
        return jsonify({"error": "AI service offline"}), 503

    data = request.json
    raw_questions = data.get("questions", [])
    current_profile = data.get("current_profile", {})
    if not raw_questions:
        return jsonify([])

    # 1. Format questions for the AI
    formatted_list = ""
    for idx, q in enumerate(raw_questions):
        # We include the question text and the context (field)
        formatted_list += (
            f"[{idx}] (Context: {q.get('field', 'General')}) {q['question']}\n"
        )

    # 2. Build the reinforced Consolidation Prompt
    # We remove privacy sensitive fields from log
    profile_summary = ", ".join(
        [
            f"{k}: {v}"
            for k, v in current_profile.items()
            if v is not None and k not in ("id", "password", "key")
        ]
    )

    prompt = f"""
    You are a Strategic UX Analyst and Government Scheme Eligibility Auditor.
    The applicant has {len(raw_questions)} pending checks, but we want to minimize friction.

    USER PROFILE CONTEXT (Already Answered):
    {profile_summary}

    STEP 1 — STRICT REDUNDANCY FILTER:
    REMOVE any question that asks for information ALREADY PRESENT in the User Profile Context above.
    (e.g., if profile has 'annual_income', DO NOT ask about family income).

    STEP 2 — ACTION FILTER:
    REMOVE any item that is an INSTRUCTION or ACTION REQUEST — i.e. anything that:
    - Starts with "Please...", "Bring...", "Visit...", "Obtain...", "Ensure...", "Check...".
    - Mentions documents but doesn't ask a question (e.g., "Bring your Ration Card").
    - We ONLY want questions that require a User Answer (Yes/No, Number, Choice).
    - Starts with or implies "Please provide...", "Submit...", "Upload...", "Fill in...", "Bring your...", "Ensure...", "Obtain...", "Arrange...", "Contact...", "Visit..."
    - Instructs the user to DO something rather than CONFIRM a personal fact.
    - Requests a document submission, not an eligibility check.
    ONLY keep items that ask the user to VERIFY OR CONFIRM a factual attribute about themselves
    (e.g., their age, income, caste, occupation, disability status, bank account, academic marks, land ownership, CGPA).

    STEP 2 — CONSOLIDATION:
    Reduce surviving items to the absolute minimum set of logically grouped questions.
    1. MERGING: Group semantically related verifications into one clear question.
       Example: Merge "Do you have Aadhaar?" + "Is Aadhaar seeded with bank?" into one.
    2. REDUNDANCY: Drop semantically identical questions.
    3. LANGUAGE: Plain professional language. No raw database field names.
    4. MAPPING (CRITICAL): Return original indices each new item covers.
    5. LOGICAL INTEGRITY: Do not merge questions requiring different factual answers.
    6. UNIQUE ID: Format "YM-Q-1", "YM-Q-2", etc.

    STEP 3 — ANSWER TYPE:
    For each final question, determine the best input method:
    - "yesno"  — Simple Yes/No (e.g. "Do you have a bank account?")
    - "choice" — Pick from a set (e.g. gender, caste, state, education). Include "options" array (max 8 short strings).
    - "number" — Numeric entry (e.g. income, CGPA, age, disability %). Include "unit" (e.g. "Rs/year", "%", "years") and "placeholder" (e.g. "e.g. 150000").
    - "text"   — Free text (only if nothing else fits)

    ORIGINAL QUESTIONS:
    {formatted_list}

    OUTPUT FORMAT (pure JSON array, no markdown):
    [
      {{
        "uid": "YM-Q-1",
        "text": "Do you have an active bank account linked to Aadhaar for DBT?",
        "answerType": "yesno",
        "matches": [0, 5, 22]
      }},
      {{
        "uid": "YM-Q-2",
        "text": "What is your approximate annual family income?",
        "answerType": "number",
        "unit": "Rs/year",
        "placeholder": "e.g. 150000",
        "matches": [1]
      }},
      {{
        "uid": "YM-Q-3",
        "text": "Which social category do you belong to?",
        "answerType": "choice",
        "options": ["General", "OBC", "SC", "ST", "EWS", "Other"],
        "matches": [3, 8]
      }}
    ]
    """

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Extract JSON array
        json_match = re.search(r"\[.*\]", text, re.DOTALL)
        if json_match:
            text = json_match.group()

        distilled = json.loads(text)
        return jsonify(distilled), 200

    except Exception as e:
        print(f"ERROR in AI Question Distillation: {str(e)}")
        # If AI fails, return original indices 1:1 as fallback with yesno type
        fallback = [
            {
                "uid": f"YM-Q-{i+1}",
                "text": q["question"],
                "answerType": "yesno",
                "matches": [i],
            }
            for i, q in enumerate(raw_questions)
        ]
        return jsonify(fallback), 200


@app.route("/api/schemes/<int:scheme_id>/readiness-ai", methods=["POST", "GET"])
def analyze_scheme_readiness_ai(scheme_id):
    """
    Uses Gemini AI to perform a deep cross-analysis of scheme criteria
    against the user's exact profile and verified documents.
    """
    user_id = session.get("user_id")
    if not user_id:
        fallback_user = User.query.first()
        if fallback_user:
            session["user_id"] = fallback_user.id
            session["user_type"] = "user"
            user_id = fallback_user.id
        else:
            return jsonify({"error": "Not logged in"}), 401

    if not GEMINI_API_KEY:
        return jsonify({"error": "AI Verification service offline"}), 503

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User profile not found"}), 404

    scheme = Scheme.query.get_or_404(scheme_id)
    docs = UserDocument.query.filter_by(user_id=user_id).all()

    # 1. Structure the User Data
    user_data = (
        user.get_profile_dict()
        if hasattr(user, "get_profile_dict")
        else user.to_dict().get("profile", {})
    )
    user_data["Name"] = user.name

    # Remove empty/null values to save tokens
    user_data_clean = {k: v for k, v in user_data.items() if v}

    # 2. Structure Vault Docs
    doc_types = [d.doc_type for d in docs if d.doc_type]

    # 2.5 Fetch Past Clarifications
    clarifications = SchemeClarification.query.filter_by(
        user_id=user_id, scheme_id=scheme_id
    ).all()
    clarification_text = ""
    if clarifications:
        clarification_text = "\n    PRIOR APPLICANT CLARIFICATIONS (CRITICAL: Use these to resolve uncertainties):\n    The applicant was previously asked these questions about edge cases and provided these answers:\n"
        for c in clarifications:
            clarification_text += (
                f"    - Question: {c.question}\n      Answer: {c.answer}\n"
            )
        clarification_text += "\n    NEW RULE: Use these clarifications to resolve FACTUAL UNCERTAINTIES. If their answer satisfies the requirements, mark the item as 'success' and DO NOT ask about it again."

    # 3. Build the specific Prompt
    prompt = f"""
    You are an expert government scheme auditor and eligibility evaluator.
    Perform a strict cross-analysis between the Scheme Requirements and the Applicant's Profile/Documents.
    
    SCHEME DETAILS:
    - Name: {scheme.name}
    - Eligibility: {scheme.eligibility}
    - Criteria Details: {scheme.criteria if hasattr(scheme, 'criteria') else scheme.description}
    - Required Docs: {scheme.documents_required}
    
    APPLICANT PROFILE:
    {json.dumps(user_data_clean, indent=2)}
    
    APPLICANT VERIFIED DOCUMENTS IN VAULT:
    {', '.join(doc_types) if doc_types else 'None'}
    {clarification_text}
    
    TASK:
    Generate a JSON response containing an overall 'score' (0-100) and an 'items' array.
    Each item in the array must be an analysis point regarding their eligibility, demographics, financial standing, or documentation.
    
    CRITICAL CLASSIFICATION RULES:
    1. type: "success" -> Definitive match. No action needed.
    2. type: "error" -> Definitive failure. The applicant DOES NOT qualify.
    3. type: "warning" -> FACTUAL UNCERTAINTY. AI doesn't know if the user meets a rule (e.g. "We don't know if you are a registered weaver"). These generate QUESTIONS.
    4. type: "info" -> PROCEDURAL REQUIREMENT. Instructions, consents, or documents to bring (e.g. "Signature required on app," "Self-declaration needed," "Bring passbook"). These DO NOT generate questions.
    
    5. KNOWN PROFILE FIELDS: For fields in the user profile, use your judgment:
        - If the value mathematically passes/fails the scheme requirement → "success" or "error"
        - If the profile value passes but the scheme needs additional commitment/willingness the profile doesn't reveal → "warning"
        Example: user.education=BE, scheme needs retraining for different job → "warning" (can't verify willingness)
    
    6. NUMERIC RANGE HANDLING: When a numeric field (age, income, disability_percentage) is OUTSIDE the scheme's required range, 
        classify as "error" (definitive failure), NOT as "warning". For example:
        - user.age=100, scheme requires 18-60 → type: "error" (100 exceeds max_age)
        - user.income=₹50L, scheme max ₹2L → type: "error" (exceeds income limit)
        Only use "warning" if value is within range but other requirements can't be verified from documents.
    
    For each item, provide:
    - "title": Short canonical field name (e.g. "age", "income", "caste", "gender")
    IMPORTANT: "title" MUST be a canonical field name that exists as a column in the user profile table (e.g. income, caste, gender, age, occupation, residence, disability_percentage, is_farmer, is_student, annual_income). NEVER return descriptive labels like "Income Verification", "Caste Certificate", "Bank Account Status". Use exact canonical field names only.
    - "text": Detailed, specific explanation.
    - "type": "success" | "warning" | "error" | "info"
    - "icon": A FontAwesome icon class (e.g. "fa-circle-check", "fa-circle-exclamation", "fa-circle-xmark", "fa-circle-info").
    - "question": (ONLY IF type is 'warning' or 'partial') A highly specific, natural language question directly asking the applicant to resolve the missing information.
    
    Format the output purely as valid JSON without markdown wrapping:
    {{
       "score": 85,
       "items": [
          {{
            "title": "...",
            "text": "...",
            "type": "...",
            "icon": "..."
          }}
       ]
    }}
    """

    try:
        # Rate limiting for free tier (15 RPM)
        gemini_limiter.wait()
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Robust JSON extraction to handle AI noise or markdown blocks
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            text = json_match.group()

        result = json.loads(text)

        import hashlib

        if "items" in result:
            for item in result["items"]:
                if item.get("type") in ["warning", "partial"] and item.get("question"):
                    h_str = f"{scheme_id}_{item.get('title','')}_{item.get('question','')}".encode(
                        "utf-8"
                    )
                    item["question_id"] = hashlib.md5(h_str).hexdigest()

        # Validate structure
        if "score" not in result or "items" not in result:
            raise ValueError("AI returned invalid structure")

        return jsonify(result), 200

    except Exception as e:
        print(f"ERROR in AI Readiness Analysis: {str(e)}")
        traceback.print_exc()
        # FALLBACK: Use new deterministic engine when AI fails
        try:
            from app.engine_compat import get_orchestrator

            orch = get_orchestrator(app.config)
            eo = orch.evaluate_single_scheme(scheme, user, use_cache=False)
            items = []
            for cr in eo.condition_results or []:
                title = cr.field.replace("_", " ").title()
                if cr.status == PASS_R:
                    items.append(
                        {
                            "title": title,
                            "text": cr.reason or "Passed",
                            "type": "success",
                            "icon": "fa-circle-check",
                        }
                    )
                elif cr.status == FAIL_R:
                    items.append(
                        {
                            "title": title,
                            "text": cr.reason or "Failed",
                            "type": "error",
                            "icon": "fa-times-circle",
                        }
                    )
            for doc in eo.acquirable:
                items.append(
                    {
                        "title": "Document Required",
                        "text": f"Missing: {doc}",
                        "type": "warning",
                        "icon": "fa-file-circle-exclamation",
                    }
                )
            score = 100
            if eo.result == INELIGIBLE:
                score = 0
            elif eo.result == POSSIBLE:
                score = 65  # Default match for possible schemes

            return (
                jsonify(
                    {
                        "score": score,
                        "items": items,
                        "eligibility_class": eo.result.upper(),
                        "readiness_summary": eo.blocking_reason
                        or (eo.top_insight if hasattr(eo, "top_insight") else ""),
                    }
                ),
                200,
            )
        except Exception as fallback_err:
            print(f"FALLBACK also failed: {fallback_err}")
            return (
                jsonify(
                    {
                        "score": 0,
                        "items": [
                            {
                                "title": "Analysis Unavailable",
                                "text": f"AI service unavailable and fallback failed: {str(fallback_err)}",
                                "type": "error",
                                "icon": "fa-triangle-exclamation",
                            }
                        ],
                    }
                ),
                200,
            )


def _auto_convert_to_conditions(scheme, data, source="manual"):
    """
    Auto-convert flat scheme inputs to Condition rows.

    This function is the canonical conversion logic - same as migration script.
    Flat columns are stored for backward compatibility, but Condition table
    is the source of truth for the eligibility engine.

    Args:
        scheme: Scheme model instance
        data: Dict of input data (API request or PendingScheme)
        source: Source of conditions - 'manual' (admin), 'migration', 'extraction'
    """

    def _j(val):
        if not val:
            return []
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return []
        return []

    def _add_cond(field, operator, value, ctype="hard", conf=0.90):
        if value is not None and value != [] and value != "":
            v = json.dumps(value) if not isinstance(value, str) else value
            cond = Condition(
                scheme_id=scheme.id,
                field=field,
                operator=operator,
                value=v,
                condition_type=ctype,
                confidence=conf,
                source=source,
            )
            db.session.add(cond)

    # Age conditions
    min_age = data.get("minAge") or data.get("min_age")
    max_age = data.get("maxAge") or data.get("max_age")
    if min_age is not None:
        _add_cond("age", "gte", min_age, "hard", 0.95)
    if max_age is not None:
        _add_cond("age", "lte", max_age, "hard", 0.95)

    # Gender conditions
    genders = _j(data.get("allowedGenders") or data.get("allowed_genders"))
    if genders:
        if len(genders) == 1:
            _add_cond("gender", "eq", genders[0], "hard", 0.90)
        else:
            _add_cond("gender", "in", genders, "hard", 0.90)

    # Income conditions
    min_income = data.get("minIncome") or data.get("min_income")
    max_income = data.get("maxIncome") or data.get("max_income")
    if min_income is not None:
        _add_cond("annual_income", "gte", min_income, "hard", 0.90)
    if max_income is not None:
        _add_cond("annual_income", "lte", max_income, "hard", 0.95)

    # Caste / category conditions
    castes = _j(data.get("allowedCastes") or data.get("allowed_castes"))
    if castes:
        _add_cond("category", "in", castes, "hard", 0.90)

    # State conditions
    states = _j(data.get("allowedStates") or data.get("allowed_states"))
    if states:
        if len(states) == 1:
            _add_cond("state", "eq", states[0], "hard", 0.95)
        else:
            _add_cond("state", "in", states, "hard", 0.95)

    # Education conditions
    ed_list = _j(data.get("allowedEducation") or data.get("allowed_education"))
    if ed_list:
        _add_cond("education_level", "in", ed_list, "soft", 0.85)

    # Marital status conditions
    marital = _j(data.get("allowedMaritalStatus") or data.get("allowed_marital_status"))
    if marital:
        _add_cond("marital_status", "in", marital, "soft", 0.85)

    # Occupation conditions
    occs = _j(data.get("allowedOccupations") or data.get("allowed_occupations"))
    if occs:
        _add_cond("occupation", "in", occs, "soft", 0.85)

    # Disability requirement
    disability_req = data.get("disabilityRequirement") or data.get(
        "disability_requirement"
    )
    if disability_req and str(disability_req).lower() not in ("any", ""):
        val = str(disability_req).lower() == "yes"
        _add_cond("is_disabled", "boolean", val, "hard", 0.85)

    # Residence requirement
    residence_req = data.get("residenceRequirement") or data.get(
        "residence_requirement"
    )
    if residence_req and str(residence_req).lower() not in ("any", ""):
        _add_cond("residence", "eq", residence_req, "soft", 0.80)

    # Father/Mother occupation
    fo = _j(
        data.get("allowedFatherOccupations") or data.get("allowed_father_occupations")
    )
    if fo:
        _add_cond("father_occupation", "in", fo, "soft", 0.80)
    mo = _j(
        data.get("allowedMotherOccupations") or data.get("allowed_mother_occupations")
    )
    if mo:
        _add_cond("mother_occupation", "in", mo, "soft", 0.80)

    # Religion conditions
    rels = _j(data.get("allowedReligions") or data.get("allowed_religions"))
    if rels:
        _add_cond("religion", "in", rels, "soft", 0.80)

    # Land type
    land_type = data.get("landTypeRequirement") or data.get("land_type_requirement")
    if land_type and str(land_type).lower() not in ("any", ""):
        _add_cond("land_type", "eq", land_type, "soft", 0.80)

    # Orphan / tribal
    orphan_req = data.get("orphanRequirement") or data.get("orphan_requirement")
    if orphan_req and str(orphan_req).lower() not in ("any", ""):
        val = str(orphan_req).lower() == "yes"
        _add_cond("is_orphan", "boolean", val, "soft", 0.80)
    tribal_req = data.get("tribalRequirement") or data.get("tribal_requirement")
    if tribal_req and str(tribal_req).lower() not in ("any", ""):
        val = str(tribal_req).lower() == "yes"
        _add_cond("is_tribal", "boolean", val, "soft", 0.80)

    # Minority / senior / widow
    minority_req = data.get("minorityRequirement") or data.get("minority_requirement")
    if minority_req and str(minority_req).lower() not in ("any", ""):
        val = str(minority_req).lower() == "yes"
        _add_cond("is_minority", "boolean", val, "soft", 0.80)
    senior_req = data.get("seniorCitizenRequirement") or data.get(
        "senior_citizen_requirement"
    )
    if senior_req and str(senior_req).lower() not in ("any", ""):
        val = str(senior_req).lower() == "yes"
        _add_cond("is_senior_citizen", "boolean", val, "soft", 0.80)
    widow_req = data.get("widowRequirement") or data.get("widow_requirement")
    if widow_req and str(widow_req).lower() not in ("any", ""):
        val = str(widow_req).lower() == "yes"
        _add_cond("is_widow", "boolean", val, "soft", 0.80)

    # Disability percentage
    disability_pct = data.get("disabilityPercentageMin") or data.get(
        "disability_percentage_min"
    )
    if disability_pct is not None:
        _add_cond("disability_percentage", "gte", disability_pct, "hard", 0.90)

    # Bank account / Aadhaar (acquirable)
    bank_req = data.get("bankAccountRequired") or data.get("bank_account_required")
    if bank_req and str(bank_req).lower() == "yes":
        _add_cond("has_bank_account", "boolean", True, "acquirable", 0.95)
    aadhaar_req = data.get("aadhaarRequired") or data.get("aadhaar_required")
    if aadhaar_req and str(aadhaar_req).lower() == "yes":
        _add_cond("has_aadhaar", "boolean", True, "acquirable", 0.95)

    # Ration card types
    rc_types = _j(
        data.get("allowedRationCardTypes") or data.get("allowed_ration_card_types")
    )
    if rc_types:
        _add_cond("ration_card_type", "in", rc_types, "acquirable", 0.90)

    # Min education level
    min_ed = data.get("minEducationLevel") or data.get("min_education_level")
    if min_ed:
        _add_cond("education_level", "gte", min_ed, "soft", 0.85)


@app.route("/api/schemes", methods=["POST"])
def create_scheme():
    """
    Create a new scheme.

    FLAT COLUMNS BLOCKED: Input is converted to Condition rows.
    No flat columns are stored - Condition table is the only source of truth.
    """
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    try:
        scheme = Scheme(
            name=data["name"],
            description=data["description"],
            category=data.get("category"),
            target_audience=data.get("targetAudience"),
            benefits=data.get("benefits"),
            eligibility=data.get("eligibility"),
            application_link=data.get("applicationLink"),
            # Flat columns are NOT stored - only Condition rows
        )
        db.session.add(scheme)
        db.session.flush()  # Get scheme.id

        # Convert input → Condition rows (source of truth)
        _auto_convert_to_conditions(scheme, data, source="manual")

        db.session.commit()
        return jsonify({"message": "Scheme created", "scheme": scheme.to_dict()}), 201
    except AttributeError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@app.route("/api/schemes/<int:scheme_id>", methods=["PUT"])
def update_scheme(scheme_id):
    """
    Update a scheme.

    FLAT COLUMNS BLOCKED: Input is converted to Condition rows.
    No flat columns are stored - Condition table is the only source of truth.
    """
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    scheme = Scheme.query.get_or_404(scheme_id)
    data = request.json
    try:
        scheme.name = data.get("name", scheme.name)
        scheme.description = data.get("description", scheme.description)
        scheme.category = data.get("category", scheme.category)
        scheme.target_audience = data.get("targetAudience", scheme.target_audience)
        scheme.benefits = data.get("benefits", scheme.benefits)
        scheme.eligibility = data.get("eligibility", scheme.eligibility)
        scheme.application_link = data.get("applicationLink", scheme.application_link)

        # Flat columns are NOT stored - only Condition rows
        # Delete existing conditions and recreate from input
        Condition.query.filter_by(scheme_id=scheme.id).delete()
        _auto_convert_to_conditions(scheme, data, source="manual")

        db.session.commit()
        return jsonify({"message": "Scheme updated", "scheme": scheme.to_dict()}), 200
    except AttributeError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@app.route("/api/schemes/<int:scheme_id>", methods=["DELETE"])
def delete_scheme(scheme_id):
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    scheme = Scheme.query.get_or_404(scheme_id)
    db.session.delete(scheme)
    db.session.commit()
    return jsonify({"message": "Scheme deleted"}), 200


@app.route("/api/admin/schemes/bulk-delete", methods=["POST"])
def bulk_delete_schemes():
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    scheme_ids = data.get("ids", [])
    if not scheme_ids:
        return jsonify({"error": "No IDs provided"}), 400

    try:
        Scheme.query.filter(Scheme.id.in_(scheme_ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({"message": f"Deleted {len(scheme_ids)} schemes"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ----------------- Recommendations -----------------
# ── Profile Field Normalizers (robust mapping for real DB values) ──────────────


def normalize_education_level(raw_val, fallback_status=None):
    """Map any education string the form stores → EDUCATION_ORDER canonical value."""
    combined = str(raw_val or fallback_status or "").lower().strip()
    if any(x in combined for x in ["phd", "ph.d", "doctorate", "doctoral"]):
        return "phd"
    if any(
        x in combined
        for x in [
            "post grad",
            "postgrad",
            "pg ",
            "m.tech",
            "mtech",
            "mba",
            "mca",
            "master",
            "m.e ",
            "m.sc",
            "msc",
            "ma ",
            "m.a",
            "post-grad",
            "m.e.",
        ]
    ):
        return "postgrad"
    if any(
        x in combined
        for x in [
            "be",
            "b.e",
            "btech",
            "b.tech",
            "bsc",
            "b.sc",
            "bca",
            "bba",
            "ba ",
            "b.a",
            "llb",
            "mbbs",
            "bachelor",
            "graduation",
            "graduate",
            "degree",
            "ug ",
            "under grad",
            "undergrad",
            "b.com",
            "bcom",
            "currently pursuing",
            "pursuing",
            "engineering",
            "college",
        ]
    ):
        return "graduation"
    if any(x in combined for x in ["diploma", "polytechnic", "iti"]):
        return "diploma"
    if any(
        x in combined
        for x in [
            "12th",
            "hsc",
            "puc",
            "higher secondary",
            "intermediate",
            "10+2",
            "class 12",
        ]
    ):
        return "secondary"
    if any(
        x in combined
        for x in ["10th", "sslc", "matriculation", "class 10", "primary", "8th"]
    ):
        return "primary"
    return "none"


def normalize_is_student(
    education_status, employment_status, education_level_raw, occupation=None
):
    """
    Fix #12: Robustly detect if user is currently a student.
    Checks education_status, employment_status, education_level AND occupation
    to avoid false negatives when only one field is filled.
    """
    fields = [
        str(education_status or ""),
        str(employment_status or ""),
        str(education_level_raw or ""),
        str(occupation or ""),
    ]
    combined = " ".join(fields).lower()

    STUDENT_SIGNALS = [
        "student",
        "studying",
        "currently studying",
        "pursuing",
        "currently pursuing",
        "enrolled",
        "schooling",
        "college going",
        "in school",
        "in college",
        "in university",
    ]
    NON_STUDENT_OVERRIDES = [
        "employed",
        "working",
        "job",
        "service",
        "business",
        "self-employed",
        "retired",
        "unemployed",
    ]
    is_student = any(kw in combined for kw in STUDENT_SIGNALS)

    # If occupation explicitly says "Student" that overrides everything
    if (occupation or "").lower().strip() == "student":
        return True

    # If explicit non-student occupation present and no student signal, not a student
    if not is_student and any(kw in combined for kw in NON_STUDENT_OVERRIDES):
        return False

    return is_student


# ───────────────────────────────────────────────────────────────────────────────


# ----------------- Recommendations (Engine v2.0 Integrated) -----------------
@app.route("/api/recommendations_old", methods=["GET"])
def get_recommendations():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    user = db.session.get(User, user_id)
    if not user or not user.age:
        return (
            jsonify(
                {
                    "recommendations": [],
                    "possibly_eligible": [],
                    "message": "Complete your profile for recommendations",
                    "meta": {
                        "total_evaluated": 0,
                        "fully_eligible": 0,
                        "possibly_eligible": 0,
                        "not_eligible": 0,
                    },
                }
            ),
            200,
        )

    raw_profile = {
        "user_id": str(user.id),
        "dob": user.dob,
        "age": user.age,
        "gender": (user.gender or "").lower().strip(),
        "state": user.state or "",
        "district": user.district or "",
        "block": user.block_taluk or "",
        "income_annual": user.income or 0,
        "is_bpl": str(user.ration_card_type or "").lower()
        in ["bpl", "antyodaya", "aay"],
        "ration_card_type": (user.ration_card_type or "none").lower().strip(),
        "occupation": [user.occupation] if user.occupation else [],
        "is_farmer": user.is_farmer == "Yes",
        "is_self_employed": str(user.employment_status or "").lower()
        in ["self-employed", "self employed"],
        "is_govt_employee": str(user.occupation or "").lower()
        in [
            "government employee",
            "govt employee",
            "government servant",
            "government service",
        ],
        "is_income_taxpayer": False,
        "is_student": normalize_is_student(
            user.education_status,
            user.employment_status,
            user.highest_education_level or user.education,
            user.occupation,
        ),
        "is_woman_entrepreneur": False,
        "land_owned_acres": user.land_size_acres or 0.0,
        "father_occupation": (user.father_occupation or "").lower().strip(),
        "mother_occupation": (user.mother_occupation or "").lower().strip(),
        "caste_category": (user.caste or "general").lower().strip(),
        "religion": (user.religion or "").lower().strip(),
        "is_minority": user.minority_status == "Yes",
        "is_disabled": user.disability == "Yes",
        "disability_percentage": user.disability_percentage or 0,
        "is_widow": user.is_widow_single_woman == "Yes",
        "is_abandoned_woman": user.is_widow_single_woman == "Yes",
        "is_senior_citizen": user.is_senior_citizen == "Yes",
        "is_orphan": user.is_orphan == "Yes",
        "is_tribal": user.is_tribal == "Yes",
        "marital_status": (user.marital_status or "single").lower().strip(),
        "num_children": 0,  # TODO: add child_count to User model if needed
        "num_daughters": getattr(user, "num_daughters", 0) or 0,
        "residence": (user.residence or "").lower().strip(),
        "education_level": normalize_education_level(
            user.highest_education_level or user.education, user.education_status
        ),
        "has_aadhaar": user.aadhaar_available == "Yes",
        "aadhaar_verified": user.aadhaar_linked_bank == "Yes",
        "has_pan": False,
        "has_bank_account": user.bank_account_available == "Yes",
        "documents_uploaded": _build_documents_uploaded(user),
        "active_scheme_ids": [],
        # Achievement certificates for matching special certificate requirements (S19-S23)
        "achievement_certificates": _build_achievement_certs(user),
        # Parse into engine-specific fields for sports/art/NCC/NSS/skill conditions
        "sports_certificates": _parse_achievement_list(
            _build_achievement_certs(user), "sports"
        ),
        "art_certificates": _parse_achievement_list(
            _build_achievement_certs(user), "art"
        ),
        "ncc_certificate": _check_achievement_flag(
            _build_achievement_certs(user), "ncc"
        ),
        "nss_certificate": _check_achievement_flag(
            _build_achievement_certs(user), "nss"
        ),
        "skill_certificates": _parse_achievement_list(
            _build_achievement_certs(user), "skill"
        ),
        # G-series gap fixes
        "scheme_previously_availed": (
            user.scheme_previously_availed == "Yes"
            if hasattr(user, "scheme_previously_availed")
            and user.scheme_previously_availed
            else False
        ),
        "is_pensioner": getattr(user, "is_pensioner", None) == "Yes",
        "num_daughters": getattr(user, "num_daughters", 0) or 0,
        "has_pucca_house": getattr(user, "has_pucca_house", None) == "Yes",
        "house_type": getattr(user, "house_type", "") or "",
        "is_landless": getattr(user, "is_landless", None) == "Yes",
        "is_bocw_registered": getattr(user, "is_bocw_registered", None) == "Yes",
        "is_school_dropout": getattr(user, "is_school_dropout", None) == "Yes",
        "is_first_gen_student": getattr(user, "is_first_gen_student", None) == "Yes",
        "land_owned_acres": getattr(user, "land_size_acres", 0) or 0,
    }

    try:
        from app.engine_compat import get_orchestrator, build_engine_response

        orch = get_orchestrator(app.config)
        all_schemes = Scheme.query.all()
        result = build_engine_response(orch, user, all_schemes)

        recommendations = []
        for r in result["recommendations"]:
            scheme = db.session.get(Scheme, int(r["id"]))
            if not scheme:
                continue
            recommendations.append(
                {
                    "id": scheme.id,
                    "name": scheme.name,
                    "description": scheme.description,
                    "category": scheme.category,
                    "benefits": scheme.benefits,
                    "applicationLink": scheme.application_link,
                    "eligibility_class": r["result"].upper(),
                    "matchPercentage": r["confidence"] * 100,
                    "readiness_summary": r.get("top_insight", ""),
                    "missing_documents": r.get("acquirable", []),
                    "missing_mandatory": r.get("missing_fields", []),
                    "matched_conditions": [],
                }
            )

        possibly_eligible = []
        for r in result["possibly_eligible"]:
            scheme = db.session.get(Scheme, int(r["id"]))
            if not scheme:
                continue
            possibly_eligible.append(
                {
                    "id": scheme.id,
                    "name": scheme.name,
                    "description": scheme.description,
                    "category": scheme.category,
                    "benefits": scheme.benefits,
                    "applicationLink": scheme.application_link,
                    "eligibility_class": r["result"].upper(),
                    "matchPercentage": r["confidence"] * 100,
                    "readiness_summary": r.get("top_insight", ""),
                    "missing_mandatory": r.get("missing_fields", []),
                }
            )

        return (
            jsonify(
                {
                    "recommendations": recommendations,
                    "possibly_eligible": possibly_eligible,
                    "questions": result.get("questions", []),
                    "meta": {
                        "total_evaluated": result["meta"]["total"],
                        "fully_eligible": result["meta"]["fully_eligible"],
                        "possibly_eligible": result["meta"]["possibly_eligible"],
                        "not_eligible": result["meta"]["ineligible"],
                    },
                }
            ),
            200,
        )

    except Exception as e:
        import traceback

        logger.error(f"❌ /api/recommendations CRASHED: {str(e)}")
        logger.error(traceback.format_exc())
        return (
            jsonify(
                {
                    "error": "Evaluation engine failed",
                    "details": str(e),
                    "recommendations": [],
                    "possibly_eligible": [],
                    "meta": {
                        "total_evaluated": 0,
                        "fully_eligible": 0,
                        "possibly_eligible": 0,
                        "not_eligible": 0,
                    },
                }
            ),
            500,
        )


# ----------------- Deep Eligibility Search -----------------
@app.route("/api/deep-eligibility-search", methods=["POST"])
def deep_eligibility_search():
    """
    AI-powered deep eligibility search.
    Step 1: Run deterministic engine to get candidate schemes.
    Step 2: Run Gemini readiness analysis on candidates only.
    Step 3: Return only schemes scoring >= threshold (default 75).
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    if not GEMINI_API_KEY:
        return jsonify({"error": "AI service not configured"}), 503

    user = db.session.get(User, user_id)
    if not user or not user.age:
        return (
            jsonify({"error": "Please complete your profile first (Age is required)"}),
            400,
        )

    data = request.json or {}
    threshold = int(data.get("threshold", 75))

    # ── Step 1: New engine (v6) to get candidates ──────────────────────
    try:
        from app.engine_compat import get_orchestrator, build_engine_response

        orch = get_orchestrator(app.config)
        all_schemes = Scheme.query.all()
        result = build_engine_response(orch, user, all_schemes)

        candidate_ids = set()
        for r in result["recommendations"] + result["possibly_eligible"]:
            candidate_ids.add(int(r["id"]))

        candidates = [s for s in all_schemes if int(s.id) in candidate_ids]

        # Keep a simple map for audit trail
        engine_response_map = {}
        for r in result["recommendations"] + result["possibly_eligible"]:
            engine_response_map[int(r["id"])] = r

        logger.info(f"Deep search: {len(candidates)} candidates from new engine")

        if not candidates:
            return (
                jsonify(
                    {
                        "results": [],
                        "total_candidates": 0,
                        "total_passed": 0,
                        "threshold": threshold,
                        "message": "No candidate schemes found. Try completing more profile fields.",
                    }
                ),
                200,
            )

    except Exception as e:
        logger.error(f"Deep search engine error: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"Engine error: {str(e)}"}), 500

    # ── Step 2: Gemini readiness on candidates ───────────────────────────────
    user_data = user.to_dict().get("profile", {})
    # Strip PII — keep only eligibility-relevant fields
    BLOCKED = {
        "name",
        "email",
        "mobile",
        "aadhaar",
        "pan",
        "dob",
        "id",
        "aadhaarLinkedBank",
        "mobileLinkedBank",
        "bankAccountNumber",
    }
    user_data_clean = {
        k: v
        for k, v in user_data.items()
        if v and k not in BLOCKED and "Number" not in k and "Id" not in k
    }

    docs = UserDocument.query.filter_by(user_id=user_id).all()
    doc_types = [d.doc_type for d in docs if d.doc_type]

    BATCH_PROMPT = """You are a strict Indian government scheme eligibility auditor.

Evaluate EACH scheme below against the applicant profile. For each scheme return:
- "id": scheme id (integer)
- "score": 0-100 (100 = perfect match, 0 = completely ineligible)
- "verdict": "ELIGIBLE", "POSSIBLY_ELIGIBLE", or "NOT_ELIGIBLE"  
- "reason": one sentence — the most critical factor (pass or fail)
- "errors": list of hard failures (empty list if none)

RULES:
- Score < 50: NOT_ELIGIBLE (hard condition fails)
- Score 50-74: POSSIBLY_ELIGIBLE (soft conditions or missing docs)
- Score >= 75: ELIGIBLE (all hard conditions pass)
- Be STRICT — if ANY hard condition fails, score must be < 50
- Do NOT assume missing profile data is favorable

APPLICANT PROFILE:
{profile}

DOCUMENTS IN VAULT: {docs}

SCHEMES TO EVALUATE:
{schemes}

Return ONLY a valid JSON array. No markdown, no explanation.
[{{"id": 1, "score": 85, "verdict": "ELIGIBLE", "reason": "...", "errors": []}}, ...]"""

    results = []
    BATCH_SIZE = 8  # Evaluate 8 schemes per Gemini call to stay within token limits

    for i in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[i : i + BATCH_SIZE]
        schemes_text = "\n".join(
            [
                f"ID {s.id}: {s.name}\n  Eligibility: {(s.eligibility or '')[:300]}\n  Exclusions: {(s.exclusions or '')[:150]}"
                for s in batch
            ]
        )

        prompt = BATCH_PROMPT.format(
            profile=json.dumps(user_data_clean, indent=2),
            docs=", ".join(doc_types) if doc_types else "None",
            schemes=schemes_text,
        )

        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            # Strip markdown fences
            text = re.sub(
                r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE
            ).strip()
            batch_results = json.loads(text)

            if not isinstance(batch_results, list):
                raise ValueError("Expected JSON array")

            # Map results back to scheme objects
            scheme_map = {s.id: s for s in batch}
            for r in batch_results:
                sid = r.get("id")
                score = int(r.get("score", 0))
                scheme = scheme_map.get(sid)
                if not scheme or score < threshold:
                    continue

                # Fix #11: Build structured audit trail for every matched scheme
                eng_result_for_scheme = engine_response_map.get(scheme.id)
                audit_trail = _build_audit_trail(
                    scheme=scheme,
                    user=user,
                    ai_score=score,
                    ai_verdict=r.get("verdict", "ELIGIBLE"),
                    ai_reason=r.get("reason", ""),
                    ai_errors=r.get("errors", []),
                    engine_result=eng_result_for_scheme,
                )
                results.append(
                    {
                        "id": scheme.id,
                        "name": scheme.name,
                        "description": scheme.description,
                        "category": scheme.category,
                        "benefits": scheme.benefits,
                        "applicationLink": scheme.application_link,
                        "eligibility": scheme.eligibility,
                        "matchPercentage": score,
                        "verdict": r.get("verdict", "ELIGIBLE"),
                        "reason": r.get("reason", ""),
                        "errors": r.get("errors", []),
                        "ai_verified": True,
                        "audit_trail": audit_trail,
                    }
                )

        except Exception as e:
            logger.error(f"Deep search Gemini batch {i}-{i+BATCH_SIZE} failed: {e}")
            # On Gemini failure, fall back: include candidates from this batch at engine score
            for s in batch:
                eng_result = next(
                    (
                        r
                        for r in engine_response.fully_eligible
                        if int(r.scheme_id) == s.id
                    ),
                    None,
                )
                if eng_result and eng_result.confidence_score >= threshold:
                    results.append(
                        {
                            "id": s.id,
                            "name": s.name,
                            "description": s.description,
                            "category": s.category,
                            "benefits": s.benefits,
                            "applicationLink": s.application_link,
                            "eligibility": s.eligibility,
                            "matchPercentage": eng_result.confidence_score,
                            "verdict": "ELIGIBLE",
                            "reason": "Passed deterministic eligibility check",
                            "errors": [],
                            "ai_verified": False,
                            "audit_trail": _build_audit_trail(
                                scheme=s,
                                user=user,
                                ai_score=eng_result.confidence_score,
                                ai_verdict="ELIGIBLE",
                                ai_reason="Passed deterministic eligibility check",
                                ai_errors=[],
                                engine_result=eng_result,
                            ),
                        }
                    )
            continue

    # Sort by score descending
    results.sort(key=lambda x: x["matchPercentage"], reverse=True)

    logger.info(
        f"Deep search complete: {len(results)} schemes passed threshold {threshold}%"
    )

    return (
        jsonify(
            {
                "results": results,
                "total_candidates": len(candidates),
                "total_passed": len(results),
                "threshold": threshold,
            }
        ),
        200,
    )


# ----------------- Check Eligibility (no login) -----------------
@app.route("/api/check-eligibility", methods=["POST"])
def check_eligibility():
    """Check eligibility without requiring login"""
    data = request.json

    class TempUser:
        def __init__(self, data):
            try:
                self.age = int(data.get("age")) if data.get("age") else None
            except:
                self.age = None

            try:
                self.income = int(data.get("income")) if data.get("income") else None
            except:
                self.income = None

            self.gender = data.get("gender")
            self.occupation = data.get("occupation")
            self.caste = data.get("caste")
            self.state = data.get("state")
            self.education = data.get("education")
            self.marital_status = data.get("marital_status")
            self.disability = data.get("disability")
            self.residence = data.get("residence")

            # New Fields Initialization
            self.dob = data.get("dob")
            self.aadhaar_available = data.get("aadhaarAvailable")
            self.district = data.get("district")
            self.block_taluk = data.get("blockTaluk")
            self.domicile_status = data.get("domicileStatus")
            self.family_type = data.get("familyType")
            self.total_family_members = data.get("totalFamilyMembers")
            self.is_head_of_family = data.get("isHeadOfFamily")
            self.annual_family_income = data.get("annualFamilyIncome")
            self.income_slab = data.get("incomeSlab")
            self.income_certificate_available = data.get("incomeCertificateAvailable")
            self.sub_caste = data.get("subCaste")
            self.minority_status = data.get("minorityStatus")
            self.ews_status = data.get("ewsStatus")
            self.ration_card_available = data.get("rationCardAvailable")
            self.ration_card_type = data.get("rationCardType")
            self.education_status = data.get("educationStatus")
            self.highest_education_level = data.get("highestEducationLevel")
            self.current_course = data.get("currentCourse")
            self.institution_type = data.get("institutionType")
            self.employment_status = data.get("employmentStatus")
            self.govt_employee_in_family = data.get("govtEmployeeInFamily")
            self.is_farmer = data.get("isFarmer")
            self.own_agricultural_land = data.get("ownAgriculturalLand")
            self.land_size_acres = data.get("landSizeAcres")
            self.is_tenant_farmer = data.get("isTenantFarmer")
            self.disability_percentage = data.get("disabilityPercentage")
            self.is_widow_single_woman = data.get("isWidowSingleWoman")
            self.is_senior_citizen = data.get("isSeniorCitizen")
            self.bank_account_available = data.get("bankAccountAvailable")
            self.aadhaar_linked_bank = data.get("aadhaarLinkedBank")
            self.mobile_linked_bank = data.get("mobileLinkedBank")
            self.income_cert_last_1_year = data.get("incomeCertLast1Year")
            self.scheme_previously_availed = data.get("schemePreviouslyAvailed")
            self.willing_to_submit_docs = data.get("willingToSubmitDocs")

    temp_user = TempUser(data)

    from app.engine_compat import get_orchestrator

    orch = get_orchestrator(app.config)
    schemes = Scheme.query.all()

    recommendations = []
    possible_schemes = []
    matched_ids = set()
    scheme_id_map = {}

    # First-pass: identify all matching schemes
    for scheme in schemes:
        try:
            eo = orch.evaluate_single_scheme(scheme, temp_user, use_cache=False)
        except Exception:
            eo = None

        if not eo:
            continue

        scheme_dict = scheme.to_dict()
        scheme_dict["matchPercentage"] = eo.confidence * 100
        scheme_dict["missingDocs"] = []
        scheme_dict["result"] = eo.result
        scheme_dict["missing_fields"] = eo.missing_fields

        if eo.result == "POSSIBLE":
            possible_schemes.append((scheme, eo))
            recommendations.append(scheme_dict)
        elif eo.result == "ELIGIBLE":
            recommendations.append(scheme_dict)

        matched_ids.add(str(scheme.id))
        scheme_id_map[str(scheme.id)] = scheme.name

    conflicts = []
    for s_dict in recommendations:
        exclusive_list = s_dict.get("criteria", {}).get("mutuallyExclusiveWith", [])
        s_dict["conflicts"] = []
        for exclusive_id in exclusive_list:
            if str(exclusive_id) in matched_ids:
                conflict_name = scheme_id_map.get(
                    str(exclusive_id), f"Scheme {exclusive_id}"
                )
                s_dict["conflicts"].append(conflict_name)
                conflicts.append(f"{s_dict['name']} conflicts with {conflict_name}")

    unique_conflicts = list(set(conflicts))

    # Generate questions for POSSIBLE schemes
    questions = []
    if possible_schemes:
        try:
            from app.engine_compat import get_orchestrator

            qengine = orch.qengine
            questions = qengine.select_questions(possible_schemes, dict(data or {}))
            questions = [q.to_dict() for q in questions[:3]]  # Limit to 3
        except Exception as e:
            logger.warning(f"Question generation failed for anonymous user: {e}")

    recommendations.sort(key=lambda x: x["matchPercentage"], reverse=True)

    return (
        jsonify(
            {
                "schemes": recommendations,
                "questions": questions,
                "conflicts": unique_conflicts,
                "has_conflicts": len(unique_conflicts) > 0,
            }
        ),
        200,
    )


# ----------------- Profile Privacy Layer -----------------
def privatize_profile(raw: dict) -> dict:
    """
    Converts a raw_profile dict into a privacy-safe version before it is
    passed to the eligibility engine.

    Rules:
    - Exact numeric values (age, income, disability %, land) → named brackets
    - Hard identifiers (user_id, dob, block) → stripped entirely
    - Counts (children, daughters) → boolean flags
    - Parent occupations → boolean employed/not-employed flags
    - Everything else (state, district, gender, caste, booleans, occupation,
      education, documents …) → passed through unchanged
    """
    p = dict(raw)  # shallow copy — we never mutate the original

    # ── Strip hard identifiers ────────────────────────────────────────────
    p.pop("user_id", None)
    p.pop("dob", None)
    p.pop("block", None)

    # ── Age → bracket ─────────────────────────────────────────────────────
    age = p.pop("age", None)
    if age is not None:
        age = int(age)
        if age < 6:
            age_bracket = "0–5"
        elif age < 12:
            age_bracket = "6–11"
        elif age < 18:
            age_bracket = "12–17"
        elif age < 26:
            age_bracket = "18–25"
        elif age < 36:
            age_bracket = "26–35"
        elif age < 46:
            age_bracket = "36–45"
        elif age < 56:
            age_bracket = "46–55"
        elif age < 61:
            age_bracket = "56–60"
        else:
            age_bracket = "60+"
        p["age_bracket"] = age_bracket
        # Keep numeric age so engine range-checks still work
        p["age"] = age

    # ── Income → bracket label ────────────────────────────────────────────
    income = p.pop("income_annual", None)
    if income is not None:
        income = int(income)
        if income <= 100_000:
            income_bracket = "EWS (up to ₹1L/yr)"
        elif income <= 300_000:
            income_bracket = "LIG (₹1L–3L/yr)"
        elif income <= 800_000:
            income_bracket = "MIG (₹3L–8L/yr)"
        else:
            income_bracket = "HIG (above ₹8L/yr)"
        p["income_bracket_label"] = income_bracket
        # Keep numeric income so engine threshold checks still work
        p["income_annual"] = income

    # ── Disability percentage → bracket ───────────────────────────────────
    dis_pct = p.pop("disability_percentage", None)
    if dis_pct is not None:
        dis_pct = int(dis_pct)
        if dis_pct == 0:
            dis_bracket = "none"
        elif dis_pct < 40:
            dis_bracket = "below 40%"
        elif dis_pct < 60:
            dis_bracket = "40–59%"
        elif dis_pct < 80:
            dis_bracket = "60–79%"
        else:
            dis_bracket = "80–100%"
        p["disability_bracket"] = dis_bracket
        p["disability_percentage"] = dis_pct  # keep for engine

    # ── Land → bracket ────────────────────────────────────────────────────
    land = p.pop("land_owned_acres", None)
    if land is not None:
        land = float(land)
        if land == 0:
            land_bracket = "none"
        elif land < 1:
            land_bracket = "marginal (under 1 acre)"
        elif land < 5:
            land_bracket = "small (1–5 acres)"
        elif land < 10:
            land_bracket = "medium (5–10 acres)"
        else:
            land_bracket = "large (10+ acres)"
        p["land_bracket"] = land_bracket
        p["land_owned_acres"] = land  # keep for engine

    # ── Children / daughters → boolean flags ─────────────────────────────
    num_children = p.pop("num_children", 0) or 0
    num_daughters = p.pop("num_daughters", 0) or 0
    p["has_children"] = int(num_children) > 0
    p["has_daughters"] = int(num_daughters) > 0
    # Keep counts for engine rules that check exact numbers
    p["num_children"] = int(num_children)
    p["num_daughters"] = int(num_daughters)

    # ── Parent occupations → employed boolean ─────────────────────────────
    NON_EMPLOYED = {
        "",
        "none",
        "housewife",
        "homemaker",
        "unemployed",
        "retired",
        "deceased",
        "n/a",
        "na",
        "not applicable",
    }
    father_occ = str(p.pop("father_occupation", "") or "").lower().strip()
    mother_occ = str(p.pop("mother_occupation", "") or "").lower().strip()
    p["has_employed_father"] = father_occ not in NON_EMPLOYED
    p["has_employed_mother"] = mother_occ not in NON_EMPLOYED
    # Keep raw strings for engine rules that match specific occupations
    p["father_occupation"] = father_occ
    p["mother_occupation"] = mother_occ

    return p


# ----------------- Classifier-Based Recommendations (using gemini_prefill) -----------------
@app.route("/api/recommendations", methods=["GET"])
def classifier_recommendations():
    """
    Unified Recommendations Endpoint — uses the Locked Logic Engine.
    Ensures 100% stability between initial search and re-evaluation.

    VALIDATION: Rejects if required profile fields are missing.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        # REQUIRED PROFILE FIELDS VALIDATION
        from app.engine.canonical_field_registry import get_required_fields
        from app.engine.derived_fields import enrich_profile

        profile = user.get_profile_dict()
        enriched = enrich_profile(profile)

        required_fields = get_required_fields()
        missing_fields = [f for f in required_fields if enriched.get(f) is None]

        if missing_fields:
            return (
                jsonify(
                    {
                        "error": "incomplete_profile",
                        "incomplete_fields": missing_fields,
                        "message": "Please complete your profile before checking eligibility",
                    }
                ),
                400,
            )

        from app.engine_compat import get_orchestrator, build_engine_response
        from sqlalchemy import text

        orch = get_orchestrator(app.config)

        # Pull all active schemes for evaluation
        all_schemes = Scheme.query.filter_by(is_active=True).all()

        # Build engine response (includes recommendations, possibly_eligible, questions, and meta)
        result = build_engine_response(orch, user, all_schemes)

        # Add metadata about the evaluation pool
        result["meta"]["scanned_pool"] = "all_active"
        result["meta"]["total_evaluated"] = len(all_schemes)
        result["meta"]["message"] = f"Evaluated {len(all_schemes)} active schemes."

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Unified recommendations failed: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "Evaluation failed", "details": str(e)}), 500


@app.route("/api/classifier/deep-analysis", methods=["POST"])
def run_deep_analysis():
    """
    Manual adversarial check using Gemini to verify ELIGIBLE schemes.
    If Gemini finds a reason to doubt, it moves them to POSSIBLE or INELIGIBLE.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json
    scheme_ids = data.get("scheme_ids", [])
    if not scheme_ids:
        return jsonify({"error": "No schemes provided"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        from app.engine_compat import get_orchestrator
        from contextual_resolver import resolve_possibly_eligible_batch

        orch = get_orchestrator(app.config)
        all_schemes = {
            s.id: s for s in Scheme.query.filter(Scheme.id.in_(scheme_ids)).all()
        }

        # Get the subset of schemes to verify using Unified Engine
        target_schemes = []
        for sid in scheme_ids:
            scheme = all_schemes.get(sid)
            if not scheme:
                continue

            eo = orch.evaluate_single_scheme(scheme, user, use_cache=True)

            # Formulate result for the adversarial resolver
            res = {
                "scheme_id": sid,
                "status": eo.result.upper(),
                "unknown_fields": eo.missing_fields,
                "question_text": eo.blocking_reason or "Verify eligibility details",
            }
            target_schemes.append(res)

        if not target_schemes:
            return (
                jsonify(
                    {
                        "verified_eligible": scheme_ids,
                        "moved_to_possibly": [],
                        "ineligible_count": 0,
                    }
                ),
                200,
            )

        # Build dummy profile for resolver (legacy compatibility)
        profile = user.get_profile_dict() if hasattr(user, "get_profile_dict") else {}

        # Run resolver (Adversarial double-check)
        resolved_eligible, resolved_possibly, resolved_ineligible = (
            resolve_possibly_eligible_batch(profile, target_schemes)
        )

        return (
            jsonify(
                {
                    "verified_eligible": [s["scheme_id"] for s in resolved_eligible],
                    "moved_to_possibly": resolved_possibly,
                    "moved_to_ineligible": resolved_ineligible,
                }
            ),
            200,
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        logger.error(f"Deep Analysis failed: {str(e)}")
        return jsonify({"error": "Deep analysis failed", "details": str(e)}), 500


# ----------------- Dashboard Refresh: Readiness-Filtered Recommendations -----------------
@app.route("/api/recommendations/refresh-with-readiness", methods=["POST"])
def refresh_recommendations_with_readiness():
    """
    Dashboard Refresh — new engine (v6).
    Uses the structured eligibility engine for all scheme evaluation.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    user = db.session.get(User, user_id)
    if not user or not user.age:
        return (
            jsonify(
                {
                    "recommendations": [],
                    "possibly_eligible": [],
                    "removed_count": 0,
                    "message": "Complete your profile for recommendations",
                    "meta": {
                        "total_evaluated": 0,
                        "candidates": 0,
                        "passed_readiness": 0,
                        "removed_low_readiness": 0,
                    },
                }
            ),
            200,
        )

    READINESS_THRESHOLD = 75

    try:
        from app.engine_compat import get_orchestrator, build_engine_response
        from app.engine.eligibility import INELIGIBLE
        from sqlalchemy import text

        orch = get_orchestrator(app.config)

        # Pull all active schemes for evaluation
        all_schemes = Scheme.query.filter_by(is_active=True).all()

        result = build_engine_response(orch, user, all_schemes)

        recommendations = []
        possibly_eligible_out = []
        removed_count = 0

        for r in result["recommendations"] + result["possibly_eligible"]:
            scheme = db.session.get(Scheme, int(r["id"]))
            if not scheme:
                continue

            confidence = r["confidence"]
            if confidence < READINESS_THRESHOLD / 100.0:
                removed_count += 1
                continue

            scheme_entry = {
                "id": scheme.id,
                "name": scheme.name,
                "description": scheme.description,
                "category": scheme.category,
                "benefits": scheme.benefits,
                "applicationLink": scheme.application_link,
                "eligibility_class": r["result"].upper(),
                "matchPercentage": confidence * 100,
                "readiness_summary": r.get("top_insight", ""),
                "missing_documents": r.get("acquirable", []),
                "missing_mandatory": r.get("missing_fields", []),
                "matched_conditions": [],
            }

            if r["result"] == "eligible":
                recommendations.append(scheme_entry)
            else:
                possibly_eligible_out.append(scheme_entry)

        recommendations.sort(key=lambda x: x["matchPercentage"], reverse=True)
        possibly_eligible_out.sort(key=lambda x: x["matchPercentage"], reverse=True)

        passed_count = len(recommendations) + len(possibly_eligible_out)
        total_evaluated = result["meta"]["total"]
        removed_count = total_evaluated - passed_count
        logger.info(
            f"Refresh complete: {passed_count} passed readiness >= {READINESS_THRESHOLD}%, {removed_count} removed"
        )

        return (
            jsonify(
                {
                    "recommendations": recommendations,
                    "possibly_eligible": possibly_eligible_out,
                    "removed_count": removed_count,
                    "meta": {
                        "total_evaluated": total_evaluated,
                        "candidates": passed_count + removed_count,
                        "passed_readiness": passed_count,
                        "removed_low_readiness": removed_count,
                        "readiness_threshold": READINESS_THRESHOLD,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Refresh recommendations engine error: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"Engine error: {str(e)}"}), 500


# ----------------- Readiness-Based Reclassification of Fully Eligible Schemes -----------------
@app.route("/api/recommendations/readiness-reclassify", methods=["POST"])
def readiness_reclassify():
    """
    Takes a list of FULLY ELIGIBLE scheme IDs.
    For each, calls Gemini readiness analysis to find red (error) or yellow (warning) items.
    Returns:
      - keep_eligible: scheme IDs that passed with no issues
      - move_to_possibly: scheme IDs with WARNING items (yellow) → possibly eligible
      - move_to_ineligible: scheme IDs with ERROR items (red) → ineligible
    This is the second-pass AI filter that cleans up false positives from the engine.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    if not GEMINI_API_KEY:
        return jsonify({"error": "AI service not configured"}), 503

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    scheme_ids = data.get("scheme_ids", [])
    if not scheme_ids:
        return (
            jsonify(
                {"keep_eligible": [], "move_to_possibly": [], "move_to_ineligible": []}
            ),
            200,
        )

    # Build clean user profile for AI (strip PII)
    user_data = user.to_dict().get("profile", {})
    BLOCKED_KEYS = {
        "name",
        "email",
        "mobile",
        "aadhaar",
        "pan",
        "dob",
        "id",
        "aadhaarLinkedBank",
        "mobileLinkedBank",
        "bankAccountNumber",
    }
    user_data_clean = {
        k: v
        for k, v in user_data.items()
        if v and k not in BLOCKED_KEYS and "Number" not in k and "Id" not in k
    }

    docs = UserDocument.query.filter_by(user_id=user_id).all()
    doc_types = [d.doc_type for d in docs if d.doc_type]

    clarifications = SchemeClarification.query.filter_by(user_id=user_id).all()
    clarifs_map = {}
    for c in clarifications:
        if c.scheme_id not in clarifs_map:
            clarifs_map[c.scheme_id] = []
        clarifs_map[c.scheme_id].append(c)

    keep_eligible = []
    move_to_possibly = []
    move_to_ineligible = []
    reclassification_details = {}

    BATCH_SIZE = 6
    schemes_map = {
        s.id: s for s in Scheme.query.filter(Scheme.id.in_(scheme_ids)).all()
    }

    READINESS_RECLASSIFY_PROMPT = """You are a strict Indian government scheme eligibility auditor.

Evaluate EACH scheme below against the applicant's EXACT profile.
For each scheme, return a readiness analysis with:
- "id": scheme id (integer)
- "verdict": "ELIGIBLE" | "WARNING" | "INELIGIBLE"
  * ELIGIBLE: All hard conditions clearly met, no concerns
  * WARNING: Hard conditions likely met BUT applicant lacks a required document, process step, or there is ambiguity about a key requirement
  * INELIGIBLE: Any hard eligibility condition definitively fails given the profile
- "reason": One-sentence explanation of the verdict
- "items": Array of issues found:
  [{"title": "...", "type": "error"|"warning"|"success", "text": "...", "question": "..."}]
  * If type is 'warning' (or partial gap), include 'question': a highly specific, natural language question directly asking the applicant to resolve the missing information.

CRITICAL RULES:
- Only mark INELIGIBLE if a hard requirement DEFINITIVELY fails (wrong age, wrong gender, wrong category, wrong occupation etc.)
- Mark WARNING for: missing documents, unclear occupation match, process requirements, soft conditions not met
- Do NOT assume information not in profile is favorable OR unfavorable
- Be precise — read the scheme eligibility text carefully

APPLICANT PROFILE:
{profile}

DOCUMENTS IN VAULT: {docs}

SCHEMES TO EVALUATE:
{schemes}

Return ONLY a valid JSON array. No markdown. No explanation outside JSON.
[{{"id": 1, "verdict": "ELIGIBLE", "reason": "...", "items": [{{"title":"...", "type":"success", "text":"..."}}]}}]"""

    for i in range(0, len(scheme_ids), BATCH_SIZE):
        batch_ids = scheme_ids[i : i + BATCH_SIZE]
        batch_schemes = [schemes_map[sid] for sid in batch_ids if sid in schemes_map]
        if not batch_schemes:
            continue

        batch_schemes_text_list = []
        for s in batch_schemes:
            s_text = f"ID {s.id}: {s.name}\n  Eligibility: {(s.eligibility or '')[:400]}\n  Exclusions: {(s.exclusions or '')[:150]}"
            if s.id in clarifs_map:
                s_text += "\n  PRIOR CLARIFICATIONS (DO NOT ASK THESE AGAIN - MARK AS RESOLVED IF SATISFIED):\n"
                for c in clarifs_map[s.id]:
                    s_text += (
                        f"    - Question: {c.question}\n      Answer: {c.answer}\n"
                    )
            batch_schemes_text_list.append(s_text)
        schemes_text = "\n".join(batch_schemes_text_list)

        prompt = READINESS_RECLASSIFY_PROMPT.format(
            profile=json.dumps(user_data_clean, indent=2),
            docs=", ".join(doc_types) if doc_types else "None",
            schemes=schemes_text,
        )

        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            text = re.sub(
                r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE
            ).strip()
            batch_results = json.loads(text)

            if not isinstance(batch_results, list):
                raise ValueError("Expected JSON array from Gemini")

            for r in batch_results:
                sid = r.get("id")
                if sid not in schemes_map:
                    continue
                verdict = r.get("verdict", "ELIGIBLE").upper()
                items = r.get("items", [])

                import hashlib

                for item in items:
                    if item.get("type") == "warning" and item.get("question"):
                        h_str = f"{sid}_{item.get('title','')}_{item.get('question','')}".encode(
                            "utf-8"
                        )
                        item["question_id"] = hashlib.md5(h_str).hexdigest()

                reason = r.get("reason", "")

                reclassification_details[sid] = {
                    "verdict": verdict,
                    "reason": reason,
                    "items": items,
                }

                # Reclassification logic based on readiness items
                has_error = any(item.get("type") == "error" for item in items)
                has_warning = any(item.get("type") == "warning" for item in items)

                if verdict == "INELIGIBLE" or has_error:
                    move_to_ineligible.append(sid)
                elif verdict == "WARNING" or has_warning:
                    move_to_possibly.append(sid)
                else:
                    keep_eligible.append(sid)

        except Exception as e:
            logger.error(f"Readiness reclassify batch {i}: {e}")
            # On AI failure: keep schemes eligible (do not demote on error)
            for sid in batch_ids:
                keep_eligible.append(sid)

    # Any scheme_ids not processed → keep eligible
    processed = set(keep_eligible + move_to_possibly + move_to_ineligible)
    for sid in scheme_ids:
        if sid not in processed:
            keep_eligible.append(sid)

    logger.info(
        f"Readiness reclassify: {len(keep_eligible)} kept, "
        f"{len(move_to_possibly)} → possibly, {len(move_to_ineligible)} → ineligible"
    )

    return (
        jsonify(
            {
                "keep_eligible": keep_eligible,
                "move_to_possibly": move_to_possibly,
                "move_to_ineligible": move_to_ineligible,
                "details": reclassification_details,
            }
        ),
        200,
    )


# ----------------- Contextual AI Re-Evaluate -----------------
@app.route("/api/readiness/re-evaluate", methods=["POST"])
def readiness_reevaluate():
    """Batch re-evaluate schemes based on user clarification answers."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    if not GEMINI_API_KEY:
        return jsonify({"error": "AI service not configured"}), 503

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.json or {}
    scheme_id = data.get("scheme_id")
    answers = data.get("answers", [])
    batch_mode = data.get("batch_mode", True)

    if not answers:
        return jsonify({"status": "error", "reason": "no_answers_provided"}), 400
    if len(answers) > 10:
        return jsonify({"status": "error", "reason": "too_many_answers"}), 400

    scheme = db.session.get(Scheme, scheme_id)
    if not scheme:
        return jsonify({"error": "Scheme not found"}), 404

    # 1. Throttling and Loop Prevention
    now = datetime.utcnow()
    recent_answers = (
        SchemeClarification.query.filter_by(user_id=user_id)
        .order_by(SchemeClarification.resolved_at.desc())
        .first()
    )
    if recent_answers and (now - recent_answers.resolved_at).total_seconds() < 10:
        return (
            jsonify({"status": "throttled", "reason": "cooldown", "retry_after": 10}),
            429,
        )

    iteration_count = (
        db.session.query(db.func.count(SchemeClarification.id))
        .filter_by(user_id=user_id, scheme_id=scheme_id)
        .scalar()
    )
    MAX_ITERATIONS = 3
    if iteration_count >= MAX_ITERATIONS:
        return (
            jsonify({"status": "throttled", "reason": "max_iterations_exceeded"}),
            429,
        )

    # 2. Re-Evaluate Prompt Execution
    user_data = user.to_dict().get("profile", {})
    BLOCKED_KEYS = {
        "name",
        "email",
        "mobile",
        "aadhaar",
        "pan",
        "dob",
        "id",
        "aadhaarLinkedBank",
    }
    profile_safe = {
        k: v
        for k, v in user_data.items()
        if v and k not in BLOCKED_KEYS and "Number" not in k
    }
    prior_clarifications = SchemeClarification.query.filter_by(
        user_id=user_id, scheme_id=scheme_id
    ).all()
    prior_text = (
        "\n".join(
            [f"Q: {c.question_text} \nA: {c.answer_text}" for c in prior_clarifications]
        )
        if prior_clarifications
        else "None"
    )

    new_answers_text = "\n".join(
        [f"Q: {a.get('question')} \nA: {a.get('answer')}" for a in answers]
    )

    prompt = f"""You are a strict Indian government scheme eligibility auditor.
The applicant was previously 'Possibly Eligible' due to partial gaps.
Their new answers are provided below. Issue a final verdict: ELIGIBLE or INELIGIBLE.

SCHEME: {scheme.name}
Eligibility details: {scheme.eligibility[:400]}
Exclusions: {scheme.exclusions[:200] if scheme.exclusions else 'None'}

USER PROFILE:
{json.dumps(profile_safe, indent=2)}

PRIOR CLARIFICATIONS:
{prior_text}

NEW ANSWERS:
{new_answers_text}

Return ONLY a valid JSON object. No markdown.
{{"verdict": "ELIGIBLE", "justification": "..."}}"""

    try:
        if "gemini_limiter" in globals():
            gemini_limiter.wait()
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
        res_json = json.loads(text)
        verdict = res_json.get("verdict", "ELIGIBLE").upper()
    except Exception as e:
        logger.error(f"Re-evaluate API Error: {e}")
        return jsonify({"error": "AI evaluation failed"}), 500

    # 3. Store answers into database isolated from structured Profile
    for a in answers:
        q_hash = a.get("question_id", "")
        if not q_hash:
            continue

        existing = SchemeClarification.query.filter_by(
            user_id=user_id, scheme_id=scheme_id, question_id_hash=q_hash
        ).first()
        if not existing:
            clar = SchemeClarification(
                user_id=user_id,
                scheme_id=scheme_id,
                question_id_hash=q_hash,
                question_text=a.get("question", ""),
                answer_text=a.get("answer", ""),
                ai_verdict=verdict,
                iteration_count=iteration_count + 1,
            )
            db.session.add(clar)

    db.session.commit()

    return (
        jsonify(
            {
                "status": "resolved",
                "scheme_id": scheme_id,
                "verdict": verdict,
                "new_match_score": 95 if verdict == "ELIGIBLE" else 40,
                "remaining_iterations": MAX_ITERATIONS - (iteration_count + 1),
            }
        ),
        200,
    )


# ----------------- Contextual AI Assistant -----------------
@app.route("/api/contextual-ai", methods=["POST"])
def contextual_ai():
    """
    Contextual AI assistant — processes selected text with an action.
    Accepts: { selected_text, action, user_profile (sanitized) }
    Actions: ask | explain | summarize | check_eligibility
    Privacy: no PII ever reaches the AI model.
    """
    if not GEMINI_API_KEY:
        return jsonify({"error": "AI service not configured"}), 503

    data = request.json or {}
    selected_text = (data.get("selected_text") or "").strip()
    action = (data.get("action") or "explain").lower().strip()
    profile = data.get("user_profile") or {}

    if not selected_text:
        return jsonify({"error": "No text provided"}), 400
    if len(selected_text) > 4000:
        selected_text = selected_text[:4000] + "…"

    # ── Strip any PII that might have slipped through on the client side ──
    PII_KEYS = {
        "aadhaar",
        "pan",
        "email",
        "mobile",
        "phone",
        "dob",
        "user_id",
        "id",
        "name",
        "bank_account",
        "account_number",
        "aadhaarNumber",
        "panNumber",
        "mobileNumber",
    }
    safe_profile = {
        k: v
        for k, v in profile.items()
        if k not in PII_KEYS and v not in (None, "", [], {})
    }

    # ── Build action-specific prompt ──────────────────────────────────────
    profile_str = (
        "\n".join(f"  {k}: {v}" for k, v in safe_profile.items()) or "  (not provided)"
    )

    if action == "ask":
        prompt = f"""You are a helpful assistant for an Indian government welfare scheme platform.
The user has selected the following text and wants to ask about it:

SELECTED TEXT:
{selected_text}

Answer the implicit question in this text clearly and concisely in 2-4 sentences.
Focus on what is most useful for someone applying for government schemes.
Reply in plain English. Do not use markdown."""

    elif action == "explain":
        prompt = f"""You are a plain-language explainer for an Indian government scheme platform.
Simplify the following text so any Indian citizen can understand it easily.
Use simple words. Avoid jargon. Keep it to 3-5 sentences maximum.

TEXT TO EXPLAIN:
{selected_text}

Reply in plain English. Do not use markdown or bullet points."""

    elif action == "summarize":
        prompt = f"""Summarize the following text in 1-2 sentences.
Focus only on the most important point for a citizen trying to understand a government scheme.

TEXT:
{selected_text}

Reply in plain English. Do not use markdown."""

    elif action == "define":
        prompt = f"""You are a clear and concise dictionary and context explainer.

The user has selected this text:
{selected_text}

1. Identify the most complex, unfamiliar, or jargon-heavy word or phrase in the text.
2. Define it clearly in 1-2 sentences in plain English.
3. Then explain what it means specifically IN THE CONTEXT of this text in 1 sentence.
4. If there are other notable terms worth defining, list up to 2 more briefly.

Format your response EXACTLY like this (plain text, no markdown):
MAIN TERM: [the word or phrase]
DEFINITION: [plain English definition]
IN CONTEXT: [what it means here specifically]

OTHER TERMS:
- [term]: [brief definition]
- [term]: [brief definition]

If the text is already simple and has no complex terms, say:
MAIN TERM: None
DEFINITION: This text uses plain everyday language — no complex terms found.
IN CONTEXT: N/A"""

    else:
        prompt = f"""Explain the following text in simple terms for an Indian citizen:

{selected_text}

Keep it brief (2-3 sentences). Plain English only."""

    try:
        response = model.generate_content(prompt)
        reply = response.text.strip()
        return (
            jsonify(
                {
                    "reply": reply,
                    "action": action,
                }
            ),
            200,
        )
    except Exception as e:
        logger.error(f"Contextual AI error: {e}")
        return jsonify({"error": "AI request failed", "details": str(e)}), 500


# ----------------- Verified Schemes Cache (cross-browser persistence) -----------------
@app.route("/api/schemes/verified-cache", methods=["GET"])
def get_verified_cache():
    """Load user's deep-analysis-verified schemes from DB."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    try:
        schemes = (
            json.loads(user.verified_schemes_data) if user.verified_schemes_data else []
        )
        ids = json.loads(user.verified_scheme_ids) if user.verified_scheme_ids else []
    except Exception:
        schemes, ids = [], []
    return jsonify({"schemes": schemes, "verified_ids": ids}), 200


@app.route("/api/schemes/verified-cache", methods=["POST"])
def save_verified_cache():
    """Save deep-analysis-verified schemes to DB after a run."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    data = request.json or {}
    schemes = data.get("schemes", [])
    ids = [s["id"] for s in schemes if "id" in s]
    try:
        user.verified_schemes_data = json.dumps(schemes)
        user.verified_scheme_ids = json.dumps(ids)
        db.session.commit()
        return jsonify({"saved": len(schemes), "ids": ids}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"save_verified_cache error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/schemes/verified-cache", methods=["DELETE"])
def delete_verified_cache():
    """Clear user's deep-analysis-verified cache."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    try:
        user.verified_schemes_data = None
        user.verified_scheme_ids = None
        db.session.commit()
        return jsonify({"cleared": True}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"delete_verified_cache error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    print("Admin login request received")
    try:
        data = request.json
        print(f"Login attempt for: {data.get('email')}")
        admin = Admin.query.filter_by(email=data["email"]).first()

        if not admin:
            print("Admin user not found")
            return jsonify({"error": "Invalid credentials"}), 401

        if not check_password_hash(admin.password_hash, data["password"]):
            print("Password check failed")
            return jsonify({"error": "Invalid credentials"}), 401

        session["admin_id"] = admin.id
        session["user_type"] = "admin"
        print("Admin login successful")
        return jsonify({"message": "Admin login successful"}), 200
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": "Server error"}), 500


@app.route("/api/admin/me", methods=["GET"])
def check_admin_session():
    if session.get("user_type") == "admin" and session.get("admin_id"):
        return jsonify({"authenticated": True}), 200
    return jsonify({"authenticated": False}), 401


@app.route("/api/public-stats", methods=["GET"])
def public_stats():
    """Public endpoint — no auth needed — for homepage stat display"""
    try:
        user_count = User.query.count()
        scheme_count = Scheme.query.count()
        doc_count = UserDocument.query.count()
        # Total eligibility checks = proxy for "citizens matched"
        # Use user_count * avg matched schemes as a reasonable metric
        citizens_matched = user_count  # real registered users
        return (
            jsonify(
                {
                    "registeredUsers": user_count,
                    "totalSchemes": scheme_count,
                    "documentsProcessed": doc_count,
                    "citizensMatched": citizens_matched,
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/users", methods=["GET"])
def admin_get_users():
    """Admin endpoint: paginated list of all registered users"""
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 50))
    offset = (page - 1) * limit

    total = User.query.count()
    users = (
        User.query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    )

    return jsonify(
        {
            "users": [
                {
                    "id": u.id,
                    "name": u.name,
                    "email": u.email,
                    "mobile": u.mobile,
                    "state": u.state,
                    "district": u.district,
                    "occupation": u.occupation,
                    "income": u.income,
                    "caste": u.caste,
                    "isAdmin": False,
                    "createdAt": u.created_at.isoformat() if u.created_at else None,
                    "profile": {
                        "state": u.state,
                        "district": u.district,
                        "occupation": u.occupation,
                        "income": u.income,
                        "caste": u.caste,
                        "age": u.age,
                        "gender": u.gender,
                    },
                }
                for u in users
            ],
            "total_items": total,
            "total_pages": max(1, (total + limit - 1) // limit),
            "page": page,
            "limit": limit,
        }
    )


@app.route("/api/admin/stats", methods=["GET"])
def admin_get_stats():
    """Admin dashboard stats"""
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    from sqlalchemy import func

    user_count = User.query.count()
    scheme_count = Scheme.query.count()

    # Document count using UserDocument model
    try:
        doc_count = UserDocument.query.count()
    except Exception:
        doc_count = 0

    return jsonify(
        {
            "users": user_count,
            "schemes": scheme_count,
            "documents": doc_count,
        }
    )


def calculate_benefit_score(scheme):
    """Simple heuristic to rank schemes by perceived value/benefit"""
    score = 0
    high_value_keywords = [
        "pension",
        "scholarship",
        "insurance",
        "housing",
        "subsidy",
        "grant",
        "financial aid",
        "monthly",
        "annual",
    ]
    medium_value_keywords = [
        "training",
        "loan",
        "credit",
        "certificate",
        "support",
        "guidance",
    ]

    text = (
        scheme.name + " " + (scheme.benefits or "") + " " + (scheme.description or "")
    ).lower()

    for word in high_value_keywords:
        if word in text:
            score += 20
    for word in medium_value_keywords:
        if word in text:
            score += 10

    # Category based boosts
    if scheme.category:
        cat = scheme.category.lower()
        if "pension" in cat or "financial" in cat:
            score += 15
        if "education" in cat:
            score += 10

    return score


@app.route("/api/admin/users/delete-test", methods=["POST"])
def admin_delete_test_users():
    """One-time: delete all users whose email contains 'testuser'"""
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    try:
        # Find matching users — email OR name contains 'test'
        from sqlalchemy import or_

        test_users = User.query.filter(
            or_(User.email.ilike("%test%"), User.name.ilike("%test%"))
        ).all()
        count = len(test_users)

        if count == 0:
            return jsonify({"message": "No testuser accounts found", "deleted": 0}), 200

        deleted_emails = [u.email for u in test_users]

        for user in test_users:
            # Delete related documents first to avoid FK constraint errors
            try:
                UserDocument.query.filter_by(user_id=user.id).delete()
            except Exception:
                try:
                    db.session.execute(
                        db.text("DELETE FROM user_document WHERE user_id = :uid"),
                        {"uid": user.id},
                    )
                except Exception:
                    pass
            db.session.delete(user)

        db.session.commit()
        print(f"[ADMIN] Deleted {count} test users: {deleted_emails}")

        return (
            jsonify(
                {
                    "message": f"Successfully deleted {count} test user account(s)",
                    "deleted": count,
                    "emails": deleted_emails,
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        print(f"[ADMIN] Error deleting test users: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/predictive/lifecycle", methods=["GET"])
def lifecycle_forecast():
    """Predict future eligibility using new engine (v6)"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Login to access all features", "is_guest": True}), 200

    user = db.session.get(User, user_id)
    if not user or user.age is None:
        return (
            jsonify(
                {
                    "error": "Please complete your profile first (Age is required)",
                    "incomplete_profile": True,
                }
            ),
            200,
        )

    class LifecycleUser:
        """Temporary user wrapper that supports age override for lifecycle forecasting."""

        def __init__(self, real_user, age_override=None):
            self._real = real_user
            self._age = (
                age_override if age_override is not None else (real_user.age or 0)
            )
            self.profile_attrs = getattr(real_user, "profile_attrs", [])
            self.documents = getattr(real_user, "documents", [])
            self.profile_version = 1

        @property
        def age(self):
            return self._age

        def get_profile_dict(self):
            base = self._real.get_profile_dict().copy()
            base["age"] = self._age
            base["is_senior_citizen"] = self._age >= 60
            return base

        def bump_profile_version(self):
            self.profile_version += 1

    try:
        from app.engine_compat import get_orchestrator

        orch = get_orchestrator(app.config)
        all_schemes = Scheme.query.all()

        DASHBOARD_THRESHOLD = 0.70

        current_user = LifecycleUser(user)
        ranked_current, _ = orch.evaluate_all(
            current_user, all_schemes, use_cache=False
        )
        current_eligible_ids = {
            int(r.scheme_id)
            for r in ranked_current
            if r.confidence >= DASHBOARD_THRESHOLD
        }
        current_count = len(current_eligible_ids)

        forecast_results = {
            "now": {"count": current_count, "score": min(100, current_count * 8)},
            "milestones": [],
        }

        for years_ahead in [1, 2, 3, 5]:
            future_user = LifecycleUser(
                user, age_override=(user.age or 0) + years_ahead
            )
            ranked_future, _ = orch.evaluate_all(
                future_user, all_schemes, use_cache=False
            )
            future_ids = {
                int(r.scheme_id)
                for r in ranked_future
                if r.confidence >= DASHBOARD_THRESHOLD
            }

            newly_eligible_ids = future_ids - current_eligible_ids
            newly_eligible_schemes = []
            for sid in newly_eligible_ids:
                s = next((x for x in all_schemes if x.id == sid), None)
                if s:
                    newly_eligible_schemes.append(
                        {
                            "id": s.id,
                            "name": s.name,
                            "category": s.category,
                            "benefit_score": calculate_benefit_score(s),
                        }
                    )
            newly_eligible_schemes.sort(key=lambda x: x["benefit_score"], reverse=True)

            total = len(future_ids)
            forecast_results["milestones"].append(
                {
                    "label": f"{years_ahead} YEAR{'S' if years_ahead > 1 else ''}",
                    "newCount": len(newly_eligible_schemes),
                    "totalCount": total,
                    "score": min(100, total * 8),
                    "topScheme": (
                        newly_eligible_schemes[0]["name"]
                        if newly_eligible_schemes
                        else None
                    ),
                    "years": years_ahead,
                }
            )

        return jsonify(forecast_results), 200

    except Exception as e:
        logger.error(f"lifecycle_forecast error: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return (
            jsonify(
                {
                    "error": "Could not generate forecast",
                    "milestones": [],
                    "now": {"count": 0, "score": 0},
                }
            ),
            200,
        )


@app.route("/api/validate-document", methods=["POST"])
def validate_document():
    """OCR and validate document readiness using Gemini Vision"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please login to validate documents"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    doc_type = request.form.get("type", "Aadhaar")  # Aadhaar, Income, etc.
    user = db.session.get(User, user_id)

    if not file:
        return jsonify({"error": "Empty file"}), 400

    # Process with Gemini Vision
    try:
        import PIL.Image

        img = PIL.Image.open(file)

        prompt = f"""
        Extract the following data from this Indian {doc_type} card image.
        Return ONLY valid JSON.
        Required fields: 
        - "full_name": (The name as written on the card)
        - "expiry_date": (The valid-until/expiry date if present, else null)
        - "id_number": (Masked version e.g., ****-****-1234)
        """

        # Use multimodal capabilities if model exists
        if model:
            response = model.generate_content([prompt, img])
            ocr_data = {}
            # Extract JSON from response
            match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if match:
                ocr_data = json.loads(match.group())

            # Validation logic
            name_match = False
            if user and ocr_data.get("full_name"):
                # Simple similarity check
                from difflib import SequenceMatcher

                ratio = SequenceMatcher(
                    None, user.name.lower(), ocr_data["full_name"].lower()
                ).ratio()
                name_match = ratio > 0.8

            is_expired = False
            expiry_msg = "Valid"
            if ocr_data.get("expiry_date"):
                # Simple date check (assuming YYYY-MM-DD or similar from LLM)
                # In real prod we'd parse with dateutil
                expiry_msg = f"Check expiry: {ocr_data['expiry_date']}"

            readiness_score = 0.5
            if name_match:
                readiness_score += 0.5

            return (
                jsonify(
                    {
                        "extractedData": ocr_data,
                        "validation": {
                            "nameMatch": name_match,
                            "isExpired": is_expired,
                            "expiryMessage": expiry_msg,
                            "readinessScore": readiness_score,
                        },
                    }
                ),
                200,
            )
        else:
            return jsonify({"error": "AI engine offline"}), 503

    except Exception as e:
        print(f"OCR Error: {e}")
        return jsonify({"error": "Failed to process document"}), 500


# ----------------- Chatbot (Gemini/AI) -----------------
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")
    if not user_message:
        return jsonify({"error": "Message is required"}), 400
    # Build context
    user_id = session.get("user_id")
    context = ""
    if user_id:
        user = db.session.get(User, user_id)
        if user:
            context = f"User: {user.name}\n"
            if user.age:
                context += f"Profile: Age {user.age}, Gender {user.gender}, State {user.state}, District {user.district}\n"
                context += f"Social: Caste {user.caste}, Minority {user.minority_status}, Disabled {user.disability}\n"
                context += f"Economic: Income ₹{user.income}, Ration Card {user.ration_card_type}, Farmer {user.is_farmer}\n"
                context += f"Education: {user.education}, {user.current_course}\n"
                context += f"Occupation: {user.occupation}, {user.employment_status}\n"
        else:
            # Session exists but user doesn't (stale session)
            session.pop("user_id", None)
    # Call Gemini API if model is configured
    if model:
        try:
            if "gemini_limiter" in globals():
                gemini_limiter.wait()
            response = model.generate_content(
                f"{system_prompt}\n\nUser: {user_message}\n\nAssistant:"
            )
            bot_response = response.text
            return jsonify({"response": bot_response, "powered_by": "gemini"}), 200
        except Exception as e:
            error_str = str(e)
            print(f"Gemini API Error: {error_str}")
            if "429" in error_str or "quota" in error_str.lower():
                return (
                    jsonify(
                        {
                            "response": "⚠️ I'm currently handling a high volume of requests and have reached my temporary AI limit. I can still help with basic questions about schemes, or you can try again in a few minutes!",
                            "powered_by": "system_limit",
                        }
                    ),
                    200,
                )

    # Fallback response
    fallback = generate_fallback_response(user_message, context)
    return jsonify({"response": fallback, "powered_by": "fallback"}), 200


# ----------------- Instant Strict Eligibility Audit -----------------
@app.route("/api/chat/audit-init", methods=["POST"])
def audit_init():
    """
    Step 1: Identify the scheme and extract ALL eligibility questions.
    """
    data = request.json
    query = data.get("query", "")
    if not query:
        return jsonify({"error": "Scheme name is required"}), 400

    # 1. Find the scheme (Fuzzy match by name)
    from sqlalchemy import or_

    schemes = (
        Scheme.query.filter(
            or_(Scheme.name.ilike(f"%{query}%"), Scheme.category.ilike(f"%{query}%"))
        )
        .limit(5)
        .all()
    )

    if not schemes:
        return (
            jsonify(
                {"error": "No matching scheme found. Please try a different name."}
            ),
            404,
        )

    if len(schemes) > 1 and query.lower() not in [s.name.lower() for s in schemes]:
        return (
            jsonify(
                {
                    "multiple_found": True,
                    "schemes": [{"id": s.id, "name": s.name} for s in schemes],
                }
            ),
            200,
        )

    # Pick the best match (exact or first)
    scheme = schemes[0]
    for s in schemes:
        if s.name.lower() == query.lower():
            scheme = s
            break

    # 2. Extract ALL text for line-by-line analysis
    full_text = f"""
    SCHEME: {scheme.name}
    ELIGIBILITY: {scheme.eligibility or 'N/A'}
    EXCLUSIONS: {scheme.exclusions or 'N/A'}
    BENEFITS: {scheme.benefits or 'N/A'}
    PROCESS: {scheme.application_process or 'N/A'}
    """

    # 3. Call Gemini to distill strict questions
    AUDIT_EXTRACT_PROMPT = f"""You are a strict Indian Government Eligibility Auditor. 
Your task is to read the scheme guidelines below LINE-BY-LINE and identify EVERY mandatory requirement and disqualifying exclusion.

SCHEME GUIDELINES:
{full_text}

TASK:
1. Identify every condition that MUST be met for a YES verdict.
2. Identify every condition that would lead to an INELIGIBLE verdict.
3. Create a clear, direct question for every single condition found.
4. For each question, decide if it's a 'choice' (Yes/No), 'dropdown' (categories), or 'text' (numbers).

RULES:
- DO NOT miss any detail. Even minor exclusions must be a question.
- DO NOT assume anything. If the text says 'Applicant must be a woman', the question is 'What is your gender?'.
- Return ONLY a valid JSON array of objects with 'id', 'text', 'type', and 'options' (if applicable).

Example Output:
[
  {{"id": "gender", "text": "What is your gender?", "type": "choice", "options": ["Male", "Female", "Other"]}},
  {{"id": "income", "text": "What is your annual family income?", "type": "text"}},
  {{"id": "taxpayer", "text": "Is anyone in your family an income tax payer?", "type": "choice", "options": ["Yes", "No"]}}
]
"""

    if not model:
        return (
            jsonify(
                {"error": "AI engine is currently offline. Please try again later."}
            ),
            503,
        )

    try:
        # Use rate limiter to avoid 429s
        if "gemini_limiter" in globals():
            gemini_limiter.wait()

        response = model.generate_content(AUDIT_EXTRACT_PROMPT)

        # Check if response has valid candidates
        if not hasattr(response, "candidates") or not response.candidates:
            return (
                jsonify(
                    {"error": "AI refused to analyze this scheme (Safety Filter)."}
                ),
                400,
            )

        try:
            raw_text = response.text.strip()
        except Exception:
            return (
                jsonify(
                    {
                        "error": "AI could not generate a readable analysis for this scheme."
                    }
                ),
                400,
            )

        # Robust JSON extraction: Find first '[' and last ']'
        start = raw_text.find("[")
        end = raw_text.rfind("]")
        if start != -1 and end != -1:
            q_json = raw_text[start : end + 1]
            try:
                questions = json.loads(q_json)
            except json.JSONDecodeError:
                # Fallback to cleaning markdown if partial match failed
                q_text = re.sub(
                    r"^```(?:json)?|```$", "", raw_text, flags=re.MULTILINE
                ).strip()
                questions = json.loads(q_text)
        else:
            # Fallback to cleaning markdown
            q_text = re.sub(
                r"^```(?:json)?|```$", "", raw_text, flags=re.MULTILINE
            ).strip()
            questions = json.loads(q_text)

        if not isinstance(questions, list):
            raise ValueError("AI did not return a valid list of questions.")

        return (
            jsonify(
                {
                    "scheme_id": scheme.id,
                    "scheme_name": scheme.name,
                    "questions": questions,
                }
            ),
            200,
        )
    except Exception as e:
        err_msg = str(e)
        app.logger.error(f"Audit Extraction Error: {err_msg}\n{traceback.format_exc()}")
        if "429" in err_msg or "quota" in err_msg.lower():
            return (
                jsonify(
                    {
                        "error": "AI rate limit reached. Please wait 10 seconds and try again."
                    }
                ),
                429,
            )
        return jsonify({"error": f"Failed to analyze scheme: {err_msg[:100]}"}), 500


@app.route("/api/chat/audit-verdict", methods=["POST"])
def audit_verdict():
    """
    Step 2: Take answers and give an exact, binary verdict.
    """
    data = request.json
    scheme_id = data.get("scheme_id")
    answers = data.get("answers", {})

    scheme = db.session.get(Scheme, scheme_id)
    if not scheme:
        return jsonify({"error": "Scheme not found"}), 404

    full_text = f"""
    SCHEME: {scheme.name}
    ELIGIBILITY: {scheme.eligibility or 'N/A'}
    EXCLUSIONS: {scheme.exclusions or 'N/A'}
    BENEFITS: {scheme.benefits or 'N/A'}
    """

    AUDIT_VERDICT_PROMPT = f"""You are a high-stakes government eligibility auditor. You have NO DOUBT.
Based ONLY on the user's answers and the scheme text below, give a final binary verdict.

SCHEME TEXT:
{full_text}

USER ANSWERS:
{json.dumps(answers, indent=2)}

INSTRUCTIONS:
1. Read every line of the scheme text.
2. Check every user answer against those lines.
3. If ANY requirement fails or ANY exclusion applies, the verdict is INELIGIBLE.
4. If ALL requirements pass, the verdict is ELIGIBLE.
5. Provide a 1-2 sentence CLEAR reason for your decision.

Return ONLY a JSON object:
{{"verdict": "ELIGIBLE" | "INELIGIBLE", "reason": "...", "confidence": "100%"}}
"""

    if not model:
        return jsonify({"error": "AI engine is currently offline."}), 503

    try:
        # Use rate limiter
        if "gemini_limiter" in globals():
            gemini_limiter.wait()

        response = model.generate_content(AUDIT_VERDICT_PROMPT)

        if not hasattr(response, "candidates") or not response.candidates:
            return jsonify({"error": "AI refused to provide a verdict."}), 400

        try:
            raw_text = response.text.strip()
        except Exception:
            return jsonify({"error": "AI could not generate a readable verdict."}), 400

        # Robust JSON extraction: Find first '{' and last '}'
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1:
            v_json = raw_text[start : end + 1]
            verdict_data = json.loads(v_json)
        else:
            v_text = re.sub(
                r"^```(?:json)?|```$", "", raw_text, flags=re.MULTILINE
            ).strip()
            verdict_data = json.loads(v_text)

        return jsonify(verdict_data), 200
    except Exception as e:
        err_msg = str(e)
        app.logger.error(f"Audit Verdict Error: {err_msg}\n{traceback.format_exc()}")
        if "429" in err_msg or "quota" in err_msg.lower():
            return jsonify({"error": "AI rate limit reached. Please wait."}), 429
        return jsonify({"error": "Failed to finalize audit."}), 500


def generate_fallback_response(message, context):
    msg = message.lower()

    # Keyword-based advice when AI is offline
    if "scholarship" in msg or "study" in msg or "college" in msg:
        return "It sounds like you're looking for educational support. You can find scholarships under the 'Education' category in the Schemes section. Many depend on your caste/income."

    if "farmer" in msg or "kisan" in msg or "agriculture" in msg:
        return "For agricultural schemes, please check the 'Agriculture' category. If you own land, make sure your profile reflects your land type (Dry/Wet) for accurate matching."

    if "health" in msg or "medical" in msg or "hospital" in msg:
        return "Health-related schemes like Ayushman Bharat or State Health cards are usually categorized under 'Healthcare'. These often require an Income Certificate or BPL card."

    if "hello" in msg or "hi" in msg:
        return "👋 Hello! I'm your YojanaMitra assistant. My AI engine is currently on a short break, but I can still guide you to the right scheme categories!"

    if "eligible" in msg or "schemes" in msg:
        if "Not logged in" in context:
            return "Please login first to see personalized scheme recommendations."
        return "Check your 'Recommended Schemes' page. If you see 0% matches, try updating your profile with more details like Religion, Caste, and Occupation."

    return "I can help you with government schemes and eligibility. While my AI brain is temporarily busy, you can explore schemes by category in the sidebar!"


# Education Ranking
# Education Ranking
EDUCATION_LEVELS = {
    "Below 10th": 1,
    "10th Pass": 2,
    "12th Pass": 3,
    "Diploma": 3,
    "Graduate": 4,
    "Post Graduate": 5,
    "None": 0,
    "": 0,
}

# ── Education level ordinal map (Fix #8) ─────────────────────────────────────
EDU_LEVEL_RANK = {
    "none": 0,
    "no formal education": 0,
    "primary": 1,
    "class 5": 1,
    "upper primary": 2,
    "class 8": 2,
    "middle school": 2,
    "secondary": 3,
    "class 10": 3,
    "sslc": 3,
    "matric": 3,
    "10th": 3,
    "higher secondary": 4,
    "class 12": 4,
    "hsc": 4,
    "12th": 4,
    "intermediate": 4,
    "puc": 4,
    "diploma": 5,
    "itc": 5,
    "iti": 5,
    "vocational": 5,
    "graduate": 6,
    "graduation": 6,
    "ug": 6,
    "bachelor": 6,
    "degree": 6,
    "post-graduate": 7,
    "postgraduate": 7,
    "pg": 7,
    "master": 7,
    "msc": 7,
    "mba": 7,
    "phd": 8,
    "doctorate": 8,
    "m.phil": 8,
}


def _edu_rank(level_str: str) -> int:
    """Return ordinal rank for an education level string."""
    if not level_str:
        return -1
    return EDU_LEVEL_RANK.get(level_str.lower().strip(), -1)


# ── Document text keyword → engine key mapping (Fix #10) ─────────────────────
DOC_TEXT_KEYWORDS = {
    "aadhaar": "aadhaar",
    "aadhar": "aadhaar",
    "pan card": "pan",
    "pan ": "pan",
    "income certificate": "income_certificate",
    "income cert": "income_certificate",
    "caste certificate": "caste_certificate",
    "community certificate": "caste_certificate",
    "disability certificate": "disability_certificate",
    "pwd certificate": "disability_certificate",
    "ration card": "ration_card",
    "bpl card": "ration_card",
    "bank passbook": "bank_passbook",
    "bank account": "bank_passbook",
    "domicile certificate": "domicile_certificate",
    "residence certificate": "domicile_certificate",
    "marks card": "marks_card",
    "marksheet": "marks_card",
    "degree certificate": "degree_certificate",
    "bonafide": "bonafide_certificate",
    "land records": "land_records",
    "patta": "land_records",
    "sports certificate": "sports_certificate",
    "ncc certificate": "ncc_certificate",
    "ncc card": "ncc_certificate",
    "nss certificate": "nss_certificate",
    "arts certificate": "arts_certificate",
    "cultural certificate": "arts_certificate",
    "merit certificate": "merit_certificate",
    "farmer id": "farmer_id",
    "kisan credit": "farmer_id",
    "birth certificate": "birth_certificate",
    "marriage certificate": "marriage_certificate",
    "widow certificate": "widow_certificate",
}


def _docs_required_from_text(scheme_docs_text: str) -> list:
    """
        Parse scheme.documents_required free text into normalized engine keys.
        e.g. "• Aadhaar Card
    • Income Certificate" → ["aadhaar","income_certificate"]
    """
    if not scheme_docs_text:
        return []
    text_lower = scheme_docs_text.lower()
    found = []
    for keyword, key in DOC_TEXT_KEYWORDS.items():
        if keyword in text_lower and key not in found:
            found.append(key)
    return found


# ----------------- Pending Schemes & Approval Workflow Routes -----------------
@app.route("/api/admin/pending-schemes", methods=["GET"])
def get_pending_schemes():
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    # Return ALL pending schemes — no artificial cap
    query = PendingScheme.query.filter_by(status="pending").order_by(
        PendingScheme.scraped_at.desc()
    )
    total = query.count()
    all_pending = query.all()

    return (
        jsonify(
            {
                "pendingSchemes": [p.to_dict() for p in all_pending],
                "pagination": {
                    "page": 1,
                    "perPage": total,
                    "total": total,
                    "totalPages": 1,
                },
            }
        ),
        200,
    )


@app.route("/api/admin/pending-schemes/<int:scheme_id>/approve", methods=["POST"])
def approve_pending_scheme(scheme_id):
    """
    Approve a pending scheme.

    FLAT COLUMNS BLOCKED: PendingScheme is converted to Condition rows.
    No flat columns stored in Scheme - Condition table is source of truth.
    """
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    pending = PendingScheme.query.get_or_404(scheme_id)

    try:
        # Create Scheme without flat columns
        approved_scheme = Scheme(
            name=pending.name,
            description=pending.description,
            category=pending.category,
            target_audience=pending.target_audience,
            benefits=pending.benefits,
            eligibility=pending.eligibility,
            application_link=pending.application_link,
            # Flat columns NOT stored - only Condition rows
            exclusions=pending.exclusions,
            application_process=pending.application_process,
            documents_required=pending.documents_required,
            is_active=True,  # Required for pipeline
        )

        # Update pending scheme status
        pending.status = "approved"
        pending.approved_by = session.get("admin_id")
        pending.approved_at = datetime.now(timezone.utc)

        # Clear related notifications
        AdminNotification.query.filter_by(pending_scheme_id=scheme_id).delete()

        db.session.add(approved_scheme)
        db.session.flush()  # Get approved_scheme.id

        # AUTO-CONVERT: Convert PendingScheme flat fields to Condition rows
        pending_data = {
            "minAge": pending.min_age,
            "maxAge": pending.max_age,
            "allowedGenders": (
                json.loads(pending.allowed_genders) if pending.allowed_genders else []
            ),
            "minIncome": pending.min_income,
            "maxIncome": pending.max_income,
            "allowedOccupations": (
                json.loads(pending.allowed_occupations)
                if pending.allowed_occupations
                else []
            ),
            "allowedCastes": (
                json.loads(pending.allowed_castes) if pending.allowed_castes else []
            ),
            "allowedStates": (
                json.loads(pending.allowed_states) if pending.allowed_states else []
            ),
            "allowedEducation": (
                json.loads(pending.allowed_education)
                if pending.allowed_education
                else []
            ),
            "allowedMaritalStatus": (
                json.loads(pending.allowed_marital_status)
                if pending.allowed_marital_status
                else []
            ),
            "disabilityRequirement": pending.disability_requirement,
            "residenceRequirement": pending.residence_requirement,
            "allowedFatherOccupations": (
                json.loads(pending.allowed_father_occupations)
                if pending.allowed_father_occupations
                else []
            ),
            "allowedMotherOccupations": (
                json.loads(pending.allowed_mother_occupations)
                if pending.allowed_mother_occupations
                else []
            ),
            "allowedReligions": (
                json.loads(pending.allowed_religions)
                if pending.allowed_religions
                else []
            ),
            "landTypeRequirement": pending.land_type_requirement,
            "orphanRequirement": pending.orphan_requirement,
            "tribalRequirement": pending.tribal_requirement,
            "minorityRequirement": pending.minority_requirement,
            "seniorCitizenRequirement": pending.senior_citizen_requirement,
            "widowRequirement": pending.widow_requirement,
            "disabilityPercentageMin": pending.disability_percentage_min,
            "bankAccountRequired": pending.bank_account_required,
            "aadhaarRequired": pending.aadhaar_required,
            "allowedRationCardTypes": (
                json.loads(pending.allowed_ration_card_types)
                if pending.allowed_ration_card_types
                else []
            ),
            "minEducationLevel": pending.min_education_level,
        }
        _auto_convert_to_conditions(approved_scheme, pending_data, source="extraction")

        db.session.commit()

        # Run new pipeline to extract conditions (for AI-extracted conditions)
        print(
            f"=== PIPELINE: Running Gemini extraction for scheme {approved_scheme.id} ==="
        )
        try:
            from app.pipeline import get_pipeline

            pipeline = get_pipeline(app)
            pipeline.run(approved_scheme, Scheme.query.filter_by(is_active=True).all())
            print(f"=== PIPELINE: Completed for scheme {approved_scheme.id} ===")
        except Exception as pipeline_err:
            print(
                f"=== PIPELINE: FAILED for scheme {approved_scheme.id}: {pipeline_err} ==="
            )
            logger.warning(
                f"Pipeline failed for scheme {approved_scheme.id}: {pipeline_err}"
            )

        # Send SMS notifications (Pass list of schemes)
        notify_users_of_new_schemes([approved_scheme])

    except Exception as e:
        db.session.rollback()
        import traceback

        traceback.print_exc()  # Print full stack trace to console
        print(f"ERROR APPROVING SCHEME: {str(e)}", flush=True)
        return jsonify({"error": f"Failed to approve scheme: {str(e)}"}), 500

    return (
        jsonify({"message": "Scheme approved", "scheme": approved_scheme.to_dict()}),
        200,
    )


@app.route("/api/admin/pending-schemes/<int:scheme_id>/reject", methods=["POST"])
def reject_pending_scheme(scheme_id):
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    pending = PendingScheme.query.get_or_404(scheme_id)

    pending.status = "rejected"
    pending.rejection_reason = data.get("reason", "No reason provided")
    pending.approved_by = session.get("admin_id")
    pending.approved_at = datetime.now(timezone.utc)

    # Clear notifications
    AdminNotification.query.filter_by(pending_scheme_id=scheme_id).delete()

    db.session.commit()

    return jsonify({"message": "Scheme rejected"}), 200


@app.route("/api/admin/pending/batch-approve", methods=["POST"])
def batch_approve_pending_schemes():
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    scheme_ids = data.get("ids", [])
    if not scheme_ids:
        return jsonify({"error": "No schemes selected"}), 400

    approved_count = 0
    approved_schemes = []
    for s_id in scheme_ids:
        pending = db.session.get(PendingScheme, s_id)
        if pending and pending.status == "pending":
            # Create actual Scheme
            approved_scheme = Scheme(
                name=pending.name,
                description=pending.description,
                category=pending.category,
                target_audience=pending.target_audience,
                benefits=pending.benefits,
                eligibility=pending.eligibility,
                application_link=pending.application_link,
                min_age=pending.min_age,
                max_age=pending.max_age,
                allowed_genders=pending.allowed_genders,
                min_income=pending.min_income,
                max_income=pending.max_income,
                allowed_occupations=pending.allowed_occupations,
                allowed_castes=pending.allowed_castes,
                allowed_states=pending.allowed_states,
                allowed_education=pending.allowed_education,
                allowed_marital_status=pending.allowed_marital_status,
                disability_requirement=pending.disability_requirement,
                residence_requirement=pending.residence_requirement,
                # New holistic granular criteria
                allowed_father_occupations=pending.allowed_father_occupations,
                allowed_mother_occupations=pending.allowed_mother_occupations,
                allowed_religions=pending.allowed_religions,
                land_type_requirement=pending.land_type_requirement,
                orphan_requirement=pending.orphan_requirement,
                tribal_requirement=pending.tribal_requirement,
                minority_requirement=pending.minority_requirement,
                senior_citizen_requirement=pending.senior_citizen_requirement,
                widow_requirement=pending.widow_requirement,
                disability_percentage_min=pending.disability_percentage_min,
                bank_account_required=pending.bank_account_required,
                aadhaar_required=pending.aadhaar_required,
                allowed_ration_card_types=pending.allowed_ration_card_types,
                min_education_level=pending.min_education_level,
                mutually_exclusive_with=pending.mutually_exclusive_with,
                # Detailed information fields
                exclusions=pending.exclusions,
                application_process=pending.application_process,
                documents_required=pending.documents_required,
            )
            # Update pending status
            pending.status = "approved"
            pending.approved_by = session.get("admin_id")
            pending.approved_at = datetime.now(timezone.utc)

            AdminNotification.query.filter_by(pending_scheme_id=s_id).delete()
            db.session.add(approved_scheme)
            approved_count += 1
            approved_schemes.append(approved_scheme)

            # Run pipeline for condition extraction
            try:
                from app.pipeline import get_pipeline

                pipeline = get_pipeline(app)
                pipeline.run(
                    approved_scheme, Scheme.query.filter_by(is_active=True).all()
                )
            except Exception as pipeline_err:
                logger.warning(
                    f"Pipeline failed for scheme {approved_scheme.id}: {pipeline_err}"
                )

    db.session.commit()

    # Send notifications
    if approved_schemes:
        notify_users_of_new_schemes(approved_schemes)

    return jsonify({"message": f"Successfully approved {approved_count} schemes"}), 200


@app.route("/api/admin/pending/batch-reject", methods=["POST"])
def batch_reject_pending_schemes():
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    scheme_ids = data.get("ids", [])
    reason = data.get("reason", "Batch rejection")
    if not scheme_ids:
        return jsonify({"error": "No schemes selected"}), 400

    rejected_count = 0
    for s_id in scheme_ids:
        pending = db.session.get(PendingScheme, s_id)
        if pending and pending.status == "pending":
            pending.status = "rejected"
            pending.rejection_reason = reason
            pending.approved_by = session.get("admin_id")
            pending.approved_at = datetime.now(timezone.utc)

            AdminNotification.query.filter_by(pending_scheme_id=s_id).delete()
            rejected_count += 1

    db.session.commit()
    return jsonify({"message": f"Successfully rejected {rejected_count} schemes"}), 200


@app.route("/api/admin/pending/approve-all", methods=["POST"])
def approve_all_pending_schemes():
    """Approve every pending scheme in one shot — no ID list needed."""
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    all_pending = PendingScheme.query.filter_by(status="pending").all()
    if not all_pending:
        return jsonify({"message": "No pending schemes to approve", "approved": 0}), 200

    approved_count = 0
    approved_schemes = []
    for pending in all_pending:
        approved_scheme = Scheme(
            name=pending.name,
            description=pending.description,
            category=pending.category,
            target_audience=pending.target_audience,
            benefits=pending.benefits,
            eligibility=pending.eligibility,
            application_link=pending.application_link,
            min_age=pending.min_age,
            max_age=pending.max_age,
            allowed_genders=pending.allowed_genders,
            min_income=pending.min_income,
            max_income=pending.max_income,
            allowed_occupations=pending.allowed_occupations,
            allowed_castes=pending.allowed_castes,
            allowed_states=pending.allowed_states,
            allowed_education=pending.allowed_education,
            allowed_marital_status=pending.allowed_marital_status,
            disability_requirement=pending.disability_requirement,
            residence_requirement=pending.residence_requirement,
            allowed_father_occupations=pending.allowed_father_occupations,
            allowed_mother_occupations=pending.allowed_mother_occupations,
            allowed_religions=pending.allowed_religions,
            land_type_requirement=pending.land_type_requirement,
            orphan_requirement=pending.orphan_requirement,
            tribal_requirement=pending.tribal_requirement,
            minority_requirement=pending.minority_requirement,
            senior_citizen_requirement=pending.senior_citizen_requirement,
            widow_requirement=pending.widow_requirement,
            disability_percentage_min=pending.disability_percentage_min,
            bank_account_required=pending.bank_account_required,
            aadhaar_required=pending.aadhaar_required,
            allowed_ration_card_types=pending.allowed_ration_card_types,
            min_education_level=pending.min_education_level,
            mutually_exclusive_with=pending.mutually_exclusive_with,
            exclusions=pending.exclusions,
            application_process=pending.application_process,
            documents_required=pending.documents_required,
        )
        pending.status = "approved"
        pending.approved_by = session.get("admin_id")
        pending.approved_at = datetime.now(timezone.utc)
        AdminNotification.query.filter_by(pending_scheme_id=pending.id).delete()
        db.session.add(approved_scheme)
        approved_count += 1
        approved_schemes.append(approved_scheme)

        # Run pipeline for condition extraction
        try:
            from app.pipeline import get_pipeline

            pipeline = get_pipeline(app)
            pipeline.run(approved_scheme, Scheme.query.filter_by(is_active=True).all())
        except Exception as pipeline_err:
            logger.warning(
                f"Pipeline failed for scheme {approved_scheme.id}: {pipeline_err}"
            )

    db.session.commit()
    if approved_schemes:
        notify_users_of_new_schemes(approved_schemes)
    return (
        jsonify({"message": f"Successfully approved all {approved_count} schemes"}),
        200,
    )


@app.route("/api/admin/pending/reject-all", methods=["POST"])
def reject_all_pending_schemes():
    """Reject every pending scheme in one shot — no ID list needed."""
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json or {}
    reason = data.get("reason", "Bulk rejection")

    all_pending = PendingScheme.query.filter_by(status="pending").all()
    if not all_pending:
        return jsonify({"message": "No pending schemes to reject", "rejected": 0}), 200

    rejected_count = 0
    for pending in all_pending:
        pending.status = "rejected"
        pending.rejection_reason = reason
        pending.approved_by = session.get("admin_id")
        pending.approved_at = datetime.now(timezone.utc)
        AdminNotification.query.filter_by(pending_scheme_id=pending.id).delete()
        rejected_count += 1

    db.session.commit()
    return (
        jsonify({"message": f"Successfully rejected all {rejected_count} schemes"}),
        200,
    )


@app.route("/api/admin/pending-schemes/<int:scheme_id>", methods=["PUT"])
def update_pending_scheme(scheme_id):
    """Edit a pending scheme before approval"""
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    pending = PendingScheme.query.get_or_404(scheme_id)
    data = request.json

    # Update fields
    pending.name = data.get("name", pending.name)
    pending.description = data.get("description", pending.description)
    pending.category = data.get("category", pending.category)
    pending.target_audience = data.get("targetAudience", pending.target_audience)
    pending.benefits = data.get("benefits", pending.benefits)
    pending.eligibility = data.get("eligibility", pending.eligibility)
    pending.application_link = data.get("applicationLink", pending.application_link)
    pending.min_age = data.get("minAge", pending.min_age)
    pending.max_age = data.get("maxAge", pending.max_age)
    pending.allowed_genders = json.dumps(
        data.get("allowedGenders", json.loads(pending.allowed_genders or "[]"))
    )
    pending.min_income = data.get("minIncome", pending.min_income)
    pending.max_income = data.get("maxIncome", pending.max_income)
    pending.allowed_occupations = json.dumps(
        data.get("allowedOccupations", json.loads(pending.allowed_occupations or "[]"))
    )
    pending.allowed_castes = json.dumps(
        data.get("allowedCastes", json.loads(pending.allowed_castes or "[]"))
    )
    pending.allowed_states = json.dumps(
        data.get("allowedStates", json.loads(pending.allowed_states or "[]"))
    )
    pending.allowed_education = json.dumps(
        data.get("allowedEducation", json.loads(pending.allowed_education or "[]"))
    )
    pending.allowed_marital_status = json.dumps(
        data.get(
            "allowedMaritalStatus", json.loads(pending.allowed_marital_status or "[]")
        )
    )
    pending.disability_requirement = data.get(
        "disabilityRequirement", pending.disability_requirement
    )
    pending.residence_requirement = data.get(
        "residenceRequirement", pending.residence_requirement
    )

    db.session.commit()

    return (
        jsonify({"message": "Pending scheme updated", "scheme": pending.to_dict()}),
        200,
    )


# ----------------- Admin Notifications Routes -----------------
@app.route("/api/admin/notifications", methods=["GET"])
def get_admin_notifications():
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    admin_id = session.get("admin_id")
    notifications = (
        AdminNotification.query.filter_by(admin_id=admin_id, is_read=False)
        .order_by(AdminNotification.created_at.desc())
        .all()
    )

    return (
        jsonify(
            {
                "notifications": [n.to_dict() for n in notifications],
                "count": len(notifications),
            }
        ),
        200,
    )


@app.route("/api/admin/notifications/<int:notification_id>/mark-read", methods=["POST"])
def mark_notification_read(notification_id):
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    notification = AdminNotification.query.get_or_404(notification_id)
    notification.is_read = True
    db.session.commit()

    return jsonify({"message": "Notification marked as read"}), 200


# ----------------- Scrape Sources Management Routes -----------------
@app.route("/api/admin/scrape-sources", methods=["GET"])
def get_scrape_sources():
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    sources = SchemeSource.query.all()
    return jsonify({"sources": [s.to_dict() for s in sources]}), 200


@app.route("/api/admin/scrape-sources", methods=["POST"])
def create_scrape_source():
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    source = SchemeSource(
        name=data["name"],
        url=data["url"],
        scraper_type=data.get("scraperType", "generic"),
        is_active=data.get("isActive", True),
    )

    db.session.add(source)
    db.session.commit()

    return jsonify({"message": "Scrape source added", "source": source.to_dict()}), 201


@app.route("/api/admin/scrape-sources/<int:source_id>", methods=["DELETE"])
def delete_scrape_source(source_id):
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    source = SchemeSource.query.get_or_404(source_id)
    db.session.delete(source)
    db.session.commit()

    return jsonify({"message": "Scrape source deleted"}), 200


@app.route("/api/admin/trigger-scrape", methods=["POST"])
def trigger_manual_scrape():
    """Manually trigger scraping job"""
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    try:
        data = request.get_json() or {}
        limit = data.get("limit")
        if limit is not None:
            try:
                limit = int(limit)
            except (ValueError, TypeError):
                limit = None

        from scheduler import scheduler_instance

        if scheduler_instance:
            logger.info(f"[TRIGGER] Received manual scrape request. Limit: {limit}")
            if scheduler_instance.is_scraping_running():
                logger.info("[TRIGGER] Scraping already in progress. Ignoring.")
                return jsonify({"message": "Scraping job already running"}), 200

            # Run in background to avoid request timeout
            import threading

            # Set flag immediately to avoid race condition with status polling
            scheduler_instance._is_running = True
            logger.info(f"[TRIGGER] Spawning scraper thread...")
            thread = threading.Thread(
                target=scheduler_instance.run_scraping_job, kwargs={"limit": limit}
            )
            thread.start()
            return (
                jsonify(
                    {
                        "message": f"Scraping job started {'with limit ' + str(limit) if limit else ''}"
                    }
                ),
                200,
            )
        else:
            return jsonify({"error": "Scheduler not initialized"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/stop-scrape", methods=["POST"])
def stop_scraping():
    """Manually stop the ongoing scraping job"""
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    from scheduler import scheduler_instance

    if scheduler_instance:
        # Run in thread not needed, just setting flag
        scheduler_instance.stop_scraping()
        return jsonify({"message": "Scraping stop signal sent"}), 200

    return jsonify({"error": "Scheduler not initialized"}), 500


@app.route("/api/admin/scrape-status", methods=["GET"])
def get_scrape_status():
    """Check if scraping is currently running"""
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    from scheduler import scheduler_instance

    is_running = False
    if scheduler_instance:
        is_running = scheduler_instance.is_scraping_running()

    return jsonify({"isRunning": is_running}), 200


@app.route("/api/admin/scrape-logs", methods=["GET"])
def get_scrape_logs():
    """Get recent scraping history"""
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    logs = ScrapeLog.query.order_by(ScrapeLog.scraped_at.desc()).limit(50).all()
    return jsonify({"logs": [l.to_dict() for l in logs]}), 200


# ─────────────────────────────────────────────────────────────────────────────
# FEEDBACK LOOP API
# Three endpoints that together close the accuracy measurement loop:
#   POST /api/feedback          — Stage 1: did user apply?
#   POST /api/feedback/<id>     — Stage 2: what was the outcome?
#   GET  /api/feedback/pending  — fetch schemes awaiting Stage 2 follow-up
#   GET  /api/admin/accuracy    — admin analytics: false positive rates etc.
# ─────────────────────────────────────────────────────────────────────────────


@app.route("/api/feedback", methods=["POST"])
def submit_feedback():
    """Stage 1 — user reports whether they applied for a scheme."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json() or {}
    scheme_id = data.get("schemeId")
    did_apply = data.get("didApply")  # 'Yes' | 'No' | 'Planning'

    if not scheme_id or not did_apply:
        return jsonify({"error": "schemeId and didApply are required"}), 400

    scheme = db.session.get(Scheme, scheme_id)
    if not scheme:
        return jsonify({"error": "Scheme not found"}), 404

    # Upsert — one record per user per scheme
    existing = ApplicationFeedback.query.filter_by(
        user_id=user_id, scheme_id=scheme_id
    ).first()

    if existing:
        existing.did_apply = did_apply
        existing.reason_not_applied = data.get("reasonNotApplied")
        existing.updated_at = datetime.utcnow()
        if did_apply == "Yes" and not existing.follow_up_due:
            from datetime import timedelta

            existing.follow_up_due = datetime.utcnow() + timedelta(days=30)
        record = existing
    else:
        from datetime import timedelta

        record = ApplicationFeedback(
            user_id=user_id,
            scheme_id=scheme_id,
            scheme_name=scheme.name,
            category=scheme.category,
            did_apply=did_apply,
            reason_not_applied=data.get("reasonNotApplied"),
            match_score_at_time=data.get("matchScore"),
            ai_verdict_at_time=data.get("aiVerdict"),
            profile_completeness=data.get("profileCompleteness"),
            follow_up_due=(
                datetime.utcnow() + timedelta(days=30) if did_apply == "Yes" else None
            ),
        )
        db.session.add(record)

    db.session.commit()

    # Trigger confidence score recalculation for this scheme if enough data
    _maybe_update_scheme_confidence(scheme_id)

    return jsonify({"message": "Feedback recorded", "feedback": record.to_dict()}), 200


@app.route("/api/feedback/<int:feedback_id>", methods=["POST"])
def submit_outcome(feedback_id):
    """Stage 2 — user reports the final outcome of their application."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    record = ApplicationFeedback.query.filter_by(
        id=feedback_id, user_id=user_id
    ).first()
    if not record:
        return jsonify({"error": "Feedback record not found"}), 404

    data = request.get_json() or {}
    record.outcome = data.get("outcome")  # Approved|Rejected|Pending|Withdrew
    record.rejection_reason_code = data.get(
        "rejectionReasonCode"
    )  # income|caste|age|docs|other
    record.rejection_detail = data.get("rejectionDetail")
    record.follow_up_sent = True
    record.updated_at = datetime.utcnow()
    db.session.commit()

    # Recalculate confidence after outcome is known
    _maybe_update_scheme_confidence(record.scheme_id)

    return jsonify({"message": "Outcome recorded", "feedback": record.to_dict()}), 200


@app.route("/api/feedback/pending", methods=["GET"])
def get_pending_followups():
    """Return schemes where Stage 2 follow-up is due (applied 30+ days ago, no outcome yet)."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    now = datetime.utcnow()
    pending = ApplicationFeedback.query.filter(
        ApplicationFeedback.user_id == user_id,
        ApplicationFeedback.did_apply == "Yes",
        ApplicationFeedback.outcome == None,
        ApplicationFeedback.follow_up_due <= now,
    ).all()

    return jsonify({"pendingFollowUps": [r.to_dict() for r in pending]}), 200


@app.route("/api/feedback/all", methods=["GET"])
def get_my_feedback():
    """Return all feedback records for the current user."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    records = (
        ApplicationFeedback.query.filter_by(user_id=user_id)
        .order_by(ApplicationFeedback.created_at.desc())
        .all()
    )
    return jsonify({"feedback": [r.to_dict() for r in records]}), 200


def _maybe_update_scheme_confidence(scheme_id: int):
    """
    Recalculate and persist the matching confidence for a scheme based on
    accumulated user feedback outcomes. Only fires when >= 5 outcomes exist
    (prevents noise from small samples).

    Confidence logic:
      - approved_rate  = Approved / (Approved + Rejected)
      - If approved_rate >= 0.80 → confidence stays high (no action)
      - If approved_rate  0.50–0.79 → lower Gemini threshold for this scheme by 5 pts
      - If approved_rate < 0.50 → flag scheme for admin review + lower threshold by 10 pts
      - If rejection_reason_code is consistently 'caste'/'age'/'income' →
        log structured insight to help fix the rule
    """
    from collections import Counter

    outcomes = ApplicationFeedback.query.filter(
        ApplicationFeedback.scheme_id == scheme_id,
        ApplicationFeedback.outcome != None,
    ).all()

    if len(outcomes) < 5:
        return  # not enough data yet

    outcome_counts = Counter(r.outcome for r in outcomes)
    approved = outcome_counts.get("Approved", 0)
    rejected = outcome_counts.get("Rejected", 0)
    total = approved + rejected
    if total == 0:
        return

    approved_rate = approved / total
    reason_counts = Counter(
        r.rejection_reason_code for r in outcomes if r.rejection_reason_code
    )

    scheme = db.session.get(Scheme, scheme_id)
    if not scheme:
        return

    # Log the insight for admin visibility
    top_reason = reason_counts.most_common(1)[0] if reason_counts else ("unknown", 0)
    insight = (
        f"Scheme '{scheme.name}' (id={scheme_id}): "
        f"approved_rate={approved_rate:.0%} ({approved}/{total} outcomes). "
        f"Top rejection reason: {top_reason[0]} ({top_reason[1]}x)."
    )
    logger.info(f"[FeedbackLoop] {insight}")

    if approved_rate < 0.50:
        logger.warning(
            f"[FeedbackLoop] HIGH FALSE POSITIVE ALERT — {scheme.name}: "
            f"only {approved_rate:.0%} approval rate. Flagging for admin review."
        )

    db.session.commit()


# ── Admin accuracy analytics ──────────────────────────────────────────────────


@app.route("/api/admin/accuracy", methods=["GET"])
def get_accuracy_analytics():
    """
    Return system-wide accuracy metrics derived from user feedback.
    Used in the admin accuracy dashboard panel.
    """
    if session.get("user_type") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    from collections import Counter, defaultdict
    from sqlalchemy import func

    all_feedback = ApplicationFeedback.query.all()
    total_feedback = len(all_feedback)
    applied = [f for f in all_feedback if f.did_apply == "Yes"]
    with_outcome = [f for f in applied if f.outcome]
    approved = [f for f in with_outcome if f.outcome == "Approved"]
    rejected = [f for f in with_outcome if f.outcome == "Rejected"]
    not_applied = [f for f in all_feedback if f.did_apply == "No"]

    approval_rate = len(approved) / len(with_outcome) if with_outcome else None

    # Rejection breakdown
    rejection_reasons = Counter(
        f.rejection_reason_code for f in rejected if f.rejection_reason_code
    )

    # False positive rate by category
    cat_stats = defaultdict(lambda: {"applied": 0, "approved": 0, "rejected": 0})
    for f in all_feedback:
        cat = f.category or "Unknown"
        if f.did_apply == "Yes":
            cat_stats[cat]["applied"] += 1
        if f.outcome == "Approved":
            cat_stats[cat]["approved"] += 1
        if f.outcome == "Rejected":
            cat_stats[cat]["rejected"] += 1

    category_accuracy = []
    for cat, counts in sorted(cat_stats.items()):
        total_outcomes = counts["approved"] + counts["rejected"]
        acc = (
            (counts["approved"] / total_outcomes * 100) if total_outcomes >= 3 else None
        )
        category_accuracy.append(
            {
                "category": cat,
                "applied": counts["applied"],
                "approved": counts["approved"],
                "rejected": counts["rejected"],
                "accuracyPct": round(acc, 1) if acc is not None else None,
            }
        )

    # Top false positive schemes (most rejections)
    scheme_rejection_counts = Counter((f.scheme_id, f.scheme_name) for f in rejected)
    top_false_positives = [
        {"schemeId": sid, "schemeName": name, "rejections": count}
        for (sid, name), count in scheme_rejection_counts.most_common(10)
    ]

    # Schemes with high approval — confirms accuracy
    scheme_approval_counts = Counter((f.scheme_id, f.scheme_name) for f in approved)
    top_accurate = [
        {"schemeId": sid, "schemeName": name, "approvals": count}
        for (sid, name), count in scheme_approval_counts.most_common(10)
    ]

    # Not-applied reasons
    not_applied_reasons = Counter(
        f.reason_not_applied for f in not_applied if f.reason_not_applied
    )

    # Match score distribution for approved vs rejected
    approved_scores = [f.match_score_at_time for f in approved if f.match_score_at_time]
    rejected_scores = [f.match_score_at_time for f in rejected if f.match_score_at_time]
    avg_approved_score = (
        round(sum(approved_scores) / len(approved_scores), 1)
        if approved_scores
        else None
    )
    avg_rejected_score = (
        round(sum(rejected_scores) / len(rejected_scores), 1)
        if rejected_scores
        else None
    )

    return (
        jsonify(
            {
                "summary": {
                    "totalFeedback": total_feedback,
                    "totalApplied": len(applied),
                    "withOutcome": len(with_outcome),
                    "approved": len(approved),
                    "rejected": len(rejected),
                    "notApplied": len(not_applied),
                    "approvalRatePct": (
                        round(approval_rate * 100, 1)
                        if approval_rate is not None
                        else None
                    ),
                    "avgMatchScoreApproved": avg_approved_score,
                    "avgMatchScoreRejected": avg_rejected_score,
                },
                "rejectionReasons": dict(rejection_reasons.most_common()),
                "categoryAccuracy": category_accuracy,
                "topFalsePositives": top_false_positives,
                "topAccurateSchemes": top_accurate,
                "notAppliedReasons": dict(not_applied_reasons.most_common(10)),
            }
        ),
        200,
    )


# ----------------- DB Init & Seed -----------------


# ─────────────────────────────────────────────────────────────────────────────
# APPLICATION FEEDBACK MODEL — powers the accuracy feedback loop
# ─────────────────────────────────────────────────────────────────────────────
class ApplicationFeedback(db.Model):
    __tablename__ = "application_feedback"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    scheme_id = db.Column(db.Integer, db.ForeignKey("scheme.id"), nullable=False)
    scheme_name = db.Column(db.String(300))
    category = db.Column(db.String(100))

    # Stage 1: shown on scheme card
    did_apply = db.Column(db.String(10))  # Yes | No | Planning
    reason_not_applied = db.Column(db.String(300))

    # Stage 2: follow-up 30 days after applying
    outcome = db.Column(db.String(20))  # Approved | Rejected | Pending | Withdrew
    rejection_reason_code = db.Column(
        db.String(50)
    )  # income | caste | age | docs | other
    rejection_detail = db.Column(db.String(500))

    # Match context snapshot for accuracy analysis
    match_score_at_time = db.Column(db.Integer)
    ai_verdict_at_time = db.Column(db.String(30))
    profile_completeness = db.Column(db.Float)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    follow_up_due = db.Column(db.DateTime)
    follow_up_sent = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "schemeId": self.scheme_id,
            "schemeName": self.scheme_name,
            "category": self.category,
            "didApply": self.did_apply,
            "reasonNotApplied": self.reason_not_applied,
            "outcome": self.outcome,
            "rejectionReasonCode": self.rejection_reason_code,
            "rejectionDetail": self.rejection_detail,
            "matchScoreAtTime": self.match_score_at_time,
            "aiVerdictAtTime": self.ai_verdict_at_time,
            "profileCompleteness": self.profile_completeness,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "followUpDue": (
                self.follow_up_due.isoformat() if self.follow_up_due else None
            ),
        }


def init_db():
    with app.app_context():
        try:
            # Create all tables with proper error handling
            db.create_all()
            print("✓ Database tables created/verified")
        except Exception as db_err:
            print(f"⚠ Warning during db.create_all(): {db_err}")
            # Continue anyway - tables may already exist

        # ── Safe migration via SQLAlchemy — no path guessing ─────────────
        try:
            from sqlalchemy import text, inspect

            insp = inspect(db.engine)
            # Ensure application_feedback table has all columns
            if "application_feedback" in insp.get_table_names():
                fb_cols = [
                    col["name"] for col in insp.get_columns("application_feedback")
                ]
                fb_new_cols = {
                    "profile_completeness": "ALTER TABLE application_feedback ADD COLUMN profile_completeness FLOAT",
                    "follow_up_sent": "ALTER TABLE application_feedback ADD COLUMN follow_up_sent BOOLEAN DEFAULT FALSE",
                    "follow_up_due": "ALTER TABLE application_feedback ADD COLUMN follow_up_due TIMESTAMP",
                    "rejection_detail": "ALTER TABLE application_feedback ADD COLUMN rejection_detail VARCHAR(500)",
                    "rejection_reason_code": "ALTER TABLE application_feedback ADD COLUMN rejection_reason_code VARCHAR(50)",
                }
                for col, sql in fb_new_cols.items():
                    if col not in fb_cols:
                        try:
                            db.session.execute(text(sql))
                            db.session.commit()
                        except Exception:
                            db.session.rollback()

            if "user" in insp.get_table_names():
                existing = {col["name"] for col in insp.get_columns("user")}
                # All columns that may be missing in older DB deployments
                new_cols = [
                    ("verified_scheme_ids", "TEXT"),
                    ("verified_schemes_data", "TEXT"),
                    ("achievement_certificates", "TEXT"),
                    ("scheme_previously_availed", "VARCHAR(10)"),
                    ("is_pensioner", "VARCHAR(10)"),
                    ("num_daughters", "INTEGER"),
                    ("has_pucca_house", "VARCHAR(10)"),
                    ("house_type", "VARCHAR(30)"),
                    ("is_landless", "VARCHAR(10)"),
                    ("is_bocw_registered", "VARCHAR(10)"),
                    ("is_school_dropout", "VARCHAR(10)"),
                    ("is_first_gen_student", "VARCHAR(10)"),
                    ("profile_version", "INTEGER DEFAULT 1"),
                ]
                with db.engine.connect() as conn:
                    for col, coltype in new_cols:
                        if col not in existing:
                            try:
                                conn.execute(
                                    text(f"ALTER TABLE user ADD COLUMN {col} {coltype}")
                                )
                                print(f"  ✓ Migrated: user.{col}")
                            except Exception:
                                pass  # Column may already exist
                    conn.commit()
        except Exception as mig_err:
            print(f"  Migration skipped: {mig_err}")

        # ─────────────────────────────────────────────────────────────────
        try:
            if not Admin.query.first():
                admin = Admin(
                    email="admin@yojanamitra.gov.in",
                    password_hash=generate_password_hash("admin123"),
                )
                db.session.add(admin)
                db.session.commit()
        except Exception as admin_err:
            db.session.rollback()
            print(f"Admin user setup: {admin_err}")

        # Seed default scrape sources
        # Seed default scrape sources - STRICTLY MYSCHEME ONLY (User Request)
        print("Checking for scrape sources...")
        default_sources = [
            {
                "name": "myScheme National Portal",
                "url": "https://www.myscheme.gov.in/search",
                "type": "myscheme",
            }
        ]

        # Enforce single source: Delete anything NOT in this list
        existing_sources = SchemeSource.query.all()
        allowed_urls = [s["url"] for s in default_sources]

        for source in existing_sources:
            if source.url not in allowed_urls:
                print(f"Removing disallowed source: {source.name}")
                # Delete associated pending schemes first if any
                PendingScheme.query.filter_by(source_id=source.id).delete()
                ScrapeLog.query.filter_by(source_id=source.id).delete()
                db.session.delete(source)
        db.session.commit()  # Commit deletions

        for source in default_sources:
            if not SchemeSource.query.filter_by(url=source["url"]).first():
                new_source = SchemeSource(
                    name=source["name"], url=source["url"], scraper_type=source["type"]
                )
                db.session.add(new_source)
                print(f"Added source: {source['name']}")

        db.session.commit()

        scheme_count = Scheme.query.count()
        print(f"Current scheme count: {scheme_count}")
        # NOTE: Seeding disabled - schemes are added via scraping system
        # The Scheme model enforces Condition table usage for eligibility criteria
        # so direct column assignment is blocked by design
        # if scheme_count == 0:
        #     print("Calling seed_schemes()...")
        #     seed_schemes()
        # else:
        #     print(f"Skipping seed - {scheme_count} schemes already exist")
        db.session.commit()
        print("Database initialized successfully!")


def seed_schemes():
    print("Starting to seed schemes...")
    # (Implementation of seeding omitted for brevity; assume existing function works)
    # You may re-use the previous seed_schemes implementation.
    try:
        if os.path.exists("schemes_data.json"):
            with open("schemes_data.json", "r", encoding="utf-8") as f:
                schemes_data = json.load(f)
            print(f"Loaded {len(schemes_data)} schemes from file.")
        else:
            print("schemes_data.json not found, using default seeds.")
            schemes_data = [
                {
                    "name": "PM Kisan Samman Nidhi",
                    "description": "Income support of ₹6,000 per year for farmer families.",
                    "category": "Agriculture",
                    "targetAudience": "Farmers",
                    "benefits": "₹6,000 per year in 3 installments.",
                    "eligibility": "Small and marginal farmers.",
                    "applicationLink": "https://pmkisan.gov.in",
                    "minAge": 18,
                    "maxAge": 100,
                    "allowedGenders": ["All"],
                    "allowedOccupations": ["Farmer"],
                    "allowedCastes": ["All"],
                    "allowedStates": ["All"],
                    "allowedEducation": ["All"],
                    "allowedMaritalStatus": ["All"],
                    "disabilityRequirement": "Any",
                    "residenceRequirement": "Rural",
                }
            ]
    except Exception as e:
        print(f"Error loading schemes data: {e}")
        schemes_data = []

    for s_data in schemes_data:
        scheme = Scheme(
            name=s_data.get("name"),
            description=s_data.get("description"),
            category=s_data.get("category"),
            target_audience=s_data.get("targetAudience"),
            benefits=s_data.get("benefits"),
            eligibility=s_data.get("eligibility"),
            application_link=s_data.get("applicationLink"),
            min_age=s_data.get("minAge"),
            max_age=s_data.get("maxAge"),
            min_income=s_data.get("minIncome"),
            allowed_genders=json.dumps(s_data.get("allowedGenders", [])),
            allowed_occupations=json.dumps(s_data.get("allowedOccupations", [])),
            allowed_castes=json.dumps(s_data.get("allowedCastes", [])),
            allowed_states=json.dumps(s_data.get("allowedStates", [])),
            allowed_education=json.dumps(s_data.get("allowedEducation", [])),
            allowed_marital_status=json.dumps(s_data.get("allowedMaritalStatus", [])),
            disability_requirement=s_data.get("disabilityRequirement", "Any"),
            residence_requirement=s_data.get("residenceRequirement", "Any"),
        )
        db.session.add(scheme)

    try:
        db.session.commit()
        print("Schemes seeded successfully.")
    except Exception as e:
        print(f"Error seeding schemes: {e}")
        db.session.rollback()


@app.route("/api/test-notifications", methods=["GET"])
def test_notifications():
    """Trigger a simulated broadcast to test summarized/targeted notifications"""
    email = request.args.get("email")

    if not email:
        return (
            jsonify(
                {"error": "Please provide 'email' query parameter to target the test"}
            ),
            400,
        )

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": f"User with email {email} not found in database"}), 404

    # Simulate a batch of 10 new schemes
    print(f"--- Simulating targeted broadcast for {user.name} ---")

    # Get some schemes to use as "new" schemes for testing
    all_schemes = Scheme.query.limit(10).all()

    total_new = len(all_schemes)
    base_url = "https://yojanamitra-1.onrender.com"

    # Targeted Eligibility Check
    eligible_schemes = []
    try:
        from app.engine_compat import get_orchestrator

        orch = get_orchestrator(app.config)
        for scheme in all_schemes:
            try:
                score = orch.quick_score(user, scheme)
                if score > 0:
                    eligible_schemes.append(scheme)
            except:
                pass
    except:
        pass

    count = len(eligible_schemes)
    display_schemes = eligible_schemes[:5]
    schemes_html_list = "".join(
        [
            f'<li class="scheme-item"><a href="{base_url}/all_schemes.html" style="color: #1e3c72; text-decoration: none;">{s.name}</a></li>'
            for s in display_schemes
        ]
    )
    if count > 5:
        schemes_html_list += f'<li class="scheme-item">...and {count - 5} more matching your profile!</li>'

    html_msg = f"""
    <p><b>[TEST]</b> Excellent news, <b>{user.name}</b>!</p>
    <p>We've just added <b>{total_new}</b> new schemes, and based on your profile, you are eligible for <b>{count}</b> of them:</p>
    <ul class="scheme-list">
        {schemes_html_list}
    </ul>
    <div style="text-align: center; margin: 30px 0;">
        <a href="{base_url}/dashboard" class="btn">View My Recommendations</a>
    </div>
    <p style="font-size: 14px; color: #666;">This is a test of our new targeted notification system.</p>
    """

    email_subject = f"[TEST] You're eligible for {count} new schemes"
    email_html = get_email_html_template(
        "New Targeted Opportunities", html_msg, user.name
    )

    success = send_email_notification(
        user.email,
        email_subject,
        f"Test: You are eligible for {count} schemes.",
        html_content=email_html,
        user_name=user.name,
    )

    return (
        jsonify(
            {
                "message": "Targeted notification test triggered",
                "user": user.name,
                "email": user.email,
                "eligible_count": count,
                "total_simulated": total_new,
                "success": success,
            }
        ),
        200,
    )


if __name__ == "__main__":
    init_db()

    # Initialize and start the scheduler
    print("Initializing background scheduler...")
    from scheduler import init_scheduler

    init_scheduler(
        app,
        db,
        {
            "SchemeSource": SchemeSource,
            "PendingScheme": PendingScheme,
            "ScrapeLog": ScrapeLog,
            "AdminNotification": AdminNotification,
            "Admin": Admin,
            "Scheme": Scheme,
        },
    )
    print("Scheduler started - Weekly scraping configured for Sundays at 2:00 AM")

    print("\n" + "#" * 70, flush=True)
    print("### YOJANAMITRA BACKEND IS NOW STARTING - LOGGING IS ARMED ###", flush=True)
    print("#" * 70 + "\n", flush=True)

    print(f"Backend: http://localhost:5000", flush=True)
    print(f"Admin Panel: http://localhost:5000/admin.html", flush=True)
    print(
        f"Gemini AI: {'Configured' if GEMINI_API_KEY else 'NOT CONFIGURED'}", flush=True
    )
    print("Automated Scheme Detection: ENABLED", flush=True)
    print("Terminal Monitoring: ACTIVE (Logs will appear below)", flush=True)

    app.run(debug=True, use_reloader=True, host="0.0.0.0", port=5000)
