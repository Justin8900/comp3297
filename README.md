# UniHaven API Documentation

## Overview

UniHaven is a RESTful API system for managing student accommodations at the University of Hong Kong. The system allows HKU members to search and reserve accommodations, while CEDARS specialists manage these accommodations and reservations.

## Authentication and Role-Based Access

All API endpoints use role-based access control. When making API requests, you must include role parameters:

### Role Parameters

1. **For HKU Members**:
   ```
   ?role=hku_member&current_user_id=YOUR_UID
   ```
   Example: `?role=hku_member&current_user_id=3035940999`

2. **For CEDARS Specialists**:
   ```
   ?role=cedars_specialist
   ```

These parameters must be included in all API requests to determine the appropriate access level.

## Installation and Setup

```bash
# Clone the repository
git clone https://github.com/Justin8900/comp3297.git

# Navigate to the project directory
cd comp3297

# Install Django
pip install django
pip install djangorestframework

# Run migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

The API will be available at http://localhost:8000/

## Using the Browsable API Interface

Django REST Framework provides a powerful browsable API interface that makes it easy to interact with the UniHaven API through your web browser.

### Getting Started with the Browsable API

1. Start the development server and navigate to http://localhost:8000/ in your web browser
2. You'll see a list of available API endpoints
3. Click on any endpoint to explore it
4. **Important**: Always append the required role parameters to the URL:
   - For HKU members: `?role=hku_member&current_user_id=YOUR_UID`
   - For CEDARS specialists: `?role=cedars_specialist`

### Making Requests

The browsable API interface allows you to:

1. **GET requests**: 
   - Simply navigate to the URL with appropriate parameters
   - Example: http://localhost:8000/accommodations/?role=hku_member&current_user_id=3035940999

2. **POST/PUT/PATCH requests**:
   - Navigate to the appropriate URL
   - Scroll down to find the HTML form
   - Fill in the required fields
   - Click the "POST", "PUT", or "PATCH" button to submit

3. **Using Filters**:
   - Add filter parameters to the URL
   - The browsable API will show you the filtered results
   - Example: http://localhost:8000/accommodations/?role=hku_member&current_user_id=3035940999&type=apartment

### Example Workflow

Here's how to reserve an accommodation using the browsable API:

1. Browse to http://localhost:8000/accommodations/?role=hku_member&current_user_id=3035940999 to see available accommodations
2. Note the ID of the accommodation you want to reserve
3. Navigate to http://localhost:8000/hku-members/3035940999/reserve_accommodation/?role=hku_member&current_user_id=3035940999
4. Fill in the form with:
   - accommodation_id: The ID you noted
   - start_date: Your check-in date
   - end_date: Your check-out date
5. Click "POST" to create the reservation

## API Endpoints

### Accommodations

#### List Accommodations
- **URL**: `/accommodations/`
- **Method**: GET
- **Required Role**: `hku_member` or `cedars_specialist`
- **Parameters**:
  - `role`: Required role parameter
  - `current_user_id`: Required for HKU members
  - Additional filter parameters (optional):
    - `type`: Filter by accommodation type
    - `min_price`/`max_price`: Filter by price range
    - `min_beds`: Filter by minimum number of beds
    - `address_contains`: Filter by address text
    - `available_now=true`: Show only currently available accommodations

**Example**:
```
# In your web browser:
http://localhost:8000/accommodations/?role=hku_member&current_user_id=3035940999
```

#### Get Accommodation Details
- **URL**: `/accommodations/{id}/`
- **Method**: GET
- **Required Role**: `hku_member` or `cedars_specialist`

**Example**:
```
# In your web browser:
http://localhost:8000/accommodations/1/?role=hku_member&current_user_id=3035940999
```

#### Search Accommodations
- **URL**: `/accommodations/search/`
- **Method**: GET
- **Required Role**: `hku_member` or `cedars_specialist`
- **Parameters**:
  - `type`: Filter by accommodation type (apartment, house, villa, studio, hostel)
  - `min_beds`: Filter by minimum number of beds
  - `exact_beds`: Filter by exact number of beds
  - `min_bedrooms`: Filter by minimum number of bedrooms
  - `exact_bedrooms`: Filter by exact number of bedrooms
  - `min_rating`: Filter by minimum rating (0-5)
  - `exact_rating`: Filter by exact rating (0-5)
  - `max_price`: Filter by maximum daily price
  - `available_from`: Filter by availability start date (YYYY-MM-DD)
  - `available_until`: Filter by availability end date (YYYY-MM-DD)
  - `distance_from`: Sort by distance from a specific HKU location (Main Campus, Sassoon Road Campus, Swire Institute of Marine Science, Kadoorie Centre, Faculty of Dentistry)

**Example**:
```
# In your web browser:
http://localhost:8000/accommodations/search/?role=hku_member&current_user_id=3035940999&type=apartment&min_beds=2&max_price=1500.00&distance_from=Main%20Campus
```

#### Create Accommodation
- **URL**: `/accommodations/`
- **Method**: POST
- **Required Role**: `cedars_specialist` only
- **Data Parameters**:
  - `type`: Accommodation type (required)
  - `address`: Physical address (required)
  - `available_from`: Start date of availability (required, YYYY-MM-DD)
  - `available_until`: End date of availability (required, YYYY-MM-DD)
  - `beds`: Number of beds (required, min: 0)
  - `bedrooms`: Number of bedrooms (required, min: 0)
  - `daily_price`: Price per day (required, min: 0.01)
  - `owner_id`: ID of existing property owner (optional)
  - `owner_name` and `owner_phone`: For creating a new owner (both required if owner_id not provided)
  - `specialist_id`: ID of managing specialist (optional)

**Example**:
```
# In your web browser:
1. Navigate to http://localhost:8000/accommodations/?role=cedars_specialist
2. Scroll down to the HTML form
3. Fill in all required fields
4. Click "POST" to submit
```

#### Update Accommodation
- **URL**: `/accommodations/{id}/`
- **Method**: PUT or PATCH
- **Required Role**: `cedars_specialist` only

#### Delete Accommodation
- **URL**: `/accommodations/{id}/`
- **Method**: DELETE
- **Required Role**: `cedars_specialist` only

### HKU Members

#### List HKU Members
- **URL**: `/hku-members/`
- **Method**: GET
- **Required Role**: `cedars_specialist` only

#### Get HKU Member Details
- **URL**: `/hku-members/{uid}/`
- **Method**: GET
- **Required Role**: `cedars_specialist` or the same HKU member (`current_user_id` must match `uid`)

#### View Member's Reservations
- **URL**: `/hku-members/{uid}/reservations/`
- **Method**: GET
- **Required Role**: `cedars_specialist` or the same HKU member (`current_user_id` must match `uid`)
- **Parameters**:
  - `status`: Filter by reservation status (optional, values: pending, confirmed, cancelled, completed)

**Example**:
```
# In your web browser:
http://localhost:8000/hku-members/3035940999/reservations/?role=hku_member&current_user_id=3035940999&status=confirmed
```

#### Reserve Accommodation
- **URL**: `/hku-members/{uid}/reserve_accommodation/`
- **Method**: POST
- **Required Role**: `cedars_specialist` or the same HKU member (`current_user_id` must match `uid`)
- **Data Parameters**:
  - `accommodation_id`: ID of the accommodation to reserve (required)
  - `start_date`: Start date of the reservation (required, YYYY-MM-DD)
  - `end_date`: End date of the reservation (required, YYYY-MM-DD)
  - `member_name`: Name of the HKU member (only required for first-time users)

**Example**:
```
# In your web browser:
1. Navigate to http://localhost:8000/hku-members/3035940999/reserve_accommodation/?role=hku_member&current_user_id=3035940999
2. Fill in the form with:
   - accommodation_id: The ID of the accommodation
   - start_date: Start date (YYYY-MM-DD)
   - end_date: End date (YYYY-MM-DD)
3. Click "POST" to submit
```

#### Cancel Reservation
- **URL**: `/hku-members/{uid}/cancel_reservation/`
- **Method**: POST
- **Required Role**: `cedars_specialist` or the same HKU member (`current_user_id` must match `uid`)
- **Data Parameters**:
  - `reservation_id`: ID of the reservation to cancel (required)

**Example**:
```
# In your web browser:
1. Navigate to http://localhost:8000/hku-members/3035940999/cancel_reservation/?role=hku_member&current_user_id=3035940999
2. Fill in the form with:
   - reservation_id: The ID of the reservation to cancel
3. Click "POST" to submit
```

#### Rate Accommodation
- **URL**: `/hku-members/{uid}/rate_accommodation/`
- **Method**: POST
- **Required Role**: The same HKU member only (`current_user_id` must match `uid`)
- **Data Parameters**:
  - `reservation_id`: ID of the completed reservation (required, status must be 'completed')
  - `score`: Rating score, 0-5 (required)
  - `comment`: Optional comment about the stay (optional)

**Example**:
```
# In your web browser:
1. Navigate to http://localhost:8000/hku-members/3035940999/rate_accommodation/?role=hku_member&current_user_id=3035940999
2. Fill in the form with:
   - reservation_id: The ID of the completed reservation
   - score: Rating from 0-5
   - comment: Optional feedback
3. Click "POST" to submit
```

### CEDARS Specialists

#### List CEDARS Specialists
- **URL**: `/cedars-specialists/`
- **Method**: GET
- **Required Role**: `cedars_specialist` only

#### Get CEDARS Specialist Details
- **URL**: `/cedars-specialists/{id}/`
- **Method**: GET
- **Required Role**: `cedars_specialist` only

#### View Managed Accommodations
- **URL**: `/cedars-specialists/{id}/managed_accommodations/`
- **Method**: GET
- **Required Role**: `cedars_specialist` only

**Example**:
```
# In your web browser:
http://localhost:8000/cedars-specialists/1/managed_accommodations/?role=cedars_specialist
```

#### Add Accommodation
- **URL**: `/cedars-specialists/{id}/add_accommodation/`
- **Method**: POST
- **Required Role**: `cedars_specialist` only
- **Data Parameters**: Same as Create Accommodation

**Example**:
```
# In your web browser:
1. Navigate to http://localhost:8000/cedars-specialists/1/add_accommodation/?role=cedars_specialist
2. Fill in the form with accommodation details
3. Click "POST" to submit
```

#### Update Accommodation
- **URL**: `/cedars-specialists/{id}/update_accommodation/`
- **Method**: POST
- **Required Role**: `cedars_specialist` only
- **Data Parameters**:
  - `accommodation_id`: ID of the accommodation to update (required)
  - Any additional fields to update

**Example**:
```
# In your web browser:
1. Navigate to http://localhost:8000/cedars-specialists/1/update_accommodation/?role=cedars_specialist
2. Fill in the form with:
   - accommodation_id: The ID of the accommodation to update
   - Any fields you want to change
3. Click "POST" to submit
```

#### Cancel Reservation
- **URL**: `/cedars-specialists/{id}/cancel_reservation/`
- **Method**: POST
- **Required Role**: `cedars_specialist` only
- **Data Parameters**:
  - `reservation_id`: ID of the reservation to cancel (required)

**Example**:
```
# In your web browser:
1. Navigate to http://localhost:8000/cedars-specialists/1/cancel_reservation/?role=cedars_specialist
2. Fill in the form with:
   - reservation_id: The ID of the reservation to cancel
3. Click "POST" to submit
```

### Reservations

#### List Reservations
- **URL**: `/reservations/`
- **Method**: GET
- **Required Role**: `cedars_specialist` only
- **Parameters**:
  - `member_id`: Filter by HKU member (optional)
  - `accommodation_id`: Filter by accommodation (optional)
  - `status`: Filter by status (optional, values: pending, confirmed, cancelled, completed)

**Example**:
```
# In your web browser:
http://localhost:8000/reservations/?role=cedars_specialist&status=pending
```

#### Get Reservation Details
- **URL**: `/reservations/{id}/`
- **Method**: GET
- **Required Role**: `cedars_specialist` or the reservation's HKU member

**Example**:
```
# In your web browser:
http://localhost:8000/reservations/1/?role=cedars_specialist
```

#### Confirm Reservation
- **URL**: `/reservations/{id}/confirm/`
- **Method**: POST
- **Required Role**: `cedars_specialist` only

**Example**:
```
# In your web browser:
1. Navigate to http://localhost:8000/reservations/1/confirm/?role=cedars_specialist
2. Click "POST" to confirm the reservation
```

### Ratings

#### List Ratings
- **URL**: `/ratings/`
- **Method**: GET
- **Required Role**: `hku_member` or `cedars_specialist`
- **Parameters**:
  - `reservation_id`: Filter by reservation (optional)
  - `accommodation_id`: Filter by accommodation (optional)
  - `member_id`: Filter by HKU member (optional)

**Example**:
```
# In your web browser:
http://localhost:8000/ratings/?role=cedars_specialist&accommodation_id=1
```

#### Get Rating Details
- **URL**: `/ratings/{id}/`
- **Method**: GET
- **Required Role**: `hku_member` or `cedars_specialist`

**Example**:
```
# In your web browser:
http://localhost:8000/ratings/1/?role=cedars_specialist
```

## Data Models

### PropertyOwner
- `id`: Unique identifier
- `name`: Name of the property owner
- `phone_no`: Phone number of the property owner

### CEDARSSpecialist
- `id`: Unique identifier
- `name`: Name of the CEDARS specialist
- Methods: addAccommodation(), updateAccommodation(), cancelReservation(), viewReservations(), receiveNotifications()

### Accommodation
- `type`: Type of accommodation (apartment, house, villa, studio, hostel)
- `address`: Physical address
- `latitude`: Latitude coordinate (auto-populated)
- `longitude`: Longitude coordinate (auto-populated)
- `geo_address`: Geocoded address (auto-populated)
- `available_from`: Start date of availability
- `available_until`: End date of availability
- `beds`: Number of beds
- `bedrooms`: Number of bedrooms
- `daily_price`: Price per day
- `owner`: Reference to PropertyOwner
- `specialist`: Reference to CEDARSSpecialist

### HKUMember
- `uid`: Unique identifier (primary key)
- `name`: Name of the HKU member
- Methods: searchAccommodation(), reserveAccommodation(), cancelReservation(), rateAccommodation()

### Reservation
- `status`: Status of the reservation (pending, confirmed, cancelled, completed)
- `start_date`: Start date of the reservation
- `end_date`: End date of the reservation
- `cancelled_by`: Who cancelled the reservation (if applicable)
- `member`: Reference to HKUMember
- `accommodation`: Reference to Accommodation

### Rating
- `score`: Rating score between 0 and 5
- `date_rated`: Date when the rating was submitted
- `comment`: Optional comment for the rating
- `reservation`: Reference to Reservation

## Notification System

The system automatically sends notifications (emails in production) for the following events:

1. **Reservation Confirmation**: When a new reservation is created
2. **Status Updates**: When a reservation's status changes (confirmed, cancelled, completed)

In development mode, these notifications are printed to the console.

## Limitations and Notes

1. This API uses role-based access control through query parameters instead of token-based authentication.
2. Geocoding of addresses is handled automatically for accommodations.
3. New HKU members are automatically created in the system when they make their first reservation.
4. Ratings can only be created for reservations with 'completed' status.
5. All date fields should use the YYYY-MM-DD format.