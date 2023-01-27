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
#WeatherWidget (c) Don Atherton don@donatherton.co.uk

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio
import urllib.request
from datetime import datetime
import json
import os, sys

class Win(Gtk.Window):
	def __init__(self):
		Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
		self.preferences = []
		self.path = os.path.dirname(__file__)

		# Get prefs and assign to variables. Purely for readability.
		prefs_file = self.path + os.sep + 'prefs'
		with open(prefs_file, 'r') as file_object:
			for line in file_object:
				self.preferences.append(line)
			try:
				self.APPID = self.preferences[0].strip()
			except:
				print('API key required')
			try:
				self.lat = self.preferences[1].strip()
			except:
				self.lat = '51.5'
			try:
				self.lon = self.preferences[2].strip()
			except:
				self.lon = '0.0'
			try:
				self.loc = self.preferences[3].strip()
			except:
				self.loc = 'London'
			try:
				self.temp_unit = self.preferences[4].strip()
			except:
				self.emp_unit = 'C'
			try:
				self.speed_unit = self.preferences[5].strip()
			except:
				self.speed_unit = 'mph'
			try:
				self.font_size = self.preferences[7].strip()
			except:
				self.font_size = 12
			try:
				self.x = int(self.preferences[8])
			except:
				self.x = 250
			try:
				self.y = int(self.preferences[9])
			except:
				self.y= 10

		# CSS
		css = bytes('window {font-size: ' + str(self.font_size) + 'px;}', 'UTF-8')
		screen = Gdk.Screen.get_default()
		provider = Gtk.CssProvider()
		provider.load_from_data(css)
		try:
			custom = Gtk.CssProvider()  # From custom.css file
			custom.load_from_file(Gio.File.new_for_path(self.path + os.sep + 'custom.css'))
			Gtk.StyleContext.add_provider_for_screen(screen, custom, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
		except:
			pass
		Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

		# Set up main window
		self.set_default_size(410, 310)
		self.move(self.x,self.y)
		self.set_border_width(10)
		self.set_title('Weather Widget')
		self.set_skip_taskbar_hint(True)
		self.set_keep_below(True)
		self.set_decorated(False)

		visual = screen.get_rgba_visual() # opacity from custom.css
		self.set_visual(visual)

		self.main_container = Gtk.VBox(spacing=8)
		self.add(self.main_container)

		# Box for the hourly & 5 day buttons
		hbox = Gtk.HBox()
		self.main_container.pack_end(hbox, False, False, 0)

		# Button for 5 day forecast
		fivedaybutton = Gtk.LinkButton.new_with_label("5 day forecast")
		fivedaybutton.connect("clicked", self.call_five_day)
		hbox.pack_start(fivedaybutton, False, False, 0)
		fivedaybutton.set_tooltip_text('3 hourly forecast for next 5 days')

		# Button for hourly forecast
		button = Gtk.LinkButton.new_with_label("Hourly forecast")
		button.connect("clicked", self.call_hourly)
		hbox.pack_end(button, False, False, 0)
		button.set_tooltip_text('Hourly forecast for next 48h')

		# Right-click menu
		menu = Gtk.Menu()
		context = menu.get_style_context()
		context.add_class('menu')
		Reload = Gtk.MenuItem()
		Reload.set_label('Reload')
		menu.append(Reload)
		Reload.show()

		Prefs = Gtk.MenuItem()
		Prefs.set_label('Preferences')
		menu.append(Prefs)
		Prefs.show()

		quit = Gtk.MenuItem()
		quit.set_label('Quit')
		menu.append(quit)
		quit.show()

		self.connect('button_press_event', self.button_press, menu)
		Reload.connect('button_press_event',self.refresh)
		Prefs.connect('button_press_event', self.set_preferences)
		quit.connect('button_press_event', self.stop)

	def get_timeout(self):
		""" Time to refresh. timeout is accessed from outside, so use get method """
		try:
			timeout = preferences[6].strip()
			if timeout < 10: timeout = 10 # Let's not refresh too often
		except:
			timeout = 15
		return timeout

	def call_hourly(self, button):
		pos = self.get_position()
		self.hourly_forecast(pos)

	def call_five_day(self, fivedaybutton):
		pos = self.get_position()
		self.five_days(pos)

	def refresh(self, widget, event):
		#Reload
		if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
			os.execv(sys.argv[0], sys.argv)
	def button_press(self, widget, event, menu):
		# Handle right click, bring up menu
		if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
			menu.popup(None, None, None, event.button, 1, event.time)
	def stop(self, widget, event):
		if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
			Gtk.main_quit()
	def set_preferences(self, widget, event):
		# Open prefs dialogue
		if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
			pos = self.get_position()
			self.prefs(pos)

	def wnd_spd_unit(self, wndspd):
		if self.speed_unit == 'm/s': pass
		elif self.speed_unit == 'kph': wndspd = wndspd*3.6
		elif self.speed_unit == 'mph': wndspd = wndspd*2.23694
		elif self.speed_unit == 'kt': wndspd = wndspd*1.944
		elif self.speed_unit == 'Bf': wndspd = (float(wndspd)/0.836)**(2/3)
		return wndspd

	def get_wnd_dir(self, wndDir):
		# Convert deg to bearing
		if wndDir <= 11: wndDir = 'N'
		elif wndDir > 11 and wndDir <= 33: wndDir = 'NNE'
		elif wndDir > 33 and wndDir <= 56: wndDir = 'NE'
		elif wndDir > 56 and wndDir <= 78: wndDir = 'ENE'
		elif wndDir > 78 and wndDir <= 101: wndDir = 'E'
		elif wndDir >101 and wndDir <= 123: wndDir = 'ESE'
		elif wndDir > 123 and wndDir <= 146: wndDir = 'SE'
		elif wndDir > 146 and wndDir <= 168: wndDir = 'SSE'
		elif wndDir > 168 and wndDir <= 190: wndDir = 'S'
		elif wndDir > 190 and wndDir <= 213: wndDir = 'SSW'
		elif wndDir > 213 and wndDir <= 235: wndDir = 'SW'
		elif wndDir > 235 and wndDir <= 258: wndDir = 'WSW'
		elif wndDir > 258 and wndDir <= 280: wndDir = 'W'
		elif wndDir > 280 and wndDir <= 303: wndDir = 'WNW'
		elif wndDir > 303 and wndDir <= 325: wndDir = 'NW'
		elif wndDir > 325 and wndDir <= 347: wndDir = 'NNW'
		elif wndDir > 347 and wndDir <= 360: wndDir = 'N'
		return wndDir

	def theLoop(self):
		""" The main display, refreshes every timeout minutes """
		try:
			# The data source
			url = 'https://api.openweathermap.org/data/2.5/onecall?lat=' + self.lat + '&lon=' + self.lon + '&exclude=minutely,alerts&units=metric&appid=' + self.APPID
			data = urllib.request.urlopen(url)
		except:
			return True
		try: # Remove previous grid if not just started
			self.grid.destroy()
		except:
			pass

		self.grid = Gtk.Grid()
		self.grid.set_column_homogeneous(True)
		self.grid.set_row_spacing(10)
		self.grid.set_column_spacing(5)
		self.main_container.add(self.grid)

		# Get current conditions
		self.Json = json.load(data)
		cc = self.Json['current']

		temp = cc['temp']
		feels_like = cc['feels_like']
		if self.temp_unit == 'F':
			temp = (temp*1.8)+32
			feels_like = (feels_like*1.8)+32
		temp = str(round(temp,1))
		feels_like = str(round(feels_like,1))
		cond = cc['weather'][0]['description']
		icon = cc['weather'][0]['icon']
		wndSpd = cc['wind_speed']
		wndSpd = str(round(self.wnd_spd_unit(wndSpd)))
		try:
			gust = cc['wind_gust']
			gust = '/' + str(round(self.wnd_spd_unit(gust)))
		except:
			gust = ''
		wndDir = cc['wind_deg']
		pres = cc['pressure']
		hum = cc['humidity']

		sunrise = cc['sunrise']
		sunset = cc['sunset']
		update = cc['dt']
		update = datetime.fromtimestamp(update)

		wndDir = self.get_wnd_dir(wndDir)

		# Create the boxes
		vbox1 = Gtk.VBox(spacing=0)
		self.grid.attach(vbox1,0,0,2,1)
		vbox1.set_tooltip_text('Current conditions')
		vbox2 = Gtk.VBox(spacing=0)
		self.grid.attach(vbox2,3,0,2,1)
		vbox2.set_tooltip_text('Current conditions')
		vbox3 = Gtk.VBox(spacing=0)
		self.grid.attach(vbox3,5,0,2,1)

		city = Gtk.Label()
		vbox1.pack_start(city,True,True,0)
		temperature = Gtk.Label()
		vbox1.pack_start(temperature,True,True,0)
		temperature.set_margin_top(10)
		currentCond = Gtk.Label()
		vbox1.pack_start(currentCond,True,True,0)
		currentCond.set_margin_top(10)
		weatherIcon = Gtk.Image.new_from_pixbuf()
		vbox1.pack_start(weatherIcon,True,True,0)
		wndBox = Gtk.HBox()
		vbox2.pack_start(wndBox, True,True,0)
		windSpeed = Gtk.Label()
		wndBox.pack_start(windSpeed,True,True,0)
		WndDir = Gtk.Image.new_from_pixbuf()
		vbox3.pack_start(WndDir,True,True,0)
		WndDir.set_valign(Gtk.Align.START)
		pressure = Gtk.Label()
		vbox2.pack_start(pressure,True,True,0)
		humidity = Gtk.Label()
		vbox2.pack_start(humidity,True,True,0)
		sunSet = Gtk.Label()
		vbox2.pack_start(sunSet,True,True,0)
		lastUpdate = Gtk.Label()
		vbox2.pack_start(lastUpdate,True,True,0)

		# Print data
		city.set_markup('<span size=\"large\"><b>' + self.loc + '</b></span>')
		city.set_halign(Gtk.Align.START)
		city.set_line_wrap(True)

		temperature.set_markup('<span size=\"large\"><b>' + temp + u'\N{DEGREE SIGN}' + self.temp_unit + '</b></span> ' + 'f/l ' + feels_like + u'\N{DEGREE SIGN}' + self.temp_unit)
		temperature.set_halign(Gtk.Align.START)

		currentCond.set_markup('<span variant=\"smallcaps\">' + cond + '</span>')
		currentCond.set_line_wrap(True)

		currentCond.set_halign(Gtk.Align.START)

		weathericon = self.path + os.sep + 'PNG' + os.sep + icon + '.png'
		pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(weathericon,50,50)
		weatherIcon.set_from_pixbuf(pixbuf)
		weatherIcon.set_halign(Gtk.Align.START)

		windSpeed.set_text('Wind: ' + wndSpd + gust + self.speed_unit + ' ' + wndDir)
		windSpeed.set_halign(Gtk.Align.START)

		wndDirIcon = self.path + os.sep + 'bearingicons' + os.sep + wndDir + '.png'
		pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(wndDirIcon,60,60)
		WndDir.set_from_pixbuf(pixbuf)
		WndDir.set_tooltip_text('Wind direction')

		pressure.set_text('Pressure: ' + str(pres) + 'mb')
		pressure.set_halign(Gtk.Align.START)

		humidity.set_text('Humidity: ' + str(hum) + '%')
		humidity.set_halign(Gtk.Align.START)

		sunrisetime = datetime.fromtimestamp(sunrise)
		sunset = datetime.fromtimestamp(sunset)
		sunSet.set_text('Sunrise: ' + sunrisetime.time().strftime('%H:%M') + '\n' + 'Sunset:  ' + sunset.time().strftime('%H:%M'))
		sunSet.set_halign(Gtk.Align.START)

		lastUpdate.set_text('Updated: ' + update.time().strftime('%H:%M:%S'))
		lastUpdate.set_halign(Gtk.Align.START)

		# 7 day forecast
		fc = self.Json['daily']

		for i in range(0,7):
			t = fc[i]['dt']
			temp = fc[i]['temp']['day']
			minTemp = fc[i]['temp']['min']
			if self.temp_unit == 'F':
				minTemp = (minTemp*1.8)+32
			minTemp = str(round(minTemp))
			maxTemp = fc[i]['temp']['max']
			if self.temp_unit == 'F':
				maxTemp = (maxTemp*1.8)+32
			maxTemp = str(round(maxTemp))
			symbol = fc[i]['weather'][0]['icon']
			cond = fc[i]['weather'][0]['description']
			wndSpd = fc[i]['wind_speed']
			wndSpd = str(round(self.wnd_spd_unit(wndSpd)))
			wndDir = fc[i]['wind_deg']
			try:
				gust = fc[i]['wind_gust']
				gust = str(round(self.wnd_spd_unit(gust)))
				gust = '/' + gust
			except:
				gust = ''
			pres = fc[i]['pressure']
			prec = fc[i]['pop']
			hum = fc[i]['humidity']
			try:
				rain = fc[i]['rain']
				rain = round(rain,1)
			except:
				rain = '0'
	#		cloud = fc[i]['clouds']

			t = datetime.fromtimestamp(t)
			t = t.date().strftime('%a')

			wndDir = self.get_wnd_dir(wndDir)

			vbox = Gtk.VBox()
			self.grid.attach(vbox,i,1,1,1)

			forecastTime = Gtk.Label()
			vbox.pack_start(forecastTime,True,True,0)
			forecastTime.set_text(t)
			forecastTime.set_halign(Gtk.Align.START)

			minMax = Gtk.Label()
			vbox.pack_start(minMax,True,True,0)
			minMax.set_text(maxTemp + '/' + minTemp + u'\N{DEGREE SIGN}' + 'C')
			minMax.set_tooltip_text('Max and min temp')
			minMax.set_halign(Gtk.Align.START)

			weathericon = self.path + os.sep + 'PNG' + os.sep + symbol + '.png'
			Icon = Gtk.Image.new_from_pixbuf()
			vbox.pack_start(Icon,True,True,0)
			pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(weathericon,30,30)
			Icon.set_from_pixbuf(pixbuf)
			Icon.set_tooltip_text(cond)
			Icon.set_halign(Gtk.Align.START)

			Wind = Gtk.Label()
			vbox.pack_start(Wind,True,True,0)
			Wind.set_text(str(wndSpd) + gust + self.speed_unit)
			Wind.set_tooltip_text('Wind speed')
			Wind.set_halign(Gtk.Align.START)

			WindDir = Gtk.Label()
			vbox.pack_start(WindDir,True,True,0)
			WindDir.set_text(str(wndDir))
			WindDir.set_tooltip_text('Wind direction')
			WindDir.set_halign(Gtk.Align.START)

			Hum = Gtk.Label()
			vbox.pack_start(Hum,True,True,0)
			Hum.set_text('H ' + str(hum) + '%')
			Hum.set_tooltip_text('Humidity')
			Hum.set_halign(Gtk.Align.START)

			precipitation = Gtk.Label()
			vbox.pack_start(precipitation,True,True,0)
			precipitation.set_text(str(round(prec*100)) + '%')
			precipitation.set_tooltip_text('Chance of rain')
			precipitation.set_halign(Gtk.Align.START)

			Rain = Gtk.Label()
			vbox.pack_start(Rain,True,True,0)
			Rain.set_text(str(rain) + 'mm')
			Rain.set_tooltip_text('Total amount of rain')
			Rain.set_halign(Gtk.Align.START)

			Pres = Gtk.Label()
			vbox.pack_start(Pres,True,True,0)
			Pres.set_text(str(pres) + 'mb')
			Pres.set_tooltip_text('Pressure')
			Pres.set_halign(Gtk.Align.START)

		self.grid.show_all()
		return True

	def hourly_forecast(self, pos):
		""" Opens sub-window with 48h forecast """
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
		wnd = Gtk.Window()
		wnd.set_title('Hourly forecast')
		wnd.set_default_size(420, 500)
		wnd.move(pos[0],pos[1])

		gridBox = Gtk.ScrolledWindow()

		wnd.add(gridBox)
		box = Gtk.VBox()
		box.set_border_width(10)
		gridBox.add(box)

		grid = Gtk.Grid()
		grid.set_row_spacing(1)
		box.add(grid)

		top = ['Time','Temp',' Cond','    ','Rain','Wind','','Cloud','Pres']
		f = 0
		for item in top:
			Item = Gtk.Label()
			grid.attach(Item, f,0,1,1)
			Item.set_markup('<b>' + item + '</b>')
			f = f + 1

		fc = self.Json['hourly']

		for i in range(0,48):
			ts = fc[i]['dt']
			temp = fc[i]['temp']
			Tbg = self.tempColour(temp) # Colour coded text
			if self.temp_unit == 'F':
				temp = (temp*1.8)+32
			symbol = fc[i]['weather'][0]['icon']
			cond = fc[i]['weather'][0]['description']
			wndSpd = fc[i]['wind_speed']
			Wbg = self.windColour(wndSpd)
			wndSpd = round(self.wnd_spd_unit(wndSpd))
			wndDir = fc[i]['wind_deg']
			try:
				gust = fc[i]['wind_gust']
				Wgbg = self.windColour(gust)
				gust = round(self.wnd_spd_unit(gust))
			except:
				gust = 0
			pres = fc[i]['pressure']
			try:
				rain = fc[i]['rain']['1h']
				rain = round(float(rain),1)
			except:
				rain = 0
			cloud = fc[i]['clouds']

			sunrise = self.Json['current']['sunrise']
			sunset = self.Json['current']['sunset']

			t = datetime.fromtimestamp(ts)
			d = t.date().strftime('%a')
			t = t.time().strftime('%H')

			wndDir = self.get_wnd_dir(wndDir)

			dn = self.dayNight(sunrise, sunset, ts)

			Day = Gtk.Label()
			grid.attach(Day, 0,i+1,1,1)

			if dn == '-n':
				context = Day.get_style_context()
				context.add_class('night')
			else:
				context = Day.get_style_context()
				context.add_class('day')
			Day.set_markup('<b>' + d + ' ' + t + 'h</b>')

			temp = round(temp,1)
			Temp = Gtk.Label()
			grid.attach(Temp, 1,i+1,1,1)

			if dn == '-n':
				context = Temp.get_style_context()
				context.add_class('night')
			else:
				context = Temp.get_style_context()
				context.add_class('day')

			Temp.set_markup('<b><span foreground=\"' + Tbg + '\">' + str(temp) + u'\N{DEGREE SIGN}' + 'C</span></b>')

			weatherIcon = self.path + os.sep + 'PNG' + os.sep + symbol + '.png'
			weathericon = Gtk.Image.new_from_pixbuf()
			grid.attach(weathericon, 2,i+1,1,1)

			if dn == '-n':
				context = weathericon.get_style_context()
				context.add_class('night')
			else:
				context = weathericon.get_style_context()
				context.add_class('day')
			pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(weatherIcon,20,20)
			weathericon.set_from_pixbuf(pixbuf)
			weathericon.show()

			Name = Gtk.Label()
			grid.attach(Name, 3,i+1,1,1)

			if dn == '-n':
				context = Name.get_style_context()
				context.add_class('night')
			else:
				context = Name.get_style_context()
				context.add_class('day')
			Name.set_markup('<span variant=\"smallcaps\">' + cond + '</span>')
			Name.set_line_wrap(True)

			Prec = Gtk.Label()
			grid.attach(Prec, 4,i+1,1,1)

			if dn == '-n':
				context = Prec.get_style_context()
				context.add_class('night')
			else:
				context = Prec.get_style_context()
				context.add_class('day')
			if rain > 0:
				Prec.set_markup('<b>' + str(rain) + 'mm</b>')
			else:
				Prec.set_text(str(rain) + 'mm')

			WndSpd = Gtk.Label()
			grid.attach(WndSpd, 5,i+1,1,1)

			if dn == '-n':
				context = WndSpd.get_style_context()
				context.add_class('night')
			else:
				context = WndSpd.get_style_context()
				context.add_class('day')

			WndSpd.set_markup('<span foreground=\"' + Wbg + '\">' + str(wndSpd) + '/</span><span foreground=\"' + Wgbg + '\">' +  str(gust) + self.speed_unit + '</span>')

			WndDir = Gtk.Label()
			grid.attach(WndDir, 6,i+1,1,1)

			if dn == '-n':
				context = WndDir.get_style_context()
				context.add_class('night')
			else:
				context = WndDir.get_style_context()
				context.add_class('day')
			WndDir.set_text(str(wndDir))

			Cloud = Gtk.Label()
			grid.attach(Cloud, 7,i+1,1,1)

			if dn == '-n':
				context = Cloud.get_style_context()
				context.add_class('night')
				Cloud.set_text(str(cloud) + '%')
			else:
				context = Cloud.get_style_context()
				context.add_class('day')
				Clbg = self.cloudColour(cloud)
				Cloud.set_markup('<span background=\"' + Clbg + '\">' + str(cloud) + '%</span>')

			pres = round(float(pres))
			Pres = Gtk.Label()
			grid.attach(Pres, 8,i+1,1,1)

			if dn == '-n':
				context = Pres.get_style_context()
				context.add_class('night')
			else:
				context = Pres.get_style_context()
				context.add_class('day')
			Pres.set_text(str(pres) + 'mb')

		grid.show_all()

		wnd.connect("destroy", Gtk.main_quit)
		wnd.show_all()
		Gtk.main()

	def tempColour(self, temp):
		""" Selects font colour based on temperature """
		if temp <= 0:
			Tbg = '#00ffff'
		elif temp > 0 and temp < 5:
			Tbg = '#3399ff'
		elif temp >= 5 and temp < 10:
			Tbg = '#3366cc'
		elif temp >= 10 and temp < 15:
			Tbg = '#3319FF'
		elif temp >= 15 and temp < 20:
			Tbg= '#ff3300'
		elif temp >= 20 and temp < 25:
			Tbg = '#ff0000'
		elif temp >=25:
			 Tbg = '#993300'
		return Tbg

	def cloudColour(self, cloud):
		""" Selects BG colour based on amount of cloud """
		if cloud >= 0 and cloud < 20:
			Clbg = '#eeeeee'
		elif cloud >= 20 and cloud < 40:
			Clbg = '#dddddd'
		elif cloud >= 40 and cloud < 60:
			Clbg = '#cccccc'
		elif cloud >= 60 and cloud < 80:
			Clbg= '#bbbbbb'
		elif cloud >= 80:
			Clbg = '#aaaaaa'
		return Clbg

	def windColour(self, wndSpd):
		""" Selects font colour based on wind speed """
		if wndSpd < 8:
			Wbg = '#2E423B'
		if wndSpd >= 8 and wndSpd < 15:
			Wbg = '#CE5C00'
		elif wndSpd >= 15 and wndSpd < 20:
			Wbg = '#CE1600'
		elif wndSpd >= 20 and wndSpd < 25:
			Wbg = '#CC0000'
		elif wndSpd >= 25:
			Wbg = '#A40075'
		return Wbg

	def dayNight(self, sr, ss, h):
		""" Selects BG colour to show day/night """
		if (int(sr) <= int(h) and int(h) <= int(ss)) or (int(sr) <= int(h - 86400) and int(h - 86400) <= int(ss)) or (int(sr) <= int(h - 172800) and int(h - 172800) <= int(ss)):
			dn = '-d'
		else:
			dn = '-n'
		return dn

	def five_days(self, pos):
		""" Opens sub-window with 5 day forecast """
		url_forecast = 'http://api.openweathermap.org/data/2.5/forecast?lat='+ self.lat + '&lon=' + self.lon + '&appid=' + self.APPID

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
		win = Gtk.Window()
		win.set_title('5 day 3 hour forecast')
		win.set_default_size(450, 500)
		win.move(pos[0]-460,pos[1])

		container = Gtk.ScrolledWindow()
		#container.set_policy (Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)

		win.add(container)
		flowbox = Gtk.VBox()
		flowbox.set_border_width(10)
		container.add(flowbox)

		grid = Gtk.Grid()
		grid.set_row_spacing(1)
		flowbox.add(grid)

		forecastUrl = urllib.request.urlopen(url_forecast)
		forecast = json.load(forecastUrl)

		sunrise = forecast['city']['sunrise']
		sunset = forecast['city']['sunset']
		sunrisetime = datetime.fromtimestamp(sunrise)
		sunrise = sunrisetime.time().strftime('%H:%M')
		sunsettime = datetime.fromtimestamp(sunset)
		sunset = sunsettime.time().strftime('%H:%M')

		top = ['Time','Temp','    ','    ','Rain','Wind','','Cloud','Pres']
		f = 0
		for item in top:
			Item = Gtk.Label()
			grid.attach(Item, f,0,1,1)
			Item.set_markup('<b>' + item + '</b>')
			Item.set_halign(Gtk.Align.START)
			f = f + 1

		for i in range(0,40):
			t = forecast['list'][i]['dt']
			t = datetime.fromtimestamp(t)
			d = t.strftime('%a')
			t = t.time().strftime('%H')

			dn = self.dayNight5Day(sunrise, sunset, t)

			Day = Gtk.Label()
			grid.attach(Day, 0,i+1,1,1)
			if dn == '-n':
				context = Day.get_style_context()
				context.add_class('night')
			else:
				context = Day.get_style_context()
				context.add_class('day')

			Day.set_markup('<b>' + d + ' ' + t + 'h</b>')

			temp = forecast['list'][i]['main']['temp'] - 273.15
			Tbg = self.tempColour(temp) # Colour coded text
			if self.temp_unit == 'F':
				temp = (temp*1.8)+32
			temp = round(temp,1)
			Temp = Gtk.Label()
			grid.attach(Temp, 1,i+1,1,1)

			if dn == '-n':
				context = Temp.get_style_context()
				context.add_class('night')
			else:
				context = Temp.get_style_context()
				context.add_class('day')

			Temp.set_markup('<b><span foreground=\"' + Tbg + '\">' + str(temp) + u'\N{DEGREE SIGN}' + 'C</span></b>')

			symbol = forecast['list'][i]['weather'][0]['icon']
			weatherIcon = self.path + os.sep +  'PNG' + os.sep + symbol + '.png'
			weathericon = Gtk.Image.new_from_pixbuf()
			grid.attach(weathericon, 2,i+1,1,1)
			if dn == '-n':
				context = weathericon.get_style_context()
				context.add_class('night')
			else:
				context = weathericon.get_style_context()
				context.add_class('day')

			pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(weatherIcon, 20, 20)
			weathericon.set_from_pixbuf(pixbuf)
			weathericon.show()

			name = forecast['list'][i]['weather'][0]['description']
			Name = Gtk.Label()
			grid.attach(Name, 3,i+1,1,1)
			if dn == '-n':
				context = Name.get_style_context()
				context.add_class('night')
			else:
				context = Name.get_style_context()
				context.add_class('day')

			Name.set_markup('<span variant=\"smallcaps\">' + name + '</span>')
			Name.set_line_wrap(True)

			try:
				prec = forecast['list'][i]['rain']['3h']
			except:
				prec = 0

			prec = round(float(prec),1)
			Prec = Gtk.Label()
			grid.attach(Prec, 4,i+1,1,1)
			if dn == '-n':
				context = Prec.get_style_context()
				context.add_class('night')
			else:
				context = Prec.get_style_context()
				context.add_class('day')
			if prec > 0:
				Prec.set_markup('<b>' + str(prec) + 'mm</b>')
			else:
				Prec.set_text(str(prec) + 'mm')

			wndSpd = forecast['list'][i]['wind']['speed']
			Wbg = self.windColour(wndSpd)
			wndSpd = round(self.wnd_spd_unit(wndSpd))
			WndSpd = Gtk.Label()
			try:
				wndGst = forecast['list'][i]['wind']['gust']
				Wgbg = self.windColour(wndGst)
				wndGst = '/' + str(round(self.wnd_spd_unit(wndGst)))
			except:
				Wgbg = '#2E423B'
				wndGst = ''
			grid.attach(WndSpd, 5,i+1,1,1)
			if dn == '-n':
				context = WndSpd.get_style_context()
				context.add_class('night')
			else:
				context = WndSpd.get_style_context()
				context.add_class('day')

			WndSpd.set_markup('<span foreground=\"' + Wbg + '\">' + str(wndSpd) + '</span><span foreground=\"' + Wgbg + '\">' + wndGst + self.speed_unit + '</span>')

			wndDir = self.get_wnd_dir(forecast['list'][i]['wind']['deg'])
			WndDir = Gtk.Label()
			grid.attach(WndDir, 6,i+1,1,1)
			if dn == '-n':
				context = WndDir.get_style_context()
				context.add_class('night')
			else:
				context = WndDir.get_style_context()
				context.add_class('day')

			WndDir.set_text(str(wndDir))

			cloud = forecast['list'][i]['clouds']['all']
			Cloud = Gtk.Label()
			grid.attach(Cloud, 7,i+1,1,1)
			Clbg = self.cloudColour(cloud)
			if dn == '-n':
				context = Cloud.get_style_context()
				context.add_class('night')
				Cloud.set_markup(str(cloud) + '%')
			else:
				context = Cloud.get_style_context()
				context.add_class('day')
				Cloud.set_markup('<span background=\"' + Clbg + '\">' + str(cloud) + '%</span>')

			pres = forecast['list'][i]['main']['pressure']
			Pres = Gtk.Label()
			grid.attach(Pres, 8,i+1,1,1)
			if dn == '-n':
				context = Pres.get_style_context()
				context.add_class('night')
			else:
				context = Pres.get_style_context()
				context.add_class('day')

			Pres.set_text(str(pres) + 'mb')

		win.connect("destroy", Gtk.main_quit)
		win.show_all()
		Gtk.main()

	def dayNight5Day(self, sr, ss, h):
		if sr <= h and h <= ss:
			dn = '-d'
		else:
			dn = '-n'
		return dn

	def prefs(self, pos):
		""" Saves and stores preferences """
		from urllib.parse import quote

		def geoSearch(self):
			""" Shows up to 5 location search results """
			try:
				store.clear()
			except:
				pass

			geosearch = geosearch_input.get_text()

			searchUrl = 'https://nominatim.openstreetmap.org/?format=json&addressdetails=1&q=' + quote(geosearch) + '&limit=5'

			location = urllib.request.urlopen(searchUrl)
			location = json.load(location)

			for i in range(len(location)):
				try:
					try:
						loc = location[i]['address']['city']
					except:
						loc = location[i]['address']['town']
				except:
					try:
						loc = location[i]['address']['village']
					except:
						loc = 'Unknown'

				store.append([location[i]['display_name'],loc,location[i]['lat'],location[i]['lon'],i])

			treeview.show_all()

		def save_and_reload(button, self):
			select = treeview.get_selection()
			model, treeiter = select.get_selected()
			if treeiter is not None:
				lat1 = model[treeiter][2]
				lon1 = model[treeiter][3]
				place_name1 = model[treeiter][1]
			else:
				place_name1 = self.loc
				lat1 = self.lat
				lon1 = self.lon

			APPID = appid.get_text()
			temp_button = [r for r in button1.get_group() if r.get_active()]
			speed_button = [r for r in wndspdButton1.get_group() if r.get_active()]
			timeout = timeOut.get_text()
			if int(timeout) < 10: timeout = '10'
			font_size = font.get_value_as_int()

			with open(self.path + os.sep + 'prefs', 'w') as f:
				f.write(APPID + '\n')
				f.write(lat1 + '\n')
				f.write(lon1 + '\n')
				f.write(place_name1 + '\n')
				f.write(temp_button[0].get_label() + '\n')
				f.write(speed_button[0].get_label() + '\n')
				f.write(timeout + '\n')
				f.write(str(font_size) + '\n')
				f.write(str(pos[0]) + '\n')
				f.write(str(pos[1]))
			os.execv(sys.argv[0], sys.argv) #Reload

	#	def lock_position(self):
	#		self.pos = win.get_position()
	#		save_and_reload(self)

		win = Gtk.Window()
		win.set_default_size(400, 550)
		win.set_border_width(10)
		win.set_title('Preferences')

		container = Gtk.ScrolledWindow()
		win.add(container)

		box = Gtk.VBox()
		container.add(box)

		searchLabel = Gtk.Label()
		box.pack_start(searchLabel, False, False, 0)
		searchLabel.set_markup('<b>Search location</b>')

		searchHBox = Gtk.HBox()
		box.pack_start(searchHBox, False, False, 0)
		geosearch_input = Gtk.SearchEntry()
		geosearch_input.set_text(self.loc)
		geosearch_input.connect("activate", geoSearch)
		searchHBox.pack_start(geosearch_input, True, True, 5)
		searchLabel.set_halign(Gtk.Align.START)

		searchButton = Gtk.Button().new_with_label(" Search location ")
		searchButton.connect('clicked', geoSearch)
		searchHBox.pack_end(searchButton, False, False, 0)

		gridBox = Gtk.ScrolledWindow()
		box.pack_start(gridBox,True,True,5)

		treeview = Gtk.TreeView()
		store = Gtk.ListStore(str,str,str,str,int)
		treeview.set_model(store)

		rendererText = Gtk.CellRendererText()
		column = Gtk.TreeViewColumn('Add location from search results', rendererText, text=0)
		treeview.append_column(column)
		gridBox.add(treeview)

		appidLabel = Gtk.Label()
		box.pack_start(appidLabel,False,False,5)
		appidLabel.set_markup('<b>OpenWeatherMap key:</b>')
		appid = Gtk.Entry()
		box.pack_start(appid,False,False,0)
		appid.set_text(self.APPID)
		appidLabel.set_halign(Gtk.Align.START)

		tempBox = Gtk.Box(spacing=6)
		box.pack_start(tempBox, False, False, 5)
		tempLabel = Gtk.Label()
		tempBox.pack_start(tempLabel, False, False, 5)
		tempLabel.set_markup('<b>Temperature unit:</b>')
		button1 = Gtk.RadioButton.new_with_label_from_widget(None, "C")
		tempBox.pack_start(button1, False, False, 0)
		button2 = Gtk.RadioButton.new_from_widget(button1)
		button2.set_label("F")
		tempBox.pack_start(button2, False, False, 0)
		if self.temp_unit == 'F':
			button2.set_active(True)
		else:
			button1.set_active(True)

		wndspdBox = Gtk.Box(spacing=6)
		box.pack_start(wndspdBox, False, False, 5)
		wndspdLabel = Gtk.Label()
		wndspdBox.pack_start(wndspdLabel, False, False, 5)
		wndspdLabel.set_markup('<b>Windspeed unit:</b>')
		wndspdButton1 = Gtk.RadioButton.new_with_label_from_widget(None, "kt")
		wndspdBox.pack_start(wndspdButton1, False, False, 0)
		wndspdButton2 = Gtk.RadioButton.new_from_widget(wndspdButton1)
		wndspdButton2.set_label("mph")
		wndspdBox.pack_start(wndspdButton2, False, False, 0)
		wndspdButton3 = Gtk.RadioButton.new_from_widget(wndspdButton1)
		wndspdButton3.set_label("m/s")
		wndspdBox.pack_start(wndspdButton3, False, False, 0)
		wndspdButton4 = Gtk.RadioButton.new_from_widget(wndspdButton1)
		wndspdButton4.set_label("kph")
		wndspdBox.pack_start(wndspdButton4, False, False, 0)
		wndspdButton5 = Gtk.RadioButton.new_from_widget(wndspdButton1)
		wndspdButton5.set_label("Bf")
		wndspdBox.pack_start(wndspdButton5, False, False, 0)
		if self.speed_unit == 'mph':
			wndspdButton2.set_active(True)
		elif self.speed_unit == 'm/s':
			wndspdButton3.set_active(True)
		elif self.speed_unit == 'kph':
			wndspdButton4.set_active(True)
		elif self.speed_unit == 'Bf':
			wndspdButton5.set_active(True)
		else:
			wndspdButton1.set_active(True)

		timeoutLabel = Gtk.Label()
		box.pack_start(timeoutLabel,False,False,0)
		timeoutLabel.set_markup('<b>Refresh time (minutes):</b>')
		timeOut = Gtk.Entry()
		box.pack_start(timeOut,False,False,5)
		timeOut.set_text(str(self.get_timeout()))
		timeoutLabel.set_halign(Gtk.Align.START)

		fontLabel = Gtk.Label()
		box.pack_start(fontLabel,False,False,5)
		fontLabel.set_markup('<b>Font size:</b>')
		font_adjustment = Gtk.Adjustment(lower=9, upper=48, step_increment=1, page_increment=10)
		font = Gtk.SpinButton()
		font.set_adjustment(font_adjustment)
		box.pack_start(font,False,False,0)
		font.set_value(int(self.font_size))
		fontLabel.set_halign(Gtk.Align.START)

	#	lockButton = Gtk.Button.new_with_label("Lock position")
	#	lockButton.connect("clicked", lock_position)
	#	box.pack_end(lockButton,False,False,5)
	#	lockButton.connect("clicked", lock_position)
	#	context = lockButton.get_style_context()
	#	context.add_class('prefs')

		button = Gtk.Button.new_with_label("Save and Reload")
		button.connect("clicked", save_and_reload, self)
		box.pack_end(button,False,False,5)
#		context = button.get_style_context()
#		context.add_class('prefs')

		win.connect('destroy', Gtk.main_quit)
		win.show_all()
		Gtk.main()

if __name__ == '__main__':
	win = Win()
	win.connect("destroy", Gtk.main_quit)
	win.show_all()
	win.theLoop()
	timeout_add = GLib.timeout_add_seconds(win.get_timeout()*60, win.theLoop)
	Gtk.main()
