from django.contrib.auth.models import AbstractUser, User
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.conf import settings

class CustomUser(AbstractUser):
    is_admin = models.BooleanField(default=False)
    admin_code = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
        ('Prefer not to say', 'Prefer not to say'),
    ])
    dob = models.DateField(blank=True, null=True)
    medical_condition = models.CharField(max_length=100, blank=True, null=True, choices=[
        ('None', 'None'),
        ('Diabetes', 'Diabetes'),
        ('Hypertension', 'Hypertension'),
        ('Asthma', 'Asthma'),
        ('Allergy (Peanut)', 'Allergy (Peanut)'),
        ('Allergy (Lactose)', 'Allergy (Lactose)'),
        ('Heart Disease', 'Heart Disease'),
        ('Other', 'Other'),
    ])
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email

class Product(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    name = models.CharField(max_length=200)
    manufacture_date = models.DateField()
    expire_date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('Available', 'Available'),
        ('Donated', 'Donated'),
        ('Thrown', 'Thrown'),
    ], default='Available')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class Donation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='donations',
        help_text="The user making the donation."
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='donations',
        help_text="The product being donated."
    )
    donor_name = models.CharField(
        max_length=255,
        help_text="Name of the donor or organization."
    )
    contact_email = models.EmailField(
        help_text="Contact email for donation coordination."
    )
    contact_number = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^[0-9+\-\s]{7,15}$',
                message="Phone number must be 7-15 characters, including digits, +, -, and spaces."
            )
        ],
        help_text="Contact phone number (e.g., +977-9841000000)."
    )
    pickup_address = models.TextField(
        help_text="Full address for donation pickup."
    )
    pickup_datetime = models.DateTimeField(
        help_text="Preferred date and time for pickup."
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes or special instructions (optional)."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the donation was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the donation was last updated."
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Donation"
        verbose_name_plural = "Donations"

    def __str__(self):
        return f"Donation of {self.product.name} by {self.donor_name}"

class CommunityReport(models.Model):
    reporter_name = models.CharField(max_length=100)
    item_name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    issue_type = models.CharField(max_length=100)
    description = models.TextField()
    photo = models.ImageField(upload_to='reports/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Comment(models.Model):
    report = models.ForeignKey(CommunityReport, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
