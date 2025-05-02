# UniHaven API

## Overview

UniHaven is a Django REST Framework API designed to manage student accommodation listings and reservations across multiple universities (initially HKU, CUHK, HKUST).

It provides endpoints for University Specialists to manage properties and related entities, and for University Members (students/staff) to search for accommodations, make reservations, and provide ratings. Access control is primarily managed through a `role` query parameter.

## Features

*   **Multi-University Support:** Designed to handle members, specialists, and accommodations linked to specific universities (HKU, CU, HKUST).
*   **Role-Based Access:** API access is controlled via a `role` query parameter, differentiating between Members and Specialists from specific universities.
*   **Accommodation Management:** CRUD operations for accommodation listings, including detailed address components, availability, pricing, and university association.
*   **Geocoding:** Automatic geocoding of accommodation addresses (latitude/longitude) based on building name or address.
*   **Member & Specialist Management:** Basic CRUD operations for university members and specialists, filtered by university.
*   **Property Owner Management:** CRUD operations for property owners associated with accommodations.
*   **Reservation System:** Members can reserve accommodations; specialists can manage and confirm/cancel reservations for their university. Members can only cancel their own *pending* reservations.
*   **Rating System:** Members can rate accommodations based on completed reservations. Ratings are visible to members/specialists within the same university as the reservation.
*   **Targeted Notifications:** Automated console/email notifications for actions like new reservations or cancellations.
*   **API Documentation:** Auto-generated OpenAPI 3 schema using `drf-spectacular`.

## API Structure & Role Parameter

The API primarily uses a role-based access system controlled by the `role` query parameter, which must be included in most requests. Endpoints are accessed directly from the root URL (e.g., `/accommodations/`).

The `role` parameter format is: `uni_code:role_type:id`

*   `uni_code`: Lowercase university code (e.g., `hku`, `cu`, `hkust`).
*   `role_type`: Either `member` or `specialist`.
*   `id`: The Member's UID (e.g., `resmem1`) or the Specialist's database ID (e.g., `1`). The ID may be optional for some general specialist list actions.

**Example:**
`GET /accommodations/?role=hku:member:resmem1`
`POST /members/?role=cu:specialist:2`

Permissions are enforced based on this role parameter and the context of the requested resource (e.g., ensuring users only access data relevant to their university or ownership).

## API Usage Examples (curl)

*(Replace BASE_URL, university codes, member UIDs, specialist IDs, and resource IDs as needed)*

**1. Member Lists Accommodations at their University:**
```bash
export BASE_URL="http://127.0.0.1:8000"
export MEMBER_ROLE="hku:member:resmem1"

curl -X GET "$BASE_URL/accommodations/?role=$MEMBER_ROLE"
```

**2. Member Creates a Reservation:**
```bash
export BASE_URL="http://127.0.0.1:8000"
export MEMBER_ROLE="hku:member:resmem1"
export ACC_ID=1 # ID of the accommodation to reserve

curl -X POST "$BASE_URL/reservations/?role=$MEMBER_ROLE" \
     -H "Content-Type: application/json" \
     -d '{
           "accommodation": '"$ACC_ID"', 
           "start_date": "2026-10-01", 
           "end_date": "2026-10-10"
         }'
```

**3. Specialist Lists All Pending Reservations for their University:**
```bash
export BASE_URL="http://127.0.0.1:8000"
export SPEC_ROLE="hku:specialist:1"

curl -X GET "$BASE_URL/reservations/?role=$SPEC_ROLE&status=pending"
```

**4. Specialist Confirms a Reservation:**
```bash
export BASE_URL="http://127.0.0.1:8000"
export SPEC_ROLE="hku:specialist:1"
export RES_ID=12 # ID of the reservation to confirm

curl -X PATCH "$BASE_URL/reservations/$RES_ID/?role=$SPEC_ROLE" \
     -H "Content-Type: application/json" \
     -d '{"status": "confirmed"}'
```

**5. Member Cancels Own Pending Reservation:**
```bash
export BASE_URL="http://127.0.0.1:8000"
export MEMBER_ROLE="hku:member:resmem1"
export RES_ID=11 # ID of the PENDING reservation to cancel

curl -X PATCH "$BASE_URL/reservations/$RES_ID/?role=$MEMBER_ROLE" \
     -H "Content-Type: application/json" \
     -d '{"status": "cancelled"}'
```

**6. Member Rates a Completed Reservation:**
```bash
export BASE_URL="http://127.0.0.1:8000"
export MEMBER_ROLE="hku:member:resmem1"
export COMPLETED_RES_ID=10 # ID of the COMPLETED reservation

curl -X POST "$BASE_URL/ratings/?role=$MEMBER_ROLE" \
     -H "Content-Type: application/json" \
     -d '{
           "reservation": '"$COMPLETED_RES_ID"', 
           "score": 5, 
           "comment": "Excellent stay!"
         }'
```

**7. Specialist Deletes a Rating:**
```bash
export BASE_URL="http://127.0.0.1:8000"
export SPEC_ROLE="hku:specialist:1"
export RATING_ID=3 # ID of the rating to delete

curl -X DELETE "$BASE_URL/ratings/$RATING_ID/?role=$SPEC_ROLE"
```

**8. Specialist Creates a Member:**
```bash
export BASE_URL="http://127.0.0.1:8000"
export SPEC_ROLE="hku:specialist:1"

curl -X POST "$BASE_URL/members/?role=$SPEC_ROLE" \
     -H "Content-Type: application/json" \
     -d '{
           "uid": "newmem123", 
           "name": "New HKU Member", 
           "phone_number": "55554444", 
           "email": "newmem@hku.hk"
         }'
```

## Key Models

*   `University`: Represents HKU, CUHK, HKUST.
*   `PropertyOwner`: Represents owners of accommodation properties.
*   `Member`: Represents a student or staff member belonging to a specific University.
*   `Specialist`: Represents an administrative user belonging to a specific University, responsible for management tasks.
*   `Accommodation`: Represents a rentable property with details and links to `PropertyOwner` and the `University` entities where it is available.
*   `Reservation`: Represents a booking made by a `Member` for an `Accommodation`. Status flow includes pending, confirmed, completed, cancelled.
*   `Rating`: Represents a rating given by a `Member` for a completed `Reservation`.
*   `UniversityLocation`: Represents specific named locations within a university (used for potential distance calculations - functionality not fully tested here).

## Setup & Running

1.  **Prerequisites:**
    *   Python 3.x
    *   Django
    *   Django REST Framework (`djangorestframework`)
    *   drf-spectacular
    *   (Review `requirements.txt` for a complete list if available)

2.  **Navigate to Project Directory:**
    ```bash
    cd <path-to-project>/comp3297
    ```

3.  **Install Dependencies:** (Assuming a `requirements.txt` exists)
    ```bash
    pip install -r requirements.txt
    ```

4.  **Database Setup:**
    *   The project uses SQLite by default (`db.sqlite3`).
    *   Apply migrations to create the database schema:
        ```bash
        python manage.py migrate
        ```

5.  **Create Initial Data (Recommended):**
    *   **Universities:** Create the University records:
        ```bash
        python manage.py shell
        >>> from unihaven.models import University
        >>> University.objects.get_or_create(code='HKU', defaults={'name': 'University of Hong Kong'})
        >>> University.objects.get_or_create(code='CU', defaults={'name': 'Chinese University of Hong Kong'})
        >>> University.objects.get_or_create(code='HKUST', defaults={'name': 'Hong Kong University of Science and Technology'})
        >>> exit()
        ```
    *   **Superuser (for admin access/testing):**
        ```bash
        python manage.py createsuperuser
        ```
    *   **Initial Specialists/Members/Owners:** You may need to create initial data via the Django admin (`/admin/`, requires superuser login) or API calls (using the superuser role or after creating initial specialists) to perform some actions. For example, creating members requires a specialist role.

6.  **Run Development Server:**
    ```bash
    python manage.py runserver
    ```
    The API should be accessible at `http://127.0.0.1:8000/`.

## API Documentation

The OpenAPI 3 schema is automatically generated using `drf-spectacular`.

*   **Schema File Generation:** To generate/update the `schema.yml` file in the parent directory:
    ```bash
    # Run from the comp3297 directory
    python manage.py spectacular --file ../schema.yml --color
    ```
*   **Swagger UI:** (If configured in `COMP3297/urls.py`) Access interactive documentation via a browser, typically at `/api/schema/swagger-ui/`.
*   **ReDoc:** (If configured in `COMP3297/urls.py`) Access alternative documentation via a browser, typically at `/api/schema/redoc/`.

Refer to the generated `schema.yml` or the UI endpoints for detailed information on all available API endpoints, parameters, request bodies, and response schemas.

## Testing

Automated API tests are included.

*   **Run All Tests:**
    ```bash
    # Run from the comp3297 directory
    python manage.py test unihaven.tests
    ```
