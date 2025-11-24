from deeac.__main__ import deeac

#s = "--rewrite -t branch_1.json -e ech/BUS2_P30_Q40.ech -d fdta.dta -l lf/BUS1_P30_Q40.lf -s line_2-3.seq -o sortie -p 15 -v verbose"
s = "--rewrite -t branch_1.json -e ech/BUS1_P50_Q0.ech -d fdta.dta -l lf/BUS1_P50_Q0.lf -s line_1-5.seq -o sortie -p 15 -v verbose"

deeac(s.split())
