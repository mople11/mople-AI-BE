from django.urls import path

from home.views import HomeView, WeatherCurrentView


app_name = "home"

urlpatterns = [
    path("api/v1/weather/current", WeatherCurrentView.as_view(), name="weather-current"),
    path("api/v1/home", HomeView.as_view(), name="home"),
]
