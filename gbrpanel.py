import re

AP_RE = re.compile('\%AD(D\d+)([RCO],\d+.\d+(X\d+.\d+)?)\*\%')
D_RE = re.compile('(D(\d+))\*')
C_RE = re.compile('(([XY])(\d+))(([XY])(\d+))?(D0[12])\*')
filename = 'test.gbr'

outapdict = {}
outapDidx = 10

outgerber = []

with open(filename,'r') as file:
	inapmap = {}
	boardorigin = (100,100)
	
	for line in file:
	
		m = AP_RE.match(line)	#Check for aperture definition
		if m:
			if m.group(2) not in outapdict:	#Does this aperture already exist?
				outapdict[m.group(2)] = 'D'+str(outapDidx)  #If not, add to output dictionary
				outapDidx += 1
			inapmap[m.group(1)] = outapdict[m.group(2)] #Add a map from file D-number to output D-number
			
		m = D_RE.match(line) #Check for a D code
		if m:
			if int(m.group(2))>9: #D-code applies an aperture
				outgerber += [inapmap[m.group(1)]+'*'] #Translate the aperture
			else:
				outgerber += [m.group(1)+'*'] #Just copy reserved D-codes (below 10)
				
		m = C_RE.match(line)
		if m:
			Cline = ''
			if m.group(2)=='Y':
				CLine = 'Y'+'{:06d}'.format(int(m.group(3))+boardorigin(2)+'*'
				
			
			
#print outapdict
print outgerber
#print inapmap