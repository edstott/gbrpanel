import re
import glob
import os
import subprocess

import pairs

#filemask = '*.[Gg]*'
outdir = 'out'
outfile = 'out'
indir = 'test'

filetypes = ['GBL','GBS','GTL','GTO','GTS','Outline','TXT']
#filetypes = ['Outline']
REPORT_FILE = 'report.txt'

AP_RE = re.compile('\%AD(D\d+)(([RCOP]),(\d+(?:\.\d+)?)(?:X(\d+(?:\.\d+)?))*)\*\%')	#Aperture definition
APM_RE = re.compile('\%AD(D\d+)([a-zA-Z]\w*)\*\%')	#Aperture macro definition
AM_RE = re.compile('\%AM([a-zA-Z]\w*)\*') #Begin Aperture Macro
AMP_RE = re.compile('(1|21|4),(?:(-?\d+(?:\.\d+)?),)*(?:(-?\d+(?:\.\d+)?)\*)') #Primitive code in macro
D_RE = re.compile('(D(\d+))\*')	#Operation
C_RE = re.compile('([XY])(-?\d+)(Y(-?\d+))?(I(-?\d+))?(J(-?\d+))?(D0[12])\*') #Draw commands
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
DEF_IN_OFFSET = (15.0,15.0)

CHECK_DIMS =True
DIM_TOL = 0.5

boardpitch = (80.0,90.0)
boarddims = (70.0,80.0)
paneldims = (10,10)

def WriteGerber():	
	with open(os.path.join(outdir,outfile+str(panelidx)+'.'+ft),'w') as file:
		#Write comments
		for c in comments:
			file.write('G04'+c+'*\n')
			
		#Write precision
		file.write('%FSLAX{:d}{:d}Y{:d}{:d}*%\n'.format(outdigits[0]-outprec[0],outprec[0],outdigits[1]-outprec[1],outprec[1]))
		
		#Write units
		if True:#MOMM:
			file.write('%MOMM*%\n')
		#else:
		#	file.write('%MOIN*%\n')
			
		#Write macros
		for m,d in outamdict.items():
			file.write('%AM'+m+'*\n')
			for p in d['Macro']:
				file.write(p)
			file.write('%\n')
			
		#Write apertures
		for a,d in outapdict.items():
			if d[1]: #Apertures that have been translated
				file.write('%AD'+d[0]+d[1]+'*%\n')
			else: #Apertures that are macro references
				file.write('%AD'+d[0]+a+'*%\n')
			
		#Write commands
		for g in outgerber:
			file.write(g+'\n')
			
		#Write EOFError
		file.write('M02*\n')
		
if __name__ == '__main__':

	pairs = pairs.getPairs()
	#pairs = pairs[0:5]
	panels = []
	badDimRecord = []

	for ft in filetypes:	#Loop over gerber file extensions
		print('File Extension .'+ft)
		filename = 'PCB.'+ft

		panelidx = 0

		#Set up the first panel
		boardidx = 0
		outapdict = {}
		outapDidx = 10
		outamdict = {}
		inamdict = {}

		outgerber = []
		outdigits = DEF_DIGITS
		outformat = DEF_FORMAT
		outoffformat = DEF_OFF_FORMAT
		outprec = DEF_PREC
		#print(' Panel '+str(panelidx))

		for pair in pairs:
		
			inapmap = {}
			comments = []
			digits = DEF_DIGITS
			inprec = None
			informat = DEF_FORMAT
			MOMM = None
			currentMacro = None
			unitScale = None
			inoffset = DEF_IN_OFFSET
			xcoord = 0
			ycoord = 0
			badLines = False
			badDims = 0
			
			#Set up board origin based on index and dimensions
			boardorigin = (int(boardidx/paneldims[0])*boardpitch[0],boardidx%paneldims[0]*boardpitch[1])
			#print('  Board '+str(boardidx)+': group '+pair[0]+' zip '+pair[1])
			
			#Extract file
			if not ft == 'Outline': #Don't extract the outline, use the reference PCB.Outline
				if subprocess.call(['7z','e',pair[1],'-y','Gerber/'+filename],stdout=subprocess.PIPE,stderr=subprocess.PIPE):
					print('Could not unzip '+filename+' from '+pair[1])
					raise Exception

			with open(filename,'r') as file:
				
				for line in file:
				
					lineok = False
				
					m = AP_RE.match(line)	#Check for aperture definition
					if m:
						if m.group(2) not in outapdict:	#Does this aperture already exist?
							if m.group(3) == 'C': #Circle has one dimension
								apDims = [str(float(m.group(4))*unitScale)]
							elif m.group(3) == 'P': #Polygon has one dimension, and optional rotation and hole size
								apDims = [str(float(m.group(4))*unitScale)]
								if m.group(5): #Rotation is not converted
									apDims += [m.group(5)]
									if len(m.groups())>=6: #Hole size is converted
										apDims += [str(float(m.group(6))*unitScale)]
							else:
								apDims = [str(float(i)*unitScale) for i in m.groups()[3:]]
							outapdict[m.group(2)] = ('D'+str(outapDidx),m.group(3)+','+'X'.join(apDims))  #If not, add to output dictionary
							outapDidx += 1
						inapmap[m.group(1)] = outapdict[m.group(2)][0] #Add a map from file D-number to output D-number
						lineok = True
						
					m = APM_RE.match(line)	#Check for aperture macro definition
					if m:
						macro = inamdict[m.group(2)] #Find new name for this macro
						outapdict[macro] = (outamdict[macro]['MacroD'],None) #Create an output mapping for the macros D code
						inapmap[m.group(1)] = outamdict[macro]['MacroD'] #Create a D code mapping
						lineok = True
						
					m = AM_RE.match(line) #Macro definition
					if m:
						currentMacroD = 'D'+str(outapDidx) #Give the macro a new D code
						outapDidx += 1
						currentMacro = 'MACRO'+currentMacroD #Give the macro a new name
						outamdict[currentMacro] = {'MacroD':currentMacroD, 'Macro':[]} #Initialise a new entry in macro dictionary
						inamdict[m.group(1)] = currentMacro #Relate the original name to the new name	
						lineok = True
						
					m = AMP_RE.match(line) #Match a macro primitive
					#'(1|21|4),(-?\d+(\.\d+)?,)*(-?\d+(\.\d+)?\*)')
					if m and currentMacro: #Only valid if a macro is open
						if m.group(1) == '1': #Circle
							amp = m.group(0)[:-1].split(',')
							amp[2] = str(float(amp[2])*unitScale)
							amp[3] = str(float(amp[3])*unitScale)
							amp[4] = str(float(amp[4])*unitScale)
						
							outamdict[currentMacro]['Macro'] += [','.join(amp)+'*\n']
							lineok = True
							
						if m.group(1) == '21': #Centre Line Rectangle
							amp = m.group(0)[:-1].split(',')
							amp[2] = str(float(amp[2])*unitScale)
							amp[3] = str(float(amp[3])*unitScale)
							amp[4] = str(float(amp[4])*unitScale)
							amp[5] = str(float(amp[5])*unitScale)
						
							outamdict[currentMacro]['Macro'] += [','.join(amp)+'*\n']
							lineok = True
							
						if m.group(1) == '4': #Outline
							amp = m.group(0)[:-1].split(',')
							amp = amp[0:3] + [str(float(i)*unitScale) for i in amp[3:-1]] + [amp[-1]] #Convert everything except the Exposure flag, point count and rotation
							
							outamdict[currentMacro]['Macro'] += [','.join(amp)+'*\n']
							lineok = True
						
					if line == '%\n' and currentMacro: #End of a macro
						currentMacro = None	
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
						icoord = 0
						jcoord = 0
						xPresent = False
						yPresent = False
						iPresent = False
						jPresent = False
						
						#print(line[0:-1])
						
						if m.group(1)=='Y': #Y coordinate only
							ycoord = float(m.group(2))*unitScale/10**inprec[1]-inoffset[1]
							yPresent = True
							#print('Y')
						elif m.group(3): #X and Y coordinates
							xcoord = float(m.group(2))*unitScale/10**inprec[0]-inoffset[0]
							ycoord = float(m.group(4))*unitScale/10**inprec[1]-inoffset[1]
							xPresent = True
							yPresent = True
							#print('XY')
						else: #X coordinate only
							xcoord = float(m.group(2))*unitScale/10**inprec[0]-inoffset[0]
							xPresent = True
							#print('X')
						if m.group(5):	#I offset present
							icoord = float(m.group(6))*unitScale/10**inprec[0]
							iPresent = True
						if m.group(7):	#J offset present
							jcoord = float(m.group(8))*unitScale/10**inprec[1]
							jPresent = True
							
							
						#print('X: '+str(xcoord))
						#print('Y: '+str(ycoord))
							
						
						if CHECK_DIMS:
							if xcoord+icoord < -DIM_TOL:
								#print("Drawing X outside allowed region "+str(xcoord+icoord)+' < 0.0')
								pass
							elif xcoord+icoord-boarddims[0] > DIM_TOL:
								#print("Drawing X outside allowed region "+str(xcoord+icoord)+' > '+str(boarddims[0]))
								pass
							elif ycoord+jcoord < -DIM_TOL:
								#print("Drawing Y outside allowed region "+str(ycoord+jcoord)+' < 0.0')
								pass
							elif ycoord+jcoord-boarddims[1] > DIM_TOL:
								#print("Drawing Y outside allowed region "+str(ycoord+jcoord)+' > '+str(boarddims[1]))
								pass
							else:
								lineok = True		
						else:
							lineok = True									
								
						if xPresent:
							outstr += outformat[0].format(int((xcoord+boardorigin[0])*10**outprec[0]))
						if yPresent:
							outstr += outformat[1].format(int((ycoord+boardorigin[1])*10**outprec[1]))
						if iPresent:
							outstr += outoffformat[0].format(int(icoord*10**outprec[0]))
						if jPresent:
							outstr += outoffformat[1].format(int(jcoord*10**outprec[1]))
							
							
						outstr += m.group(9)+'*'
						
						if lineok:
							outgerber += [outstr]	
						else:
							lineok = True
							badDims += 1
					
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
							unitScale = 1.0
							lineok = True
						elif m.group(1) == 'IN':
							MOMM = False
							unitScale = 25.4
							lineok = True
					
					m = LP_RE.match(line)	#New level
					if m:
						outgerber += [m.group(0)]
						lineok = True
					
					m = M02_RE.match(line) #End of file
					if m:
						lineok = True
						
					if line == '\n':
						lineok = True
							
					if not lineok:
						if not badLines:
							badLines = True
							print('Board '+str(boardidx)+': group '+pair[0]+' zip '+pair[1])
						print('Bad line: '+line[0:-1])

			if badDims:
				badDimRecord += ['Layer '+ft+' Panel '+str(panelidx)+' Board '+str(boardidx)+' group '+pair[0]+' zip '+pair[1]+' '+str(badDims)+' bad dimensions']
						
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
				#print(' Panel '+str(panelidx))
				panels += [[outfile+str(panelidx)+'.'+ft,str(boardidx)]]

		#Write any partially-full final panel
		if boardidx > 0:
			WriteGerber()
			panels += [[outfile+str(panelidx)+'.'+ft,str(boardidx)]]
			
	#Write report
	with open(os.path.join(outdir,REPORT_FILE),'w') as f:
		f.write('Gerber panelliser report\n')
		f.write('Layers processed: '+' '.join(filetypes)+'\n')
		f.write('Panels processed:'+'\n')
		for p in panels:
			f.write('  Panel '+p[0]+': '+p[1]+' boards'+'\n')
		f.write('Bad Dimensions:'+'\n')
		for b in badDimRecord:
			f.write('  '+b+'\n')
		
		
		
	