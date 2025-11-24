from deeac.__main__ import deeac

#05/03/2025 10h37
s = "--rewrite -t branch_1.json -e 05-03-25_12h37/fech.ech -d 05-03-25_12h37/fdta.dta -l 05-03-25_12h37/fech.lf -s 05-03-25_12h37/braud71pregu.seq -o 05-03-25_12h37/output -p 15 -v verbose"
#11/12/2024 17h38
#s = "--rewrite -t branch_1.json -e 11-12-24_17h38/fech.ech -d 11-12-24_17h38/fdta.dta -l 11-12-24_17h38/fech.lf -s 11-12-24_17h38/coula71tavel.seq -o 11-12-24_17h38/output -p 15 -v verbose"
#25/05/2025 08h37
#s = "--rewrite -t branch_1.json -e 25-05-25_08h37/fech.ech -d 25-05-25_08h37/fdta.dta -l 25-05-25_08h37/fech.lf -s 25-05-25_08h37/vigy71ssavo.seq -o 25-05-25_08h37/output -p 15 -v verbose"

deeac(s.split())
