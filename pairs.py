import csv
import glob
import re

PAIR_FILE = 'data/2-pairings.csv'
LOGIN_FILE = 'data/2-login.csv'

#Extract 'surname,A.B.C.' from 'surname,A.B.C. (given name)' or '***' from '*** NO PARTNER ***'
NAME_RE = re.compile('(.+)(\s\(.+\)| NO PARTNER)')

#Read all pairs into a list
with open(PAIR_FILE,'rb') as f:
	pairs = [row for row in csv.DictReader(f,('Name1','Name2','Group'))]

#Read all names into dictionary with logins
with open(LOGIN_FILE,'rb') as f:
	logins = {row['Namei']: row['login'] for row in csv.DictReader(f)}
	
logins['***'] = ''
files = {}

#Loop over pairs
for pair in pairs:
	login = []
	
	#Find the login for each partner
	for partner in [pair['Name1'],pair['Name2']]:
		try:
			pname = NAME_RE.match(partner).group(1)
		except AttributeError:
			print 'Bad Name: '+partner
			pname = ''
		try:
			login += [logins[pname]]
		except KeyError:
			print 'login not found for '+pname
			login += ['']
	
	#Look for zip file for each partner, using first in preference
	pfile =  glob.glob('data/'+login[0]+'.zip')
	if not pfile:
		pfile =  glob.glob('data/'+login[1]+'.zip')
	
	#Add zip file to output dictionary if it exists
	if pfile:
		#print pair[2]+': '+pfile[0]
		files[pair['Group']] = pfile[0]
	else:
		print pair['Group']+': NO FILE'
		#files[pair[2]] = None

print str(len(files))+' Groups with submissions'
	

	