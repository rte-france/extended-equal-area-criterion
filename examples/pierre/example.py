from deeac.__main__ import deeac
#import cProfile

#05/03/2025 10h37
#s = "--rewrite -t branche_1.json -e 05_03_25_10_37/fech.ech -d 05_03_25_10_37/fdta.dta -l 05_03_25_10_37/fech.lf -s 05_03_25_10_37/braud71pregu.seq -o 05_03_25_10_37/sortie -p 15 -v verbose"
#05/03/2025 11h37
#s = "--rewrite -t branche_1.json -e 05_03_25_11_37/fech.ech -d 05_03_25_11_37/fdta.dta -l 05_03_25_11_37/fech.lf -s 05_03_25_11_37/braud71pregu.seq -o 05_03_25_11_37/sortie -p 15 -v verbose"
#05/03/2025 12h37
s = "--rewrite -t branche_1.json -e 05_03_25_12_37/fech.ech -d 05_03_25_12_37/fdta.dta -l 05_03_25_12_37/fech.lf -s 05_03_25_12_37/braud71pregu.seq -o 05_03_25_12_37/sortie -p 15 -v verbose"
#05/03/2025 13h37
#s = "--rewrite -t branche_1.json -e 05_03_25_13_37/fech.ech -d 05_03_25_13_37/fdta.dta -l 05_03_25_13_37/fech.lf -s 05_03_25_13_37/braud71pregu.seq -o 05_03_25_13_37/sortie -p 15 -v verbose"

deeac(s.split())

'''
import difflib

def compare_files_with_difflib(file1_path, file2_path):
    with open(file1_path, 'r') as file1, open(file2_path, 'r') as file2:
        lines1 = file1.readlines()
        lines2 = file2.readlines()

    diff = difflib.unified_diff(lines1, lines2, fromfile=file1_path, tofile=file2_path)
    return list(diff)

file1_path = '/home/steveninpie/Téléchargements/variables_environnement.txt'
#file2_path = '/home/steveninpie/Téléchargements/cc_stabsys_25-03-05_12-37-42/detaille.iidm'
file2_path = '/home/steveninpie/Téléchargements/variables_environnement_remy.txt'
differences = compare_files_with_difflib(file1_path, file2_path)
for line in differences:
    print(line, end='')
'''
