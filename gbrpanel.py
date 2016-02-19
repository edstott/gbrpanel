import glob
import os
import subprocess
import shutil

import pairs
import GerberBuilder
import ExcellonBuilder

#filemask = '*.[Gg]*'
indir = 'test'

#filetypes = ['GBL','GBS','GTL','GTO','GTS','Outline']
filetypes = []
REPORT_FILE = 'report.txt'
OUT_DIR = 'out'
		
if __name__ == '__main__':

	pairs = pairs.getPairs()
	#pairs = pairs[0:5]
	panels = []
	badDimRecord = []

	for ft in filetypes:	#Loop over gerber file extensions
		print('File Extension .'+ft)
		filename = 'PCB.'+ft

		gerberOut = GerberBuilder.GerberBuilder(ft)

		for pair in pairs:
			
			#Extract file
			if not ft == 'Outline': #Don't extract the outline, use the reference PCB.Outline
				if subprocess.call(['7z','e',pair[1],'-y','Gerber/'+filename],stdout=subprocess.PIPE,stderr=subprocess.PIPE):
					print('Could not unzip '+filename+' from '+pair[1])
					raise Exception

			with open(filename,'r') as file:
				gerberOut.addBoard(file)
				
		gerberOut.closePanel()
		
	print('Drill')
	filename = 'PCB.TXT'
	drillOut = ExcellonBuilder.ExcellonBuilder()
	
	for pair in pairs:
		#Extract file
		if subprocess.call(['7z','e',pair[1],'-y',os.path.join('NC Drill',filename)],stdout=subprocess.PIPE,stderr=subprocess.PIPE):
			print('Could not unzip '+filename+' from '+pair[1])
			raise Exception
			
		with open(filename,'r') as file:
			print(pair[1])
			drillOut.addBoard(file)
			
	drillOut.closePanel()
		
			
	#Write report
	with open(os.path.join(OUT_DIR,REPORT_FILE),'w') as f:
		f.write('Gerber panelliser report\n')
		f.write('Layers processed: '+' '.join(filetypes)+'\n')
		f.write('Panels processed:'+'\n')
		for p in panels:
			f.write('  Panel '+p[0]+': '+p[1]+' boards'+'\n')
		f.write('Bad Dimensions:'+'\n')
		#for b in badDimRecord:
		#	f.write('  '+b+'\n')
		
		
		
	