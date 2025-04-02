## Installation 
```bash
git clone https://github.com/Justin8900/comp3297.git
```

```bash
pip install django~=5.1.7
```

## Run
```bash
 python manage.py runserver
```

## User Guide

### Adding Accommodations
1. To view all accommodations:
   - Visit: http://localhost:8000/accommodations/
   - You'll see a list of all available accommodations

2. To add a new accommodation:
   - Visit: http://localhost:8000/accommodations/
   - Click the "POST" button
   - Fill in the form:
     - Type: Select from apartment, house, villa, studio, or hostel
     - Address: Enter the full address
     - Available From/Until: Select dates using the calendar
     - Beds: Enter number of beds
     - Bedrooms: Enter number of bedrooms
     - Rating: Enter rating (0-5)
     - Daily Price: Enter price per day
     - Property Owner: You have two options:
       * Select an existing owner from the dropdown list
       * Create a new owner by filling in:
         - New Owner Name: Enter the owner's name
         - New Owner Contact: Enter contact information
   - Click "POST" to submit

3. To search for accommodations:
   - Base URL: http://localhost:8000/accommodations/search/
   - Use URL query parameters to filter results. Add parameters using ?parameter=value and combine multiple parameters with &
   
   Available Parameters:
   - type: Filter by accommodation type
     * Values: apartment, house, villa, studio, hostel
     * Example: ?type=apartment
   
   - min_beds: Filter by minimum number of beds
     * Values: any positive integer
     * Example: ?min_beds=2
   
   - exact_beds: Filter by exact number of beds
     * Values: any positive integer
     * Example: ?exact_beds=3
   
   - min_bedrooms: Filter by minimum number of bedrooms
     * Values: any positive integer
     * Example: ?min_bedrooms=2
   
   - exact_bedrooms: Filter by exact number of bedrooms
     * Values: any positive integer
     * Example: ?exact_bedrooms=2
   
   - min_rating: Filter by minimum rating
     * Values: 0-5
     * Example: ?min_rating=4
   
   - exact_rating: Filter by exact rating
     * Values: 0-5
     * Example: ?exact_rating=5
   
   - max_price: Filter by maximum daily price
     * Values: any positive decimal
     * Example: ?max_price=150.00
   
   - available_from: Filter by availability start date
     * Format: YYYY-MM-DD
     * Example: ?available_from=2024-04-02
   
   - available_until: Filter by availability end date
     * Format: YYYY-MM-DD
     * Example: ?available_until=2024-12-31
   
   - distance_from: Sort results by distance from a specific HKU building
     * Values (must use exact names):
       * Main Campus
       * Sassoon Road Campus
       * Swire Institute of Marine Science
       * Kadoorie Centre
       * Faculty of Dentistry
     * Example: ?distance_from=Main%20Campus
     * Note: When using distance_from, results include a distance_km field
   
   Example Combinations:
   1. Find apartments with at least 2 beds under $150/day near Main Campus:
      ```
      /accommodations/search/?type=apartment&min_beds=2&max_price=150.00&distance_from=Main%20Campus
      ```
   
   2. Find highly-rated (4+) accommodations available from April to December:
      ```
      /accommodations/search/?min_rating=4&available_from=2024-04-01&available_until=2024-12-31
      ```
   
   3. Find exactly 2-bedroom places near Sassoon Road Campus:
      ```
      /accommodations/search/?exact_bedrooms=2&distance_from=Sassoon%20Road%20Campus
      ```

   Response Format:
   ```json
   [
     {
       "id": 1,
       "type": "apartment",
       "address": "123 Test Street",
       "beds": 2,
       "bedrooms": 1,
       "rating": 4,
       "daily_price": "100.00",
       "available_from": "2024-04-02",
       "available_until": "2024-12-31",
       "distance_km": 5.52  // Only included when using distance_from
     }
   ]
   ```

### Viewing Data
1. To view all accommodations:
   - Visit: http://localhost:8000/accommodations/
   - You'll see a list of all available accommodations with their details

2. To view all HKU members:
   - Visit: http://localhost:8000/hku-members/
   - You'll see a list of all registered HKU members

3. To view all CEDARS specialists:
   - Visit: http://localhost:8000/cedars-specialists/
   - You'll see a list of all CEDARS specialists

## Limitations
- Search
    - The search according to distance from a specified building must use exact wordings, no typo can be accepted
    - no specific message would be popped up if the nothing match the requirements

- Accommodation Addition
    - No validation for duplicate addresses
    - No validation for overlapping availability dates
    - No support for bulk additions
    - No support for amenities, images, or media
    - No support for different pricing tiers or room types
    - No validation for price ranges based on accommodation type
    - No validation for bed/bedroom counts based on type

- Property Owner Addition
    - No validation for duplicate owner names
    - No validation for contact information format
    - No support for multiple contact methods
    - No support for business registration or verification
    - No support for owner preferences or payment information