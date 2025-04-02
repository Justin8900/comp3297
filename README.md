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