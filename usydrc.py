#!/usr/bin/env python2

import os
import re
import smtplib
import bs4
import requests

from datetime import date, datetime
from bs4 import BeautifulSoup
from email.mime.text import MIMEText

login_url = "https://wasm.usyd.edu.au/login.cgi"
deg_id_url = "https://ssa.usyd.edu.au/ssa/examresults/courseselect.jsp"
results_url = "https://ssa.usyd.edu.au/ssa/examresults/courseresults.jsp"

login_data = {
	'appRealm':'usyd',
	'appID':'ssa-flexsis',
	'Submit':'Log%20in',
	'destURL': ""
}

# Typical results block CSS (the *only* means of identifying the results block...)
results_css = "border-collapse: collapse; border: 1px #000065;width:100%; margin-top:0px; margin-bottom:5px; padding:2px;"

def auth_setup(username, password):
	"Add a username and password to the HTTP POST data."
	login_data['credential_0'] = username
	login_data['credential_1'] = password


def get_degree_id():
	"Fetch the ID of the user's degree."
	login_data['destURL'] = deg_id_url
	r = requests.post(login_url, data=login_data, allow_redirects=True)
	
	if r.status_code >= 400:
		return None
	

	soup = BeautifulSoup(r.text)
	link = soup.find('a', href=re.compile("courseresults*"))
	id = link['href'][-4:]
	return int(id)


def get_results(deg_id):
	"Get the results page HTML."
	login_data['destURL'] = results_url + "?degreeid=%d" % deg_id
	r = requests.post(login_url, data=login_data, allow_redirects=True)

	if r.status_code < 400:
		return r.text
	else:
		print "Error fetching results, try deleting your details file."
		r.raise_for_status()


def get_semester():
	"Work out whether to fetch results for semester 1 or 2."
	month = date.today().month
	if month >= 3 and month <= 8:
		return 1
	else:
		return 2


def interpret(g_username, g_password, page, semester=None):
	"Interpret the downloaded results page and act accordingly."
	soup = BeautifulSoup(page)

	# Find the block of most recent results
	if semester == None:
		semester = get_semester()
	result_block = soup.find_all(style=results_css)[semester - 1]

	if type(result_block) != bs4.element.Tag:
		print "Error parsing results page."
		return

	# Get a list in the form [MATH, 2969, Graph Theory, 74.0, Credit..]
	raw_results = result_block.find_all('td', 'instructions')

	# Convert each subject into a sensible dictionary
	new_results = []
	nsubjects = len(raw_results)//5
	for i in xrange(nsubjects):
		result = {}
		result["subject"] = raw_results[5*i].string
		result["subject"] += raw_results[5*i + 1].string
		result["mark"] = raw_results[5*i + 3].string
		result["grade"] = raw_results[5*i + 4].string

		# If this subject hasn't been dropped, add it
		if result["grade"] != "Withdrawn":
			new_results.append(result)

	del raw_results

	# Check the previous results file for subjects that already have marks
	results = []
	try:
		r_file = open('results.txt', 'r')
		if 'Marks are out!' in r_file.readline():
			for line in r_file:
				pair = line.split(':')
				if len(pair[0]) == 8:
					result = {}
					result["subject"] = pair[0]
					pair = pair[1].split(',')
					result["grade"] = pair[0].strip()
					result["mark"] = pair[1].strip()
					results.append(result)
		r_file.close()
	except IOError:
		pass

	for r in results:
		if r in new_results:
			new_results.remove(r)

	# Look for new marks
	new_marks_out = False
	for r in new_results:
		if r["mark"] != None:
			new_marks_out = True
			results.append(r)

	# Write results to disk, and email if appropriate
	write_results(results, new_marks_out)

	if new_marks_out:
		print "New results are out! Emailing them now!"
		email_results(g_username, g_password)


def write_results(results, new_marks_out):
	"Write the results (or lack of results) to disk."
	time_stamp = datetime.now().strftime("%a %d/%m/%y at %I:%M%p")

	r_file = open('results.txt', 'w')
	if len(results) == 0:
		r_file.write("Marks aren't out yet.\n")
	else:
		if new_marks_out:
			r_file.write("NEW ")
		r_file.write("Marks are out!\n\n")
		
		for r in results:
			result = "%(subject)s: %(grade)s, " % r
			result += "%(mark)s\n" % r
			r_file.write(result)
		
		r_file.write("\nCheck SSA for more details, ")
		r_file.write("https://ssa.usyd.edu.au/ssa/\n")

	r_file.write("\nLast checked on " + time_stamp + "\n")
	r_file.close()


def email_results(username, password):
	"Email the results to and from the gmail account specified."
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


def get_user_details():
	"Prompt the user to provide their details via the commandline."
	print "Sydney Uni login details"
	print "========================"
	creds = {}
	while True:
		creds['username'] = raw_input("Uni-key: ")
		creds['password'] = raw_input("Password: ")
		auth_setup(creds["username"], creds["password"])
		print "Validating... "
		deg_id = get_degree_id()
		if not deg_id == None:
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

def read_user_details():
	"Obtain the user's details from disk"
	creds = {}
	f = open('details.txt', 'r')
	
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


def write_user_details(creds):
	"Write the user's details to disk."
	f = open('details.txt', 'w')
	line = "Uni: %(username)s %(password)s %(deg_id)d\n" % creds
	f.write(line)
	line = "Gmail: %(g_username)s %(g_password)s\n" % creds
	f.write(line)
	f.close()


def main():
	# Read user details from the `details' file if it exists
	if os.path.isfile("details.txt"):
		creds = read_user_details()
		auth_setup(creds['username'], creds['password'])
	
		# Find degree id if missing
		if creds['deg_id'] == None:
			print "Working out what degree you're in..."
			creds['deg_id'] = get_degree_id()
			write_user_details(creds)
	else:
		creds = get_user_details()
		write_user_details(creds)

	print "Downloading the results page..."
	page = get_results(creds['deg_id'])
	interpret(creds['g_username'], creds['g_password'], page)
	print "Done."

if __name__ == '__main__':
	main()
