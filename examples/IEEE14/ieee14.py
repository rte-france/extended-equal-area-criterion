from deeac.__main__ import deeac

s = "--rewrite -t branch_1.json -e ech/1GB1P.ech -d fdta.dta -l lf/1GB1P.lf -s line_1-2.seq -o sortie -p 15 -v verbose"

deeac(s.split())
