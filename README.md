# UniHaven API

## Overview

UniHaven is a Django REST Framework API designed to manage student accommodation listings and reservations across multiple universities (initially HKU, CUHK, HKUST).

It provides endpoints for University Specialists to manage properties and related entities, and for University Members (students/staff) to search for accommodations, make reservations, and provide ratings.

## Features

*   **Multi-University Support:** Designed to handle members, specialists, and accommodations linked to specific universities (HKU, CU, HKUST).
*   **Role-Based Access:** API access is controlled via a `role` query parameter, differentiating between Members and Specialists from specific universities.
*   **Accommodation Management:** CRUD operations for accommodation listings, including detailed address components (room, flat, floor), availability, pricing, and university association.
*   **Geocoding & Nearby Search:** Automatic geocoding of accommodation addresses (latitude/longitude) and an endpoint to find accommodations near specific university locations.
*   **Member & Specialist Management:** Basic CRUD operations for university members and specialists, filtered by university.
*   **Property Owner Management:** CRUD operations for property owners associated with accommodations.
*   **Reservation System:** Members can reserve accommodations; specialists can manage and confirm reservations for their university.
*   **Rating System:** Members can rate accommodations based on completed reservations.
*   **Targeted Notifications:** Automated notifications (e.g., via email/console backend) are sent to the relevant university specialists when actions like new reservations occur.
*   **API Documentation:** Auto-generated OpenAPI 3 schema using `drf-spectacular`.

## API Structure & Role Parameter

The API primarily uses a role-based access system controlled by the `role` query parameter, which must be included in most requests.

The format is: `uni_code:role_type:id`

*   `uni_code`: Lowercase university code (e.g., `hku`, `cu`, `hkust`).
*   `role_type`: Either `member` or `specialist`.
*   `id`: The Member's UID (e.g., `u1234567`) or the Specialist's database ID (e.g., `1`). The ID may be optional for some general specialist list actions.

**Example:**
`GET /api/v1/accommodations/?role=hku:member:u1234567`
`POST /api/v1/members/?role=cu:specialist:2`

Permissions are enforced based on this role parameter and the context of the requested resource (e.g., ensuring users only access data relevant to their university).

## Key Models

*   `University`: Represents HKU, CUHK, HKUST.
*   `PropertyOwner`: Represents owners of accommodation properties.
*   `Member`: Represents a student or staff member belonging to a specific University.
*   `Specialist`: Represents an administrative user belonging to a specific University, responsible for management tasks.
*   `Accommodation`: Represents a rentable property with details and links to `PropertyOwner` and the `University` entities where it is available.
*   `Reservation`: Represents a booking made by a `Member` for an `Accommodation`.
*   `Rating`: Represents a rating given by a `Member` for a completed `Reservation`.
*   `UniversityLocation`: Represents specific named locations within a university for distance calculations.

## Setup & Running

1.  **Prerequisites:**
    *   Python 3.x
    *   Django
    *   Django REST Framework
    *   drf-spectacular
    *   (Add other dependencies if any - check `requirements.txt`)

2.  **Clone the Repository:** (Assuming it's in version control)
    ```bash
    git clone <your-repo-url>
    cd <repo-directory>/comp3297
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
    *   **Universities:** Create the University records if they don't exist:
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

6.  **Run Development Server:**
    ```bash
    python manage.py runserver
    ```
    The API should be accessible at `http://127.0.0.1:8000/` (or the specified address/port).

## API Documentation

The OpenAPI 3 schema is automatically generated using `drf-spectacular`.

*   **Schema File:** The schema is generated into the `schema.yml` file in the project root.
*   **Regenerate Schema:** To update the schema file after code changes, run:
    ```bash
    # Run from the comp3297 directory
    python manage.py spectacular --file ../schema.yml --color
    ```
*   **Swagger UI:** (If configured in `urls.py`) Access interactive documentation via a browser at `/api/schema/swagger-ui/`.
*   **ReDoc:** (If configured in `urls.py`) Access alternative documentation via a browser at `/api/schema/redoc/`.

Refer to `schema.yml` or the UI endpoints for detailed information on all available API endpoints, parameters, request bodies, and response schemas.

## Testing

Automated tests are written using Django's `APITestCase`.

*   **Run All Tests:**
    ```bash
    # Run from the comp3297 directory
    python manage.py test unihaven
    ```
*   **Run Specific Test File:**
    ```bash
    python manage.py test unihaven.test.test_accommodations
    ```
