from deeac.__main__ import deeac

s = "--rewrite -t branch_1.json -e fech.ech -d fdta.dta -l fech.lf -s line_1-5.seq -o sortie -p 15 -v verbose"
#s = "--rewrite -t branch_1.json -e ech/B1P50.ech -d fdta.dta -l lf/B1P50.lf -s line_1-5.seq -o sortie -p 15 -v verbose"

deeac(s.split())
