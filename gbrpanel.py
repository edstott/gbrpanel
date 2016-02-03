import re
import glob
import os

#filemask = '*.[Gg]*'
outdir = 'out'
outfile = 'out'
indir = 'test'

filetypes = ['GBL','GBS','GTL','GTO','GTS','Outline']

AP_RE = re.compile('\%AD(D\d+)([RCO],\d+.\d+(X\d+.\d+)?)\*\%')	#Aperture definition
D_RE = re.compile('(D(\d+))\*')	#Operation
C_RE = re.compile('([XY])(\d+)(Y(\d+))?(I(-?\d+))?(J(-?\d+))?(D0[12])\*') #Draw commands
G_RE = re.compile('G(\d\d)(.*)\*') #Graphics, modes, comments
FS_RE = re.compile('\%FSLAX(\d)(\d)Y(\d)(\d)\*\%') #Format specification
MO_RE = re.compile('\%MO(IN|MM)\*\%') #Units specification
LP_RE = re.compile('\%LP[CD]\*\%') #Level changes
M02_RE = re.compile('M02\*') #End of file

STREAM_Gs = ['01','02','03','74','75','36','37']
IGNORE_Gs = ['70','71']
OK_Ds = ['01','02','03']

DEF_DIGITS = (10,10)
DEF_PREC = (5,5)
#DEF_FORMAT = ('X{:0'+str(DEF_DIGITS[0])+'d}','Y{:0'+str(DEF_DIGITS[1])+'d}')
DEF_FORMAT = ('X{:d}','Y{:d}')
DEF_OFF_FORMAT = ('I{:d}','J{:d}')

boardpitch = (100,100)
boarddims = (100,100)
paneldims = (2,2)

def WriteGerber():	
	with open(os.path.join(outdir,outfile+str(panelidx)+'.'+ft),'w') as file:
		#Write comments
		for c in comments:
			file.write('G04'+c+'*\n')
			
		#Write precision
		file.write('%FSLAX{:d}{:d}Y{:d}{:d}*%\n'.format(outdigits[0]-outprec[0],outprec[0],outdigits[1]-outprec[1],outprec[1]))
		
		#Write units
		if MOMM:
			file.write('%MOMM*%\n')
		else:
			file.write('%MOIN*%\n')
			
		#Write apertures
		for a,d in outapdict.items():
			file.write('%AD'+d+a+'*%\n')
			
		#Write commands
		for g in outgerber:
			file.write(g+'\n')
			
		#Write EOFError
		file.write('M02*\n')

for ft in filetypes:	#Loop over gerber file extensions
	print('File Extension .'+ft)
	files = glob.glob(os.path.join(indir,'*.'+ft))

	panelidx = 0

	#Set up the first panel
	boardidx = 0
	outapdict = {}
	outapDidx = 10

	outgerber = []
	outdigits = DEF_DIGITS
	outformat = DEF_FORMAT
	outoffformat = DEF_OFF_FORMAT
	outprec = DEF_PREC
	print(' Panel '+str(panelidx))

	for filename in files:	#Loop over files with the correct extension

		inapmap = {}
		comments = []
		digits = DEF_DIGITS
		inprec = DEF_PREC
		informat = DEF_FORMAT
		MOMM = True
		
		#Set up board origin based on index and dimensions
		boardorigin = (int(boardidx/paneldims[0])*boardpitch[0],boardidx%paneldims[0]*boardpitch[1])
		print('  Board '+str(boardidx))

		with open(filename,'r') as file:
			
			for line in file:
			
				lineok = False
			
				m = AP_RE.match(line)	#Check for aperture definition
				if m:
					if m.group(2) not in outapdict:	#Does this aperture already exist?
						outapdict[m.group(2)] = 'D'+str(outapDidx)  #If not, add to output dictionary
						outapDidx += 1
					inapmap[m.group(1)] = outapdict[m.group(2)] #Add a map from file D-number to output D-number
					lineok = True
					
				m = D_RE.match(line) #Check for a D code
				if m:
					if int(m.group(2))>9: #D-code applies an aperture
						outgerber += [inapmap[m.group(1)]+'*'] #Translate the aperture
						lineok = True
					elif m.group(2) in OK_Ds:
						outgerber += [m.group(1)+'*'] #Just copy reserved D-codes (below 10)
						lineok = True
						
				m = C_RE.match(line)	#Check for a coordinate
				if m:	#'([XY])(\d+)(Y(\d+))?(I(-?\d+))?(J(-?\d+))?(D0[12])\*'
					outstr = ''
					xcoord = 0
					ycoord = 0
					if m.group(1)=='Y': #Y coordinate only
						ycoord = int(m.group(2))*scale[1]+boardorigin[1]*10**outprec[1]
						outstr = outformat[1].format(ycoord)
					elif m.group(3): #X and Y coordinates
						xcoord = int(m.group(2))*scale[0]+boardorigin[0]*10**outprec[0]
						ycoord = int(m.group(4))*scale[1]+boardorigin[1]*10**outprec[1]
						outstr = outformat[0].format(xcoord)+outformat[1].format(ycoord)
					else: #X coordinate only
						xcoord = int(m.group(2))*scale[0]+boardorigin[0]*10**outprec[0]
						outstr = outformat[0].format(xcoord)
					if m.group(5):	#I offset present
						icoord = int(m.group(6))*scale[0]
						outstr += outoffformat[0].format(icoord)
					if m.group(7):	#J offset present
						jcoord = int(m.group(8))*scale[1]
						outstr += outoffformat[1].format(jcoord)
					outstr += m.group(9)+'*'
					
					if xcoord/(10**outprec[0]) < boardorigin[0]:
						print("Drawing X outside allowed region "+str(xcoord/(10**outprec[0]))+'<'+str(boardorigin[0]))
					elif xcoord/(10**outprec[0]) > boardorigin[0]+boarddims[0]:
						print("Drawing X outside allowed region "+str(xcoord/(10**outprec[0]))+'>'+str(boardorigin[0]+boarddims[0]))
					elif ycoord/(10**outprec[1]) < boardorigin[1]:
						print("Drawing Y outside allowed region "+str(ycoord/(10**outprec[1]))+'<'+str(boardorigin[1]))
					elif ycoord/(10**outprec[1]) > boardorigin[1]+boarddims[1]:
						print("Drawing Y outside allowed region "+str(ycoord/(10**outprec[1]))+'>'+str(boardorigin[1]+boarddims[1]))
					else:
						outgerber += [outstr]				
						lineok = True
				
				m = G_RE.match(line)	#Check for G code
				if m:
					if m.group(1) == '04':	#G04 is a comment
						if m.group(2) not in comments:
							comments += [m.group(2)]
						lineok = True
					elif m.group(1) in STREAM_Gs:	#Add these Gs to output stream
						outgerber += ['G'+m.group(1)+'*']
						lineok = True
					elif m.group(1) in IGNORE_Gs: #Ignore these Gs
						lineok = True
						
				m = FS_RE.match(line)	#Coordinate spec
				if m:
						digits = (int(m.group(1))+int(m.group(2)),int(m.group(3))+int(m.group(4)))
						inprec = (int(m.group(2)),int(m.group(4)))
						informat = ('X{:0'+str(digits[0])+'d}','Y{:0'+str(digits[1])+'d}')
						scale = (10**(outprec[0]-inprec[0]),10**(outprec[1]-inprec[1]))
						lineok = True
						
				m = MO_RE.match(line)	#Units spec
				if m:
					if m.group(1) == 'MM':
						MOMM = True
					else:
						MOMM = False
						print('Bad units!')
					lineok = True
				
				m = LP_RE.match(line)	#New level
				if m:
					outgerber += [m.group(0)]
					lineok = True
				
				m = M02_RE.match(line) #End of file
				if m:
					lineok = True
						
				if not lineok:
					print('Unrecognised line: '+line)

		boardidx += 1
		if boardidx == paneldims[0]*paneldims[1]:	#Write the output if the panel is full
			WriteGerber()
			
			#Reset for the next panel
			panelidx += 1
			boardidx = 0
			outapdict = {}
			outapDidx = 10

			outgerber = []
			outdigits = DEF_DIGITS
			outformat = DEF_FORMAT
			outoffformat = DEF_OFF_FORMAT
			outprec = DEF_PREC
			print(' Panel '+str(panelidx))

	#Write any partially-full final panel
	if boardidx > 0:
		WriteGerber()
		
	