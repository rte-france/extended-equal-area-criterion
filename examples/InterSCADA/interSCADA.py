from deeac.__main__ import deeac

s = "--rewrite -t branch_1.json -e ech/RB_P200Q0.ech -d fdta.dta -l lf/RB_P200Q0.lf -s B-C_fault.seq -o sortie -p 15 -v verbose"
#s = "--rewrite -t branch_1.json -e fech.ech -d fdta.dta -l fech.lf -s B-C_fault.seq -o sortie -p 15 -v verbose"

deeac(s.split())
