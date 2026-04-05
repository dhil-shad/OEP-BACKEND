import os
import django
from django.conf import settings

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'OEP.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.serializers import UserRegistrationSerializer
from rest_framework import serializers

User = get_user_model()

def test_email_uniqueness():
    print("Testing email uniqueness...")
    email = "test_unique@example.com"
    
    # Create first user
    if User.objects.filter(email=email).exists():
        User.objects.filter(email=email).delete()
        
    User.objects.create_user(username="user1", email=email, password="password123")
    print("Created user1 with email:", email)
    
    # Try to create second user with same email via serializer
    data = {
        "username": "user2",
        "email": email,
        "password": "password123",
        "role": "STUDENT"
    }
    
    serializer = UserRegistrationSerializer(data=data)
    if not serializer.is_valid():
        errors = serializer.errors
        print("Validation failed as expected:", errors)
        if 'email' in errors and 'This email is already in use.' in str(errors['email']):
            print("SUCCESS: Custom error message for email uniqueness found.")
        else:
            print("FAILURE: Expected custom error message not found in:", errors)
    else:
        print("FAILURE: Serializer allowed duplicate email!")

def test_username_uniqueness():
    print("\nTesting username uniqueness...")
    username = "test_user_unique"
    
    # Create first user
    if User.objects.filter(username=username).exists():
        User.objects.filter(username=username).delete()
        
    User.objects.create_user(username=username, email="test1@example.com", password="password123")
    print("Created first user with username:", username)
    
    # Try to create second user with same username
    data = {
        "username": username,
        "email": "test2@example.com",
        "password": "password123",
        "role": "STUDENT"
    }
    
    serializer = UserRegistrationSerializer(data=data)
    if not serializer.is_valid():
        errors = serializer.errors
        print("Validation failed as expected:", errors)
        if 'username' in errors and 'This username is already taken.' in str(errors['username']):
            print("SUCCESS: Custom error message for username uniqueness found.")
        else:
            print("FAILURE: Expected custom error message not found in:", errors)
    else:
        print("FAILURE: Serializer allowed duplicate username!")

if __name__ == "__main__":
    try:
        test_email_uniqueness()
        test_username_uniqueness()
    except Exception as e:
        print("An error occurred during testing:", e)
    finally:
        # Cleanup
        User.objects.filter(username__in=["user1", "user2", "test_user_unique"]).delete()
