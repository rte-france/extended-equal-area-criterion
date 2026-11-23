# Power and current modelling experiments

The files are variations over [Base.ech](IEEE14/ech/Base.ech)
Each file has a single variation
[B1P50.ech](IEEE14/ech/B1P50.ech)
[B1P100.ech](IEEE14/ech/B1P100.ech)
[B1Q50.ech](IEEE14/ech/B1Q50.ech)
[B1Q100.ech](IEEE14/ech/B1Q100.ech)
[B2P50.ech](IEEE14/ech/B2P50.ech)
[B2P100.ech](IEEE14/ech/B2P100.ech)
[B2Q50.ech](IEEE14/ech/B2Q50.ech)
[B2Q100.ech](IEEE14/ech/B2Q100.ech)
[B5P50.ech](IEEE14/ech/B5P50.ech)
[B5P100.ech](IEEE14/ech/B5P100.ech)
[B5Q50.ech](IEEE14/ech/B5Q50.ech)
[B5Q100.ech](IEEE14/ech/B5Q100.ech)

The nomenclature is:
B1P50: RES in bus 1 with P = 50 MW and Q = 0 MVar

At Bus (B) 1, the active power (P) is 50

B5Q100: RES in bus 5 with P = 0 MW and Q = 100 MVar

At Bus (B) 5, reactive power (Q) = 100

| Fault    | Critical cluster | Name   | Load (ms) | Current (ms) | Dynawo (ms) | Ecarts Load/Current |
|----------|------------------|--------|-----------|--------------|-------------|---------------------|
| line_1-2 | GEN    1         | B1P50  | 491       | 475          | 314         | 3.26 %              |
| line_1-2 | GEN    1         | B1P100 | 512       | 481          | 369         | 6.05 %              |
| line_1-2 | GEN    1         | B1Q50  | 441       | 438          | 183         | 0.68 %              |
| line_1-2 | GEN    1         | B1Q100 | 406       | 402          | 26          | 0.99 %              |
| line_1-2 | GEN    1         | B2P50  | 469       | 468          | 253         | 0.21 %              |
| line_1-2 | GEN    1         | B2P100 | 470       | 468          | 260         | 0.43 %              |
| line_1-2 | GEN    1         | B2Q50  | 468       | 453          | 242         | 3.21 %              |
| line_1-2 | GEN    1         | B2Q100 | 447       | 420          | 242         | 6.04 %              |
| line_1-2 | GEN    1         | B5P50  | 491       | 475          | 251         | 3.26 %              |
| line_1-2 | GEN    1         | B5P100 | 512       | 481          | 257         | 6.05 %              |
| line_1-2 | GEN    1         | B5Q50  | 441       | 438          | 227         | 0.68 %              |
| line_1-2 | GEN    1         | B5Q100 | 406       | 402          | 207         | 0.99 %              |
| line_1-2 | GEN    1         | Base   | 468       | 468          | 242         | 0.00 %              |
| line_1-5 | GEN    1         | B1P50  | 495       | 492          | 463         | 0.61 %              |
| line_1-5 | GEN    1         | B1P100 | 514       | 510          | 498         | 0.78 %              |
| line_1-5 | GEN    1         | B1Q50  | 442       | 445          | 391         | -0.68 %             |
| line_1-5 | GEN    1         | B1Q100 | 407       | 411          | 349         | -0.98 %             |
| line_1-5 | GEN    1         | B2P50  | 482       | 481          | 434         | 0.21 %              |
| line_1-5 | GEN    1         | B2P100 | 483       | 481          | 441         | 0.41 %              |
| line_1-5 | GEN    1         | B2Q50  | 480       | 465          | 424         | 3.13 %              |
| line_1-5 | GEN    1         | B2Q100 | 462       | 437          | 424         | 5.41 %              |
| line_1-5 | GEN    1         | B5P50  | 495       | 492          | 432         | 0.61 %              |
| line_1-5 | GEN    1         | B5P100 | 514       | 510          | 438         | 0.78 %              |
| line_1-5 | GEN    1         | B5Q50  | 442       | 445          | 421         | -0.68 %             |
| line_1-5 | GEN    1         | B5Q100 | 407       | 411          | 416         | -0.98 %             |
| line_1-5 | GEN    1         | Base   | 480       | 480          | 424         | 0.00 %              |

For Load: We used the eeac v2
For Current: We used the eec v1, RES modification
For Dynawo, dynawo