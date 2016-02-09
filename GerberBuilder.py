import re
import os

STREAM_Gs = ['01','02','03','74','75','36','37']
IGNORE_Gs = ['70','71']
OK_Ds = ['01','02','03']
DEF_DIGITS = (10,10)
DEF_PREC = (5,5)
DEF_FORMAT = ('X{:d}','Y{:d}')
DEF_OFF_FORMAT = ('I{:d}','J{:d}')
DEF_IN_OFFSET = (15.0,15.0)
CHECK_DIMS =True
DIM_TOL = 0.5
BOARD_PITCH = (80.0,90.0)
BOARD_DIMS = (70.0,80.0)
PANEL_DIMS = (10,10)
OUT_DIR = 'out'
OUT_FILE = 'out'

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
EOM_RE = re.compile('\%$') #End of macro
NL_RE = re.compile('$') #Newline/empty string

def decodeAM(self,m): #Decode a aperture macro definition
	currentMacroD = 'D'+str(self.outapDidx) #Give the macro a new D code
	self.outapDidx += 1
	self.currentMacro = 'MACRO'+currentMacroD #Give the macro a new name
	self.outamdict[self.currentMacro] = {'MacroD':currentMacroD, 'Macro':[]} #Initialise a new entry in macro dictionary
	self.inamdict[m.group(1)] = self.currentMacro #Relate the original name to the new name	
	return True
	
def decodeAMP(self,m):#Decode an aperture macro primitvie
	#'(1|21|4),(-?\d+(\.\d+)?,)*(-?\d+(\.\d+)?\*)')
	lineok = False
	if m and self.currentMacro: #Only valid if a macro is open
		if m.group(1) == '1': #Circle
			amp = m.group(0)[:-1].split(',')
			amp[2] = str(float(amp[2])*self.unitScale)
			amp[3] = str(float(amp[3])*self.unitScale)
			amp[4] = str(float(amp[4])*self.unitScale)
		
			self.outamdict[self.currentMacro]['Macro'] += [','.join(amp)+'*\n']
			lineok = True
			
		if m.group(1) == '21': #Centre Line Rectangle
			amp = m.group(0)[:-1].split(',')
			amp[2] = str(float(amp[2])*self.unitScale)
			amp[3] = str(float(amp[3])*self.unitScale)
			amp[4] = str(float(amp[4])*self.unitScale)
			amp[5] = str(float(amp[5])*self.unitScale)
		
			self.outamdict[self.currentMacro]['Macro'] += [','.join(amp)+'*\n']
			lineok = True
			
		if m.group(1) == '4': #Outline
			amp = m.group(0)[:-1].split(',')
			amp = amp[0:3] + [str(float(i)*self.unitScale) for i in amp[3:-1]] + [amp[-1]] #Convert everything except the Exposure flag, point count and rotation
			
			self.outamdict[self.currentMacro]['Macro'] += [','.join(amp)+'*\n']
			lineok = True
			
	return lineok
	
def decodeAP(self,m):#Decode an aperture declaration
	if m.group(2) not in self.outapdict:	#Does this aperture already exist?
		if m.group(3) == 'C': #Circle has one dimension
			apDims = [str(float(m.group(4))*self.unitScale)]
		elif m.group(3) == 'P': #Polygon has one dimension, and optional rotation and hole size
			apDims = [str(float(m.group(4))*self.unitScale)]
			if m.group(5): #Rotation is not converted
				apDims += [m.group(5)]
				if len(m.groups())>=6: #Hole size is converted
					apDims += [str(float(m.group(6))*self.unitScale)]
		else:
			apDims = [str(float(i)*self.unitScale) for i in m.groups()[3:]]
			
		self.outapdict[m.group(2)] = ('D'+str(self.outapDidx),m.group(3)+','+'X'.join(apDims))  #If not, add to output dictionary
		self.outapDidx += 1
	self.inapmap[m.group(1)] = self.outapdict[m.group(2)][0] #Add a map from file D-number to output D-number
	return True
	
def decodeAPM(self,m):#Decode an aperture macro declaration
	macro = self.inamdict[m.group(2)] #Find new name for this macro
	self.outapdict[macro] = (self.outamdict[macro]['MacroD'],None) #Create an output mapping for the macros D code
	self.inapmap[m.group(1)] = self.outamdict[macro]['MacroD'] #Create a D code mapping
	return True
	
def decodeC(self,m):#Decode a coordinate
	outstr = ''
	icoord = 0
	jcoord = 0
	xPresent = False
	yPresent = False
	iPresent = False
	jPresent = False
	lineok = False
	
	if m.group(1)=='Y': #Y coordinate only
		self.ycoord = float(m.group(2))*self.unitScale/10**self.inprec[1]-self.inoffset[1]
		yPresent = True
		#print('Y')
	elif m.group(3): #X and Y coordinates
		self.xcoord = float(m.group(2))*self.unitScale/10**self.inprec[0]-self.inoffset[0]
		self.ycoord = float(m.group(4))*self.unitScale/10**self.inprec[1]-self.inoffset[1]
		xPresent = True
		yPresent = True
		#print('XY')
	else: #X coordinate only
		self.xcoord = float(m.group(2))*self.unitScale/10**self.inprec[0]-self.inoffset[0]
		xPresent = True
		#print('X')
	if m.group(5):	#I offset present
		icoord = float(m.group(6))*self.unitScale/10**self.inprec[0]
		iPresent = True
	if m.group(7):	#J offset present
		jcoord = float(m.group(8))*self.unitScale/10**self.inprec[1]
		jPresent = True
		
	if CHECK_DIMS:
		if self.xcoord < -DIM_TOL:
			#print("Drawing X outside allowed region "+str(xcoord+icoord)+' < 0.0')
			pass
		elif self.xcoord-BOARD_DIMS[0] > DIM_TOL:
			#print("Drawing X outside allowed region "+str(xcoord+icoord)+' > '+str(boarddims[0]))
			pass
		elif self.ycoord < -DIM_TOL:
			#print("Drawing Y outside allowed region "+str(ycoord+jcoord)+' < 0.0')
			pass
		elif self.ycoord-BOARD_DIMS[1] > DIM_TOL:
			#print("Drawing Y outside allowed region "+str(ycoord+jcoord)+' > '+str(boarddims[1]))
			pass
		else:
			lineok = True		
	else:
		lineok = True									
			
	if xPresent:
		outstr += self.outformat[0].format(int((self.xcoord+self.boardorigin[0])*10**self.outprec[0]))
	if yPresent:
		outstr += self.outformat[1].format(int((self.ycoord+self.boardorigin[1])*10**self.outprec[1]))
	if iPresent:
		outstr += self.outoffformat[0].format(int(icoord*10**self.outprec[0]))
	if jPresent:
		outstr += self.outoffformat[1].format(int(jcoord*10**self.outprec[1]))
			
	outstr += m.group(9)+'*'
	
	if lineok:
		self.outgerber += [outstr]	
	else:
		self.badDims += 1
	return True
	
def decodeD(self,m):#Decode a D-code
	lineok = False
	if int(m.group(2))>9: #D-code applies an aperture
		self.outgerber += [self.inapmap[m.group(1)]+'*'] #Translate the aperture
		lineok = True
	elif m.group(2) in OK_Ds:
		self.outgerber += [m.group(1)+'*'] #Just copy reserved D-codes (below 10)
		lineok = True		
	return lineok
	
def decodeFS(self,m):#Decode coordinate specification
	digits = (int(m.group(1))+int(m.group(2)),int(m.group(3))+int(m.group(4)))
	self.inprec = (int(m.group(2)),int(m.group(4)))
	self.informat = ('X{:0'+str(digits[0])+'d}','Y{:0'+str(digits[1])+'d}')
	return True
	
def decodeG(self,m):#Decode a G-code
	lineok = False
	if m.group(1) == '04':	#G04 is a comment
		if m.group(2) not in self.comments:
			self.comments += [m.group(2)]
		lineok = True
	elif m.group(1) in STREAM_Gs:	#Add these Gs to output stream
		self.outgerber += ['G'+m.group(1)+'*']
		lineok = True
	elif m.group(1) in IGNORE_Gs: #Ignore these Gs
		lineok = True	
	return lineok
	
def decodeLP(self,m):#Decode new level
	self.outgerber += [m.group(0)]
	return True
	
def decodeM02(self,m):#Decode EOF
	return True
	
def decodeMO(self,m):#Decode units declaration
	lineok = False
	if m.group(1) == 'MM':
		self.MOMM = True
		self.unitScale = 1.0
		lineok = True
	elif m.group(1) == 'IN':
		self.MOMM = False
		self.unitScale = 25.4
		lineok = True
	return lineok
	
def decodeEOM(self,m):#Decode end of macro
	self.currentMacro = None
	return True
	
def decodeNL(self,m):#Decode newline or empty string
	return True

DECODE_LIST = 	[[AP_RE,decodeAP],\
					[APM_RE,decodeAPM],\
					[AM_RE,decodeAM],\
					[AMP_RE,decodeAMP],\
					[D_RE,decodeD],\
					[C_RE,decodeC],\
					[G_RE,decodeG],\
					[FS_RE,decodeFS],\
					[MO_RE,decodeMO],\
					[LP_RE,decodeLP],\
					[M02_RE,decodeM02],\
					[EOM_RE,decodeEOM],\
					[NL_RE,decodeNL]]
					
class GerberBuilder:
				
	def __init__(self,ext='gbr'):
		self.panelidx = 0
		self.ext = ext
		self.panels = []
		self.newPanel()
		
	def newPanel(self):
		self.boardidx = 0
		self.outapdict = {}
		self.outapDidx = 10
		self.outamdict = {}
		self.inamdict = {}

		self.outgerber = []
		self.outdigits = DEF_DIGITS
		self.outformat = DEF_FORMAT
		self.outoffformat = DEF_OFF_FORMAT
		self.outprec = DEF_PREC
		
	def addBoard(self,gerber):
		
		self.inapmap = {}
		self.comments = []
		self.digits = DEF_DIGITS
		self.inprec = None
		self.informat = DEF_FORMAT
		self.MOMM = None
		self.currentMacro = None
		self.unitScale = None
		self.inoffset = DEF_IN_OFFSET
		self.xcoord = 0
		self.ycoord = 0
		self.badLines = False
		self.badDims = 0
		self.boardorigin = (int(self.boardidx/PANEL_DIMS[0])*BOARD_PITCH[0],self.boardidx%PANEL_DIMS[0]*BOARD_PITCH[1])
		
		for line in gerber:
			LineOK = False
			for pattern in DECODE_LIST:
				m = pattern[0].match(line)
				if m:
					LineOK = pattern[1](self,m)
				
			if not LineOK:
				print('Bad line: '+line[0:-1])
							
		self.boardidx += 1
		if self.boardidx == PANEL_DIMS[0]*PANEL_DIMS[1]:	#Write the output if the panel is full
			self.closePanel()
			
	def closePanel(self):				
		#Reset for the next panel
		self.panelidx += 1
		if self.boardidx > 0:
			self.writePanel()
			
		self.panels += [[OUT_FILE+str(self.panelidx)+'.'+self.ext,str(self.boardidx)]]
		self.newPanel()
		
	def writePanel(self):
		with open(os.path.join(OUT_DIR,OUT_FILE+str(self.panelidx)+'.'+self.ext),'w') as file:
			#Write comments
			for c in self.comments:
				file.write('G04'+c+'*\n')
				
			#Write precision
			file.write('%FSLAX{:d}{:d}Y{:d}{:d}*%\n'.format(self.outdigits[0]-self.outprec[0],self.outprec[0],self.outdigits[1]-self.outprec[1],self.outprec[1]))
			
			#Write units
			file.write('%MOMM*%\n')
				
			#Write macros
			for m,d in self.outamdict.items():
				file.write('%AM'+m+'*\n')
				for p in d['Macro']:
					file.write(p)
				file.write('%\n')
				
			#Write apertures
			for a,d in self.outapdict.items():
				if d[1]: #Apertures that have been translated
					file.write('%AD'+d[0]+d[1]+'*%\n')
				else: #Apertures that are macro references
					file.write('%AD'+d[0]+a+'*%\n')
				
			#Write commands
			for g in self.outgerber:
				file.write(g+'\n')
				
			#Write EOF
			file.write('M02*\n')
			

		
		
		