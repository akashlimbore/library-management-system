from django.db import models
from django.contrib.auth.models import User
from datetime import date, timedelta

class Book(models.Model):
    CATEGORY_CHOICES = [
        ('fiction', 'Fiction'),
        ('non_fiction', 'Non-Fiction'),
        ('science', 'Science'),
        ('technology', 'Technology'),
        ('history', 'History'),
        ('biography', 'Biography'),
        ('other', 'Other'),
    ]
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    isbn = models.CharField(max_length=20, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)
    published_year = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} by {self.author}"

    @property
    def is_available(self):
        return self.available_copies > 0


class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    member_id = models.CharField(max_length=20, unique=True)
    joined_on = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.member_id})"

    @property
    def pending_fine(self):
        total = sum(t.fine_amount for t in self.transaction_set.filter(is_returned=False) if t.is_overdue)
        return total


class Transaction(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    issued_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    returned_date = models.DateField(null=True, blank=True)
    is_returned = models.BooleanField(default=False)
    fine_paid = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.due_date = date.today() + timedelta(days=14)
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        if self.is_returned:
            return False
        return date.today() > self.due_date

    @property
    def days_overdue(self):
        if not self.is_overdue:
            return 0
        return (date.today() - self.due_date).days

    @property
    def fine_amount(self):
        return self.days_overdue * 2  # ₹2 per day fine

    def __str__(self):
        return f"{self.member.name} - {self.book.title}"
