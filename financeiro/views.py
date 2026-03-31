from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone
from django.contrib import messages

import json
from datetime import date
import calendar
