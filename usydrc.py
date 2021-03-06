#!/usr/bin/env python

import os
import re
import sys
import bs4
import stat
import smtplib
import requests

HAS_KEYRING = False
try:
	import keyring
	HAS_KEYRING = True
except ImportError:
	print("Warning: falling back to insecure password storage.")

from datetime import date, datetime
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from getpass import getpass

# Override Python 2's input (is this wrong?)
if sys.version_info.major < 3:
	input = raw_input

LOGIN_URL = "https://wasm.usyd.edu.au/login.cgi"
DEG_ID_URL = "https://ssa.usyd.edu.au/ssa/examresults/courseselect.jsp"
RESULTS_URL = "https://ssa.usyd.edu.au/ssa/examresults/courseresults.jsp"

LOGIN_DATA = {
	'appRealm': 'usyd',
	'appID': 'ssa-flexsis',
	'Submit': 'Log in',
	'destURL': ""
}

def new_login_data(username, password, url):
	"""Create an HTTP data block for an authenticated request."""
	data = {i: LOGIN_DATA[i] for i in LOGIN_DATA}
	data['credential_0'] = username
	data['credential_1'] = password
	data['destURL'] = url
	return data


def get_degree_id(username, password):
	"""Fetch the ID of the user's degree."""
	login_data = new_login_data(username, password, DEG_ID_URL)
	r = requests.post(LOGIN_URL, data=login_data, allow_redirects=True)

	if r.status_code >= 400:
		return None

	soup = BeautifulSoup(r.text)
	link = soup.find('a', href=re.compile(r"courseresults.*"))
	if link == None:
		return None
	id = link['href'].split('=')
	return int(id[-1])


def get_results_page(username, password, deg_id):
	"""Get the results page HTML."""
	url = RESULTS_URL + "?degreeid={:d}".format(deg_id)
	login_data = new_login_data(username, password, url)
	r = requests.post(LOGIN_URL, data=login_data, allow_redirects=True, timeout=5)

	if r.status_code < 400:
		return r.text
	else:
		print("Error fetching results, try deleting your details file.")
		print("If that doesn't work, check whether the results web page is down.")
		r.raise_for_status()


def guess_semester():
	"""Guess the year and semester that the user wants results for.

	Return value:
	* Tuple of ints: (year, semester)
	"""
	current_year = date.today().year
	month = date.today().month
	if month <= 5:
		year = current_year - 1
		semester = 2
	elif month <= 10:
		year = current_year
		semester = 1
	else:
		year = current_year
		semester = 2

	return (year, semester)


def diff_results(new, old):
	"""Compare two sets of results and extract interesting changes."""
	interesting = []

	# Look for unseen results
	for r in new:
		if r not in old and r['mark'] != None:
			interesting.append(r)

	return interesting


def extract_results(page, semester=None):
	"""Extract a set of results from a downloaded SSA page.

	Arguments:
	* page: SSA webpage as a string, as returned by get_results_page()
	* semester: Tuple with the year and the semester, e.g. (2013, 2)
	"""
	# Guess the semester if it isn't provided
	if semester is None:
		semester = guess_semester()

	# Unpack the semester tuple
	year, semester = semester

	# Create a BeautifulSoup object to allow HTML parsing
	soup = BeautifulSoup(page)

	# Find the heading that precedes the year's results
	year_heading = soup.find(text="Results for Academic Year: {:d}".format(year))

	if year_heading is None:
		print("Couldn't find results for year {:d}.".format(year))
		print("This could indicate a download error.")
		return []

	# Find the table that contains this heading
	year_table = year_heading.find_parent("table")

	# Find the semester block, which should be a sibling of the year block
	def correct_semester(tag):
		desired_text = "Semester {:d}".format(semester)
		if tag.find(text=desired_text):
			return True
		return False

	result_block = year_table.find_next_sibling(correct_semester)

	# Get a list in the form [MATH, 2969, Graph Theory, 74.0, Credit..]
	raw_results = result_block.find_all('td', 'instructions')

	# Convert each subject into a sensible dictionary
	results = []
	nsubjects = len(raw_results) // 5
	for i in range(nsubjects):
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
	"""Read a set of results from disk."""
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
	"""Write the results (or lack of results) to disk."""
	time_stamp = datetime.now().strftime("%a %d/%m/%y at %I:%M%p")

	r_file = open(filename, 'w')
	if len(results) == 0:
		r_file.write("Marks aren't out yet.\n")
	else:
		if new_marks_out:
			r_file.write("NEW ")
		r_file.write("Marks are out!\n\n")

		for r in results:
			result = "{subject}: {grade}, {mark:d}\n".format(**r)
			r_file.write(result)

		r_file.write("\nCheck SSA for more details, ")
		r_file.write("https://ssa.usyd.edu.au/ssa/\n")

	r_file.write("\nLast checked on {}\n".format(time_stamp))
	r_file.close()


def get_mail_server(username):
	"""Guess a suitable SMTP server for a given email address."""
	domain = username.split('@')[1]
	if domain == 'gmail.com':
		return "smtp.gmail.com:587"
	elif re.match(r"^yahoo.*", domain):
		return "plus.smtp.mail.yahoo.com:465"
	elif (re.match(r"^(live|hotmail|outlook)+.*", domain) or
		domain == 'uni.sydney.edu.au'):
		return "smtp.office365.com:587"
	return None


def email_results(username, password, server_addr, test=False):
	"""Email the results to and from the email account specified."""
	if test:
		msg = MIMEText("This is how your results will be delivered!")
	else:
		r_file = open('results.txt', 'r')
		msg = MIMEText(r_file.read())
		r_file.close()
	msg['Subject'] = 'Exam results'
	msg['From'] = username
	msg['To'] = username

	server = smtplib.SMTP(server_addr)
	server.starttls()
	server.login(username, password)
	server.sendmail(username, username, msg.as_string())
	server.quit()


def request_user_details():
	"""Prompt the user to provide their details via the commandline."""
	print("Sydney Uni login details")
	print("========================")
	creds = {}
	while True:
		creds['username'] = input("Uni-key: ")
		creds['password'] = getpass("Password: ")
		print("Validating... ")
		deg_id = get_degree_id(creds['username'], creds['password'])
		if deg_id != None:
			creds["deg_id"] = deg_id
			print("Done!")
			break
		print("\nError logging in... Please try again.")

	print("Email login details")
	print("===================")
	creds['e_username'] = input("Email Address: ")
	creds['e_password'] = getpass("Password: ")

	# Sort out SMTP server business
	server_addr = get_mail_server(creds['e_username'])
	if server_addr == None:
		print("Please enter the address & port of your SMTP server...")
		print("If you have no idea, Google it/ask a friend.")
		server_addr = input("Server [address:port]:  ")
	creds["mailserver"] = server_addr

	test = input("Send a test email? [Y/n] ").lower()
	if test in "yes":
		print("Emailing...")
		email_results(creds['e_username'], creds['e_password'],
				creds['mailserver'], test=True)
		print("Done! Check that it worked...")
	return creds


def read_user_details(filename='details.txt'):
	"""Obtain the user's details from disk."""
	# Check file permissions
	p = stat.S_IMODE(os.stat(filename).st_mode)
	if p != 0o600:
		os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR)

	creds = {}
	f = open(filename, 'r')

	# USYD username
	line = f.readline().split()
	creds['username'] = line[1]

	# USYD password
	if HAS_KEYRING:
		creds['password'] = keyring.get_password("usydrc", "unipass")
	else:
		creds['password'] = line[2]

	# Degree ID
	if len(line) < 4:
		creds['deg_id'] = None
	else:
		creds['deg_id'] = int(line[3])

	# Email address
	line = f.readline().split()
	creds['e_username'] = line[1]

	# Email password
	if HAS_KEYRING:
		creds['e_password'] = keyring.get_password("usydrc", "emailpass")
	else:
		creds['e_password'] = line[2]

	# SMTP server
	line = f.readline().split()
	creds['mailserver'] = line[1] if (line != "") else None

	f.close()
	return creds


def write_user_details(creds, filename='details.txt'):
	"""Write the user's details to disk."""

	# If we have keyring available, store the passwords securely then write
	# dummy values to the file.
	if HAS_KEYRING:
		passwords = {"password": creds["password"], "e_password": creds["e_password"]}
		keyring.set_password("usydrc", "unipass",  creds["password"])
		keyring.set_password("usydrc", "emailpass", creds["e_password"])

		# Set the dummy values
		creds["password"] = "KEYRING"
		creds["e_password"] = "KEYRING"

	f = open(filename, 'w')
	line = "Uni: {username} {password} {deg_id:d}\n".format(**creds)
	f.write(line)
	line = "Email: {e_username} {e_password}\n".format(**creds)
	f.write(line)
	if creds['mailserver'] != None:
		line = "Server: {mailserver}\n".format(**creds)
		f.write(line)
	f.close()

	# Set file permissions so only the user can read & write
	os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR)

	# Restore actual passwords
	if HAS_KEYRING:
		creds["password"] = passwords["password"]
		creds["e_password"] = passwords["e_password"]


def get_user_details():
	"""Get the user's details by whatever means neccessary."""
	if os.path.isfile("details.txt"):
		creds = read_user_details()

		# Find degree id if missing
		if creds['deg_id'] == None:
			print("Working out what degree you're in...")
			deg_id = get_degree_id(creds['username'], creds['password'])
			if deg_id == None:
				print("Authentication Failure! Delete details.txt")
				os.exit(1)
			creds['deg_id'] = deg_id
			write_user_details(creds)
	else:
		creds = request_user_details()
		write_user_details(creds)
	return creds


def main():
	creds = get_user_details()
	semester = guess_semester()

	print("Checking for {} semester {} results...".format(*semester))
	page = get_results_page(creds['username'], creds['password'], creds['deg_id'])
	new_results = extract_results(page, semester)
	old_results = read_results()
	interesting = diff_results(new_results, old_results)
	new_marks_out = (len(interesting) != 0)

	# Extend the set of old results to contain all results
	old_results.extend(interesting)

	# Store the results and email if appropriate
	write_results(old_results, new_marks_out)
	if new_marks_out:
		print("New results are out! Emailing them now!")
		email_results(creds['e_username'], creds['e_password'], creds['mailserver'])
	else:
		print("No new results.")

if __name__ == '__main__':
	main()
