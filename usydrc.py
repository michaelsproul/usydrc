#!/usr/bin/env python2

import os
import re
import smtplib
import bs4
import requests

from datetime import date, datetime
from bs4 import BeautifulSoup
from email.mime.text import MIMEText

LOGIN_URL = "https://wasm.usyd.edu.au/login.cgi"
DEG_ID_URL = "https://ssa.usyd.edu.au/ssa/examresults/courseselect.jsp"
RESULTS_URL = "https://ssa.usyd.edu.au/ssa/examresults/courseresults.jsp"

LOGIN_DATA = {
	'appRealm':'usyd',
	'appID':'ssa-flexsis',
	'Submit':'Log%20in',
	'destURL': ""
}

# Typical results block CSS (the *only* means of identifying the results block...)
results_css = "border-collapse: collapse; border: 1px #000065;width:100%; margin-top:0px; margin-bottom:5px; padding:2px;"

def new_login_data(username, password, url):
	"Create an HTTP data block for an authenticated request."
	data = {i: LOGIN_DATA[i] for i in LOGIN_DATA}
	data['credential_0'] = username
	data['credential_1'] = password
	data['destURL'] = url
	return data


def get_degree_id(username, password):
	"Fetch the ID of the user's degree."
	login_data = new_login_data(username, password, DEG_ID_URL)
	r = requests.post(LOGIN_URL, data=login_data, allow_redirects=True)

	if r.status_code >= 400:
		return None

	soup = BeautifulSoup(r.text)
	link = soup.find('a', href=re.compile("courseresults*"))
	if link == None:
		return None
	id = link['href'][-4:]
	return int(id)


def get_results_page(username, password, deg_id):
	"Get the results page HTML."
	url = RESULTS_URL + "?degreeid=%d" % deg_id
	login_data = new_login_data(username, password, url)
	r = requests.post(LOGIN_URL, data=login_data, allow_redirects=True)

	if r.status_code < 400:
		return r.text
	else:
		print "Error fetching results, try deleting your details file."
		print "If that doesn't work, check whether the results web page is down."
		r.raise_for_status()


def get_semester():
	"Work out whether to fetch results for semester 1 or 2."
	month = date.today().month
	if month >= 3 and month <= 8:
		return 1
	else:
		return 2


def diff_results(new, old):
	"Compare two sets of results and extract interesting changes."
	interesting = []

	# Look for unseen results
	for r in new:
		if r not in old and r['mark'] != None:
			interesting.append(r)

	return interesting


def extract_results(page, semester=None):
	"""Extract a set of results from a downloaded SSA page.

	The semester is guessed if none is provided.
	"""
	if semester == None:
		semester = get_semester()
	
	# Find the block of most recent results
	soup = BeautifulSoup(page)	
	result_block = soup.find_all(style=results_css)

	if len(result_block) == 0:
		print "Is the SSA website down?"
		return []

	result_block = result_block[semester - 1]

	if type(result_block) != bs4.element.Tag:
		print "Error parsing results page."
		return []

	# Get a list in the form [MATH, 2969, Graph Theory, 74.0, Credit..]
	raw_results = result_block.find_all('td', 'instructions')

	# Convert each subject into a sensible dictionary
	results = []
	nsubjects = len(raw_results)//5
	for i in xrange(nsubjects):
		result = {}
		result["subject"] = raw_results[5*i].string
		result["subject"] += raw_results[5*i + 1].string
		mark = raw_results[5*i + 3].string
		mark = int(float(mark)) if (mark != None) else None
		result['mark'] = mark
		result["grade"] = raw_results[5*i + 4].string

		# If this subject hasn't been dropped, add it
		if result["grade"] != "Withdrawn":
			results.append(result)

	return results


def read_results(filename='results.txt'):
	"Read a set of results from disk."
	try:
		results = []
		r_file = open(filename, 'r')
		if 'Marks are out!' in r_file.readline():
			for line in r_file:
				pair = line.split(':')
				# Look for an 8 character subject code
				if len(pair[0]) == 8:
					result = {}
					result["subject"] = pair[0]
					pair = pair[1].split(',')
					result["grade"] = pair[0].strip()
					result["mark"] = int(pair[1].strip())
					results.append(result)
		r_file.close()
		return results
	except IOError:
		return []


def write_results(results, new_marks_out, filename='results.txt'):
	"Write the results (or lack of results) to disk."
	time_stamp = datetime.now().strftime("%a %d/%m/%y at %I:%M%p")

	r_file = open(filename, 'w')
	if len(results) == 0:
		r_file.write("Marks aren't out yet.\n")
	else:
		if new_marks_out:
			r_file.write("NEW ")
		r_file.write("Marks are out!\n\n")
		
		for r in results:
			result = "%(subject)s: %(grade)s, " % r
			result += "%(mark)d\n" % r
			r_file.write(result)
		
		r_file.write("\nCheck SSA for more details, ")
		r_file.write("https://ssa.usyd.edu.au/ssa/\n")

	r_file.write("\nLast checked on " + time_stamp + "\n")
	r_file.close()


def email_results(username, password):
	"Email the results to and from the Gmail account specified."
	r_file = open('results.txt', 'r')
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


def request_user_details():
	"Prompt the user to provide their details via the commandline."
	print "Sydney Uni login details"
	print "========================"
	creds = {}
	while True:
		creds['username'] = raw_input("Uni-key: ")
		creds['password'] = raw_input("Password: ")
		print "Validating... "
		deg_id = get_degree_id(creds['username'], creds['password'])
		if deg_id != None:
			creds["deg_id"] = deg_id
			print "Done!"
			break
		print "\nError logging in... Please try again."

	print "Gmail login details"
	print "==================="
	creds['g_username'] = raw_input("Username: ")
	creds['g_username'] = creds['g_username'].split('@')[0]
	creds['g_password'] = raw_input("Password: ")

	return creds

def read_user_details(filename='details.txt'):
	"Obtain the user's details from disk."
	creds = {}
	f = open(filename, 'r')
	
	line = f.readline().split()
	creds['username'] = line[1]
	creds['password'] = line[2]
	if len(line) < 4:
		creds['deg_id'] = None
	else:
		creds['deg_id'] = int(line[3])
	
	line = f.readline().split()
	creds['g_username'] = line[1]
	creds['g_password'] = line[2]

	f.close()
	return creds


def write_user_details(creds, filename='details.txt'):
	"Write the user's details to disk."
	f = open(filename, 'w')
	line = "Uni: %(username)s %(password)s %(deg_id)d\n" % creds
	f.write(line)
	line = "Gmail: %(g_username)s %(g_password)s\n" % creds
	f.write(line)
	f.close()

def get_user_details():
	"Get the user's details by whatever means neccessary."
	if os.path.isfile("details.txt"):
		creds = read_user_details()

		# Find degree id if missing
		if creds['deg_id'] == None:
			print "Working out what degree you're in..."
			deg_id = get_degree_id(creds['username'], creds['password'])
			if deg_id == None:
				print "Authentication Failure! Delete details.txt"
				os.exit(1)
			creds['deg_id'] = deg_id
			write_user_details(creds)
	else:
		creds = request_user_details()
		write_user_details(creds)
	return creds


def main():
	creds = get_user_details()

	print "Downloading the results page..."
	page = get_results_page(creds['username'], creds['password'], creds['deg_id'])

	new_results = extract_results(page)
	old_results = read_results()

	interesting = diff_results(new_results, old_results)
	new_marks_out = (len(interesting) != 0)

	# Extend the set of old results to contain all results
	# TODO: Handle *changes* in marks more elegantly
	old_results.extend(interesting)

	# Store the results and email if appropriate
	write_results(old_results, new_marks_out)
	if new_marks_out:
		print "New results are out! Emailing them now!"
		email_results(creds['g_username'], creds['g_password'])
	print "Done."

if __name__ == '__main__':
	main()
