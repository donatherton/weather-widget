#!/usr/bin/env python3
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Author: Don Atherton
# Web: donatherton.co.uk
# WeatherWidget (c) Don Atherton don@donatherton.co.uk

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio, WebKit2
import urllib.request
from datetime import datetime
import json
import os
import sys

class Win(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.path = os.path.dirname(__file__)
        self.prefs_values = self.get_prefs()
        self.grid = Gtk.Grid()
        self.Json = {}

        # CSS
        css = bytes('window {font-size: ' + str(self.prefs_values['font_size']) + 'px;}', 'UTF-8')
        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        try:
            custom = Gtk.CssProvider()  # From custom.css file
            custom.load_from_file(Gio.File.new_for_path(self.path + os.sep + 'custom.css'))
            Gtk.StyleContext.add_provider_for_screen(screen, custom, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except FileNotFoundError:
            pass

        # Set up main window
        self.set_default_size(410, 310)
        self.move(int(self.prefs_values['x']), int(self.prefs_values['y']))
        self.set_border_width(10)
        self.set_title('Weather Widget')
        self.set_skip_taskbar_hint(True)
        self.set_keep_below(True)
        self.set_decorated(False)

        visual = screen.get_rgba_visual()  # opacity from custom.css
        self.set_visual(visual)

        self.main_container = Gtk.VBox(spacing=8)
        self.add(self.main_container)

        # Box for the hourly & 5 day buttons
        hbox = Gtk.HBox()
        self.main_container.pack_end(hbox, False, False, 0)

        # Button for 5 day forecast
        fivedaybutton = Gtk.LinkButton.new_with_label("Full 5 day forecast")
        fivedaybutton.connect("clicked", self.call_five_day)
        hbox.pack_start(fivedaybutton, False, False, 0)
        fivedaybutton.set_tooltip_text('3 hourly forecast for next 5 days')

        # Button for rainfall radar
        #radar = Gtk.LinkButton.new_with_label("Rainfall radar")
        #radar.connect("clicked", self.call_radar)
        #hbox.pack_end(radar, False, False, 0)
        #radar.set_tooltip_text('Rainfall radar')

        # Right-click menu
        menu = Gtk.Menu()
        context = menu.get_style_context()
        context.add_class('menu')
        reload = Gtk.MenuItem()
        reload.set_label('reload')
        menu.append(reload)
        reload.show()

        preferences = Gtk.MenuItem()
        preferences.set_label('Preferences')
        menu.append(preferences)
        preferences.show()

        close_widget = Gtk.MenuItem()
        close_widget.set_label('Quit')
        menu.append(close_widget)
        close_widget.show()

        self.connect('button_press_event', self.button_press, menu)
        reload.connect('button_press_event', self.refresh)
        preferences.connect('button_press_event', self.set_preferences)
        close_widget.connect('button_press_event', self.stop)

    def get_prefs(self):
        prefs_file = self.path + os.sep + 'prefs'
        default_prefs = {
            'appid': 'API key from https://home.openweathermap.org',
            'lat': '51.5',
            'lon': '0.0',
            'loc': 'London',
            'temp_unit': 'C',
            'speed_unit': 'mph',
            'timeout': '15',
            'font_size': '12',
            'x': '250',
            'y': '10'
        }
        try:
            with open(prefs_file, 'r') as file_object:
                prefs_values = {}
                for line in file_object:
                    pref_value = line.split(',')
                    prefs_values[pref_value[0]] = pref_value[1].strip()
        except (IndexError, FileNotFoundError):
            print('No prefs file, creating one')
            print('API key required')
            with open(prefs_file, 'w'): pass
            self.prefs_values = default_prefs
            print(self.prefs_values)
            # Bring up prefs dialog
            self.prefs([250, 10])
        return prefs_values

    #def call_radar(self, button):
    #    self.rainfall_radar()

    def get_timeout(self):
        """ Time to refresh. timeout is accessed from outside, so use get method """
        try:
            timeout = int(self.prefs_values['timeout'])
            if timeout < 10: timeout = 10  # Let's not refresh too often
        except IndexError:
            timeout = 15
        return timeout

    def call_five_day(self, button):
        pos = self.get_position()
        self.five_days(pos)

    @staticmethod
    def refresh(widget, event):
        # reload
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            os.execv(sys.argv[0], sys.argv)

    @staticmethod
    def button_press(widget, event, menu):
        """ Handle right click, bring up menu """
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            menu.popup(None, None, None, event.button, 1, event.time)

    @staticmethod
    def stop(widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            Gtk.main_quit()

    def set_preferences(self, widget, event):
        # Open prefs dialogue
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            pos = self.get_position()
            self.prefs(pos)

    def wnd_spd_unit(self, wndspd):
        if self.prefs_values['speed_unit'] == 'm/s':
            pass
        elif self.prefs_values['speed_unit'] == 'kph':
            wndspd = wndspd * 3.6
        elif self.prefs_values['speed_unit'] == 'mph':
            wndspd = wndspd * 2.23694
        elif self.prefs_values['speed_unit'] == 'kt':
            wndspd = wndspd * 1.944
        elif self.prefs_values['speed_unit'] == 'Bf':
            wndspd = (float(wndspd) / 0.836) ** (2 / 3)
        return wndspd

    def temp_convert(self, t):
        if self.prefs_values['temp_unit'] == 'F':
                temp = (t * 1.8) + 32
        else:
                temp = t
        return temp

    @staticmethod
    def get_wnd_dir(wnd_dir):
        # Convert deg to bearing
        if wnd_dir <= 11:
            wnd_dir = 'N'
        elif wnd_dir > 11 and wnd_dir <= 33:
            wnd_dir = 'NNE'
        elif wnd_dir > 33 and wnd_dir <= 56:
            wnd_dir = 'NE'
        elif wnd_dir > 56 and wnd_dir <= 78:
            wnd_dir = 'ENE'
        elif wnd_dir > 78 and wnd_dir <= 101:
            wnd_dir = 'E'
        elif wnd_dir > 101 and wnd_dir <= 123:
            wnd_dir = 'ESE'
        elif wnd_dir > 123 and wnd_dir <= 146:
            wnd_dir = 'SE'
        elif wnd_dir > 146 and wnd_dir <= 168:
            wnd_dir = 'SSE'
        elif wnd_dir > 168 and wnd_dir <= 190:
            wnd_dir = 'S'
        elif wnd_dir > 190 and wnd_dir <= 213:
            wnd_dir = 'SSW'
        elif wnd_dir > 213 and wnd_dir <= 235:
            wnd_dir = 'SW'
        elif wnd_dir > 235 and wnd_dir <= 258:
            wnd_dir = 'WSW'
        elif wnd_dir > 258 and wnd_dir <= 280:
            wnd_dir = 'W'
        elif wnd_dir > 280 and wnd_dir <= 303:
            wnd_dir = 'WNW'
        elif wnd_dir > 303 and wnd_dir <= 325:
            wnd_dir = 'NW'
        elif wnd_dir > 325 and wnd_dir <= 347:
            wnd_dir = 'NNW'
        elif wnd_dir > 347 and wnd_dir <= 360:
            wnd_dir = 'N'
        return wnd_dir

    def the_loop(self):
        """ The main display, refreshes every timeout minutes """
        try:
            # The data source
            url_current = 'https://api.openweathermap.org/data/2.5/weather?lat=' + self.prefs_values['lat'] + '&lon=' + self.prefs_values['lon'] + '&units=metric&appid=' + self.prefs_values['appid']
            data = urllib.request.urlopen(url_current)
        except Exception as e:
            print(e)
#            error_box = Gtk.Label()
#            self.main_container.pack_start(error_box, True, True, 0)
#            error_box.set_markup('<span size=\"large\"><b>Error with connection</b></span>')
            return True
#        try:  # Remove previous grid if not just started
        self.grid.destroy()
#        except:
#            pass

        self.grid = Gtk.Grid()
        self.grid.set_column_homogeneous(True)
        self.grid.set_row_spacing(10)
        self.grid.set_column_spacing(5)
        self.main_container.add(self.grid)

        # Get current conditions
        cc = json.load(data)

        temp = cc['main']['temp']
        feels_like = cc['main']['feels_like']
        if self.prefs_values['temp_unit'] == 'F':
            temp = (temp * 1.8) + 32
            feels_like = (feels_like * 1.8) + 32
        temp = str(round(temp, 1))
        feels_like = str(round(feels_like, 1))
        cond = cc['weather'][0]['description']
        icon = cc['weather'][0]['icon']
        wnd_spd = cc['wind']['speed']
        wnd_spd = str(round(self.wnd_spd_unit(wnd_spd)))
        try:
            gust = cc['wind']['gust']
            gust = '/' + str(round(self.wnd_spd_unit(gust)))
        except KeyError:
            gust = ''
        wnd_dir = cc['wind']['deg']
        pres = cc['main']['pressure']
        humidity = cc['main']['humidity']

        sunrise = cc['sys']['sunrise']
        sunset = cc['sys']['sunset']
        update = cc['dt']
        update = datetime.fromtimestamp(update)

        wnd_dir = self.get_wnd_dir(wnd_dir)

        # Create the boxes
        vbox1 = Gtk.VBox(spacing=0)
        self.grid.attach(vbox1, 0, 0, 2, 1)
        vbox1.set_tooltip_text('Current conditions')
        vbox2 = Gtk.VBox(spacing=0)
        self.grid.attach(vbox2, 2, 0, 3, 1)
        vbox2.set_tooltip_text('Current conditions')
#        vbox3 = Gtk.VBox(spacing=0)
#        self.grid.attach(vbox3, 5, 0, 2, 1)

        city = Gtk.Label()
        vbox1.pack_start(city, True, True, 0)
        temperature = Gtk.Label()
        vbox1.pack_start(temperature, True, True, 0)
        temperature.set_margin_top(10)
        current_cond = Gtk.Label()
        vbox1.pack_start(current_cond, True, True, 0)
        current_cond.set_margin_top(10)
        weather_icon = Gtk.Image.new_from_pixbuf()
        vbox1.pack_start(weather_icon, True, True, 0)
        wnd_box = Gtk.HBox()
        vbox2.pack_start(wnd_box, True, True, 0)
        wnd_speed = Gtk.Label()
        wnd_box.pack_start(wnd_speed, True, True, 0)
#        wnd_dir_icon = Gtk.Image.new_from_pixbuf()
##        vbox3.pack_start(wnd_dir_icon, True, True, 0)
#        wnd_dir_icon.set_valign(Gtk.Align.START)
        pressure = Gtk.Label()
        vbox2.pack_start(pressure, True, True, 0)
        hum = Gtk.Label()
        vbox2.pack_start(hum, True, True, 0)
        sun_set = Gtk.Label()
        vbox2.pack_start(sun_set, True, True, 0)
        last_update = Gtk.Label()
        vbox2.pack_start(last_update, True, True, 0)

        # Print data
        city.set_markup('<span size=\"large\"><b>' + self.prefs_values['loc'] + '</b></span>')
        city.set_halign(Gtk.Align.START)
        city.set_line_wrap(True)

        temperature.set_markup(
            '<span size=\"xx-large\"><b>' + temp + u'\N{DEGREE SIGN}' + self.prefs_values['temp_unit'] + '</b></span> ' + 'f/l ' + feels_like + u'\N{DEGREE SIGN}' + self.prefs_values['temp_unit'])
        temperature.set_halign(Gtk.Align.START)

        current_cond.set_markup('<span variant=\"smallcaps\">' + cond + '</span>')
        current_cond.set_line_wrap(True)

        current_cond.set_halign(Gtk.Align.START)

        weathericon = self.path + os.sep + 'PNG' + os.sep + icon + '.png'
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(weathericon, 70, 70)
        weather_icon.set_from_pixbuf(pixbuf)
        weather_icon.set_halign(Gtk.Align.START)

        wnd_speed.set_text('Wind: ' + wnd_spd + gust + ' ' + self.prefs_values['speed_unit'] + ' ' + wnd_dir)
        wnd_speed.set_halign(Gtk.Align.START)

#        wnd_icon = self.path + os.sep + 'bearingicons' + os.sep + wnd_dir + '.png'
#        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(wnd_icon, 60, 60)
#        wnd_dir_icon.set_from_pixbuf(pixbuf)
#        wnd_dir_icon.set_tooltip_text('Wind direction')

        pressure.set_text('Pressure: ' + str(pres) + ' mb')
        pressure.set_halign(Gtk.Align.START)

        hum.set_text('Humidity: ' + str(humidity) + '%')
        hum.set_halign(Gtk.Align.START)

        sunrisetime = datetime.fromtimestamp(sunrise)
        sunset = datetime.fromtimestamp(sunset)
        sun_set.set_text(
            'Sunrise: ' + sunrisetime.time().strftime('%H:%M') + '\n' + 'Sunset:  ' + sunset.time().strftime('%H:%M'))
        sun_set.set_halign(Gtk.Align.START)

        last_update.set_text('Updated: ' + datetime.now().strftime('%H:%M:%S') + '\n' + 'On server: ' + update.time().strftime('%H:%M:%S'))
        last_update.set_halign(Gtk.Align.START)

        # brief 5 day forecast
        url_forecast = 'http://api.openweathermap.org/data/2.5/forecast?lat=' + self.prefs_values['lat'] + '&lon=' + self.prefs_values['lon'] + '&units=metric&appid=' + self.prefs_values['appid']
        forecast = urllib.request.urlopen(url_forecast)
        self.forecast = json.load(forecast)

        wt2 = []
        for data in self.forecast['list']:
                temp = round(data['main']['temp'])
                dt = datetime.utcfromtimestamp(data['dt']+self.forecast['city']['timezone'])
                _day = dt.strftime('%a')
                _date = dt.strftime('%d.%m')
                _time = dt.strftime('%H:%M')
                icon = data['weather'][0]['icon']+'.png'
                text = data['weather'][0]['description']
                wind_speed = round(data['wind']['speed'])
                wind_direct = data['wind']['deg']
                wind_gust = round(data['wind']['gust'])
                pres = data['main']['pressure']
                try:
                        rain = data['rain']['3h']
                except KeyError:
                        rain = 0
                chance_rain = data['pop']

                wt2.append({
                        't':temp,
                        'day': _day,
                        'date': _date,
                        'time': _time,
                        'icon': icon,
                        'text': text,
                        'wind_speed': wind_speed,
                        'wind_direct': wind_direct,
                        'wind_gust': wind_gust,
                        'rain': rain,
                        'pop': chance_rain,
                        'pres': pres
                        })

        wt = [[]]
        i = 0
        _date = dt.strftime('%d')
        # true sort by date for local time
        for item in wt2:
                if _date != item['date']:
                        i+=1
                        wt.append([])
                        _date = item['date']
                wt[i].append(item)

        t_day = []
        t_night = []
        day = []
        img = []
        text = []
        wind_speed = []
        gust = []
        wind_direct = []
        rain = []
        pop = []
        average_pres = []

        for i in range(1, len(wt)):
                max_t = None
                min_t = None
                w_s = 0
                g = None
                r = 0
                max_pop = None
                p = 0
                # find max min temp

                for item in wt[i]:
                        if max_t is None:
                                max_t = item['t']
                                min_t = item['t']
                        elif item['t'] > max_t:
                                max_t = item['t']
                        elif item['t'] < min_t:
                                min_t = item['t']

                        # find average wind speed
                        w_s += item['wind_speed']
                        # find average pressure
                        p += item['pres']
                        # find rain
                        r += item['rain']

                        try:
                                #find max chance rain
                                if max_pop is None:
                                        max_pop = item['pop']
#                                        min_pop = item['pop']
                                if item['pop'] > max_pop:
                                        max_pop = item['pop']

                        except KeyError:
                                max_pop = 0

                        try:
                                # find max wind gust
                                if g is None:
                                        g = item['wind_gust']
#                                        min_g = item['wind_gust']
                                if int(item['wind_gust']) > int(g):
                                        g = item['wind_gust']
                        except KeyError:
                                g = 0

                t_day.append(str(round(self.temp_convert(float(max_t)))))
                t_night.append(str(round(self.temp_convert(float(min_t)))))
                day.append(wt[i][0]['day'])
                index = -1 if len(wt[i]) < 5 else 4 # pick 22h today or 13h
                img.append(wt[i][index]['icon'])
                text.append(wt[i][index]['text'])
                wind_speed.append(str(round(self.wnd_spd_unit(w_s/len(wt[i])))))
                gust.append(str(round(self.wnd_spd_unit(g))))
                wind_direct.append(wt[i][index]['wind_direct'])
                rain.append(r)
                pop.append(max_pop)
                average_pres.append(str(round(p/len(wt[i]))))

        for i in range(0, 5):
            vbox = Gtk.VBox()
            self.grid.attach(vbox, i, 1, 1, 1)

            forecast_time = Gtk.Label()
            vbox.pack_start(forecast_time, True, True, 0)
            forecast_time.set_text(day[i])
            forecast_time.set_halign(Gtk.Align.START)

            min_max = Gtk.Label()
            vbox.pack_start(min_max, True, True, 0)
            min_max.set_text(t_day[i] + '/' + t_night[i] + u'\N{DEGREE SIGN}' + 'C')
            min_max.set_tooltip_text('Max / min temp')
            min_max.set_halign(Gtk.Align.START)

            symbol = img[i]
            weathericon = self.path + os.sep + 'PNG' + os.sep + symbol
            icon = Gtk.Image.new_from_pixbuf()
            vbox.pack_start(icon, True, True, 0)
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(weathericon, 30, 30)
            icon.set_from_pixbuf(pixbuf)
            icon.set_tooltip_markup('<span variant=\"smallcaps\">' + text[i] + '</span>')
            icon.set_halign(Gtk.Align.START)

            wnd_spd = str(round(float(wind_speed[i])))
            try:
                wnd_gust = '/' + gust[i]
            except KeyError:
                wnd_gust = ''
            wind = Gtk.Label()
            vbox.pack_start(wind, True, True, 0)
            wind.set_text(str(wnd_spd) + wnd_gust + ' ' + self.prefs_values['speed_unit'])
            wind.set_tooltip_text('Average wind speed / max gust')
            wind.set_halign(Gtk.Align.START)

            wnd_dir = self.get_wnd_dir(wind_direct[i])
            wnddir = Gtk.Label()
            vbox.pack_start(wnddir, True, True, 0)
            wnddir.set_text(str(wnd_dir))
            wnddir.set_tooltip_text('Wind direction')
            wnddir.set_halign(Gtk.Align.START)

#            humidity = fc[i]['humidity']
#            hum = Gtk.Label()
#            vbox.pack_start(hum, True, True, 0)
#            hum.set_text('H ' + str(humidity) + '%')
#            hum.set_tooltip_text('Humidity')
#            hum.set_halign(Gtk.Align.START)

            prec = pop[i]
            precipitation = Gtk.Label()
            vbox.pack_start(precipitation, True, True, 0)
            precipitation.set_text(str(round(prec * 100)) + '%')
            precipitation.set_tooltip_text('Chance of rain')
            precipitation.set_halign(Gtk.Align.START)

            try:
                r = rain[i]
                r = round(r, 1)
            except KeyError:
                r = '0'
            rainfall = Gtk.Label()
            vbox.pack_start(rainfall, True, True, 0)
            rainfall.set_text(str(r) + ' mm')
            rainfall.set_tooltip_text('Total amount of rain')
            rainfall.set_halign(Gtk.Align.START)

            pres = average_pres[i]
            pressure = Gtk.Label()
            vbox.pack_start(pressure, True, True, 0)
            pressure.set_text(str(pres) + ' mb')
            pressure.set_tooltip_text('Pressure')
            pressure.set_halign(Gtk.Align.START)

        self.grid.show_all()
        return True

    @staticmethod
    def temp_colour(temp):
        """ Selects font colour based on temperature """
        if temp <= 0:
            temp_colour = '#00ffff'
        elif temp > 0 and temp < 5:
            temp_colour = '#3399ff'
        elif temp >= 5 and temp < 10:
            temp_colour = '#3366cc'
        elif temp >= 10 and temp < 15:
            temp_colour = '#3319FF'
        elif temp >= 15 and temp < 20:
            temp_colour = '#ff3300'
        elif temp >= 20 and temp < 25:
            temp_colour = '#ff0000'
        elif temp >= 25:
            temp_colour = '#993300'
        return temp_colour

    @staticmethod
    def cloud_colour(cloud):
        """ Selects BG colour based on amount of cloud """
        if cloud >= 0 and cloud < 20:
            cloud_bg = '#eeeeee'
        elif cloud >= 20 and cloud < 40:
            cloud_bg = '#dddddd'
        elif cloud >= 40 and cloud < 60:
            cloud_bg = '#cccccc'
        elif cloud >= 60 and cloud < 80:
            cloud_bg = '#bbbbbb'
        elif cloud >= 80:
            cloud_bg = '#aaaaaa'
        return cloud_bg

    @staticmethod
    def wind_colour(wnd_spd):
        """ Selects font colour based on wind speed """
        if wnd_spd < 8:
            wnd_colour = '#2E423B'
        if wnd_spd >= 8 and wnd_spd < 15:
            wnd_colour = '#CE5C00'
        elif wnd_spd >= 15 and wnd_spd < 20:
            wnd_colour = '#CE1600'
        elif wnd_spd >= 20 and wnd_spd < 25:
            wnd_colour = '#CC0000'
        elif wnd_spd >= 25:
            wnd_colour = '#A40075'
        return wnd_colour

    @staticmethod
    def day_night(sr, ss, h):
        """ Selects BG colour to show day/night """
        if (int(sr) <= int(h) and int(h) <= int(ss)) or (int(sr) <= int(h - 86400) and int(h - 86400) <= int(ss)) or (
                int(sr) <= int(h - 172800) and int(h - 172800) <= int(ss)):
            dn = '-d'
        else:
            dn = '-n'
        return dn

    def five_days(self, pos):
        """ Opens window with 5 day forecast """

        # CSS
        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()
        css = b"""
        label.day,image.day {
        padding: 0 3px 0 3px;
        min-height: 30px;
        border-bottom: 1px solid #bbbbbb;
        background: #eeeeee;
        color: #191919;
        }
        label.night, image.night {
        padding: 0 3px 0 3px;
        min-height: 30px;
        border-bottom: 1px solid #bbbbbb;
        background: #bbbbbb;
        color: #191919;
        }
        """
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Create window
        five_day_win = Gtk.Window()
        five_day_win.set_title('5 day 3 hour forecast')
        five_day_win.set_default_size(450, 500)
        five_day_win.move(pos[0], pos[1])

        container = Gtk.ScrolledWindow()
        # container.set_policy (Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)

        five_day_win.add(container)
        flowbox = Gtk.VBox()
        flowbox.set_border_width(10)
        container.add(flowbox)

        grid = Gtk.Grid()
        grid.set_row_spacing(1)
        flowbox.add(grid)

        sunrise = self.forecast['city']['sunrise']
        sunset = self.forecast['city']['sunset']
        sunrisetime = datetime.fromtimestamp(sunrise)
        sunrise = sunrisetime.time().strftime('%H:%M')
        sunsettime = datetime.fromtimestamp(sunset)
        sunset = sunsettime.time().strftime('%H:%M')

        top = ['Time', 'Temp', '    ', '    ', 'Rain', 'Wind', '', 'Cloud', 'Pres']
        f = 0
        for item in top:
            item_label = Gtk.Label()
            grid.attach(item_label, f, 0, 1, 1)
            item_label.set_markup('<b>' + item + '</b>')
            item_label.set_halign(Gtk.Align.START)
            f = f + 1

        for i in range(0, 40):
            t = self.forecast['list'][i]['dt']
            t = datetime.fromtimestamp(t)
            d = t.strftime('%a')
            t = t.time().strftime('%H')

            dn = self.day_night_5day(sunrise, sunset, t)

            day_label = Gtk.Label()
            grid.attach(day_label, 0, i + 1, 1, 1)
            if dn == '-n':
                context = day_label.get_style_context()
                context.add_class('night')
            else:
                context = day_label.get_style_context()
                context.add_class('day')

            day_label.set_markup('<b>' + d + ' ' + t + 'h</b>')

            temp = self.forecast['list'][i]['main']['temp']
            temp_colour = self.temp_colour(temp)  # Colour coded text
            if self.prefs_values['temp_unit'] == 'F':
                temp = (temp * 1.8) + 32
            temp = round(temp, 1)
            temp_label = Gtk.Label()
            grid.attach(temp_label, 1, i + 1, 1, 1)

            if dn == '-n':
                context = temp_label.get_style_context()
                context.add_class('night')
            else:
                context = temp_label.get_style_context()
                context.add_class('day')

            temp_label.set_markup('<b><span foreground=\"' + temp_colour + '\">' + str(temp) + u'\N{DEGREE SIGN}' + 'C</span></b>')

            symbol = self.forecast['list'][i]['weather'][0]['icon']
            weather_icon = self.path + os.sep + 'PNG' + os.sep + symbol + '.png'
            weathericon = Gtk.Image.new_from_pixbuf()
            grid.attach(weathericon, 2, i + 1, 1, 1)
            if dn == '-n':
                context = weathericon.get_style_context()
                context.add_class('night')
            else:
                context = weathericon.get_style_context()
                context.add_class('day')

            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(weather_icon, 20, 20)
            weathericon.set_from_pixbuf(pixbuf)
            weathericon.show()

            name = self.forecast['list'][i]['weather'][0]['description']
            name_label = Gtk.Label()
            grid.attach(name_label, 3, i + 1, 1, 1)
            if dn == '-n':
                context = name_label.get_style_context()
                context.add_class('night')
            else:
                context = name_label.get_style_context()
                context.add_class('day')

            name_label.set_markup('<span variant=\"smallcaps\">' + name + '</span>')
            name_label.set_line_wrap(True)

            try:
                prec = self.forecast['list'][i]['rain']['3h']
            except KeyError:
                prec = 0

            prec = round(float(prec), 1)
            precipitation = Gtk.Label()
            grid.attach(precipitation, 4, i + 1, 1, 1)
            if dn == '-n':
                context = precipitation.get_style_context()
                context.add_class('night')
            else:
                context = precipitation.get_style_context()
                context.add_class('day')
            if prec > 0:
                precipitation.set_markup('<b>' + str(prec) + ' mm</b>')
            else:
                precipitation.set_text(str(prec) + ' mm')

            wnd_spd = self.forecast['list'][i]['wind']['speed']
            wnd_colour = self.wind_colour(wnd_spd)
            wnd_spd = round(self.wnd_spd_unit(wnd_spd))
            wnd_spd_label = Gtk.Label()
            try:
                wnd_gust = self.forecast['list'][i]['wind']['gust']
                gust_colour = self.wind_colour(wnd_gust)
                wnd_gust = '/' + str(round(self.wnd_spd_unit(wnd_gust)))
            except KeyError:
                gust_colour = '#2E423B'
                wnd_gust = ''
            grid.attach(wnd_spd_label, 5, i + 1, 1, 1)
            if dn == '-n':
                context = wnd_spd_label.get_style_context()
                context.add_class('night')
            else:
                context = wnd_spd_label.get_style_context()
                context.add_class('day')

            wnd_spd_label.set_markup('<span foreground=\"' + wnd_colour + '\">' + str(
                wnd_spd) + '</span><span foreground=\"' + gust_colour + '\">' + wnd_gust + self.prefs_values['speed_unit'] + '</span>')

            wnd_dir = self.get_wnd_dir(self.forecast['list'][i]['wind']['deg'])
            wnd_dir_label = Gtk.Label()
            grid.attach(wnd_dir_label, 6, i + 1, 1, 1)
            if dn == '-n':
                context = wnd_dir_label.get_style_context()
                context.add_class('night')
            else:
                context = wnd_dir_label.get_style_context()
                context.add_class('day')

            wnd_dir_label.set_text(str(wnd_dir))

            cloud = self.forecast['list'][i]['clouds']['all']
            cloud_label = Gtk.Label()
            grid.attach(cloud_label, 7, i + 1, 1, 1)
            cloud_bg = self.cloud_colour(cloud)
            if dn == '-n':
                context = cloud_label.get_style_context()
                context.add_class('night')
                cloud_label.set_markup(str(cloud) + '%')
            else:
                context = cloud_label.get_style_context()
                context.add_class('day')
                cloud_label.set_markup('<span background=\"' + cloud_bg + '\">' + str(cloud) + '%</span>')

            pres = self.forecast['list'][i]['main']['pressure']
            pressure = Gtk.Label()
            grid.attach(pressure, 8, i + 1, 1, 1)
            if dn == '-n':
                context = pressure.get_style_context()
                context.add_class('night')
            else:
                context = pressure.get_style_context()
                context.add_class('day')

            pressure.set_text(str(pres) + ' mb')

        five_day_win.connect("destroy", Gtk.main_quit)
        five_day_win.show_all()
        Gtk.main()

    @staticmethod
    def day_night_5day(sr, ss, h):
        if sr <= h and h <= ss:
            dn = '-d'
        else:
            dn = '-n'
        return dn

    def rainfall_radar(self):
        """ Brings up rainfall radar window """
        # Create window
        rain_win = Gtk.Window()
        rain_win.set_default_size(900, 700)

        # Create view for webpage
        viewport = Gtk.ScrolledWindow()
        webview = WebKit2.WebView()
        webview.load_uri('file://' + self.path + os.sep + 'radar.html?lat=' + self.prefs_values['lat'] + '&lon=' + self.prefs_values['lon'])
        viewport.add(webview)
        # Add everything and initialize
        container = Gtk.VBox()
        container.pack_start(viewport,True,True,0)
        rain_win.add(container)

        rain_win.connect("destroy", Gtk.main_quit)
        rain_win.show_all()
        Gtk.main()

    def prefs(self, pos):
        """ Saves and stores preferences """
        from urllib.parse import quote

        def geo_search(self):
            """ Shows up to 5 location search results """
#            try:
            store.clear()
#            except:
#                pass

            geosearch = geosearch_input.get_text()

            search_url = 'https://nominatim.openstreetmap.org/?format=json&addressdetails=1&q=' + quote(
                geosearch) + '&limit=5'

            location = urllib.request.urlopen(search_url)
            location = json.load(location)

            for i in range(len(location)):
                try:
                    try:
                        loc = location[i]['address']['city']
                    except KeyError:
                        loc = location[i]['address']['town']
                except KeyError:
                    try:
                        loc = location[i]['address']['village']
                    except KeyError:
                        loc = 'Unknown'

                store.append([location[i]['display_name'], loc, location[i]['lat'], location[i]['lon'], i])

            treeview.show_all()

        def save_and_reload(button, self):
            select = treeview.get_selection()
            model, treeiter = select.get_selected()
            if treeiter is not None:
                lat1 = model[treeiter][2]
                lon1 = model[treeiter][3]
                place_name1 = model[treeiter][1]
            else:
                place_name1 = self.prefs_values['loc']
                lat1 = self.prefs_values['lat']
                lon1 = self.prefs_values['lon']

            appid_value = appid.get_text()
            temp_button = [r for r in button1.get_group() if r.get_active()]
            speed_button = [r for r in wnd_spd_button1.get_group() if r.get_active()]
            timeout = time_out.get_text()
            if int(timeout) < 10: timeout = '10'
            font_size = font.get_value_as_int()

            with open(self.path + os.sep + 'prefs', 'w') as f:
                f.write('appid,' + appid_value + '\n')
                f.write('lat,' + lat1 + '\n')
                f.write('lon,' + lon1 + '\n')
                f.write('loc,' + place_name1 + '\n')
                f.write('temp_unit,' + temp_button[0].get_label() + '\n')
                f.write('speed_unit,' +speed_button[0].get_label() + '\n')
                f.write('timeout,' + timeout + '\n')
                f.write('font_size,' + str(font_size) + '\n')
                f.write('x,' + str(pos[0]) + '\n')
                f.write('y,' + str(pos[1]))
            os.execv(sys.argv[0], sys.argv)  # reload

        #    def lock_position(self):
        #        self.pos = win.get_position()
        #        save_and_reload(self)

        prefs_win = Gtk.Window()
        prefs_win.set_default_size(400, 550)
        prefs_win.set_border_width(10)
        prefs_win.set_title('Preferences')

        container = Gtk.ScrolledWindow()
        prefs_win.add(container)

        box = Gtk.VBox()
        container.add(box)

        #        searchLabel = Gtk.Label()
        #        box.pack_start(searchLabel, False, False, 0)
        #        searchLabel.set_markup('<b>Search location</b>')

        search_hbox = Gtk.HBox()
        box.pack_start(search_hbox, False, False, 0)
        geosearch_input = Gtk.SearchEntry()
        geosearch_input.set_text(self.prefs_values['loc'])
        geosearch_input.connect("activate", geo_search)
        search_hbox.pack_start(geosearch_input, True, True, 5)
        #        searchLabel.set_halign(Gtk.Align.START)

        search_button = Gtk.Button().new_with_label(" Search location ")
        search_button.connect('clicked', geo_search)
        search_hbox.pack_end(search_button, False, False, 0)

        grid_box = Gtk.ScrolledWindow()
        box.pack_start(grid_box, True, True, 5)

        treeview = Gtk.TreeView()
        store = Gtk.ListStore(str, str, str, str, int)
        treeview.set_model(store)

        renderer_text = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Add location from search results', renderer_text, text=0)
        treeview.append_column(column)
        grid_box.add(treeview)

        appid_label = Gtk.Label()
        box.pack_start(appid_label, False, False, 5)
        appid_label.set_markup('<b>OpenWeatherMap key:</b>')
        appid = Gtk.Entry()
        box.pack_start(appid, False, False, 0)
        appid.set_text(self.prefs_values['appid'])
        appid_label.set_halign(Gtk.Align.START)

        temp_box = Gtk.Box(spacing=6)
        box.pack_start(temp_box, False, False, 5)
        temp_label = Gtk.Label()
        temp_box.pack_start(temp_label, False, False, 5)
        temp_label.set_markup('<b>Temperature unit:</b>')
        button1 = Gtk.RadioButton.new_with_label_from_widget(None, "C")
        temp_box.pack_start(button1, False, False, 0)
        button2 = Gtk.RadioButton.new_from_widget(button1)
        button2.set_label("F")
        temp_box.pack_start(button2, False, False, 0)
        if self.prefs_values['temp_unit'] == 'F':
            button2.set_active(True)
        else:
            button1.set_active(True)

        wnd_spd_box = Gtk.Box(spacing=6)
        box.pack_start(wnd_spd_box, False, False, 5)
        wnd_spd_label = Gtk.Label()
        wnd_spd_box.pack_start(wnd_spd_label, False, False, 5)
        wnd_spd_label.set_markup('<b>Windspeed unit:</b>')
        wnd_spd_button1 = Gtk.RadioButton.new_with_label_from_widget(None, "kt")
        wnd_spd_box.pack_start(wnd_spd_button1, False, False, 0)
        wnd_spd_button2 = Gtk.RadioButton.new_from_widget(wnd_spd_button1)
        wnd_spd_button2.set_label("mph")
        wnd_spd_box.pack_start(wnd_spd_button2, False, False, 0)
        wnd_spd_button3 = Gtk.RadioButton.new_from_widget(wnd_spd_button1)
        wnd_spd_button3.set_label("m/s")
        wnd_spd_box.pack_start(wnd_spd_button3, False, False, 0)
        wnd_spd_button4 = Gtk.RadioButton.new_from_widget(wnd_spd_button1)
        wnd_spd_button4.set_label("kph")
        wnd_spd_box.pack_start(wnd_spd_button4, False, False, 0)
        wnd_spd_button5 = Gtk.RadioButton.new_from_widget(wnd_spd_button1)
        wnd_spd_button5.set_label("Bf")
        wnd_spd_box.pack_start(wnd_spd_button5, False, False, 0)
        if self.prefs_values['speed_unit'] == 'mph':
            wnd_spd_button2.set_active(True)
        elif self.prefs_values['speed_unit'] == 'm/s':
            wnd_spd_button3.set_active(True)
        elif self.prefs_values['speed_unit'] == 'kph':
            wnd_spd_button4.set_active(True)
        elif self.prefs_values['speed_unit'] == 'Bf':
            wnd_spd_button5.set_active(True)
        else:
            wnd_spd_button1.set_active(True)

        timeout_label = Gtk.Label()
        box.pack_start(timeout_label, False, False, 0)
        timeout_label.set_markup('<b>Refresh time (minutes):</b>')
        time_out = Gtk.Entry()
        box.pack_start(time_out, False, False, 5)
        time_out.set_text(str(self.get_timeout()))
        timeout_label.set_halign(Gtk.Align.START)

        font_label = Gtk.Label()
        box.pack_start(font_label, False, False, 5)
        font_label.set_markup('<b>Font size:</b>')
        font_adjustment = Gtk.Adjustment(lower=9, upper=48, step_increment=1, page_increment=10)
        font = Gtk.SpinButton()
        font.set_adjustment(font_adjustment)
        box.pack_start(font, False, False, 0)
        font.set_value(int(self.prefs_values['font_size']))
        font_label.set_halign(Gtk.Align.START)

        #    lockButton = Gtk.Button.new_with_label("Lock position")
        #    lockButton.connect("clicked", lock_position)
        #    box.pack_end(lockButton,False,False,5)
        #    lockButton.connect("clicked", lock_position)
        #    context = lockButton.get_style_context()
        #    context.add_class('prefs')

        button = Gtk.Button.new_with_label("Save and reload")
        button.connect("clicked", save_and_reload, self)
        box.pack_end(button, False, False, 5)
        #        context = button.get_style_context()
        #        context.add_class('prefs')

        prefs_win.connect('destroy', Gtk.main_quit)
        prefs_win.show_all()
        Gtk.main()


if __name__ == '__main__':
    win = Win()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    win.the_loop()
    timeout_add = GLib.timeout_add_seconds(win.get_timeout() * 60, win.the_loop)
    Gtk.main()
