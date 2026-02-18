from deeac.__main__ import deeac

s = "--rewrite -t branch_1.json -e fech.ech -d fdta.dta -l fech.lf -s B-C_fault.seq -o sortie -p 15"
#s = "--rewrite -t branch_1.json -e ech/BAP50.ech -d fdta.dta -l lf/BAP50.lf -s B-C_fault.seq -o sortie -p 15"

deeac(s.split())
