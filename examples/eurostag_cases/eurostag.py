from deeac.__main__ import deeac

s = "--rewrite -t case_6_ren/branch_1.json -e case_6_ren/fech.ech -d case_6_ren/fdta.dta -l case_6_ren/fech.lf -s case_6_ren/B-C_fault.seq -o sortie -p 15 -v verbose"

deeac(s.split())
