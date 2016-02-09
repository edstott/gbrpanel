import re

OUT_DIR = 'out'
OUT_FILE = 'out'

BOARD_PITCH = (80.0,90.0)
BOARD_DIMS = (70.0,80.0)
PANEL_DIMS = (10,10)

M_RE = re.compile('M48$')
COM_RE = re.compile(';(.*)')
UNIT_RE = re.compile('(INCH|METRIC),(LZ|TZ)$')
T_RE = re.compile('(T\d+)([CFS]\.?\d+(?:\.\d+)?){3}$')
EOH_RE = re.compile('\%$|M95$')

def decodeM(self,m):#Decode M-code
	self.inHeader = True
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
			self.unitScale = 25.4
		else:
			self.unitScale = 1.0
		if m.group(2) == 'LZ':
			self.LZ = True
		else:
			self.LZ = False
		lineok = True
	return lineok
	
def decodeT(self,m):
	lineok = False
	if self.inHeader:
		drill = {'C':0.0,'F':0.0,'S':0.0}
		for s in m.groups()[1:4]:
			drill[s[0]] = float(s[1:-1])
		drillstr = 'C{C}F{F}S{S}'.format(**drill)
		if drillstr not in self.drilldict:
			self.drilldict[drillstr] = 'T{}'.format(self.drillidx)
			self.drillidx += 1
		self.drillmap[m.group(1)] = self.drilldict[drillstr]
		lineok = True
	return lineok

def decodeEOH(self,m):
	lineok = False
	if self.inHeader:
		lineok = True
	self.inHeader = False
	return lineok
	
DECODE_LIST = 	[[M_RE,decodeM],\
				[COM_RE,decodeCOM],\
				[UNIT_RE,decodeUNIT],\
				[T_RE,decodeT],\
				[EOH_RE,decodeEOH]]

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
		
	def addBoard(self,excellon):
	
		self.inHeader = False
		self.unitScale = 1.0
		self.LZ = True
		self.drillmap = {}
	
		for line in excellon:
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
			
		self.panels += [[OUT_FILE+str(self.panelidx)+'.TXT',str(self.boardidx)]]
		self.newPanel()
		
	def writePanel(self):
		pass
		
		