#!/usr/bin/env python3

import bs4
import smtplib
import requests
import re

from datetime import date, datetime
from bs4 import BeautifulSoup
from email.mime.text import MIMEText

login_url = "https://wasm.usyd.edu.au/login.cgi"
course_url = "https://ssa.usyd.edu.au/ssa/examresults/courseselect.jsp"
results_url = "https://ssa.usyd.edu.au/ssa/examresults/courseresults.jsp"

login_data = {
	'appRealm':'usyd',
	'appID':'ssa-flexsis',
	'Submit':'Log%20in',
	'destURL': ""
}

# A filthy, horrible way of identifying the results block. I blame whoever made usyd's websites.
result_style = "border-collapse: collapse; border: 1px #000065;width:100%; margin-top:0px; margin-bottom:5px; padding:2px;"


def auth_setup(username, password):
	"Add a username and password to the HTTP POST data."
	login_data['credential_0'] = username
	login_data['credential_1'] = password


def get_degree_id():
	"Fetch the ID of the user's degree."
	login_data['destURL'] = course_url
	r = requests.post(login_url, data=login_data, allow_redirects=True)
	soup = BeautifulSoup(r.text)
	link = soup.find_all('a', href=re.compile("courseresults*"))[0]
	id = link['href'][-4:]
	return int(id)


def get_results(degree_id):
	"Get the results page HTML."
	login_data['destURL'] = results_url + "?degreeid=%d" % degree_id
	r = requests.post(login_url, data=login_data, allow_redirects=True)
	if r.status_code < 400:
		return r.text
	else:
		return None


def get_semester():
	"""Work out whether it's semester 1 or 2.

	For results purposes, March to August is semester 1
	September to February is semester 2
	"""
	month = date.today().month
	if month >= 3 and month <= 8:
		return 1
	else:
		return 2


def interpret(page):
	"Interpret the downloaded results page and act accordingly."
	soup = BeautifulSoup(page)

	# Find the block of most recent results
	semester = get_semester()
	result_block = soup.find_all(style=result_style)[semester - 1]

	if type(result_block) != bs4.element.Tag:
		print('No valid data found')
		return

	# Get a list in the form MATH|2000|Maths|75.0|Distinction
	raw_results = result_block.find_all('td', 'instructions');

	# Convert the subjects into dictionaries
	results = []
	nsubjects = int(len(raw_results)/5)
	for i in range(0, nsubjects):
		entry = {}
		entry["subject"] = raw_results[5*i].string + raw_results[5*i + 1].string
		entry["mark"] = raw_results[5*i + 3].string
		entry["grade"] = raw_results[5*i + 4].string

		# Ignore subjects that've been dropped
		if entry["grade"] == "Withdrawn":
			continue

		results.append(entry)

	del raw_results

	# Check the previous results file for subjects that already have marks
	old_results = []

	try:
		r_file = open('results', 'r')
		if 'Marks are out!' in r_file.readline():
			for line in r_file:
				pair = line.split(':')
				if len(pair[0]) == 8:
					entry = {}
					entry["subject"] = pair[0]
					pair = pair[1].split(',')
					entry["grade"] = pair[0].strip()
					entry["mark"] = pair[1].strip()
					old_results.append(entry)
		r_file.close()
	except IOError:
		print('No previous results file to read, oh well.')

	for r in old_results:
		if r in results:
			del results[results.index(r)]

	print("Checking for new results for: ")
	for r in results:
		print(r["subject"])

	# Look for new marks
	new_marks_out = False
	for r in results:
		if r["mark"] != None:
			new_marks_out = True
			old_results.append(r)

	# Write results to disk, and email if appropriate
	write_results(old_results, new_marks_out)

	if new_marks_out:
		print("Emailing results...")
		email_results()


def write_results(results, new_marks_out):
	"Write the results (or lack of results) to disk."
	time_stamp = datetime.now().strftime("%a %d/%m/%y at %I:%M%p")

	with open('results', 'w') as r_file:
		if len(results) == 0:
			r_file.write("Marks aren't out yet.\n")
		else:
			if new_marks_out:
				r_file.write("NEW ")
		
			r_file.write("Marks are out!\n")
		
			for r in results:
				result = "%s: %s, %s\n" % (r["subject"],
							   r["grade"],
							   r["mark"])
				r_file.write(result)
		
			r_file.write("\nCheck SSA for more details, ")
			r_file.write("https://ssa.usyd.edu.au/ssa/\n'")

		r_file.write("\nLast checked on " + time_stamp + "\n")


def email_results(username, password):
	"Email the results to and from the gmail account specified."
	r_file = open('r_file', 'r')
	me = '%s@gmail.com' % username

	msg = MIMEText(r_file.read())
	r_file.close()
	msg['Subject'] = 'Exam results'
	msg['From'] = me
	msg['To'] = me

	server = smtplib.SMTP('smtp.gmail.com:587')
	server.starttls()
	server.login(username, password)
	server.sendmail(me, me, msg.as_string())
	server.quit()


def get_user_details():
	"Obtain the user's details from disk/the innernet."
	with open('details', 'r') as f:
		line = f.readline().split()
		username = line[1]
		password = line[2]
		if len(line) < 4:
			degree_id = None
		else:
			degree_id = int(line[3])
		line = f.readline().split()
		g_username = line[1]
		g_password = line[2]

	return (username, password, degree_id, g_username, g_password)


def write_user_details(username, password, degree_id, g_username, g_password):
	"Write the user's details to disk."
	with open('details', 'w') as f:
		line = "Uni: %s %s %d\n" % (username, password, degree_id)
		f.write(line)
		line = "Gmail: %s %s\n" % (g_username, g_password)
		f.write(line)


def main():
	username, password, deg_id, g_username, g_password = get_user_details()

	auth_setup(username, password)

	if deg_id == None:
		print("Working out what degree you're in...")
		deg_id = get_degree_id()
		write_user_details(username, password, deg_id,
					g_username, g_password)

	print("Downloading the results page...")
	interpret(get_results(deg_id))

if __name__ == '__main__':
	main()
