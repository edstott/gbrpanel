import re
import os

OUT_DIR = 'out'
OUT_FILE = 'out'

BOARD_PITCH = (80.0,90.0)
BOARD_DIMS = (70.0,80.0)
CHECK_DIMS = True
PANEL_DIMS = (10,10)
DIM_TOL = 0.5
DEF_IN_OFFSET = (15.0,15.0)

OUT_UNIT_STRING = 'METRIC,LZ'

M_RE = re.compile('M(48|30)$')
COM_RE = re.compile(';(.*)')
UNIT_RE = re.compile('(INCH|METRIC),(LZ|TZ)$')
TDEF_RE = re.compile('T(\d+)([CFS]\.?\d+(?:\.\d+)?){3}$')
EOH_RE = re.compile('\%$|M95$')
T_RE = re.compile('T(\d+)$')
C_RE = re.compile('([XY])(\d+)(?:Y(\d+))?$')

def decodeM(self,m):#Decode M-code
	if m.group(1) == '48':
		self.inHeader = True
	if m.group(1) == '30':
		pass
	return True
	
def decodeCOM(self,m):#Decode comment
	lineok = False
	if self.inHeader:
		if m.group(1) not in self.comments:
			self.comments[m.group(1)] = None
		lineok = True
	return lineok
	
def decodeUNIT(self,m):#Decode units
	lineok = False
	if self.inHeader:
		if m.group(1) == 'INCH':
			self.inch = True
		else:
			self.inch = False
		
		if m.group(2) == 'LZ':
			self.LZ = True
		else:
			self.LZ = False
		
		if self.inch and self.LZ:
			self.inunitScale = 25.4
			self.decimalscale = 10**2
			lineok = True
		else:
			print('Unsupported input units '+m.group(0))
			raise Exception
			
	return lineok
	
def decodeTdef(self,m):
	lineok = False
	if self.inHeader:
		drill = {'C':0.0,'F':0.0,'S':0.0}
		for s in m.groups()[1:4]:
			drill[s[0]] = float(s[1:-1])
		drill['C'] *= self.inunitScale
		drill['F'] = int(drill['F']*self.inunitScale*60)
		drillstr = 'C{C}F{F:03}S{S}'.format(**drill)
		if drillstr not in self.drilldict:
			self.drilldict[drillstr] = 'T{}'.format(self.drillidx)
			self.drillidx += 1
		self.drillmap['T{}'.format(int(m.group(1)))] = self.drilldict[drillstr]
		lineok = True
	return lineok
	
def decodeT(self,m):
	lineok = False
	if not self.inHeader:
		drillcode = 'T{}'.format(int(m.group(1)))
		if drillcode in self.drillmap:
			self.drilldata += [self.drillmap[drillcode]]
			lineok = True
		else:
			print('{} not in drill map'.format(drillcode))
	return lineok

def decodeEOH(self,m):
	lineok = False
	if self.inHeader:
		lineok = True
	self.inHeader = False
	return lineok
	
def decodeC(self,m):
	lineok = False
	if not self.inHeader:
		x = False
		y = False
		#print(m.group(0))
		if m.group(1) == 'X':
			lineok = True
			self.xcoord = float('0.'+m.group(2))*self.decimalscale*self.inunitScale-DEF_IN_OFFSET[0]
			x = True
			if m.group(3):
				self.ycoord = float('0.'+m.group(3))*self.decimalscale*self.inunitScale-DEF_IN_OFFSET[1]
				y = True
		elif not m.group(3):
			lineok = True
			self.ycoord = float('0.'+m.group(2))*self.decimalscale*self.inunitScale-DEF_IN_OFFSET[0]
			x = True
		#print('{}, {}'.format(self.xcoord,self.ycoord))
			
	if CHECK_DIMS:
		if self.xcoord < -DIM_TOL or \
			self.xcoord-BOARD_DIMS[0] > DIM_TOL or \
			self.ycoord < -DIM_TOL or \
			self.ycoord-BOARD_DIMS[1] > DIM_TOL:
			lineok = False
	
	outstr = ''	
	if x:
		#outstr = 'X{:06d}'.format(int(self.xcoord*self.outunitscale))
		outstr = 'X{:.3f}'.format(self.xcoord)
	if y:
		#outstr += 'Y{:06d}'.format(int(self.ycoord*self.outunitscale))
		outstr += 'Y{:.3f}'.format(self.ycoord)
		
	if lineok:
		self.drilldata += [outstr]	
	else:
		self.badDims += 1
	return True
	
DECODE_LIST = 	[[M_RE,decodeM],\
				[COM_RE,decodeCOM],\
				[UNIT_RE,decodeUNIT],\
				[TDEF_RE,decodeTdef],\
				[EOH_RE,decodeEOH],\
				[T_RE,decodeT],\
				[C_RE,decodeC]]

class ExcellonBuilder:
	
	def __init__(self):
		self.panelidx = 0
		self.panels = []
		self.newPanel()
		
	def newPanel(self):
		self.boardidx = 0
		self.drillidx = 1
		self.drilldict = {}
		self.comments = {}
		self.drilldata = []
		self.outunitscale = 10**3
		
	def addBoard(self,excellon):
	
		self.inHeader = False
		self.unitScale = 1.0
		self.LZ = True
		self.drillmap = {}
		self.xcoord = None
		self.ycoord = None
		self.badDims = 0
	
		for line in excellon:
			LineOK = False
			for pattern in DECODE_LIST:
				m = pattern[0].match(line)
				if m:
					LineOK = pattern[1](self,m)
					
			if not LineOK:
				print('Bad line: '+line[0:-1])
				
		if self.badDims:
			print('{} bad dimensions'.format(self.badDims))
				
		self.boardidx += 1
		if self.boardidx == PANEL_DIMS[0]*PANEL_DIMS[1]:	#Write the output if the panel is full
			self.closePanel()
			
	def closePanel(self):		
		#Reset for the next panel
		self.panelidx += 1
		filename = OUT_FILE+str(self.panelidx)+'.TXT'
		if self.boardidx > 0:
			self.writePanel(filename)
			
		self.panels += [[filename,str(self.boardidx)]]
		self.newPanel()
		
	def writePanel(self,filename):
		with open(os.path.join(OUT_DIR,filename),'w') as f:
		
			#Start of header
			f.write('M48\n')
			
			#Comments
			for c in self.comments:
				f.write(';{}\n'.format(c))
				
			#Units
			f.write(OUT_UNIT_STRING+'\n')
			
			#Tools
			for d,t in self.drilldict.items():
				f.write('{}{}\n'.format(t,d))
				
			#End of header
			f.write('%\n')
			
			#Drill data
			for d in self.drilldata:
				f.write(d+'\n')
				
			#End of file
			f.write('M30\n')
			
			
		
		