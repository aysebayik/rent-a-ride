import copy
import urllib
from datetime import datetime
from urllib import parse

from background_task import background
from django.core import serializers
from django.dispatch import receiver
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserChangeForm
from django.urls import reverse
from django.views.generic import ListView
from account.forms import EditProfileForm
from .filters import CarFilter, ReservationFilter

from .models import Car, Reservation, PrivateMsg, CarDealer, Branch, Customer, Admin, Profile, Notifications
from .forms import CarForm, ReservationSearchForm, MessageForm, ReservationForm, CreditCardForm, ApproveCarDealer, \
    BranchForm, UserDeleteForm


def home(request):
    context = {
        "title": "RentACar",
        "locations": Branch.objects.all().values('branch_name')
    }
    return render(request, 'home.html', context)


def available_cars(request):
    request_data = copy.deepcopy(request.POST)
    dates = request_data['dates'].split(' - ')
    request_data['pickUpDate'] = dates[0]
    request_data['returnDate'] = dates[1]

    data = ReservationSearchForm(request_data).data

    start_date_date = datetime.strptime(data['pickUpDate'], '%m/%d/%Y').strftime("%Y-%m-%d")
    end_date_date = datetime.strptime(data['returnDate'], '%m/%d/%Y').strftime("%Y-%m-%d")

    if datetime.strptime(data['pickUpDate'], '%m/%d/%Y') <= datetime.now():
        return HttpResponse('Start date cannot selected from past!')

    busy_cars = Reservation.busy_cars(start_date_date, end_date_date)

    branch_name = Branch.get_by_branch_name(data['pickUpLocation'])
    cars = Car.search_for_car(busy_cars, branch_name[0])

    if len(cars) == 0:
        return HttpResponse('No available cars')

    context = {
        "title": "RentACar",
        'cars': cars,
        'pickUpDate': start_date_date,
        'returnDate': end_date_date,
        'pickUpLocation': data['pickUpLocation'],
        'returnLocation': data['returnLocation']
    }
    return render(request, 'car/available_cars.html', context)


@login_required()
def create_reservation(request, car_id, pickUpLocation, returnLocation, pickUpDate, returnDate):
    car = Car.objects.get(id=car_id)
    start_date_date = datetime.strptime(pickUpDate, '%Y-%m-%d')
    end_date_date = datetime.strptime(returnDate, '%Y-%m-%d')
    form = ReservationForm(initial={
        'car': car,
        'customer': request.user,
        'pickUpLocation': pickUpLocation,
        'returnLocation': returnLocation,
        'pickUpDate': pickUpDate,
        'returnDate': returnDate,
        'total_price': car.price * (end_date_date - start_date_date).days
    })
    card_form = CreditCardForm()

    context = {
        "title": "RentACar",
        "reservation_form": form,
        "car_detail": car,
        "card_form": card_form
    }

    return render(request, 'reservation/reservation_order.html', context)


@login_required()
def complete_reservation(request):
    posted_data = request.GET
    branch_name = request.GET.get('pickUpLocation')
    customer_name = request.GET.get('customer_name')
    form = ReservationForm(posted_data)
    credit_form = CreditCardForm(posted_data)
    user = request.user
    customers = Customer.objects.filter(user=user)
    car_dealers = CarDealer.objects.filter(user=user)
    branch = Branch.objects.filter(branch_name=branch_name)[0]
    status = False
    if form.is_valid() and len(customers) == 0 and not request.is_ajax():
        reservation = form.save(commit=False)
        reservation.paymentStatus = False
        reservation.carDealer = car_dealers[0]
        reservation.customer_name = customer_name
        branch.rank += 10
        branch.save()
        reservation.save()
        status = True
    elif form.is_valid() and credit_form.is_valid() and not request.is_ajax():
        reservation = form.save(commit=False)
        reservation.paymentStatus = True
        reservation.customer = customers[0]
        branch.rank += 10
        branch.save()
        reservation.save()
        status = True

    context = {
        "title": "RentACar",
        "status": status
    }

    return render(request, 'reservation/reservation_approve.html', context)


def car_list_old(request):
    car = Car.objects.all()

    query = request.GET.get('q')
    if query:
        car = car.filter(
            Q(carName__icontains=query) |
            Q(model__icontains=query) |
            Q(numOfSeats__icontains=query) |
            Q(numOfDoors__icontains=query) |
            Q(transmission=query) |
            Q(airconditioner__icontains=query) |
            Q(price__icontains=query) |
            Q(carStatus__icontains=query)
        )

    paginator = Paginator(car, 12)
    page = request.GET.get('page')
    try:
        car = paginator.page(page)
    except PageNotAnInteger:
        car = paginator.page(1)
    except EmptyPage:
        car = paginator.page(paginator.num_pages)
    context = {
        'car': car,
    }
    return render(request, 'car/car_list.html', context)


def car_list(request):
    context = {}
    user = request.user
    car_dealers = CarDealer.objects.filter(user=user)
    if len(car_dealers) > 0:
        context["dataset"] = Car.objects.filter(branch=car_dealers[0].branch)

    return render(request, 'car/car_list.html', context)


def total_car_list(request):
    context = {}
    user = request.user
    labels = []
    data = []
    admin = Admin.objects.filter(user=user)
    if len(admin) > 0:
        context["cars"] = Car.objects.all()
        context["car_dealers"] = CarDealer.objects.filter(user__is_active=False)
        context["branch_form"] = ApproveCarDealer()
        context["car_dealers_dataset"] = CarDealer.objects.filter(user__is_active=True)

    queryset = Branch.objects.order_by('-rank')
    for branch in queryset:
        labels.append(branch.branch_name)
        data.append(branch.rank)

    context['labels'] = labels
    context['data'] = data

    return render(request, 'admin/admin_dashboard.html', context)


def car_dealer_approve(request, pk):
    posted_data = ApproveCarDealer(request.GET)
    dealer = CarDealer.objects.get(id=pk)
    dealer.user.is_active = True
    dealer.branch = Branch.objects.get(id=posted_data.data['dealer_branch'])
    dealer.save()
    dealer.user.save()

    return HttpResponseRedirect('/admin/dashboard')


def car_dealer_reject(request, pk):
    dealer = CarDealer.objects.get(id=pk)
    dealer.user.delete()
    dealer.delete()

    return HttpResponseRedirect('/admin/dashboard')


def car_detail(request, id=None):
    detail = get_object_or_404(Car, id=id)
    context = {
        "detail": detail
    }
    return render(request, 'car/car_detail.html', context)


@login_required
def create_car(request, branch_page=None):
    user = request.user
    car_dealers = CarDealer.objects.filter(user=user)
    branch_id = None
    if len(car_dealers) > 0:
        branch_id = car_dealers[0].branch
    if branch_page:
        branch_id = Branch.objects.get(pk=branch_page)
    posted_data = request.POST or None
    form = CarForm(posted_data, request.FILES or None, branch_status=len(car_dealers) > 0 or branch_page != None, initial={
        'branch': branch_id
    })

    if form.is_valid():
        instance = form.save(commit=False)
        instance.pk = None
        instance.save()
        if len(car_dealers) > 0:
            return redirect('/car/list')
        else:
            if branch_page:
                return redirect(f'/branch/branch_car_list/{branch_page}')
            return redirect('/admin/dashboard')
    context = {
        "form": form,
        "title": "Create Car"
    }
    return render(request, 'car/create_car.html', context)


def search(request):
    car_list = Car.objects.all()
    car_filter = CarFilter(request.GET, queryset=car_list)
    return render(request, 'car/search.html', {'filter': car_filter, 'car_list': car_list})


def search_results(request):
    car_list = Car.objects.all()
    car_filter = CarFilter(request.GET, queryset=car_list)
    return render(request, 'car/search_results.html', {'filter': car_filter, 'car_list': car_list})


# def search_reservation(request):
#     reservation_list = Reservation.objects.all()
#     reservation_filter = ReservationFilter(request.GET, queryset=reservation_list)
#     return render(request, 'search.html', {'filter': reservation_filter, 'reservation_list': reservation_list})
#
#
# def search_reservation_results(request):
#     reservation_list = Reservation.objects.all()
#     reservation_filter = ReservationFilter(request.GET, queryset=reservation_list)
#     return render(request, 'search_results.html', {'filter': reservation_filter, 'reservation_list': reservation_list})


# def search_results_try2(request):
#     cars = Car.objects.all()
#     form = CarSearchForm(request.GET)
#     if form.is_valid():
#         if form.cleaned_data["q"]:
#             cars = cars.filter(carName__icontains=form.cleaned_data["q"])
#         elif form.cleaned_data["model"]:
#             cars = cars.filter(model=form.cleaned_data["model"])
#         elif form.cleaned_data["airconditioner"]:
#             cars = cars.filter(airconditioner=form.cleaned_data["airconditioner"])
#         elif form.cleaned_data["price"]:
#             cars = cars.filter(price=form.cleaned_data["price"])
#         elif form.cleaned_data["numOfSeats"]:
#             cars = cars.filter(numOfSeats=form.cleaned_data["numOfSeats"])
#         elif form.cleaned_data["numOfDoors"]:
#             cars = cars.filter(numOfDoors=form.cleaned_data["numOfDoors"])
#         elif form.cleaned_data["transmission"]:
#             cars = cars.filter(transmission=form.cleaned_data["transmission"])
#         elif form.cleaned_data["branch"]:
#             cars = cars.filter(branch=form.cleaned_data["branch"])
#
#     return render(request, "search.html",
#                   {"form": form, "car_list": cars})
#
#
# @login_required
# def search_results_try(request):
#     car = Car.objects.all()
#     template_name = 'search_results.html'
#
#     query = request.GET.get('q')
#     if query:
#         car = car.filter(
#             Q(carName__icontains=query) |
#             Q(model__icontains=query) |
#             Q(airconditioner__icontains=query) |
#             Q(price__icontains=query) |
#             Q(branch__icontains=query) |
#             Q(stok__icontains=True)
#         )
#     context = {
#         'car': car,
#     }
#     return render(request, template_name, context)


@login_required()
def car_update(request, pk, branch_page=None):
    detail = get_object_or_404(Car, pk=pk)

    user = request.user
    car_dealers = CarDealer.objects.filter(user=user)
    form = CarForm(request.POST or None, request.FILES or None, branch_status=len(car_dealers) > 0 or branch_page != None,
                   instance=detail)
    if form.is_valid():
        instance = form.save(commit=False)
        instance.save()
        if len(car_dealers) > 0:
            return redirect('/car/list')
        else:
            if branch_page:
                return redirect(f'/branch/branch_car_list/{branch_page}')
            return redirect('/admin/dashboard')

    context = {
        "form": form,
        "title": "Update Car"
    }
    return render(request, 'car/car_update.html', context)


@login_required()
def car_delete(request, pk):
    query = get_object_or_404(Car, pk=pk)
    query.delete()

    car = Car.objects.all()
    context = {
        'car': car,
    }
    return render(request, 'car/car_deleted.html', context)


# reservation

def reservation_list_old(request):
    reservation = Reservation.objects.all()

    query = request.GET.get('q')
    if query:
        reservation = reservation.filter(
            Q(pickUpLocation__icontains=query) |
            Q(returnLocation__icontains=query) |
            Q(pickUpDate__icontains=query) |
            Q(returnDate__icontains=query)
        )

    # pagination
    paginator = Paginator(reservation, 4)  # Show 15 contacts per page
    page = request.GET.get('page')
    try:
        reservation = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        reservation = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        reservation = paginator.page(paginator.num_pages)
    context = {
        'reservation': reservation,
    }
    return render(request, 'reservation/reservation_list.html', context)


@login_required()
def reservation_list(request):
    context = {}
    context["dataset"] = Reservation.objects.filter(pickUpDate__gte=datetime.now())
    return render(request, 'reservation/reservation_list.html', context)


@login_required()
def reservation_detail(request, id=None):
    detail = get_object_or_404(Reservation, id=id)
    context = {
        "detail": detail,
    }
    return render(request, 'reservation/reservation_detail.html', context)


@login_required()
def reservation_created(request):
    form = ReservationSearchForm(request.POST or None)
    if form.is_valid():
        instance = form.save(commit=False)
        instance.save()
        return HttpResponseRedirect(instance.get_absolute_url())

    context = {
        "form": form,
        "title": "Create Reservation"
    }
    return render(request, 'reservation/reservation_create.html', context)


@login_required()
def reservation_update(request, id=None):
    detail = get_object_or_404(Reservation, id=id)
    form = ReservationSearchForm(request.POST or None, instance=detail)
    if form.is_valid():
        instance = form.save(commit=False)
        instance.save()
        return HttpResponseRedirect(instance.get_absolute_url())
    context = {
        "form": form,
        "title": "Update Reservation"
    }
    return render(request, 'reservation/reservation_create.html', context)


@login_required()
def reservation_delete(request, pk=None):
    query = get_object_or_404(Reservation, id=pk)
    if query.pickUpDate < datetime.now():
        return HttpResponse("Pick up has passed!Cannot delete.")
    carDealers = CarDealer.objects.filter(user=request.user)
    url = '/reservations/customer'
    message = f'{query} is canceled by {request.user.username}. Your payment will returned!'
    if len(carDealers) > 0:
        url = '/reservations/cardealer'
        f'{query} is canceled by you. Your payment will returned!'
    if query.customer:
        notification = Notifications(
            message=message,
            user=query.customer.user
        )
        notification.save()
    query.delete()
    return HttpResponseRedirect(url)


@login_required()
def view_my_reservation_cardealer(request):
    username = request.user
    user = User.objects.get(username=username)
    carDealer = CarDealer.objects.get(user=user)
    pickup = carDealer.branch.branch_name
    reservations = Reservation.objects.filter(pickUpLocation=pickup, pickUpDate__gte=datetime.now())
    return render(request, 'reservation/my_reservations.html', {'reservation_list': reservations,
                                                                'delete_url': ''})


@login_required()
def view_my_reservation_customer(request):
    username = request.user
    user = User.objects.get(username=username)
    reservations = Reservation.objects.filter(customer=Customer.get_customer_by_user(user),
                                              pickUpDate__gte=datetime.now())
    return render(request, 'reservation/my_reservations.html', {'reservation_list': reservations})


@login_required()
def newCar(request):
    new = Car.objects.order_by('-id')
    query = request.GET.get('q')
    if query:
        new = new.filter(
            Q(carName__icontains=query) |
            Q(model__icontains=query) |
            Q(numOfSeats__icontains=query) |
            Q(numOfDoors__icontains=query) |
            Q(transmission=query) |
            Q(airconditioner__icontains=query) |
            Q(price__icontains=query) |
            Q(carStatus__icontains=query)
        )

    paginator = Paginator(new, 12)
    page = request.GET.get('page')
    try:
        new = paginator.page(page)
    except PageNotAnInteger:
        new = paginator.page(1)
    except EmptyPage:
        new = paginator.page(paginator.num_pages)
    context = {
        'car': new,
    }
    return render(request, 'new_car.html', context)


def like_update(request, id=None):
    new = Car.objects.order_by('-id')
    like_count = get_object_or_404(Car, id=id)
    like_count.like += 1
    like_count.save()
    context = {
        'car': new,
    }
    return render(request, 'new_car.html', context)


def popular_car(request):
    new = Car.objects.order_by('-like')

    query = request.GET.get('q')
    if query:
        new = new.filter(
            Q(carName__icontains=query) |
            Q(model__icontains=query) |
            Q(numOfSeats__icontains=query) |
            Q(numOfDoors__icontains=query) |
            Q(transmission=query) |
            Q(airconditioner__icontains=query) |
            Q(price__icontains=query) |
            Q(carStatus__icontains=query)
        )

    paginator = Paginator(new, 12)  # Show 15 contacts per page
    page = request.GET.get('page')
    try:
        new = paginator.page(page)
    except PageNotAnInteger:
        new = paginator.page(1)
    except EmptyPage:
        new = paginator.page(paginator.num_pages)
    context = {
        'car': new,
    }
    return render(request, 'new_car.html', context)


def contact(request):
    form = MessageForm(request.POST or None)
    if form.is_valid():
        instance = form.save(commit=False)
        instance.save()
        return HttpResponseRedirect("/car/newcar/")
    context = {
        "form": form,
        "title": "Contact With Us",
    }
    return render(request, 'admin/contact.html', context)


# -----------------Admin Section-----------------

def admin_car_list(request):
    car = Car.objects.order_by('-id')

    query = request.GET.get('q')
    if query:
        car = car.filter(
            Q(carName__icontains=query) |
            Q(model__icontains=query) |
            Q(numOfSeats__icontains=query) |
            Q(numOfDoors__icontains=query) |
            Q(transmission=query) |
            Q(airconditioner__icontains=query) |
            Q(price__icontains=query) |
            Q(carStatus__icontains=query)
        )

    # pagination
    paginator = Paginator(car, 12)  # Show 15 contacts per page
    page = request.GET.get('page')
    try:
        car = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        car = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        car = paginator.page(paginator.num_pages)
    context = {
        'car': car,
    }
    return render(request, 'admin/admin_dashboard.html', context)


def admin_msg(request):
    msg = PrivateMsg.objects.order_by('-id')
    context = {
        "car": msg,
    }
    return render(request, 'admin/admin_msg.html', context)


def msg_delete(request, id=None):
    query = get_object_or_404(PrivateMsg, id=id)
    query.delete()
    return HttpResponseRedirect("/message/")


# fonksiyon kontrol demom sonra üzerinde oynayacağım -buse
def dashboard_car_list(request):
    cars = Car.view_car_list()
    car_detail = Car.view_car_detail(1)

    context = {
        "car_details": car_detail,
        "cars": cars
    }

    return render(request, 'car/car_detail.html', context)


def users(request):
    context = {}
    context["dataset"] = User.objects.all()

    return render(request, 'admin/users.html', context)


@login_required
def add_branch(request):
    form = BranchForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        instance = form.save(commit=False)
        instance.save()
        return redirect('/branch/list')
    context = {
        "form": form
    }
    return render(request, 'admin/add_branch.html', context)


def branch_list(request):
    context = {}
    context["dataset"] = Branch.objects.all()
    return render(request, 'admin/branch_list.html', context)


@login_required()
def branch_update(request, pk):
    detail = get_object_or_404(Branch, pk=pk)

    form = BranchForm(request.POST or None, request.FILES or None, instance=detail)
    if form.is_valid():
        instance = form.save(commit=False)
        instance.save()
        return redirect('/branch/list')
    context = {
        "form": form,
        "title": "Update Branch"
    }
    return render(request, 'admin/branch_update.html', context)


@login_required()
def branch_delete(request, pk):
    query = get_object_or_404(Branch, pk=pk)
    query.delete()

    branch = Branch.objects.all()
    context = {
        'branch': branch,
    }
    return render(request, 'admin/branch_deleted.html', context)


@background()
def clean_completed_reservations():
    print('Starts async task!')
    reservations = Reservation.objects.filter(pickUpDate__lt=datetime.now(), paymentStatus=False)
    print(reservations)
    for reservation in reservations:
        reservation.delete()


@login_required()
def delete_notification(request, pk):
    instance = get_object_or_404(Notifications, pk=pk)
    instance.delete()
    return HttpResponse(status=204)


@login_required()
def view_my_reservation_customer_history(request):
    username = request.user
    user = User.objects.get(username=username)
    reservations = Reservation.objects.filter(customer=Customer.get_customer_by_user(user),
                                              pickUpDate__lt=datetime.now())
    return render(request, 'reservation/reservation_history.html', {'reservation_history': reservations})


@login_required()
def view_my_reservation_cardealer_history(request):
    username = request.user
    user = User.objects.get(username=username)
    carDealer = CarDealer.objects.get(user=user)
    pickup = carDealer.branch.branch_name
    reservations = Reservation.objects.filter(pickUpLocation=pickup, pickUpDate__lt=datetime.now())
    return render(request, 'reservation/reservation_history.html', {'reservation_history': reservations,
                                                                    'delete_url': ''})


def view_my_reservation_admin_history(request):
    context = {}
    context["dataset"] = Reservation.objects.filter(pickUpDate__lt=datetime.now())
    return render(request, 'admin/admin_history.html', context)


def branch_car_list(request, pk):
    cars = Car.objects.all()
    branch = get_object_or_404(Branch, id=pk)
    context = {"branch": branch}
    context["cars"] = cars

    return render(request, 'admin/branch_car_list.html', context)


@login_required()
def CarDealer_delete(request, pk):
    dealer = get_object_or_404(CarDealer, id=pk)
    dealer.user.delete()
    dealer.delete()
    profile = get_object_or_404(Profile, id=pk)
    profile.delete()
    return HttpResponseRedirect('/admin/dashboard')


def view_profile(request, pk):
    profile = Profile.objects.get(user_id=pk)
    return render(request, 'layout/profile.html', {'profile': profile})


def edit_profile(request, pk):
    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            context = {'form': form}

        return redirect('profile', pk=pk)


    else:
        form = EditProfileForm(instance=request.user)
        args = {'form': form}
        return render(request, 'layout/edit_profile.html', args)
