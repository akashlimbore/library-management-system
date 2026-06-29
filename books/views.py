from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Q
from datetime import date
from .models import Book, Member, Transaction


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    total_books = Book.objects.count()
    total_members = Member.objects.filter(is_active=True).count()
    active_issues = Transaction.objects.filter(is_returned=False).count()
    overdue = Transaction.objects.filter(is_returned=False)
    overdue_count = sum(1 for t in overdue if t.is_overdue)
    recent_transactions = Transaction.objects.select_related('book', 'member').order_by('-issued_date')[:5]
    context = {
        'total_books': total_books,
        'total_members': total_members,
        'active_issues': active_issues,
        'overdue_count': overdue_count,
        'recent_transactions': recent_transactions,
        'today': date.today(),
    }
    return render(request, 'dashboard.html', context)


@login_required
def book_list(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    books = Book.objects.all()
    if query:
        books = books.filter(Q(title__icontains=query) | Q(author__icontains=query) | Q(isbn__icontains=query))
    if category:
        books = books.filter(category=category)
    return render(request, 'books/list.html', {'books': books, 'query': query, 'category': category, 'categories': Book.CATEGORY_CHOICES})


@login_required
def book_add(request):
    if request.method == 'POST':
        try:
            total_copies = int(request.POST.get('total_copies') or 1)
            published_year = request.POST.get('published_year', '').strip()
            book = Book(
                title=request.POST['title'],
                author=request.POST['author'],
                isbn=request.POST['isbn'],
                category=request.POST['category'],
                total_copies=total_copies,
                available_copies=total_copies,
                published_year=int(published_year) if published_year else None,
                description=request.POST.get('description', ''),
            )
            book.save()
            messages.success(request, f'Book "{book.title}" added successfully!')
            return redirect('book_list')
        except ValueError as e:
            messages.error(request, f'Invalid input — check Total Copies and Published Year.')
    return render(request, 'books/form.html', {'categories': Book.CATEGORY_CHOICES, 'action': 'Add'})


@login_required
def book_edit(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        book.title = request.POST['title']
        book.author = request.POST['author']
        book.isbn = request.POST['isbn']
        book.category = request.POST['category']
        book.published_year = request.POST.get('published_year') or None
        book.description = request.POST.get('description', '')
        book.save()
        messages.success(request, f'Book "{book.title}" updated!')
        return redirect('book_list')
    return render(request, 'books/form.html', {'book': book, 'categories': Book.CATEGORY_CHOICES, 'action': 'Edit'})


@login_required
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        book.delete()
        messages.success(request, 'Book deleted.')
        return redirect('book_list')
    return render(request, 'books/confirm_delete.html', {'object': book, 'type': 'Book'})


@login_required
def member_list(request):
    query = request.GET.get('q', '')
    members = Member.objects.all()
    if query:
        members = members.filter(Q(name__icontains=query) | Q(email__icontains=query) | Q(member_id__icontains=query))
    return render(request, 'members/list.html', {'members': members, 'query': query})


@login_required
def member_add(request):
    if request.method == 'POST':
        import random, string
        mid = 'LIB' + ''.join(random.choices(string.digits, k=5))
        member = Member(
            name=request.POST['name'],
            email=request.POST['email'],
            phone=request.POST['phone'],
            member_id=mid,
        )
        member.save()
        messages.success(request, f'Member "{member.name}" added! ID: {mid}')
        return redirect('member_list')
    return render(request, 'members/form.html', {'action': 'Add'})


@login_required
def member_edit(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == 'POST':
        member.name = request.POST['name']
        member.email = request.POST['email']
        member.phone = request.POST['phone']
        member.save()
        messages.success(request, 'Member updated!')
        return redirect('member_list')
    return render(request, 'members/form.html', {'member': member, 'action': 'Edit'})


@login_required
def member_delete(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == 'POST':
        member.delete()
        messages.success(request, 'Member deleted.')
        return redirect('member_list')
    return render(request, 'books/confirm_delete.html', {'object': member, 'type': 'Member'})


@login_required
def issue_book(request):
    books = Book.objects.filter(available_copies__gt=0)
    members = Member.objects.filter(is_active=True)
    if request.method == 'POST':
        book = get_object_or_404(Book, pk=request.POST['book'])
        member = get_object_or_404(Member, pk=request.POST['member'])
        if book.available_copies <= 0:
            messages.error(request, 'No copies available!')
            return redirect('issue_book')
        t = Transaction(book=book, member=member)
        t.save()
        book.available_copies -= 1
        book.save()
        messages.success(request, f'"{book.title}" issued to {member.name}. Due: {t.due_date}')
        return redirect('transactions')
    return render(request, 'transactions/issue.html', {'books': books, 'members': members})


@login_required
def return_book(request, pk):
    t = get_object_or_404(Transaction, pk=pk)
    if request.method == 'POST':
        t.is_returned = True
        t.returned_date = date.today()
        t.save()
        t.book.available_copies += 1
        t.book.save()
        if t.fine_amount > 0:
            messages.warning(request, f'Book returned! Fine: ₹{t.fine_amount} for {t.days_overdue} days overdue.')
        else:
            messages.success(request, f'Book "{t.book.title}" returned successfully!')
        return redirect('transactions')
    return render(request, 'transactions/return_confirm.html', {'transaction': t})


@login_required
def transactions(request):
    txns = Transaction.objects.select_related('book', 'member').order_by('-issued_date')
    status = request.GET.get('status', '')
    if status == 'active':
        txns = txns.filter(is_returned=False)
    elif status == 'returned':
        txns = txns.filter(is_returned=True)
    elif status == 'overdue':
        txns = [t for t in txns.filter(is_returned=False) if t.is_overdue]
    return render(request, 'transactions/list.html', {'transactions': txns, 'status': status})