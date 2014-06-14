#!/usr/bin/env python

import os
import unittest

from usydrc import *

creds = read_user_details('details.txt')

class HttpDataTest(unittest.TestCase):
	def test_login_data(self):
		username = 'dennis'
		password = 'anarchosyndicalism'
		url = 'http://python.org/'
		data = new_login_data(username, password, url)
		self.assertEqual(username, data['credential_0'])
		self.assertEqual(password, data['credential_1'])
		self.assertEqual(url, data['destURL'])

class DegIdTest(unittest.TestCase):
	def test_degree_id(self):
		deg_id = get_degree_id(creds['username'], creds['password'])
		self.assertEqual(creds['deg_id'], deg_id)

	def test_degree_id_invalid(self):
		deg_id = get_degree_id('unperson', '4891')
		self.assertIsNone(deg_id)

class ResultParsingTest(unittest.TestCase):
	def setUp(self):
		self.results = [{'subject': 'COMP2129',
				 'grade': 'High Distinction',
				 'mark': 94},
				{'subject': 'MATH2969',
				 'grade': 'Credit',
				 'mark': 74},
				{'subject': 'MATH2961',
				 'grade': 'Distinction',
				 'mark': 77},
				{'subject': 'PHYS2911',
				 'grade': 'High Distinction',
				 'mark': 88}]
		self.results.sort(key=lambda x: x['subject'])

	def test_rw_results(self):
		if os.path.exists('test_results.txt'):
			os.remove('test_results.txt')
		write_results(self.results, False, 'test_results.txt')
		observed = read_results('test_results.txt')
		observed.sort(key=lambda x: x['subject'])
		self.assertEqual(self.results, observed)
		os.remove('test_results.txt')

	def test_diff_results(self):
		new = [r for r in self.results]
		new.append({'subject': 'INFO2222', 'grade': 'Unavailable',
				'mark': None})
		interesting = diff_results(self.results + new, self.results)
		self.assertEqual([], interesting)
		new_interesting = [{'subject': 'COMP7777',
				   'grade': 'High Distinction',
				   'mark': 89}]
		new.extend(new_interesting)
		interesting = diff_results(self.results + new, self.results)
		self.assertEqual(new_interesting, interesting)

	def test_download_extract(self):
		# This test only works if you have my login details...
		page = get_results_page(creds['username'], creds['password'], creds['deg_id'])
		results = extract_results(page, semester=(2013, 1))
		results.sort(key=lambda x: x['subject'])
		self.assertEqual(self.results, results)

def suite():
	testcases = [HttpDataTest, DegIdTest, ResultParsingTest]
	tests = []
	for tc in testcases:
		tests.append(unittest.TestLoader().loadTestsFromTestCase(tc))
	suite = unittest.TestSuite()
	suite.addTests(tests)
	return suite

if __name__ == '__main__':
	alltests = suite()
	unittest.TextTestRunner(verbosity=2).run(alltests)
