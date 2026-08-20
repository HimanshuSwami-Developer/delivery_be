# Mobile Number + OTP Login (Django + DRF)

A ready-to-run Django REST Framework project implementing mobile-number
login via OTP, with:

- **Send OTP** — generates a code and sends it by SMS
- **Resend OTP** — re-sends a fresh code, with a cooldown to prevent abuse
- **Verify OTP** — checks the code and logs the user in (JWT tokens)
- **Master OTP login** — a separate endpoint that logs a user in with a
  fixed, pre-configured code **without sending any SMS at all** — handy for
  QA, app-store reviewers, or automated testing accounts

No email/username/password is used anywhere — the mobile number *is* the
identity.

## Project layout

```
core/                  # Django project (settings, root urls)
accounts/
  models.py            # User (mobile_number is USERNAME_FIELD), OTP
  serializers.py        # input validation
  sms_service.py        # SMS provider abstraction (console / Twilio / ...)
  views.py               # SendOTP, ResendOTP, VerifyOTP, MasterOTPLogin
  urls.py
  admin.py
requirements.txt
.env.example
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate         # venv\Scripts\activate on Windows
pip install -r requirements.txt

# copy env example and edit as needed (or just export the vars yourself)
cp .env.example .env

python manage.py migrate
python manage.py createsuperuser --mobile_number +910000000000  # optional, for /admin/
python manage.py runserver
```

By default `SMS_BACKEND=console`, so OTPs are simply printed to the
terminal/log instead of being sent — perfect for local development. No
external SMS account is required to try the project out.

## Switching to a real SMS provider

Set `SMS_BACKEND=fast2sms` and fill in `FAST2SMS_API_KEY` (env var or
directly in `core/settings.py`) — sends plain SMS via Fast2SMS's Quick SMS
route. See `core/service/sms_service.py` for the implementation.

To use a different provider (AWS SNS, TextLocal, Twilio, etc.), add
another `_send_via_xxx` method to `SMSService` and branch on it in
`send_otp_sms`. Every view calls `SMSService.send_otp_sms(mobile, otp)` —
nothing else in the code needs to change.

## API Reference

Base path: `/api/auth/`

All responses are JSON. All 4 endpoints are public (no auth token needed
to call them — that's the whole point, they're how you *get* a token).

### 1. Send OTP

```
POST /api/auth/send-otp/
{ "mobile_number": "+919876543210" }
```
→ `200 OK`
```json
{ "detail": "OTP sent successfully.", "mobile_number": "+919876543210", "expires_in_minutes": 5 }
```

### 2. Resend OTP

```
POST /api/auth/resend-otp/
{ "mobile_number": "+919876543210" }
```
Same response shape as Send OTP. If called again before
`RESEND_OTP_WAIT_SECONDS` (default 30s) has elapsed, returns `429`:
```json
{ "detail": "Please wait 24 second(s) before requesting another OTP." }
```

### 3. Verify OTP (real login)

```
POST /api/auth/verify-otp/
{ "mobile_number": "+919876543210", "otp_code": "482913" }
```
→ `200 OK`
```json
{
  "detail": "Login successful.",
  "is_new_user": true,
  "mobile_number": "+919876543210",
  "tokens": { "refresh": "...", "access": "..." }
}
```
Wrong code → `400` with attempts remaining; expired code, too many
attempts, or no pending OTP → `400` with an explanatory message.

### 4. Master OTP login (no SMS sent)

```
POST /api/auth/master-login/
{ "mobile_number": "+919876543210", "master_otp": "123456" }
```
→ same success shape as Verify OTP, but **no OTP row is created and no SMS
is ever sent** — the code is only checked against `settings.MASTER_OTP`.

Wrong master code → `400 {"detail": "Invalid master OTP."}`.
If `MASTER_OTP_MOBILE_NUMBERS` is set to a non-empty list, numbers outside
that list get `403 {"detail": "Master OTP login is not permitted for this number."}`.

**Security note:** the master-OTP endpoint is a deliberate backdoor for
testing. Before shipping to production:
- Set `MASTER_OTP` to something long/random via an environment variable
  (never commit it to source control).
- Restrict `MASTER_OTP_MOBILE_NUMBERS` to your specific QA/test numbers.
- Consider disabling the endpoint entirely outside staging (e.g. only
  register the URL when `DEBUG=True` or an `ENABLE_MASTER_OTP` flag is on).

### Using the access token

Once you have `tokens.access`, call any authenticated endpoint with:
```
Authorization: Bearer <access_token>
```
(`rest_framework_simplejwt` is wired up as the default authentication
class in `REST_FRAMEWORK` settings.)

## Configuration (env vars, see `.env.example`)

| Variable | Default | Purpose |
|---|---|---|
| `OTP_LENGTH` | `6` | digits per OTP |
| `OTP_EXPIRY_MINUTES` | `5` | OTP validity window |
| `MAX_OTP_ATTEMPTS` | `3` | wrong-code attempts allowed per OTP |
| `RESEND_OTP_WAIT_SECONDS` | `30` | cooldown between resends |
| `MASTER_OTP` | `123456` | fixed code that bypasses SMS entirely |
| `MASTER_OTP_MOBILE_NUMBERS` | *(empty = any number)* | comma-separated allow-list |
| `SMS_BACKEND` | `console` | `console` or `twilio` |

## Domain APIs (catalog, cart, orders, admin console, ...)

Everything past login/profile — for both the customer app and the admin
console — lives in its own app, all under `/api/`. Full interactive docs
(request/response shapes, try-it-out) are at `/api/docs/` (Swagger) or
`/api/redoc/`; this is just the map.

| App | Base path | What it's for |
|---|---|---|
| `zones` | `/api/zones/` | Dark stores / delivery zones |
| `catalog` | `/api/categories/`, `/api/subcategories/`, `/api/products/`, `/api/product-images/`, `/api/reviews/`, `/api/stocks/` | Categories, products, product images, reviews, per-zone stock |
| `delivery` | `/api/partners/` | Delivery partner roster |
| `cart` | `/api/cart/`, `/api/cart/items/`, `/api/cart/coupon/`, `/api/wishlist/` | The logged-in customer's cart + wishlist |
| `orders` | `/api/orders/` (+ `place`, `cancel`, `set_status`, `assign_partner` actions) | Placing/tracking orders (customer) and managing them (admin) |
| `promotions` | `/api/coupons/`, `/api/banners/`, `/api/notifications/` | Coupons, home banners, push campaigns |
| `support` | `/api/tickets/` | Support tickets |
| `reports` | `/api/admin/reports/dashboard/`, `/sales/`, `/gst/` | Admin-only aggregate reports, computed live from real `Order` data — nothing here is a fabricated/mock number |
| `accounts` (extra) | `/api/auth/admin/customers/` | Admin-only customer directory with live order stats |

**Read vs. write is split by role, not by URL.** Browse-first resources
(categories, products, banners, coupons, zones) use
`core.permissions.IsAdminRoleOrReadOnly`: anyone — even logged out — can
`GET`/list them (so the customer app can browse before login), but only a
`role="admin"` user can create/update/delete. Purely admin resources
(inventory, delivery partners, reports, customer directory) use
`IsAdminRole` on every method. Cart/wishlist/orders/support are scoped to
`request.user` — a customer only ever sees their own.

**Orders are never created with a raw POST.** `POST /api/orders/place/`
builds an order from whatever's currently in the customer's cart (address
either by `address_id` from their saved `Profile.addresses`, or raw
`address_line1`/`city`/`state`/`pincode`), snapshots each line's price and
GST slab onto `OrderItem` so later product edits can't rewrite history, and
empties the cart. Status changes (`packed` → `out_for_delivery` →
`delivered`, or `cancelled`) go through `PATCH /api/orders/{id}/set_status/`
(admin) or `POST /api/orders/{id}/cancel/` (customer, only while
new/packed) — never a generic `PUT`.

**GST reporting is per-line, not a flat estimate.** Each `OrderItem` snapshots
its product's `gst_slab` (0/5/12/18%) at order time; `/api/admin/reports/gst/`
groups by that slab for real CGST/SGST/taxable-value/invoice-count numbers.
`input_credit` is reported as `0` rather than invented, since there's no
purchases/procurement ledger in this project to compute it from.

## Notes / things you may want to add later

- Rate limiting here uses DRF's `AnonRateThrottle` (`10/min` by default,
  see `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`) — tune per your traffic.
- Every OTP send/resend is logged as a row in the `OTP` table, so you get
  a free audit trail. Master-OTP logins are intentionally *not* logged
  there since no OTP was generated.
- The `User` model has a `name` field you can extend with more profile
  fields as needed.
