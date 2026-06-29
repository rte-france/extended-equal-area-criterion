Citation: Bahmanyar, A.; Ernst, D.;
Vanaubel, Y.; Gemine, Q.; Pache, C.;
Panciatici, P. Extended Equal Area
Criterion Revisited: A Direct Method
for Fast Transient Stability Analysis.
Energies 2021 , 14 , 7259. https://
doi.org/10.3390/en

Academic Editor: Ali Nabavi

Received: 20 September 2021
Accepted: 30 October 2021
Published: 3 November 2021

Publisher’s Note: MDPI stays neutral
with regard to jurisdictional claims in
published maps and institutional affil-
iations.

Copyright: © 2021 by the authors.
Licensee MDPI, Basel, Switzerland.
This article is an open access article
distributed under the terms and
conditions of the Creative Commons
Attribution (CC BY) license (https://
creativecommons.org/licenses/by/
4.0/).

(^1) Department of Electrical Engineering and Computer Science Montefiore Institute, University of Liège,
4000 Liège, Belgium; dernst@uliege.be
(^2) Intelligent Systems Solutions, Haulogy, 4120 Neupré, Belgium; yvanaubel@blacklight-analytics.com (Y.V.);
qgemine@blacklight-analytics.com (Q.G.)
(^3) French Transmission System Operator Réseau de Transport d’Electricité (RTE), 7C Place du Dome,
92800 Puteaux, France; camille.pache@rte-france.com (C.P.); patrick.panciatici@rte-france.com (P.P.)
***** Correspondence: abahmanyar@uliege.be
Abstract: For transient stability analysis of a multi-machine power system, the Extended Equal Area
Criterion (EEAC) method applies the classic Equal Area Criterion (EAC) concept to an approximate
One Machine Infinite Bus (OMIB) equivalent of the system to find the critical clearing angle. The
system-critical clearing time can then be obtained by numerical integration of OMIB equations. The
EEAC method was proposed in the 1980s and 1990s as a substitute for time-domain simulation for
Transmission System Operators (TSOs) to provide fast, transient stability analysis with the limited
computational power available those days. To ensure the secure operation of the power system, TSOs
have to identify and prevent potential critical scenarios through offline analyses of a few dangerous
ones. These days, due to increased uncertainties in electrical power systems, the number of these
critical scenarios is increasing, substantially, calling for fast, transient stability analysis techniques
once more. Among them, the EEAC is a unique approach that provides not only valuable information,
but also a graphical representation of system dynamics. This paper revisits the EEAC but from a
modern, functional point of view. First, the definition of the OMIB model of a multi-machine power
system is redrawn in its general form. To achieve fast, transient stability analysis, EEAC relies on
approximate models of the true OMIB model. These approximations are clarified, and the EAC
concept is redefined with a general definition for instability, and its conditions. Based on the defined
conditions and definitions, functions are developed for each EEAC building block, which are later
put out together to provide a full-resolution, functional scheme. This functional scheme not only
covers the previous literature on the subject, but also allows to introduce several possible new EEAC
approaches and provides a detailed description of their implementation procedure. A number of
approaches are applied to the French EHV network, and the approximations are examined.
Keywords: equal area criterion; Lyapunov criterion; transient stability; time-domain simulation

1. Introduction
To ensure the secure operation of the power system, Transmission System Operators
(TSOs) perform offline Transient Stability Analysis (TSA) for a few dangerous scenarios
and design remedial actions for the critical ones, i.e., the ones with lower Critical Clearing
Time (CCT) (CCT is the maximum fault elimination time without the system losing its
capability to recover a normal operating condition [ 1 ]). The reference technique for TSA is
time-domain simulation using numerical integration of the nonlinear differential equations
representing the system dynamic model. Time-domain simulation is flexible, and it can
consider a detailed model for almost any component of the power system. However, this
detail comes at a cost, a high computational time. Moreover, the time-domain simulation
cannot provide a direct indication of the CCT, thus the system equations should be solved
for different fault elimination times to search for the critical time. In the early 20th century,

Energies 2021 , 14 , 7259. https://doi.org/10.3390/en14217259 https://www.mdpi.com/journal/energies

this was very restricting, even for transient stability analysis of a Single Machine connected
to an Infinite Bus (SMIB). This led to the development of another class of stability analysis
techniques, the direct method.
As one of the most interesting direct methods, the Equal Area Criterion (EAC) was
proposed in the 1930s and 1940s to assess the transient stability of the classical model of a
SMIB system in a simple and comprehensive way without a formal solution to the system
equations [ 2 – 4 ]. EAC was able to estimate the SMIB system Critical Clearing Angle (CCA)
with negligible computational time. Once the CCA has been calculated, the CCT can be
obtained by numerical integration of SMIB differential equations up to CCA.
EAC could provide a fast TSA and unique graphical representation of system dy-
namics. However, it was restricted to the classical model of a SMIB system. The idea
of Extended Equal Area Criterion (EEAC) was proposed in the late 1980s. It relies on
the observation that in loss of synchronism in a multi-machine power system, there is a
separation between generators into two groups. The critical group with increasing rotor
angles, and the non-critical group of remaining generators. EEAC replaces the generators
of the two groups by a two-machine system and then by a One Machine Infinite Bus (OMIB)
equivalent. It then applies the EAC concept to the OMIB equivalent model to estimate
its CCA.
The first techniques in the area were proposed under two main assumptions [ 5 – 8 ]:
(i) power system classical model is valid and (ii) the angles of machines within each of
the groups are equal to the center of angle of the group. These assumptions lead to a
time-invariant OMIB model on which the EAC can be applied. While a revised version of
this method was proposed in [ 9 ], the fact is that the OMIB model in not time-invariant. To
overcome this limitation, a piecewise time-variant method is proposed in [ 10 , 11 ]. Hybrid
methods have been proposed in the following years, coupling a time-domain transient
stability program with the equal-area criterion [ 12 – 16 ]. The other researches in the area are
mainly on the advanced applications of the concept [ 17 – 25 ], and its extension to consider
a more detailed generator model and the regulators [ 26 , 27 ], or to consider renewable
generation units [ 28 ] and AC/DC systems [ 29 ]. The various approaches proposed differ in
many respects, but they all rely on the same concept, the OMIB transformation.
These days, power systems are operating closer to their security limits and the un-
certainties are increasing. Thus, the list of scenarios to study is increasing substantially.
Therefore, though the recent significant reduction, time-domain simulation computational
time is still restrictive for the growing list of case studies, calling for fast, transient stability
analysis techniques once more. The EEAC, provides the possibility of a quick TSA, on a
large number of case studies, to filter the list of critical contingencies. The limited list of
critical contingencies can then be investigated in detail with time-domain simulations.
This paper revisits the EEAC with a modern functional point of view. In Section 2.1, it
redraws the concept of the OMIB model of a multi-machine power system and presents the
OMIB equations in their general form. The paper redefines the EAC concept in Section 2.2.
In Section 2.3, it clarifies the approximations required for the OMIB equivalent of a multi-
machine power system to enable fast TSA. It presents general definitions and conditions
for first-swing and backward-swing instability in Section 2.4. As a prerequisite of EEAC,
the proposed approaches for Critical Machines Identification (CMI) and Critical Cluster
Formation (CCF) are described in Section 3. Section 4 details Taylor series for estimation
of CCT from CCA. Each part is presented as a function with a detailed pseudocode. A
general full-resolution scheme is then presented in Section 5 that discusses the possible
combinations of the functions. It covers all the previous literature on the subject and
introduces interesting possibilities for several new approaches. Finally, a number of the
approaches are applied to two test systems to provide a detailed comparison.

2. Extended Equal Area Criterion

EAC relies on the concept of energy, and it coincides with the Lyapunov criterion
using the Lyapunov function the energy type [ 30 ]. Briefly, it states that the SMIB system is

stable (in the first-swing) if after the fault the rotor angle does not increase continuously;
therefore, it reaches a maximum value and thereafter decreases. It can be shown that
the variations of the SMIB system rotor angle δ , is linked to the area between its input
mechanical powerPmand output electrical powerPein δ −Pplane. As shown in Figure 1,
the area has a positive portion for whichPm>Peand a negative portion for whichPm<Pe.
The first portion is linked to the energy gained during rotor acceleration, and the second
portion is linked to the energy dissipated during rotor deceleration. If there is a δ mafter
which the sum of the areas betweenPmandPebecomes negative, the system is stable and
at δ mthe rotor angle starts to decrease. By increasing the fault elimination angle δ e, we
reach an angle after which clearing the fault cannot maintain the system’s stability, i.e., the
sum of the different areas is always positive and the rotor angle increases continuously.
This critical angle is the CCA of the SMIB system. Once the CCA has been calculated, the
CCT can be obtained by numerical integration of SMIB differential equations up to CCA.

Figure 1. Equal area criterion for a synchronous generator connected to an infinite bus. There is a δ m
after which the area becomes negative and δ starts to decrease, i.e., stable case.

For a multi-machine power system, the idea of EEAC was proposed in the late 1980s.
It belongs to a class of transient stability analysis methods that rely on the OMIB equivalent
model of the power system. The OMIB-based methods are based on the observation that
the loss of synchronism of a multi-machine power system originates from the irrevocable
separation of its synchronous generators into two groups: the Critical Cluster of generators
(CC) which push the system towards instability, and the remaining Non-critical Cluster
of generators (NC). These methods replace these two groups with a two-machine system
and then with an OMIB equivalent [ 1 ]. This section presents the OMIB-equivalent general
equations and discusses the approximations that let us estimate the CCA of the OMIB
model quickly and without a formal solution of its equations.

2.1. One-Machine Infinite Bus Concept and General Formulation

The OMIB can be considered as an approximate transformation of the multidimen-
sional state-space of multi-machine power system dynamics to a lower dimension space.
Based on the transformation approach, the resultant OMIB model can be a ‘time-invariant’

or ‘time-variant’ equivalent of the power system. Time-invariant OMIB assumes that the
generators within each of the CR and NC groups are coherent. This transformation freezes
the relative angles of generators within each group at the fault instant for the during-fault
and the post-fault periods. Time-variant OMIB updates the relative angle of generators in
each group with respect to each other. The update can be done by estimating the generator
angles with simplified models, detailed time-domain simulation, or field measurements.
Despite the techniques employed for the transformation, all OMIB-based methods rely
on Conjecture 1, given below [ 1 ] (Note that the system loses synchronism as soon as the
first major generators’ separation occurs. The conjecture needs to be valid until the OMIB
loses its stability, and the generators within each of the CC and NC groups may split
subsequently into subgroups):

Conjecture 1. Loss of synchronism in a power system originates from the separation of its genera-
tors into two groups:

The critical generators responsible for the loss of synchronism
The non-critical generators
The transient stability behaviour of a multi-machine system may be inferred from that of an
OMIB properly derived from the above decomposition pattern into two groups.

The OMIB transformation involves the aggregation of the generators of the NC and CC
and the replacement of the two by an OMIB. The same reasoning that is used in mechanics
to introduce the concept of center of mass can be invoked for the definition of a Center of
Angle (COA) in a multi-machine power system. The COA δ cecan be defined as the inertia
weighted average of generator rotor angles [31]:

δ ce=
1
MT
n
∑
j= 1
Mi δ i (1)
whereMiand δ iare the inertia coefficient and the rotor angle of generatori,nis the number
of generators, andMTis the total inertia of the system:

MT=
n
∑
i= 1
Mi
With generators’ separation toCRandNCsets, the Partial COA (PCOA) of each group
can be defined as follows:

δ cr=
1
Mcrk∈∑CC
Mk δ k
δ nc=
1
Mncl∈∑NC
Ml δ l
(2)
whereMcrandMncrepresent the total inertia of the critical group and the non-critical
group, respectively:

Mcr= ∑
k∈CC
Mk
Mnc= ∑
l∈NC
Ml
Ignoring the generators’ damping, for each generator of the critical set, the generator
dynamics can be described in the form of the following swing equation:

Mk
ω 0
d^2 δ k
dt^2
=Pmk−Pek ∀k∈CC (3)
wherePmdenotes the mechanical power,Peis the electrical output power, and ω 0 = 2 π f 0.
With summation over setCRequations:

∑
k∈CC
(
Mk
ω 0
d^2 δ k
dt^2
) = ∑
k∈CC
Pmk− ∑
k∈CC
Pek (4)
Considering Equation (2), we can rewrite this equation in the following form:

Mcr
ω 0
d^2 δ cr
dt^2
= ∑
k∈CC
Pmk− ∑
k∈CC
Pek (5)
Similarly, with summation over setNCswing equations we have:

Mnc
ω 0
d^2 δ nc
dt^2
= ∑
l∈NC
Pml− ∑
l∈NC
Pel (6)
Dividing both sides of Equations (5) and (6) byMcrandMnc, respectively, and subtracting
them we get:

1
ω 0
(
d^2 δ cr
dt^2
−
d^2 δ nc
dt^2
) =
∑k∈CCPmk−∑k∈CCPek
Mcr
−
∑l∈NCPml−∑l∈NCPel
Mnc
(7)
To derive the OMIB model, we define the OMIB angle δ as follows:

δ = δ cr− δ nc (8)
Multiplying both sides of Equation (7) byM=McrMMTncwe reach to the OMIB model of a
multi-machine power system:
M
ω 0

d^2 δ
dt^2
=Pm−Pe (9)
where:

Pm=
Mnc∑k∈CCPmk−Mcr∑l∈NCPml
MT
(10)
Pe=
Mnc∑k∈CCPek−Mcr∑l∈NCPel
MT
(11)
The OMIB stability can be inferred from Conjecture 2, given below:
Conjecture 2. An OMIB is first-swing unstable, if after fault inception its angle increases contin-
uously with time. The OMIB CCA, if it exists, is the smallest fault elimination angle after which
clearing the fault cannot maintain system stability.

2.2. Extended Equal Area Criterion Concept

Let us consider a simple four-machine power system shown in Figure 2. For a short-
circuit fault in one of the transmission lines, the variations of generator angles with time
can be obtained using time-domain simulation, based on which one can judge the system
transient stability. For example, Figure 3 shows the angle variations of the four machines
for two different fault elimination times. The solid lines show the trajectories when the fault
is successfully cleared at fault elimination timet^1 e, and the generator angles recover towards
stability. The dashed lines show the trajectories for a slightly larger fault elimination timet^2 e,
after which the generator angles diverge continuously, and the system losses its transient
stability.

Energies 2021 , 14 , 7259 6 of 48

synchronous generator
transmission line
short-circuit fault
load
G
G
G
G
G
Figure 2. Simplified diagram of a four-machine power system.
Figure 3. Time-angle trajectories of the four-machine power system obtained by time-domain
simulation. Dashed and solid lines show unstable and stable trajectories, respectively.
The main idea behind the EEAC is to apply the classic EAC concept to the OMIB
equivalent of a multi-machine power system. Multiplying both sides of the swing equation
of Equation (9) by 2d δ /dtand integrating we get:
M
ω 0
(
d δ
dt
)^2 = 2
∫ δ
δ 0
(Pm−Pe)d δ (12)
where δ 0 is the OMIB equivalent initial pre-fault angle.
The above equation shows that the OMIB angle variation is linked to the area between
PmandPe. Consider Figure 4, which shows the δ −Pandt− δ curves for the OMIB
equivalent of detailed model of the four-machine power system, when the fault is initiated
att=0 and corresponding δ 0 , and cleared att^1 e. The curves are obtained from time-domain
simulation results using OMIB equations in their general form. After the fault, δ starts to
increase. Based on Equation (9), as at the initial instant of the faultPm>Pe, the change of δ
int− δ plane is concave-up (the rate of change increases). Att^1 eand corresponding δ^1 e, the
fault is eliminated. A short moment after fault elimination,Pm<Peand the curve int− δ
plane becomes concave-down ( δ is still increasing, but the rate of change is decreasing).
The OMIB angle δ will continue increasing untild δ /dtin Equation (12) becomes zero, i.e.,
the area betweenPmandPebecomes zero.
As shown, the area can be divided to two portions. The positive area is wherePm>Pe
and the OMIB acceleration in Equation (9) is positive. The negative area is wherePm<Pe
and the acceleration is negative. As shown, the negative area does not necessarily start
after fault elimination. If, as in Figure 4, there is a δ mafter which the sum of the areas
betweenPmandPebecomes negative, the system is first-swing stable. The δ mat which the
sum of the areas becomes zero and δ starts to decrease is the return angle δ r.
Figure 5 shows the δ −Pandt− δ curves for the same scenario, but with a slightly
larger fault elimination timet^2 e. Similar to the previous case, a short moment after fault
elimination,Pm<Peand the variations int− δ plane becomes concave-down, i.e., OMIB
decelerates. However, a δ mcannot be found after which the area becomes negative. There-
fore, δ increases and reaches δ uat timetu. After this point,Pm>Pe, the OMIB starts to
accelerate again, δ increases continuously, and the system loses its first-swing stability.

Figure 4. OMIB δ −Pandt− δ curves defined by the swing equation for a first-swing stable case.

Figure 5. OMIB δ −Pandt− δ curves defined by the swing equation for a first-swing unstable case.

It might occur that at the initial instant of the faultPmis lower thanPe. In this case, δ
will start to decrease. Based on Equation (9), asPm<Pefollowing the fault, the change of δ
int− δ plane will be concave-down. At the point wherePebecomes lower thanPm, due to
fault elimination, decreased electrical power, or increased mechanical power, the variations
of δ become concave-up, but it will decrease until an angle δ mis reached, at whichd δ /dtin
Equation (12) becomes zero. If there cannot be a δ mwhich satisfies this condition, δ will
decrease continuously and the system will be ‘backward-swing unstable’.
The EEAC method relies on the general swing equation of Equation (9) in conjunction
with the traditional EAC concept to provide fast transient stability assessment. In this
equation,Pmcan be calculated by substituting the mechanical powers of synchronous
generators of critical and non-critical sets in Equation (10). Without considering the
governor controls,Pmis a known parameter equal to its pre-fault value. However,Pe
in Equation (11) depends on the electrical power of synchronous generators, which are
functions of their variable angles.
Let us consider Figure 3 which shows the angle trajectories of the four-machine power
system subjected to a short-circuit fault and cleared at two different elimination times. It
can be seen that for any time instant of the during-fault period, trajectories of generator
angles are similar for differentte. However, for the post-fault period, they depend on

te. In other words, with an exact simulator of the system, for each generator, and for
the during-fault period, we can calculate the trajectory of its angle with respect to time.
However, for a post-fault period the trajectory depends on δ e, and thus onte.
Let us consider the OMIB δ −Pcurves in Figure 6 plotted for the same fault scenario
and the two different fault elimination times. For the during-fault period, as the variation
of each generator angle with respect to time can be defined uniquely, the variations of the
electrical power of each generator with respect to time can be uniquely defined. Therefore,
as shown, the δ −Pcurves for differenttecoincide in the during-fault period. However,
for a post-fault period, the variations of each generator angle with respect to time depend
onte. Therefore, the variations of the OMIBPewith δ depend on the fault elimination
time. Consequently, as shown, for the post-fault period the δ −Pcurves are different and
dependent on δ e.
The problem is that we intend to apply the EAC on the OMIB model to find the critical
clearing angle, as the smallest δ eafter which the area betweenPmandPeis always negative.
However, the post-faultPeof the OMIB model is uncertain and dependent on δ e. Therefore,
the area itself depends on δ e. The scientific question here is how to find the critical clearing
angle using uncertain δ −Pcurves which are dependent on the clearing angle.
In response to this question, an approach could be to obtain δ citeratively. Using
hybrid EAC and time-domain techniques, such as Single-Machine Equivalent (SIME), δ c
can be obtained iteratively by examining different clearing times. SIME uses a generalized
OMIB model and infers its parameters from the multi-machine temporal data. These data
can be obtained either from time-domain transient stability simulations (Preventive SIME)
or from real-time measurements (Emergency SIME) [1].
However accurate, the iterative approach may not satisfy the computation speed
requirements for fast TSA. Therefore, some approximation in OMIB equations is proposed
which enable the direct and rapid estimation of CCA.

2.3. Approximations for Rapid Estimation of CCA

All OMIB-based transient stability analysis methods rely on the observation that the
loss of synchronism involves the irrevocable separation of generators into two groups:
critical generators and non-critical generators [ 1 ]. Among the general class, the ones which
are able to provide a direct estimation of the CCA are all based on some assumptions
and approximations. As the first and common assumption, these approaches model the
synchronous generators as a constant voltage behind the transient reactance, as shown in
Figure 7.
To discuss the further assumptions, let us consider that for each critical generator
δ i= δ cr+ ξ i, and for each non-critical generator δ j= δ nc+ ξ j, where ξ iand ξ jshow the
angular offset of each generator in setCRandNCfrom their respective PCOA δ crand δ nc.
As described in Appendix A, by considering the classical model of synchronous generators,
the equation for OMIB electrical power becomes:

Figure 6. Dependence of post-fault OMIB power onte. The δ −Pcurves are not necessarily sinusoidal.

Figure 7. Representation of a synchronous generator by a constant voltage behind transient reactance.

PeOM I B=
Mnc
MTk∈∑CCi∈∑CC
[gkicos( ξ k− ξ i) +bkisin( ξ k− ξ i)]
−
Mcr
MTl∈∑NCj∈∑NC
[gl jcos( ξ l− ξ j) +bl jsin( ξ l− ξ j)]
+
Mnc−Mcr
MT k∑∈CCj∈∑NC
[gkjcos( δ + ξ k− ξ j)]
+ ∑
k∈CC
∑
j∈NC
[bkjsin( δ + ξ k− ξ j)]
(13)
wheregij=EiEjGijandbij=EiEjBij,Eiis the constant voltage behind direct axis transient
reactance in the classical model of generatori, andBijandGijare the real and imaginary
parts of the element of rowiand columnjof the admittance matrix reduced to synchronous
generator internal nodes.
The first approximate technique for rapid estimation of CCA assumes that for all
generators ξ kand ξ lare zero, which means that the δ iof each generator is equal to its
corresponding PCOA [ 6 , 7 , 9 ]. In this paper, this approach is referred to as Zero Offset OMIB
(ZOOMIB). As described in Appendix A, with this assumption, the post-fault electrical
power in Equation (13) becomes purely sinusoidal and is no longer dependent on δ e:

PeOM I B=PC+Pmaxsin( δ −v) (14)
where, as discussed in Appendix A,PC,Pmax, andvare constant values for the ZOOMIB
model.
As a second approximation approach, instead of using PCOA for all generators, it is
possible to assume that the angle offsets are constant and equal to their pre-fault values. In
this paper, this approach is referred to as Constant Offset OMIB (COOMIB). As described
in Appendix A, similar to considering zero offsets, also with this assumption, the post-fault
electrical power in Equation (13) becomes purely sinusoidal, independent of δ eand in the
form of Equation (14).
ZOOMIB and COOMIB are both time-invariant models which freeze the generator
angle offsets at the fault inception instant. However, the fact is that the angle offsets are
not constant. In response to this limitation, a piecewise time-variant method is proposed
in [ 10 , 11 ]. This approach, usually referred to as Dynamic OMIB (DOMIB),first makes an
initial estimation of δ cand δ u. It then specifies some points between δ 0 and δ u, and simulates
the generator angle trajectories by individual Taylor series described in Appendix C.2.Having
the generator angles at each point, DOMIB updates the angle offsets and it considers
an updated curve with constant offsets between the points. As shown in Figure 8, this
approach leads to a piecewise sinusoidal δ −Pcurve.

Figure 8. Schematic representation of DOMIB with two added update points (two during-fault
intervals and two post-fault intervals). Dashed lines show the initial ZOOMIB (or COOMIB) δ −P
curves and solid lines show the updated DOMIB curves.

The most interesting point about the time-invariant and piecewise time-variant ap-
proaches is that the assumption of zero or constant ξ ivalues makes the post-faultPeof
the OMIB model independent of δ e. Therefore, the variations of post-faultPewith δ can
be defined uniquely. The merit is that EAC can be applied on the unique δ −Pcurves to
obtain the critical clearing angle. Table 1 compares the assumptions and approximations of
different methods based on the OMIB equivalent.

Table 1. A comparison between the assumptions of different OMIB equivalents.

Assumptions and Approximations True OMIB ZOOMIB COOMIB DOMIB
Separation of generators to CC
and NC XXXX
OMIBPe( δ )andPm( δ )have only one
value for each δ × XXX
Classical model for synchronous
generators × XXX
Constant offsets between generator
angles and their receptive PCOA × XX X
(a)
Zero offsets between generator
angles and their receptive PCOA
× X × ×
(a) DOMIB updates the constant offsets between generator angles.

With the sinusoidalPein Equation (14), the area betweenPmandPeamong an initial
angle δ iand a final angle δ fcan be obtained as follows:

A=Pm−Pc( δ f− δ i) +Pmax[cos( δ f−v)−cos( δ i−v)] (15)
2.4. Definition and Conditions of OMIB Stability

This section presents definitions and conditions for OMIB stability, that are based on
three main assumptions: (1) generators’ separation to critical and non-critical groups, (2)
independence of the post-fault OMIB equivalent electrical power of the clearing time, and
(3) for any δ there is only one possible value forPeandPm. These definitions and conditions
provide a basis for defining a general function for CCA calculation.

Definition 1 (first-swing instability). An OMIB is first-swing unstable if and only if after fault
inception its angle increases continuously with time.

Definition 2 (conditions for critical clearing angle for first-swing instability). Let δ be the
angle of the OMIB equivalent of a power system. After a fault, the critical clearing angle δ cis the
angle that satisfies the following conditions:

AD( δ 0 , δ )> 0 ∀ δ ∈[ δ 0 , δ c] (16)
AD( δ 0 , δ c+ εδ ) +AP( δ c+ εδ , δ )> 0 ∀ δ ∈[ δ c+ εδ , δ max] (17)
∀ δ c′≤ δ c∃ δ m∈[ δ ′c, δ max]| AD( δ 0 , δ c′) +AP( δ ′c, δ m)≤ 0 (18)
whereADandAPare the area betweenPmand during or post-faultPe, and εδ denotes a very small
positive angle increment.

The condition in Equation (16) checks the attainability of δ c. The condition in
Equation (17) states that by clearing the fault at δ c+ εδ ,d δ /dtwill remain positive for
any δ above δ c, i.e., continuously increasing angle. The condition of Equation (18) states
that for clearing angles less than or equal to δ c, the system remains stable.

Definition 3 (backward-swing instability). An OMIB is backward-swing unstable if and only
if after fault inception its angle decreases continuously with time.

Definition 4 (conditions for critical clearing angle for backward-swing instability). Let δ be
the angle of the OMIB equivalent of a power system. After a fault, the critical clearing angle δ cis
the angle that satisfies the following conditions:

AD( δ , δ 0 )< 0 ∀ δ ∈[ δ c, δ 0 ] (19)
AD( δ c− εδ , δ 0 ) +AP( δ , δ c− εδ )< 0 ∀ δ ∈[ δ min, δ c− εδ ] (20)
∀ δ ′c≥ δ c∃ δ m∈[ δ min, δ c′] | AD( δ ′c, δ 0 ) +AP( δ m, δ c′)≥ 0 (21)
In this case, the direction of angle variations is backward. The condition in
Equation (19) checks the attainability of δ c. The condition in Equation (20) states that
by clearing the fault at δ c− εδ ,d δ /dtwill remain negative for any δ below δ c, i.e., contin-
uously decreasing angle. The condition in Equation (21) states that for clearing angles
greater than or equal to δ cthe system remains stable.

Theorem 1 (equivalency of first-swing instability and negative backward-swing instability).
Let OMIB denote a one machine infinite node equivalent of a power system and let OMIB−denote
an OMIB at which the signs of electrical power, mechanical power, and angles are negated. The
OMIB model of the power system is backward-swing unstable, if and only if the OMIB−model

is first-swing unstable. The critical clearing angle for the OMIB is equal to the negative of the
equivalent OMIB−critical clearing angle.

Proof of Theorem. Considering thatA( δ a, δ b) = −A( δ b, δ a), by negating the signs of
electrical power, mechanical power and angles in the conditions of Definition 2 for the
critical clearing angle of a first-swing unstable OMIB we get:

AD( δ ,− δ 0 )< 0 ∀ δ ∈[− δ c,− δ 0 ] (22)
AD(− δ c− εδ ,− δ 0 ) +AP( δ ,− δ c− εδ )< 0 ∀ δ ∈[− δ max,− δ c− εδ ] (23)
∀ δ ′c≥ δ c∃ δ m∈[− δ max, δ ′c]| AD( δ c′,− δ 0 ) +AP( δ m, δ c′)≥ 0 (24)
These equations represent the conditions for the critical clearing angle of a first-swing
unstable OMIB−. Considering δ min=− δ max, the above conditions are equivalent to the
conditions of Definition 4 for the critical clearing angle of a backward-swing unstable
OMIB. Therefore, the critical clearing angle for the first-swing stability of OMIB−is equal
to the negative of the critical clearing angle for the backward-swing stability of OMIB.

2.5. The EEAC Functions

In previous sections, we discussed the concept of EEAC, OMIB general equations, and
approximations that enable one to have uniquely definedPeandPmcurves for all δ. We
also presented general definitions and conditions for OMIB stability.
Two basic functions are required for OMIB stability evaluation. The first function,
as shown in Figure 9, takes theCC,NC, the reduced system admittance matrix, and the
synchronous generators’ data to calculate the OMIB model based on the specified type
(ZOOMIB, COOMIB, or DOMIB). The output of this function is the OMIB inertia coefficient,
PmandPedefined byPc,Pmax, andvas in Equation (14). For DOMIB, the constants defining
Pewill be different for each interval. The function should be called to form the pre-fault,
during-fault, and post-fault OMIB equivalents when required. A pseudocode is presented
in Appendix B, Algorithm A1, which details the process of the OMIB function.

CC: set of names of critical machines
NC: set of names of non-critical machines
type of OMIB (ZOOMIB, COOMIB or DOMIB)
reduced system admittance matrix
synchronous generators data
synchronous generators angles for DOMIB
OMIB
Inputs Outputs
OMIB electrical power
for each interval
OMIB mechanical power
OMIB inertia coefficient
Figure 9. Schematic representation of the OMIB function to form the OMIB equivalent model based
on the specified type.

The second main function is a function using the conditions presented in the previous
section to find the CCA of the developed OMIB models. As shown in Figure 10, this
function takes the during-fault and pre-fault OMIB models as inputs. It also requires two
input parameters: the angle step size∆ δ and the maximum integration limit δ max. The idea
is to start at the OMIB initial angle δ 0 and to increase the fault elimination angle by an
angle increment∆ δ to find δ cas the smallest fault elimination angle after which for any
δ m≤ δ maxthe area betweenPeandPmis positive.

OMIB during-fault electrical
power for each interval
OMIB post-fault electrical
power for each interval
OMIB mechanical power
OMIB inertia constant
Inputs CCA Outputs
Parameters
critical clearing angle
return angle
direction of angular deviations (forward swing' orbackward swing')
the type of the case detected (always stable',always unstable' or `potentially stable')
: angle step size
: maximum integration limit
Figure 10. Schematic representation of CCA function to find the CCA of the equivalent OMIB model.

There are some exceptional cases that should be considered to avoid unreasonable
results. The first case might happen when the maximum post-fault electrical power is less
than the OMIB mechanical powerPm. In such a case, the area betweenPmandPeis always
positive and the system is unstable. Even if the maximum post-fault electrical power is
more thanPm, there might be other situations where the system is always unstable. As
shown in Figure 11a, the area betweenPmandPemight be such that even for δ c= δ 0 it
is always positive. Another exceptional case might happen for less severe disturbances,
where the maximum during-fault electrical power is much more thanPm. In such cases,
shown in Figure 11b, the system will remain stable even without removing the fault.

( a ) ( b )
Figure 11. Exceptional case: ( a ) the sum of the areas is always positive and ( b ) system is always
stable.

The function should be able to handle such cases and also backward-swing instability.
It outputs the direction of angular deviations, ‘first-swing’ or ‘backward-swing’; the type
of the case detected, ‘always stable case’, ‘always unstable case’, or ‘potentially stable case’;
and the critical clearing angle. A pseudocode is presented in Appendix B, Algorithm A2,
which details the process of CCA function.

3. Critical Machines Identification and Critical Cluster Formation

In a multi-machine power system, transient stability phenomena are governed by the
critical machines, i.e., the set of machines responsible for the loss of synchronism following
a large disturbance. Up to now, we have assumed that the critical cluster CC and the
non-critical cluster NC are known. However, identification of the CC is one of the first steps
of the EEAC algorithm and a prerequisite of OMIB equivalent model formation. Different
OMIB equivalents can be formed for different possible sets of CC and NC. The true sets of
CC and NC will be the ones with the smallest CCT. The reasoning behind this is that adding
any critical machine of the true CC to the true NC, or adding any non-critical machine of
the true NC to the true CC, will lead to slower OMIB dynamics, i.e., higher CCT.
For a power system withngenerators, the true CC can be identified by examining
all possible combinations ofngenerators, i.e., 2 n−1 candidates to find the ones with the
smallest CCT. This exhaustive process would, however, be computationally demanding.
The other solution is to find of a limited list of candidate critical generators in a CMI process.
Then, in a CCF process, different pairs of CC and NC can be formed. An OMIB equivalent

should be formed for each pair. The OMIB with the smallest CCT corresponds to the true
pair of CC and NC. The next subsections present different methods for CCI and CCF.

3.1. Critical Machines Identification

All the techniques proposed for CMI are designed to provide a ranked list of critical
machines to limit the number of possible combinations. Some are based on indices which
rank the list of machines based on a criterion calculated for the fault inception time. Some
others are based on a pre-estimation of CCT, to obtain the generators’t− δ trajectories,
and to rank them based on their estimated rotor angles at an appropriate time after fault
inception.

3.1.1. Acceleration Criterion

In the earlier stages of the EEAC development, the first approach for CMI was based
on the initial accelerations the generators acquire at the disturbance inception [ 6 , 7 , 9 ].
According to this so-called “accelerations criterion”, generators likely to be critical were
considered to be those with the largest initial accelerations. For a given contingency,
this approach first ranks the generators in a decreasing order of their initial accelerations
calculated using Equation (A32) immediately following the fault inception.
Despite the encouraging results of this approach, the studies revealed difficulties of
two types [ 9 ]. First,cmneeds to be limited to avoid computational intractability. This may
lead to unacceptable results for stability cases involving several critical generators. Second,
it may happen that some generators not appearing at the top of the initial acceleration
list experience considerable variations in their rotor angles after clearing the fault and
eventually become unstable. In such cases, the initial acceleration criterion is not valid.

3.1.2. Composite Criterion

To improve the acceleration criterion, the “composite criterion” is proposed in [ 9 ].
The “composite criterion” relies on the initial accelerations together with the generators’
pre-fault electrical distance to the fault to better identify the critical generators. It also
considers the post-fault electrical distance of the generators to the fault to obtain a sense of
the post-fault network.
To define it in the form of a criterion to rank the generators, for each generatorkwe
can write:

CCk=
γ k|t= 0 +
distprek+distpostk
(25)
where γ k|t= 0 +is generatorkinitial acceleration, anddistprekanddistpostkdenote the pre-
and post-fault electrical distances to the fault busf, calculated as follows:

distk=zkk+zf f− 2 zk f (26)
wherezijis the magnitude of the element of rowiand columnjof non-reduced system

impedance matrix Zˆ.
The composite criterion was shown to perform better than the acceleration criterion
in ranking the generators [ 9 ]. Nevertheless, it requires inversion of the bus admittance
matrix to find Zˆ and to calculate the electrical distances. Moreover, calculation of electrical
distance would be problematic when network splitting happens after fault clearance.

3.1.3. Trajectory Criterion

The trajectory criterion is proposed in [ 10 , 11 ] to rank the generators in order of their
criticality. It is conjectured that the degree of criticality of a given generator is directly
proportional to the magnitude of its rotor angle observed at an appropriate instant of
time, in its evolution along an appropriate trajectory. The appropriate trajectory is a near-
critically cleared one, i.e., cleared at a time nearly above the actual CCT, and the appropriate

observation time is defined as the time to reach the unstable equilibrium point of the OMIB
equivalent of the power system.
The estimation of the generators’ appropriate trajectory can be obtained by numerical
integration. In [ 10 , 11 ], however, the Taylor series is employed as a quick substitute. Having
an initial estimation of the CCT and the observation time, the trajectories can be obtained
using individual Taylor series detailed in the Appendix C.

3.2. Critical Cluster Formation

The CMI gives a ranked list of critical machines. The aim of CCF is to form different
combinations of CC and NC. The combinations should be later evaluated to identify the
true combination of the clusters. Different techniques are proposed to form the clusters. A
simple approach is to consider all possible combinations of critical machines as possible
CCs [ 6 , 8 , 9 ]. A more efficient technique is presented in [ 10 ]. This technique selectscm
candidate CCs composed of the first from the top, the first two from the top,.. ., up to all
cmmachines in the CC set.

3.3. CMI and CCF Functions

Three methods are discussed for CMI. As shown in Figure 12, for the acceleration
criterion, the CMI function inputs the synchronous generators’ data, their initial angle,
and the during-fault system admittance matrix to provide a ranked list of generators based
on calculated initial accelerations. For the composite criterion, the function also needs the
pre-fault and post-fault system admittance matrix and the index of the fault bus (for line
faults a virtual node should be added at the fault location) in the matrices to calculate
the distances in Equation (26). For trajectory criterion, the reduced post-fault system
admittance matrix, the fault elimination time, and the observation time are required. The
individual Taylor series is employed to obtain the generators’ angle trajectory and to rank
them based on their angles at the observation time. In this paper, the observation time is
defined as the time to reach the OMIB return angle. After ranking the generators with any
of the criteria, the generators which are close to the top generator based on a predefined
threshold are selected as critical ones and are outputted as a ranked list. A pseudocode is
presented in Appendix B, Algorithm A6, which details the process of the CMI function.
The CCF function, as shown in Figure 13, receives the ranked list of the critical
generators and forms different candidate pairs of CC and NC. A pseudocode is presented
in Appendix B, Algorithm A7, presenting one simple method, among others, for CCF.

CMI
Inputs Outputs
Parameters
ranked set of names of
synchronous machines
identified as critical
CMI threshold
: system base frequency
synchronous generators data and initial angle
type of CMI (acceleration, composite or trajectory criterion)
reduced during-fault system admittance matrix
reduced post-fault system admittance matrix (for trajectory criterion)
observation time and fault elimination time (for trajectory criterion)
pre-fault and post-fault system admittance matrix (for composite criterion)
index of the faulted bus in system admittance matrix (for composite criterion)
Figure 12. Schematic representation of CMI function to find the ranked list of critical synchronous
generators.

CCF
ranked machines set of names identified of synchronous as critical Inputs Outputs-set of pairs of CC and NC
synchronous generators names
Figure 13. Schematic representation of CCF function to form the candidate CCs and NCs.

4. Integration

The EAC, despite all the information it provides, cannot directly give an indication
of CCT which is of interest in transient stability studies. The CCT may be assessed by
integrating the dynamics of the OMIB up to the point where it reaches CCA. In principle
any numerical integration algorithm can be used. In [ 5 – 10 ], however, the Taylor series
is employed as a handy and quick substitute for numerical integration. In the context of
EAC-based methods, the Taylor series expansion can be applied to the OMIB equivalent of
a power system, or to an individual generator to obtain its rotor angle evolution with time.
The equations and the process of the Taylor series is presented in Appendix C.
As shown in Figures 14 and 15, despite the integration techniques employed, two main
functions are required. The angle-to-time function inputs the OMIB equivalent model, the
initial angle, the initial angular speed, and a desired angle (e.g., the CCA). It integrates the
OMIB equations interval by interval to find the time and angular speed associated to the
desired angle. The pseudocodes presented in Appendix B, Algorithms A8 and A9, present
the details of this process with the Taylor series. As discussed in [ 9 ], for large departures of
the desired angle from the initial angle, the Taylor series estimation may be inaccurate or
may fail to give a result.
The Trajectory function, inputs the generators’ data, their initial angle, during-fault
and post-fault reduced system admittance matrices, the fault elimination time, and the
desired final time of an individual generator’s angle trajectory. It also receives the desired
number of during-fault and post-fault intervals as input parameters. The function specifies
some time instants based on the number of intervals and the time spans. It then calculates
each individual generator’s angle and angular speed interval by interval to reach the
desired final time. The outputs will be the time instants, and the generator’s angle and
angular speed at each time. The pseudocodes presented in Appendix B, Algorithms A
and A11, detail this process with Taylor series.

Inputs angle-to-time Outputs
desired time at the given
desired angle
desired angular speed at
the given desired angle
OMIB electrical power for each interval
OMIB mechanical power
OMIB inertia constant
initial angle
initial angular speed
desired angle
Figure 14. Schematic representation of angle-to-time function to find the time and angular speed
associated with a desired angle.

Inputs Trajectory Outputs
interval time instants
synchronous generators angles at
each time instant
synchronous generators angular
speed at each time instant
synchronous generators data and initial angle
reduced during-fault system admittance matrix
reduced post-fault system admittance matrix
fault elimination time
end of trajectory time span
Parameters
d: number of during-fault intervals
p: number of post-fault intervals
Figure 15. Schematic representation of Trajectory function to find synchronous generators’ angle
trajectory in time.

5. Combining Algorithms for a Full-Resolution Scheme

The functions presented in the previous sections can be combined in different ways
to provide an estimation of the CCT. The main functions include CCF and CMI , which
can be based on acceleration, composite or trajectory criteria; OMIB which can be of type
ZOOMIB, COOMIB, or DOMIB; CCA to estimate the critical clearing angle of the OMIB;
angle-to-time to find the time corresponding to an OMIB angle; and Trajectory to find
the trajectory of generator angles in time. These functions provide an insight to rethink
the schemes proposed in previous literature, and to think of new schemes for direct CCT
estimation.

The first step for any TSA technique is the preparation of the synchronous generators
and the network data, and the formation and reduction of admittance matrices for pre-fault,
during-fault, and post-fault states. EEAC relies on the classical model of the power system.
Synchronous generators will be modeled with the classical model, and the admittance
matrices include the loads and the generators’ direct axis transient reactance. Admittance
matrix reduction can be done by Kron method considering that all the nodes have zero
injection currents except the internal nodes of synchronous generators.
The first and the simplest EEAC scheme that was proposed in [ 5 , 6 , 8 ] is as presented
in Figure 16. The types are mentioned within green parenthesis, while the variable pa-
rameters are shown within red parenthesis. The pseudocodes presented in Appendix B,
Algorithm A12, present the details of the basic-eeac scheme.
The scheme starts by identifying the critical machines (Here, the CMI is done with
acceleration criterion, but it can also be done with composite criterion) and forming a
set of CCs and a set of NCs. It then evaluates each pair of CC and NC. For each pair, it
first forms the pre-fault, during-fault, and post-fault OMIB equivalents (Here, the OMIB
models are derived with ZOOMIB assumptions, but they can also be derived with COOMIB
assumptions). Having the OMIB equivalents defined, the CCA function is applied to find
the CCA of the pair under consideration. Then, the CCT is calculated as the time to reach
the CCA. After repeating these steps for each pair, the true CC and true NC are identified as
the ones with minimum CCT. The algorithm finally returns the CCT, the identified clusters,
the CCA and the angular speed, and the observation time as the time to reach the return
angle δ rfrom δ 0 and may later be used for subsequent calculations.

(threshold)
CMI
(Acc) CCF
OMIB
(ZOOMIB)
CCA
angle_
to_time
Input data of for CC each and pair NC
select the pair CCT, CC, NC
with minimum
CCT
(? ?, ?max)
Figure 16. The basic scheme to estimate the CCT with EEAC.

When an estimation of the CCT is made with the basic-eeac , the estimation can be
improved in many ways. One approach can be as shown in Figure 17. Having a first
estimation of CCT and observation time, the Trajectory function can be used to estimate
the individual generator’s angles fordduring-fault andppost-fault intervals within δ 0
to δ max. With these estimated angles, the OMIB function can be recalled to make a better
estimation of the OMIB equivalent model with DOMIB model assumptions. Then, the
CCA function can be applied to the updated OMIB model to estimate the CCA, and the
angle-to-time function can be employed to calculate the refined CCT.

CCT, CC, NC Trajectory OMIB
(DOMIB) CCA
angle_
to_time
(d, p)
CCT, CC, NC
(? ?, ?max)
Figure 17. First refinement scheme to improve the estimation of the CCT.

The above refinement process just re-estimates the CCT and does not update the
estimate of the CC and NC. The second refinement process shown in Figure 18 uses the
calculated CCT to find the individual generator angle trajectories and to rank them based

on their angles at the estimated observation time. It then runs the CCF function to form
a set of CCs and a set of NCs, and evaluates each pair of CC and NC. For each pair, it
first forms the pre-fault, during-fault, and post-fault DOMIB equivalents. The CCA and
angle-to-time functions are then applied to estimate the CCT for each pair. Finally, the
pair with the minimum CCT is identified as the true pair (Here, the OMIB models are
derived with DOMIB assumptions, but they can also be derived with ZOOMIB or COOMIB
assumptions.).

CCT, CC, NC CMI
(Traj) CCF
OMIB
(DOMIB)
CCA
angle_
Trajectory to_time
for each pair
of CC and NC
select the pair CCT, CC, NC
with minimum
CCT
(? ?, ?max)
(threshold)
(d, p)
Figure 18. Second refinement scheme to improve the estimation of the CCT.

Figure 19 shows a more sophisticated scheme. This scheme was proposed in [ 10 ].
Similar to the second refinement scheme, this scheme relies on the ‘trajectory’ CCI. However,
for each pair of the CC and NC, it first forms a ZOOMIB equivalent, applies the angle-
to-time function, and obtains the generator angle trajectories. It then forms a DOMIB
equivalent model using the obtained trajectories, applies the CCA function on the model,
and calculates the CCT corresponding to each obtained CCA. Finally, the pair with the
smallest CCT is identified as true CC and NC. The pseudocodes presented in Appendix B,
Algorithm A13, present the details of the third refinement scheme. The pseudocodes of the
other refinement schemes are simplified versions of this scheme and are not presented.

CCT, CC, NC CMI
(Traj) CCF
OMIB
(COOMIB)
CCA
angle_
to_time
Trajectory
OMIB
(DOMIB)
CCA
angle_
to_time
(d, p)
Trajectory
(threshold)
for each pair
of CC and NC
select the pair CCT, CC, NC
with minimum
CCT
(? ?, ?max) (? ?, ?max)
(d, p)
Figure 19. Third refinement scheme to improve the estimation of the CCT.

The interesting point about this functional point of view of the EEAC is that the output
of the basic-eeac is identical to the inputs and outputs of all three refinement schemes
discussed. Therefore, as shown in Figure 20, these schemes can be repeated after each
other to achieve the desired accuracy. As shown, after running the basic-scheme or each
of the refinement functions, it is possible to terminate the calculations and output the

estimated CCT and CC. We define each path from the input to the outputs as a branch. As
ZOOMIB and COOMIB equivalents, and acceleration and composite CCIs can be used
interchangeably, there are four possible combinations and thus four variants for each
branch in Figure 20. Each branch has a different computational time which is a function
of the system scale, the short-circuit scenario, and the chosen values for parameters. The
parameters of each branch can be optimized to achieve the best performance in terms of
CCT estimation accuracy and the computational time.

Text
Input data basic-scheme
refinement
refinement
refinement
refinement
refinement
refinement
refinement
refinement
refinement
refinement
refinement
refinement
CCT, CC
Figure 20. Possible schemes to apply the EEAC concept to make an estimation of the CCT and
the CC.

6. Simulation Studies and Discussions

This section presents the results for the application of the EEAC method on two
test systems. The first is the four-machine system discussed before. The second is the
French EHV power system with more than 400 synchronous machines, 2900 transmission
lines, and 8800 transformers. Applying the EEAC on the four-machine system helps to
investigate its approximations in detail, while studies of the French network helps to
evaluate its performance for a real-life, large-scale network. For both test systems, the
EEAC results are compared against time-domain simulations.

6.1. Four-Machine System

The considered scenario for the first test system, shown in Figure 2, is a three-phase
short-circuit fault at one of the transmission lines, which is cleared by opening the line
circuit breakers. As shown in Figure 3, for this case study, there is a clear separation
between the NC generators and CC generators with increasing angles. A correct estimation
of CC and NC allows us to evaluate the effect of assumptions of OMIB equivalent models,
and also the effect of considering the classical model for synchronous generators.
To evaluate the assumptions, Figure 21 represents the δ −Pcurves obtained with
ZOOMIB- and DOMIB-equivalent models. The curves are compared against the δ −P
curves obtained from the time-domain simulation results, with the classical model for
synchronous machines, and with the detailed model with regulators, i.e., speed governor
and automatic voltage regulator. For time-domain simulation results, the angles and
powers are obtained using Equations (8), (10), and (11).
As can be seen, the OMIB δ −Pcurve obtained with ZOOMIB assumptions is close to
simulation results with the classical model. However, the modified piecewise curves ob-
tained with DOMIB assumptions are much closer. As all the approximate OMIB equivalent
models are based on the classical model of synchronous generators, the results they pro-
vide do not necessarily match the result obtained with the detailed model with regulators.
However, the estimations of CCA are still close.
To better highlight the differences in estimations, Table 2 compares the CCT and CCA
values obtained with different OMIB model assumptions against the values obtained from
time-domain simulations. The Taylor series is employed to estimate the CCTs with the
OMIB equivalents. In comparison with the results obtained with the classical model, the
results obtained with ZOOMIB and COOMIB assumptions are acceptable. There is a clear
improvement in the results obtained with DOMIB assumptions, and they are close to the
classical model results. By considering a detailed model in simulations, the estimation
errors increase; however, the DOMID still performs better.

Figure 21. Comparison of the δ −Pcurves obtained with ZOOMIB and DOMIB models with
time-domain simulations.

Table 2. A comparison between time-domain simulation results with the results obtained with
different OMIB equivalent assumptions and Taylor series.

Model CCA (rad) CCT (ms)
ZOOMIB 1.084 199.
COOMIB 1.085 199.
DOMIB 1.038 189.
Time-domain with classical model 1.036 187
Time-domain with detailed model 0.937 160
6.2. French Network

This section briefly discusses the results of several fault scenarios considered in
the French network. The considered scenarios are three-phase short-circuit faults on
transmission lines, on bus-bars or on transformers. The French network covers several
voltage levels. The faults are applied at different locations of the network, some close
to large power plants on 400 kV, others on 225 kV portions of the network. The model
considered for synchronous machines is a detailed model with regulators.
As discussed in Section 5, the functions presented in the previous sections can be com-
bined in different ways to provide an estimation of the CCT. For each fault scenario, four
of the possible schemes are examined, the basic scheme shown in Figure 16, and the basic
scheme followed by the refinement schemes shown in Figures 17–19. The pseudocodes of
these schemes are presented in Appendix B. For the basic scheme, the acceleration criterion
is used for CMI. The scheme is evaluated with ZOOMIB and COOMIB assumptions.
The results are obtained by considering certain default values for parameters. How-
ever, the parameters can be optimized to find more accurate results. The considered values
for angle step size∆ δ and maximum integration limit δ maxare 0.1 and 360 degrees, respec-
tively. Five intervals are considered for each of the during-fault and post-fault periods, and
50% is considered as the threshold for CMI.
The error in CCT calculation is calculated as follows:

Error=
CCTa−CCTe
CCTa
× 100 (27)
whereCCTeandCCTaare the estimated CCT with EEAC and Taylor series, and the actual
CCT obtained from the time-domain simulations, respectively.
Table 3 compares the CCT values obtained with time-domain simulations against
the basic scheme with ZOOMIB and COOMIB assumptions. Table 4 compares the CCT
values obtained with time-domain simulations against the refined schemes for the same
fault scenarios. As discussed in Section 2.5, there are some exceptional cases that should
be considered to avoid unrealistic results. In both tables, ‘stable’ denotes the detection of
an ‘always stable’ case, and ‘unstable’ denotes the detection of an ‘always unstable’ case
(see Figure 11). For each of the considered case studies, the error percentage (Error) is
calculated using Equation (27). Figures 22 and 23 compare the number of cases in each
Errorinterval.
It is better for TSO to be more conservative and have an estimated CCT lower than
the actual CCT, than having higher values. In other words, the TSO prefers to have a
positiveErrorrather than a negativeError. As can be seen in the tables and the figures,
with the basic scheme and ZOOMIB model assumptions, the errors are mainly positive,
while with COOMIB assumptions fewer cases have a high negativeError. The refined
schemes produce more accurate results for some fault scenarios. However, as discussed,
the use of DOMIB assumptions modifies the estimation towards the classical model and
the results are not necessarily close to the results obtained with the detailed model. On
average, the basic scheme with ZOOMIB assumptions has better estimations than the other
schemes. The first and third refined scheme decrease the maximum error, but all refined
schemes have a larger error on average. Moreover, for more cases they detect an exception
and do not provide a result.
The results show that a more complicated scheme does not necessarily provide more
accurate results, while it might involve more computational time. For the case studies
considered, the average computation time for basic schemes with ZOOMIB or COOMIB
assumptions was around 30 s, while it was around 45, 70, and 100 s for the first, second,
and third refined schemes, respectively. Moreover, the basic scheme does not identify any
scenario as stable, thus less risk for the TSO.

Table 3. A comparison between time-domain simulation results with the results obtained with
different basic schemes for the French network.

Time-Domain Basic Scheme ZOOMIBa Basic Scheme COOMIBb
Scenario CCT (ms) CCT (ms) Error (%) CCT (ms) Error (%)
1 231 323.71 −40.13 324.46 −40.46
2 159 238.16 49.79 242.21 −52.33
3 173 151.72 −12.30 155.49 10.12
4 277 240.49 −13.18 263.37 4.92
5 106 122.71 15.76 124.27 −17.24
6 258 unstablec —- unstable —-
7 227 159.41 −29.78 167.35 26.28
8 225 203.00 −9.78 210.20 6.58
9 195 216.84 11.20 221.99 −13.84
10 205 234.20 14.24 239.63 −16.89
11 184 202.48 10.04 207.15 −12.58
12 198 227.26 14.78 232.42 −17.38
13 182 201.31 10.61 205.15 −12.72
14 189 217.11 14.87 221.58 −17.24
15 267 286.32 7.24 295.36 −10.62
16 259 279.33 7.85 288.07 −11.22
17 258 280.43 8.69 288.68 −11.89
18 159 18.74 −88.21 57.62 63.76
19 135 136.73 1.28 132.62 1.76
20 119 233.84 96.50 222.42 −86.90
21 98 217.54 121.98 202.96 −107.11
22 95 77.97 −17.93 68.14 28.27
23 104 81.34 −21.78 73.70 29.14
24 120 111.19 −7.34 104.83 12.64
25 124 116.86 −5.76 110.56 10.84
26 105 79.86 −23.95 72.64 30.82
27 129 125.42 −2.78 122.28 5.21
28 129 126.42 −2.00 122.28 5.21
29 129 124.75 −3.30 120.43 6.65
30 122 112.53 −7.76 106.80 12.46
31 126 115.95 −7.98 110.49 12.31
32 140 146.38 4.56 143.14 −2.25
33 142 148.51 4.58 145.43 −2.42
minimumd 95 18.74 1.28 57.62 1.76
maximumd^277 323.71 121.98 324.46 107.11
meand 168.76 173.70 21.50 175.12 21.88
aBasic scheme with acceleration criterion for CMI and ZOOMIB assumptions for OMIB equivalent.bBasic
scheme with acceleration criterion for CMI and COOMIB assumptions for OMIB equivalent.cAn ‘always unstable
case’ is detected.dScenarios detected as stable or unstable are not considered in calculations. Absolute values are
considered.

( a ) ( b )
Figure 22. Number of cases in each Error percentage interval for the basic scheme ( a ) with ZOOMIB
assumptions and ( b ) with COOMIB assumptions
( a ) ( b ) ( c )
Figure 23. Number of cases in each Error percentage interval for the refined schemes ( a ) first
refinement scheme, ( b ) second refinement scheme, and ( c ) third refinement scheme.
Table 4. A comparison between time-domain simulation results with the results obtained with different refined schemes for
the French network.
Time-
Domain First Refinement Scheme
a Second Refinement Schemea Third Refinement Schemea
Scenario CCT (ms) CCT (ms) Error(%) CCT (ms) Error(%) CCT (ms) Error(%)

(^1231) unstableb —– 586.39 −153.85 stablec —–
2 159 235.91 −48.37 235.91 −48.37 235.86 −48.34
3 173 132.53 23.39 132.53 23.39 133.18 23.02
4 277 262.31 5.30 262.31 5.30 265.41 4.18
5 106 119.10 −12.36 119.10 −12.36 119.10 −12.36
6 258 unstable —– unstable —– unstable —–
7 227 161.43 28.89 150.50 33.70 unstable —–
8 225 208.27 7.43 197.83 12.08 unstable —–
9 195 232.52 −19.24 232.52 −19.24 unstable —–
10 205 255.70 −24.73 255.70 −24.73 245.51 −19.76
11 184 215.32 −17.02 215.32 −17.02 201.38 −9.44
12 198 249.73 −26.12 249.73 −26.12 241.21 −21.82
13 182 212.02 −16.49 212.02 −16.49 194.26 −6.73
14 189 236.59 −25.18 236.59 −25.18 229.82 −21.60
15 267 306.82 −14.91 306.82 −14.91 unstable —–
16 259 299.81 −15.76 299.81 −15.76 294.38 −13.66

Table 4. Cont.
Time-
Domain
First Refinement Schemea Second Refinement Schemea Third Refinement Schemea
Scenario CCT (ms) CCT (ms) Error(%) CCT (ms) Error(%) CCT (ms) Error(%)
17 258 failed —– 354.87 −37.54 294.26 -14.05
18 159 48.41 69.55 stable —– stable —–
19 135 129.99 3.71 129.99 3.71 unstable —–
20 119 209.06 −75.68 209.06 −75.68 209.73 −76.25
21 98 187.45 −91.28 187.45 −91.28 188.22 −92.06
22 95 52.14 45.12 stable —– stable —–
23 104 55.27 46.85 stable —– stable —–
24 120 100.46 16.29 100.46 16.29 94.12 21.57
25 124 105.90 14.60 105.90 14.60 99.90 19.43
26 105 53.55 49.00 stable —– stable —–
27 129 107.96 16.31 104.46 19.02 unstable —–
28 129 107.96 16.31 104.46 19.02 unstable —–
29 129 105.74 18.03 101.42 21.38 unstable —–
30 122 89.31 26.79 84.40 30.82 unstable —–
31 126 92.79 26.36 88.10 30.08 unstable —–
32 140 130.88 6.51 128.05 8.53 122.12 12.77
33 142 132.88 6.42 130.16 8.34 120.40 15.21
minimumd 95 48.41 3.71 84.40 3.71 94.12 4.18
maximumd 277 306.82 91.28 586.39 153.85 294.38 92.06
meand 168.76 161.26 27.13 197.21 29.46 193.46 25.43
aBasic scheme with ZOOMIB assumptions for OMIB equivalent plus a refinement scheme.bAn ‘always unstable case’ is detected.cAn ‘always stable
case’ is detected.dScenarios detected as stable or unstable are not considered in calculations. Absolute values are considered.

7. Conclusions
These days, due to increased uncertainties in electrical power systems, there are an
increasing number of transient stability scenarios that are of concern. Therefore, TSOs need
fast TSA techniques to filter the scenarios and to identify the critical ones with lower CCT for
detailed analysis. EEAC was proposed in the late 1980s as a promising and fast TSA method.
However, despite the encouraging results and approaches presented through several
papers, it was difficult to obtain a synthetic view of the key building blocks upon which
the EEAC was built. This paper has revisited the EEAC from scratch. It has presented its
very basic concept, the detailed equations, and the idea behind the approximations for fast
TSA. New definitions and conditions have been defined for approximate models forward
swing and backward swing stabilities. Based on these definitions and conditions, functions
were developed for each EEAC building block, together with detailed pseudocodes. The
idea was to propose a general full-resolution functional scheme that not only covers all the
previous literature on the subject, but also introduces interesting possibilities for several
new approaches.
Our studies show that the accuracy of the EEAC, though acceptable, depends on
the selection of the sequence of functions and parameters. Once the optimal sequence
of functions and parameters has been identified, the EEAC can serve as an effective tool
for contingency filtering. It had reduced the time required for the analysis of a fault
scenario in the French network from around 15 minutes for time-domain simulation
to just a few seconds. However, further studies are required to design result quality
indicators to tag cases where EEAC may not perform well. Moreover, the EEAC equations
should be developed to consider non-synchronous generation units (e.g., windfarms) and
HVDC links.

Author Contributions: Conceptualization, A.B., D.E. and Y.V.; Methodology, A.B., D.E. and Y.V.;
Software, Y.V,; Validation, A.B., Y.V. and C.P.; Formal analysis, A.B., Y.V. and C.P.; Investigation,
A.B., Y.V., C.P. and Q.G.; Resources, C.P. and P.P.; Data curation, Y.V., C. Pache and Q. Gemine;
Writing—original draft preparation, A.B. and D.E.; Writing—review and editing, A.B., D.E. and C.P.;
Visualization, A.B., Y.V. and C.P.; Supervision, D.E., Q.G., C.P. and P.P.; Project administration, D.E.,
Q.G., C.P. and P.P. All authors have read and agreed to the published version of the manuscript.

Funding: This research received no external funding.

Institutional Review Board Statement: Not applicable.

Informed Consent Statement: Not applicable.

Conflicts of Interest: The authors declare no conflicts of interest.

Abbreviations

The following abbreviations are used in this manuscript:

TSO Transmission System Operator
TSA Transient Stability Analysis
EAC Equal Area Criterion
EEAC Extended Equal Area Criterion
OMIB One-Machine Infinite Bus
SMIB Single Machine connected to an Infinite Bus
SIME Single-Machine Equivalent
CCT Critical Clearing Time
CCA Critical Clearing Angle
CMI Critical Machines Identification
CCF Critical Cluster Formation
CC Critical Cluster of generators
NC Non-critical Cluster of generators
COA Center of Angle
PCOA Partial Centre of Angle
ZOOMIB Zero Offset OMIB
COOMIB Constant Offset OMIB
DOMIB Dynamic OMIB

Appendix A. OMIB Electrical Power with the Classical Model

The classical model of a power system considers a constant-voltage-behind-transient-
reactance model for synchronous generators. In this model of the system, by dividing
the network nodes tonsynchronous generator internal nodes andrremaining nodes, the
relationship between the bus voltages, nodal current injections, and the network admittance
matrix is given by: [
I ̃n
0

]
= Yˆ
[
E ̃n
V ̃r
]
(A1)
where E ̃n denotes the synchronous generators’ internal voltage behind their transient
reactance, I ̃n is the generators’ current, and V ̃r denotes the voltages of the remaining
network nodes. Yˆ is the network admittance matrix which includes the load impedances
and generator transient reactances. This matrix can be partitioned as follows:

[
Yˆ nn Yˆ nr
Yˆ rn Yˆ rr
]
To obtain the electrical power, first we find the reduced admittance matrices by
eliminating all the nodes except for the internal nodes of the synchronous generators. The

reduction can be achieved through matrix operations considering that all the nodes have
zero injection currents except for the source nodes. By eliminating V ̃r we have:

I ̃n = Yˆ red E ̃n (A2)
where:
Yˆ red= Yˆ nn− Yˆ nr Yˆ −rr^1 Yˆ rn
In a power system withnsynchronous generators, to calculate the output electrical
power of each one we can write:

Pei=Re[E ̃iI ̃i
∗
]
=Re[E ̃i
n
∑
j= 1
(E ̃jyˆij)∗]
(A3)
whereE ̃i=Ei∠ δ iis the voltage behind direct axis transient reactance of the synchronous
generatori, andyˆij=yij∠ θ ijis the element of rowiand columnjof the reduced admittance
matrix.
Therefore, for each generator we have:

Pei=Re[
n
∑
j= 1
(EiEj∠( δ i− δ j)(Gij−jBij))] (A4)
whereGijandBijare conductance and susceptance parts of the admittance element of row
iand columnj.
Expanding Equation (A4) and separating the real and imaginary parts we get:

Pei=
n
∑
j= 1
EiEj[Gijcos( δ i− δ j) +Bijsin( δ i− δ j)] (A5)
For each generatorkof setCRwe can rewrite Equation (A5) in the following form:
Pek= ∑
i∈CC
EkEi[Gkicos( δ k− δ i) +Bkisin( δ k− δ i)]
+ ∑
j∈NC
EkEj[Gkjcos( δ k− δ j) +Bkjsin( δ k− δ j)]
(A6)
We can consider that for each critical generator δ i= δ cr+ ξ i, and for each non-critical
generator δ j= δ nc+ ξ j, where ξ iand ξ jshow the angular deviation of each generator in
setsCRandNCfrom their respective PSOA δ crand δ nc. Therefore, for each generatorkof
setCRwe can write:

Pek= ∑
i∈CC
EkEi[Gkicos( ξ k− ξ i) +Bkisin( ξ k− ξ i)]
+ ∑
j∈NC
EkEj[Gkjcos( δ cr− δ nc+ ξ k− ξ j) +Bkjsin( δ cr− δ nc+ ξ k− ξ j)]
(A7)
Similarly, for each generatorlof setNCwe can write:
Pel= ∑
i∈CC
ElEi[Glicos( δ l− δ i) +Blisin( δ l− δ i)]
+ ∑
j∈NC
ElEj[Gl jcos( δ l− δ j) +Bl jsin( δ l− δ j)]
(A8)
Considering δ i= δ cr+ ξ kand δ j= δ nc+ ξ j, we have:
Pel= ∑
i∈CC
ElEi[Glicos( δ nc− δ cr+ ξ l− ξ i) +Blisin( δ nc− δ cr+ ξ l− ξ i)]
+ ∑
j∈NC
ElEj[Gkjcos( ξ l− ξ j) +Bl jsin( ξ l− ξ j)]
(A9)
Substituting Equations (A7) and (A9) in Equation (11), we have:
PeOM I B=
Mnc
MT
[
∑
k∈CC
∑
i∈CC
EkEi[Gkicos( ξ k− ξ i) +Bkisin( ξ k− ξ i)]
]
+ ∑
k∈CC
∑
j∈NC
EkEj[Gkjcos( δ cr− δ nc+ ξ k− ξ j) +Bkjsin( δ cr− δ nc+ ξ k− ξ j)]
−
Mcr
MT
[
∑
l∈NC
∑
i∈CC
ElEi[Glicos( δ nc− δ cr+ ξ l− ξ i) +Blisin( δ nc− δ cr+ ξ l− ξ i)]
]
+ ∑
l∈NC
∑
j∈NC
ElEj[Gkjcos( ξ l− ξ j) +Bl jsin( ξ l− ξ j)]
(A10)
To have a simpler form of equation, by consideringgij=EiEjGijandbij=EiEjBij, we have:

PeOM I B=
Mnc
MTk∈∑CCi∈∑CC
[gkicos( ξ k− ξ i) +bkisin( ξ k− ξ i)]
−
Mcr
MTl∈∑NCj∈∑NC
[gl jcos( ξ l− ξ j) +bl jsin( ξ l− ξ j)]
+
Mnc
MTk∈∑CCj∈∑NC
[gkjcos( δ cr− δ nc+ ξ k− ξ j) +bkjsin( δ cr− δ nc+ ξ k− ξ j)]
−
Mcr
MTl∈∑NCi∈∑CC
[glicos( δ nc− δ cr+ ξ l− ξ i) +blisin( δ nc− δ cr+ ξ l− ξ i)]
(A11)
Considering thatMncM+TMcr=1, Equation (A11) can be written as follows:

PeOM I B=
Mnc
MTk∈∑CCi∈∑CC
[gkicos( ξ k− ξ i) +bkisin( ξ k− ξ i)]
−
Mcr
MTl∈∑NCj∈∑NC
[gl jcos( ξ l− ξ j) +bl jsin( ξ l− ξ j)]
+
Mnc−Mcr
MT k∑∈CCj∈∑NC
[gkjcos( δ + ξ k− ξ j)]
+ ∑
k∈CC
∑
j∈NC
[bkjsin( δ + ξ k− ξ j)]
(A12)
Appendix A.1. Considering Zero Rotor Angle Offsets with Respect to PCOA

In this section, we simplify thePefor the OMIB model by considering zero rotor angle
offsets. The assumptions are:

ξ i= ξ j=0 :∀i∈CC,∀j∈NC (A13)
With these assumptions, we can simplify Equation (A12) to the following form:
PeOM I B=
Mnc
MTk∈∑CCi∈∑CC
gki−
Mcr
MTl∈∑NCj∈∑NC
gl j
+
Mnc−Mcr
MT k∑∈CCj∈∑NC
gkjcos( δ ) + ∑
k∈CC
∑
j∈NC
bkjsin( δ )
=PC+Ccos( δ ) +Dsin( δ )
(A14)
On the other hand, in general we have:
Ccos( δ ) +Dsin( δ ) =Pmaxsin( δ −v)
⇒Pmax(sin( δ )cos(v)−cos( δ )sin(v)) =Ccos( δ ) +Dsin( δ )
⇒C=−Pmaxsin(v),D=Pmaxcos(v)
⇒Pmax=
√
(C^2 +D^2 ),v=−tan−^1 (C/D)
The equation forPebecomes:
POM I Be = (PC+Pmaxsin( δ −v)) (A15)
where:

PC=
Mnc
MTk∑∈CCi∈∑CC
gki−
Mcr
MTl∈∑NCj∈∑NC
gl j
Pmax=
√
(C^2 +D^2 )
v=−tan−^1 (C/D)
C=
Mnc−Mcr
MT k∈∑CCj∈∑NC
gkj
D= ∑
k∈CC
∑
j∈NC
bkj
wherePC,Pmax, andvare dependent onMnc,Mcr, andgij, i.e., constants.

Appendix A.2. Considering Constant Rotor Angle Offsets with Respect to PCOA

In this section, we simplify thePefor the OMIB model by assuming that∀i∈CC,∀j∈
NC, ξ i, and ξ jare not necessarily zero, but that they are constant with respect to δ. With
this assumption, we can simplify Equation (A12) to the following form:

PeOM I B=PC+
Mnc−Mcr
MT k∑∈CCj∈∑NC
gkj[cos( δ )cos( ξ k− ξ j)−sin( δ )sin( ξ k− ξ j)]
+ ∑
k∈CC
∑
j∈NC
bkj[sin( δ )cos( ξ k− ξ j) +cos( δ )sin( ξ k− ξ j)]
(A16)
=PC+
Mnc−Mcr
MT k∈∑CCj∈∑NC
gkjcos( δ )cos( ξ k− ξ j)
−
Mnc−Mcr
MT k∈∑CCj∈∑NC
gkjsin( δ )sin( ξ k− ξ j)
+ ∑
k∈CC
∑
j∈NC
bkjsin( δ )cos( ξ k− ξ j)
+ ∑
k∈CC
∑
j∈NC
bkjcos( δ )sin( ξ k− ξ j)
where:

PC=
Mnc
MTk∈∑CCi∈∑CC
[gkicos( ξ k− ξ i) +bkisin( ξ k− ξ i)]
−
Mcr
MTl∈∑NCj∈∑NC
[gl jcos( ξ l− ξ j) +bl jsin( ξ l− ξ j)]
By separating sine and cosine terms we have:
⇒PeOM I B=PC+
[
Mnc−Mcr
MT k∈∑CCj∈∑NC
gkjcos( ξ k− ξ j) + ∑
k∈CC
∑
j∈NC
bkjsin( ξ k− ξ j)]cos( δ )
+ [−
Mnc−Mcr
MT k∈∑CCj∈∑NC
gkjsin( ξ k− ξ j) + ∑
k∈CC
∑
j∈NC
bkjcos( ξ k− ξ j)]sin( δ )
(A17)
=PC+Ccos( δ ) +Dsin( δ )
The equation forPebecomes:
POM I Be = (PC+Pmaxsin( δ −v)) (A18)
where:

PC=
Mnc
MTk∈∑CCi∈∑CC
[gkicos( ξ k− ξ i) +bkisin( ξ k− ξ i)]
−
Mcr
MTl∈∑NCj∈∑NC
[gl jcos( ξ l− ξ j) +bl jsin( ξ l− ξ j)]
Pmax=
√
(C^2 +D^2 )
v=−tan−^1 (C/D)
C= ∑
k∈CC
∑
j∈NC
bkjsin( ξ k− ξ j) +
Mnc−Mcr
MT k∈∑CCj∈∑NC
gkjcos( ξ k− ξ j)
D= ∑
k∈CC
∑
j∈NC
bkjcos( ξ k− ξ j)−
Mnc−Mcr
MT k∑∈CRj∈∑NC
gkjsin( ξ k− ξ j)
wherePC,Pmax, andvare dependent onMnc,Mcr,gij,bij, and ξ i, i.e., constants.

Appendix B. Pseudocodes

This appendix presents the pseudocodes of all the algorithms discussed.
Algorithm A1 pseudocode details the function to compute the OMIB model. The
function is designed for the DOMIB model, but it can be applied for COOMIB or ZOOMIB,
which are similar to DOMIB but with only one interval. It inputs a data class ofsgenerators

including their name, inertia constant, internal voltage, mechanical power, and their initial
and final angles fornintervals. It also requires the system admittance matrix to be reduced
to generators’ internal nodes, and the sets of critical and non-critical generators. The
function should be recalled for each pre-fault, during-fault, and post-fault periods. For
each period, the pseudocode first estimates OMIBPmandM, which are constant values.
Then, for each time interval in the considered period, it estimates the OMIB angle at
the beginning and end of the interval, and the terms defining its electrical power in that
interval.

Algorithm A1 Forming the OMIB equivalent of a multi-machine power system

OMIB ( S , Yˆ
red
, CC , NC ,ty pe,range)
Input

S : data of synchronous generators considering the classical model
· S [j].name: generatorjname:str
· S [j].M: generatorjinertia constant:float
· S [j].E: generatorjinternal voltage magnitude:float
· S [j].Pm: generatorjmechanical power:float
· S [j]. δ i [i]: generatorjinitial angle of intervali:float
· S [j]. δ f [i]: generatorjfinal angle of intervali, set to δ maxby default:float
CC : set of names of critical synchronous generators:set of str
NC : set of names of non-critical synchronous generators:set of str
Yˆ
red
: reduced system admittance matrix:matrix of complex numbers
ty pe: type of OMIB approximation, ‘ZOOMIB’ for zero offset, ‘COOMIB’ for constant
offset, and ‘DOMIB’ for dynamic:str
range: a 2-tuple of the numbers of the first and last intervals in the considered period,
set to (1, 1) be default:tuple of int
Output
P : OMIB power
· P [i]. δ i: initial angle of intervali:float
· P [i]. δ f: final angle of intervali:float
· P [i].Pc: constant electrical power in intervali:float
· P [i].Pmax: maximum electrical power in intervali:float
· P [i].v: angle shift in intervali:float
· P .Pm: mechanical power:float
M: OMIB inertia constant:float
1:s←length( S ): number of synchronous generators
2: G ←real part ( Yˆ )
3: B ←imaginary part ( Yˆ )
4: for j=1 :s do :
5: for k=1 :s do :
6: b [k,j] = S [k].E· S [j].E· B [k,j]
7: g [k,j] = S [k].E· S [j].E· G [k,j]
8: end for
9: end for
Algorithm A1 Cont.

10: Mcr=∑j∈CC S [j].M
11: Mnc=∑j∈NC S [j].M
12: MT=Mcr+Mnc
13: M=McrMMTnc
14: P .Pm=M^1 T
(
Mnc∑j∈CC S [j].Pm−Mcr∑j∈NC S [j].Pm
)
15:n=range[− 1 ]−range[ 1 ] +1 : number of intervals in considered period
16: for i=1 :n do :
17: interval=range[ 1 ] +i−1: interval number in the trajectory
18: δ cri =M^1 cr∑j∈ CR ( S [j].M· S [j]. δ i [interval])
19: δ
f
cr =M^1 cr∑j∈ CR ( S [j].M· S [j]. δ f [interval])
20: δ nci =M^1 nc∑j∈ NC ( S [j].M· S [j]. δ i [interval])
21: δ
f
nc =
1
Mnc∑j∈ NC ( S [j].M· S [j]. δ
f [interval])
22: P [i]. δ i= δ icr − δ nc i
23: P [i]. δ f= δ crf − δ ncf
24: for j=1 :s do :
25: if type == ‘ZOOMIB’ then
26: ξ [j] = 0
27: else ifS [j].name∈ CRthen
28: ξ [j] = S [j]. δ i [interval]− δ cri
29: else
30: ξ [j] = S [j]. δ i [interval]− δ nci
31: end for
32: C= ∑
k∈ CR
∑
j∈ NC
(
b [k,j]·sin( ξ [k]− ξ [j]) +
Mnc−Mcr
MT
(
g [k,j]·cos( ξ [k]− ξ [j])
))
33: D= ∑
k∈ CR
∑
j∈ NC
(
b [k,j]·cos( ξ [k]− ξ [j])−
Mnc−Mcr
MT
(
g [k,j]·sin( ξ [k]− ξ [j])
))
34: P [i].Pc=MMncT ∑
k∈ CR
∑
j∈ CR
(
g [k,j]·cos( ξ [k]− ξ [j]) + b [k,j]·sin( ξ [k]− ξ [j])
)
−
35: MMcrT∑k∈ NC ∑j∈ NC
(
g [k,j]·cos( ξ [k]− ξ [j]) + b [k,j]·sin( ξ [k]− ξ [j])
)
36: P [i].Pmax=
√
(C^2 +D^2 )
37: P [i].v=−tan−^1 (C/D)
38: end for
39: returnP ,M
Algorithm A2 pseudocode details the function to compute the CCA of an OMIB
model. To perform correctly, this function has certain conditions over the interval angles of
the input data:

P[i+ 1 ]. δ initial=P[i]. δ f inal: the intervals are continuous, the end of an interval corre-
sponds to the beginning of the next one
P[i]. δ initial<P[i]. δ f inal: the interval angles increase monotonically
δ max≥PP[n]. δ f inal: the post-fault intervals include the maximum angle
δ 0 ≤PD[ 1 ]. δ initial: the during-fault intervals include the initial angle
The algorithm inputs the during-fault and post-fault OMIB equivalent models. For
each period, the OMIB model includes its mechanical power, its angle at the beginning
and at the end intervals, and the terms defining its electrical power in each interval. For
ZOOMIB or COOMIB types of the OMIB equivalent, there is only one interval for each
period. The algorithm starts from an initial angle δ 0. It first checks the direction of the
angular deviations. If a ‘backward-swing’ case is detected, as discussed in Section 2.4,
the algorithm negates the sign of electrical power, mechanical power, and OMIB angles.
The search for the critical clearing angle starts from the initial angle δ 0 with an increment

∆ δ. With two loops, for any fault elimination angle angle δ e, the algorithm searches for a
return angle δ ras a δ mat which the sum of the areas become negative. If a δ ris found, the
algorithm increases the δ e. The search continues until finding δ c, as the first δ eafter which
for any δ m≤ δ maxthe sum of the areas is always positive. A ‘potentially stable case’ refers
to a case where the system stability can be maintained by removing the fault at an angle
below the identified δ c. The algorithm can also identify an ‘always stable case’ at which
for δ e= δ 0 system is unstable, and an ‘always stable case’ at which for δ e= δ maxsystem is
stable. Algorithms A3–A5 serve Algorithm A2 as auxiliary functions.

Algorithm A2 Calculation of critical clearing angle of an OMIB model

CCA ( PD , PP )
Input

PD : vector of OMIB during-fault power
· PD [i]. δ i: initial angle of intervali:float
· PD [i]. δ f: final angle of intervali:float
· PD [i].Pc: constant electrical power in intervali:float
· PD [i].Pmax: maximum electrical power in intervali:float
· PD [i].v: angle shift in intervali:float
· PD .Pm: mechanical power:float
PP : vector of OMIB post-fault power
· PP [i]. δ i: initial angle of intervali:float
· PP [i]. δ f: final angle of intervali:float
· PP [i].Pc: constant electrical power in intervali:float
· PP [i].Pmax: maximum electrical power in intervali:float
· PP [i].v: angle shift in intervali:float
· PP .Pm: mechanical power:float
Output
dflag: presents the direction of angular deviations, ‘first-swing’ or ‘backward-swing’:
str
tflag: indicates the type of the case detected, ‘always stable case’, ‘always unstable
case’ or ‘potentially stable case’:str
δ : for a ‘potentially stable case’ δ gives the critical clearing angle, for an ‘always stable
case’ it gives δ max, and for an ‘always unstable case’ it gives δ 0 :float
δ r: for a ‘potentially stable case’ δ gives the return angle, for an ‘always stable case’ it
gives δ max, and for an ‘always unstable case’ it gives δ 0 :float
Algorithm A2 Cont.
Parameter

∆ δ : angle step size:float
δ max: maximum integration limit:float
1:dflag←‘first-swing’
2:direction← 1
3:termination←False
4: δ 0 ← PD [ 1 ]. δ i
5: Pe,Pm= compute-power ( PD , δ 0 )
6: if Pm<Pe then
7: dflag←‘backward-swing’
8: direction←-1
9: PD = negation ( PD )
10: PP = negation ( PP )
11: δ ← δ 0
12: δ r← δ 0
13: δ m← δ +∆ δ
14: while δ < δ max& termination=False do
15: AD= compute-area ( PD , δ 0 , δ )
16: while δ m≤ δ max& termination=False do
17: AP= compute-area ( PP , δ , δ m)
18: if AD+AP≤ 0 then
19: δ c=direction· δ
20: δ r= δ m
21: termination←True
22: δ m← δ m+∆ δ
23: end while
24: if δ m> δ max then
25: if δ c= δ 0 then
26: tflag←‘always unstable case’
27: δ r=direction· δ 0
28: termination←True
29: Pe,Pm= compute-powers ( PP , δ r)
30: if Pm≤Pe then
31: tflag←‘potentially stable case’
32: termination←True
33: δ r=direction· δ r
34: δ ← δ +∆ δ
35: δ m← δ +∆ δ
36: end while
37: if δ ≥ δ max then
38: tflag←‘always stable case’
39: δ c=direction· δ max
40: δ r=direction· δ max
41: return dflag, tflag, δ c, δ r
Algorithm A3 Finding the area betweenPmandPefor desired δ aand δ b

compute-area ( P , δ a, δ b)
Input

P : vector of OMIB power
· P [i]. δ i: initial angle of intervali:float
· P [i]. δ f: final angle of intervali:float
· P [i].Pc: constant electrical power in intervali:float
· P [i].Pmax: maximum electrical power in intervali:float
· P [i].v: angle shift in intervali:float
· P [i].Pm: mechanical power in intervali:float
δ a: desired initial angle:float
δ b: desired final angle:float
Output
A: area:float
1:n←length( P ): number of intervals in considered period
2:j← 1
3: A← 0
4:termination←False
5: for i=1 :n do
6: ifP [i]. δ i≤ δ athen
7: P [i]. δ i← δ a
8: j←i
9: end for
10: while j≤n& termination=False do
11: ifP [j]. δ f> δ b then
12: P [j]. δ f← δ b
13: A+ = ( P [j].Pm− P [j].Pc)( P [j]. δ f− P [j]. δ i) + P [j].Pmax[cos( P [j]. δ f− P [j].v)−
cos( P [j]. δ i− P [j].v)]
14: termination←True
15: A+ = ( P [j].Pm− P [j].Pc)( P [j]. δ f− P [j]. δ i) + P [j].Pmax[cos( P [j]. δ f− P [j].v)−
cos( P [j]. δ i− P [j].v)]
16: j←j+ 1
17: end while
18: return A
Algorithm A4 Finding electrical and mechanical powers at any desired angle δ

compute-power ( P , δ )
Input

P : vector of OMIB power
· P [i]. δ i: initial angle of intervali:float
· P [i]. δ f: final angle of intervali:float
· P [i].Pc: constant electrical power in intervali:float
· P [i].Pmax: maximum electrical power in intervali:float
· P [i].v: angle shift in intervali:float
· P .Pm: mechanical power:float
δ : desired angle:float
Output
Pe: electrical power at the desired angle δ :float
Pm: mechanical power at the desired angle δ :float
1:n←length( P ): number of intervals in considered period
2:j← 1
3:flag←‘not found’
4: Pm= P .Pm
5: while j≤n do
6: ifP [j]. δ i≤ δ < P [j]. δ f then
7: Pe= P [j].Pc+ P [j].Pmaxsin( δ − P [j].v)
8: flag=‘found’
9: end while
10: if flag = ‘not found’ then
11: Pe= P [n].Pc+ P [n].Pmaxsin( δ − P [n].v)
12: return Pe,Pm
Algorithm A5 Returning the negated values of power vector elements

negation ( P )
Input

P : vector of OMIB power
· P [i]. δ i: initial angle of intervali:float
· P [i]. δ f: final angle of intervali:float
· P [i].Pc: constant electrical power in intervali:float
· P [i].Pmax: maximum electrical power in intervali:float
· P [i].v: angle shift in intervali:float
· P .Pm: mechanical power:float
Output
P −: negated vector of power
1: for i=1 :length( P ) do
2: P −[i].Pc=− P [i].Pc
3: P −[i].Pmax=− P [i].Pmax
4: P −[i].v=− P [i].v
5: P −[i]. δ i=− P [i]. δ i
6: P −[i]. δ f=− P [i]. δ f
7: end for
8: P −[− 1 ]. δ f= δ max
9: P −.Pm=− P .Pm
10: returnP −
Algorithm A6 pseudocode details the function to identify a ranked list of critical
generators. The inputs are the type of identifier, the synchronous generators’ data class,
system admittance matrices, and the index of the faulted bus in the admittance matrix,
which helps to find the electrical distance to the fault.
For trajectory criterion, the algorithm uses the Trajectory function to estimate the
angles of individual generators at the observation time as the criterion. For the other two
criteria, the algorithm first calculates generators’ initial acceleration. If the criterion is
acceleration, the initial accelerations are taken as the criterion. Otherwise, the pre-fault
and post-fault distances to fault are estimated to calculate the composite criterion. Finally,
the generators for which the calculated criterion is close to that of the top generator based
on a predefined threshold are selected as critical generators, and a sorted list of them is
outputted.

Algorithm A6 Critical machines identification

CMI ( S , Yˆ
red
dur, Yˆ

red
post, Yˆ pre, Yˆ post,ty pe,f,tobs,te)
Input
S : data of synchronous generators considering the classical model
· S [j].name: generatorjname:str
· S [j].M: generatorjinertia constant:float
· S [j].E: generatorjinternal voltage magnitude:float
· S [j].Pm: generatorjmechanical power:float
· S [j]. δ i [ 1 ]: generatorjinitial angle of the first interval:float
ty pe: type of CMI technique, ‘Acc’ for acceleration criterion, ‘Comp’ for composite
criterion and ‘Traj’ for trajectory criterion:str
Yˆ
red
dur: reduced during-fault system admittance matrix:matrix of complex numbers
Yˆ
red
post: reduced post-fault system admittance matrix:matrix of complex numbers
Yˆ pre: pre-fault system admittance matrix:matrix of complex numbers
Yˆ post: post-fault system admittance matrix:matrix of complex numbers
f: index of the faulted bus in system admittance matrix, set to 1 by default:int
tobs: observation time for the trajectory criterion, set to 0 by default:float
te: fault elimination time for the trajectory criterion, set to 0 by default:float
Output
CM : ranked set of names of synchronous generators identified as critical:set of str
Parameter
f 0 : system base frequency:float
threshold: CMI threshold:float
1: CM ←∅
2:s←length( S ): number of synchronous generators
3: criterion [j]←0,j=1,... ,s
4: ω 0 = 2 π f 0
5: if ty pe==‘Traj’ then
6: t , S. δ i , S. δ f , S. ω i , S. ω f = Trajectory ( S , Yˆ
red
dur, Yˆ
red
post,te,tobs)
7: criterion = S. δ f
8: else
Algorithm A6 Cont.

9: for j=1 :s do :
10: Pe= S [j].E·
s
∑
k= 1
(
S [k].E·| Yˆ
red
dur[j,k]|·cos( S [j]. δ
i [ 1 ]− S [k]. δ i [ 1 ]−∠ Yˆ red
dur[j,k])
)
11: acc= S [ ω j]^0 .M( S [j].Pm−Pe)
12: if ty pe==‘Acc’ then
13: criterion [j] =acc
14: else
15: Zˆpre = inverse of Yˆ pre
16: Zˆpost = inverse of Yˆ post
17: distpre=| Zˆpre [j,j]|+| Zˆpre [f,f]|− 2 | Zˆpre [j,f]|
18: distpost=| Zˆpost [j,j]|+| Zˆpost [f,f]|− 2 | Zˆpost [j,f]|
19: criterion [j] =distpreacc+distpost
20: end for
21: for j=1 :s do :
22: ifcriterion [j]>threshold·max( criterion ) then
23: append S [j].nametoC M
24: end for
25:sort CM in decreasing order of criterion
26: returnCM
Algorithm A7 pseudocode details the function to form different candidate CCs and
NCs. This pseudocode represents a simple method among others. Forcmcritical machines,
the algorithm selectscmcandidate CCs composed of the first from the top, the first two
from the top, ..., up to allcmmachines in the CC set. It outputs the set of candidate CCs
and the set of candidate NCs.

Algorithm A7 Critical clusters formation

CCF ( S. name , CM )
Input

S. name : set of names of synchronous generators:set of str
CM : ranked set of names of synchronous generators identified as critical:set of str
Output
SCC : sets of CC:sets of str
SNC : sets of NC:sets of str
1:cm←length( CM ): number of critical machines
2: for j=1 :cm do :
3: SCC [j]= CM [1:j]
4: SNC [j]= S. name not in SCC [j]
5: end for
6: returnSCC , SNC
Algorithm A8 pseudocode details the function to estimate the time associated with a
desired angle for the OMIB model. The function angle-to-time updates the time and OMIB
angular speed interval by interval up to reaching the desired time associated to the desired
angle. This function relies on Algorithm A9 pseudocode which presents the GTS function.
For each interval, this function employs the Taylor series equations to find the time and
angular speed associated to a desired angle using the interval initial values.

Algorithm A8 Finding the time and angular speed associated to a desired angle for the
OMIB model using the global Taylor series

angle-to-time ( P ,M, δ des, δ i, ω i)
Input

P : OMIB power
· P [i]. δ i: initial angle of intervali:float
· P [i]. ω i: initial angular speed of intervali:float
· P [i].Pc: constant electrical power in intervali:float
· P [i].Pmax: maximum electrical power in intervali:float
· P [i].v: angle shift in intervali:float
· P .Pm: mechanical power:float
M: OMIB inertia constant:float
δ des: OMIB desired angle:float
δ i: initial angle for Taylor series initialization:float
ω i: initial angular speed for Taylor series initialization:float
Output
tdes: desired time at the given desired angle:float
ω des: desired angular speed at the given desired angle:float
1:n←length( P ): number of intervals in considered period
2: for i=1 :n do
3: ifP [i]. δ f> δ des then
4: tdes, ω des= GTS ( P ,M, δ des, δ i, ω i,i)
5: else if i<n then
6: t[i+ 1 ], P [i+ 1 ]. ω i= GTS ( P ,M, P [i+ 1 ]. δ i, δ i, ω i,i)
7: δ i= P [i+ 1 ]. δ i
8: ω i= P [i+ 1 ]. ω i
9: end for
10: return tdes, ω des
Algorithm A10 pseudocode details the function to estimate the generators’ angle
trajectory in time. The function Trajectory updates the generator angles interval by interval
up to a final time. This function relies on the function ITS , detailed in Algorithm A11
pseudocode, which employs Taylor series equations for each individual generator to find
a desired angle and angular speed in an interval at a desired time and using the initial
values.

Algorithm A9 Global Taylor series to find the OMIB time and angular speed associated
with a desired angle, starting from an initial angle, time and angular speed

GTS ( P ,M, δ des, δ i, ω i,i)
Input

P : OMIB power
· P [i].Pc: constant electrical power in intervali:float
· P [i].Pmax: maximum electrical power in intervali:float
· P [i].v: angle shift in intervali:float
· P .Pm: mechanical power:float
M: OMIB inertia constant:float
δ des: OMIB desired angle:float
δ i: initial angle for Taylor series initialization:float
ω i: initial angular speed for Taylor series initialization:float
i: interval number at which the Taylor series equations are initialized:int
Output
tdes: desired time at the given desired angle:float
ω des: desired angular speed at the given desired angle:float
Parameter
f 0 : system base frequency:float
1: ω 0 = 2 π f 0
2: Pe= P [i].Pc+ P [i].Pmax·sin( δ i− P [i].v)
3: dd γδ =− ω M^0 P [i].Pmax·cos( δ i− P [i].v)
4: d
(^2) γ
d δ^2 =
ω 0
M P [i].Pmax·sin( δ i− P [i].v)
5: d
(^3) γ
d δ^3 =−
d γ
d δ
6: ddt δ = ω 0 · ω i
7: d
(^2) δ
dt^2 =
ω 0
M( P .Pm−Pe)
8: d
(^3) δ
dt^3 =
d γ
d δ ·
d δ
dt
9: d
(^4) δ
dt^4 =
d^2 γ
d δ^2 ·(
d δ
dt)
(^2) +d γ
d δ ·
d^2 δ
dt^2
10: d
(^5) δ
dt^5 =
d^3 γ
d δ^3 ·(
d δ
dt)
(^3) +d γ
d δ ·
d^3 δ
dt^3 +^3
d^2 γ
d δ^2 ·
d^2 δ
dt^2 ·
d δ
dt
11:tdes=positive real root of

(
( δ i− δ des) +^12 d
(^2) δ
dt^2 t
(^2) +^1
6
d^3 δ
dt^3 t
(^3) +^1
24
d^4 δ
dt^4 t

4 )
12: ω des= ω i+ ω^10
(d (^2) δ
dt^2 tdes+
1
2
d^3 δ
dt^3 tdes
(^2) + 1
6
d^4 δ
dt^4 tdes
(^3) + 1
24
d^5 δ
dt^5 tdes

4 )
13: return tdes, ω des
Algorithm A12 clarifies the steps of the basic scheme for estimations of CCT with
EEAC. The algorithm inputs the synchronous generators’ data, the admittance matrices, the
type of the OMIB equivalent which can be of the ZOOMIB or COOMIB type for the basic
EEAC, the type of CMI, and the index of the faulted bus if the CMI criterion is ’composite’.
Besides the inputs, the algorithm also requires certain parameters: system base frequency
as a constant parameter, and variable parameters including CMI threshold, angle step size,
and maximum integration limit for CCA function. The algorithm starts by identifying
the critical generators and forming a set ofcmCCs (SCC) and a set of NCs (SNC). It then
evaluates each pair of CC and NC. For each pair it first forms the pre-fault, during-fault
and post-fault OMIB equivalents. The initial angle δ 0 is defined as the intersection point of
the pre-fault OMIB electrical power and the mechanical power. Then, the boundaries of
the OMIB equivalents of during-fault and post-fault states are set to δ 0 and δ max.

Algorithm A10 Finding synchronous generators’ angle trajectory in time using an individ-
ual Taylor series

Trajectory ( S , Yˆ
red
dur, Yˆ

red
post,te,tend)
Input
S : data of synchronous generators considering the classical model
· S [j].M: generatorjinertia constant:float
· S [j].E: generatorjinternal voltage magnitude:float
· S [j].Pm: generatorjmechanical power:float
· S [j]. δ i [ 1 ]: generatorjinitial angle of the first interval:float
Yˆ
red
dur: reduced during-fault system admittance matrix:matrix of complex numbers
Yˆ
red
post: reduced post-fault system admittance matrix:matrix of complex numbers
te: fault elimination time:float
tend: end of trajectory time span:float
Output
· S. δ f : generators’ final angle of all intervals:vectors of float
· S. ω f : generators’ final angular speed of all intervals:vectors of float

· S. δ i : generators’ initial angle of all intervals:vector of float
· S. ω i : generators’ initial angular speed of all intervals:vectors of float
· t : intervals time instants:vectors of float

Parameter
d: number of during-fault period intervals:int
p: number of post-fault period intervals:int
1: t [ 1 ]← 0
2:s←length( S ): number of synchronous generators
3: S [j]. ω i [ 1 ]←0,j=1,... ,s
4: for i=1 :d do
5: t [i+ 1 ] = t [i] +te/d
6: S [j]. δ f [i], S [j]. ω f [i]= ITS ( S , Yˆ
red
dur,t[i+^1 ],i)
7: S [j]. δ i [i+ 1 ]← S [j]. δ f [i],j=1,... ,s
8: S [j]. ω i [i+ 1 ]← S [j]. ω f [i],j=1,... ,s
9: end for
10: for i=d+1 :d+p do
11: t [i+ 1 ] = t [i] + (tend−te)/p
12: S [j]. δ f [i], S [j]. ω f [i]= ITS ( S , Yˆ
red
post,t[i+^1 ],i)
13: S [j]. δ i [i+ 1 ]← S [j]. δ f [i],j=1,... ,s
14: S [j]. ω i [i+ 1 ]← S [j]. ω f [i],j=1,... ,s
15: end for
16: returnS. δ i , S. δ f , S. ω i , S. ω f , t
Algorithm A11 Individual Taylor series to find generators’ angle and angular speed at a
desired time, starting from an initial angle and angular speed

ITS ( S , Yˆ
red
,tdes,i)
Input

S : data of synchronous generators considering the classical model
· S [j].M: generatorjinertia constant:float
· S [j].E: generatorjinternal voltage magnitude:float
· S [j].Pm: generatorjmechanical power:float
· S [j]. δ i [i]: generatorjinitial angle of intervali:float
· S [j]. ω i [i]: generatorjinitial angular speed of intervali:float
Yˆ
red
: reduced system admittance matrix:matrix of complex numbers
tdes: desired time:float
i: interval number at which the Taylor series equations are initialized:int
Output
· δ des : synchronous generators’ angle at the given desired time:vector of float
· ω des : synchronous generators’ angular speed at the given desired time:vector of float

Parameter
f 0 : system base frequency:float
1:s←length( S ): number of synchronous generators
2: ω 0 = 2 π f 0
3: for j=1 :s do :
4: Pe= S [j].E·
s
∑
k= 1
(
S [k].E·| Yˆ
red
[j,k]|·cos( S [j]. δ i [i]− S [k]. δ i [i]−∠ Yˆ
red
[j,k])
)
5: dd γδ = S [ ω j]^0 .M S [j].E·
s
∑
k= 1
(
S [k].E·| Yˆ
red
[j,k]|·sin( S [j]. δ i [i]− S [k]. δ i [i]−∠ Yˆ
red
[j,k])
)
6: d
(^2) γ
d δ^2 =
ω 0
S [j].M S [j].E·
s

∑
k= 1
(
S [k].E·| Yˆ
red
[j,k]|·cos( S [j]. δ i [i]− S [k]. δ i [i]−∠ Yˆ
red
[j,k])
)
7: d
(^3) γ
d δ^3 =−
d γ
d δ
8: ddt δ = ω 0 · S [j]. ω i [i]
9: d
(^2) δ
dt^2 =
ω 0
S [j].M( S [j].Pm−Pe)
10: d
(^3) δ
dt^3 =
d γ
d δ ·
d δ
dt
11: d
(^4) δ
dt^4 =
d^2 γ
d δ^2 ·(
d δ
dt)
(^2) +d γ
d δ ·
d^2 δ
dt^2
12: d
(^5) δ
dt^5 =
d^3 γ
d δ^3 ·(
d δ
dt)
(^3) +d γ
d δ ·
d^3 δ
dt^3 +^3
d^2 γ
d δ^2 ·
d^2 δ
dt^2 ·
d δ
dt
13: δ des [j] = S [j]. δ i [i] +ddt δ tdes+^12 d
(^2) δ
dt^2 t
des^2 +^1
6
d^3 δ
dt^3 t
des^3 +^1
24
d^4 δ
dt^4 t
des^4
14: ω des [j] = S [j]. ω i [i] + ω^10
(d (^2) δ
dt^2 t
des+^1
2
d^3 δ
dt^3 t
des^2 +^1
6
d^4 δ
dt^4 t
des^3 +^1
24
d^5 δ
dt^5 t
des^4 )
15: end for
16: return δ des , ω des
Having the OMIB equivalents defined within δ 0 to δ max, CCA is applied to find the
CCA and the return angle of the pair under consideration. Then,tcand ω care calculated
as the time to reach δ cfrom δ 0 , and the angular speed at δ c. Similarly,trand ω rcan be
calculated as the time to reach δ rfrom δ c, and the angular speed at δ r. After repeating these
steps for each pair, the true CC and the true NC are identified as the ones with minimum
tc. The algorithm finally returns the CCT, the identified clusters, the CCA and the angular
speed, and the observation time as the time to reach δ rfrom δ 0.
Algorithm A13 clarifies the steps of the third refinement scheme for estimations of
CCT with EEAC. The steps of the other two refinement schemes are not presented due to
their similarity.

Algorithm A12 Basic scheme for EEAC

basic-eeac ( S , Yˆ
red
dur, Yˆ

red
post, Yˆ pre, Yˆ post,ty peOM I B,ty peC M I,f)
Input
S : data of synchronous generators considering the classical model
· S [j].name: generatorjname:str
· S [j].M: generatorjinertia constant:float
· S [j].E: generatorjinternal voltage magnitude:float
· S [j].Pm: generatorjmechanical power:float
· S [j]. δ i : generatorjinitial angle:float
Yˆ
red
dur: reduced during-fault system admittance matrix:matrix of complex numbers
Yˆ
red
post: reduced post-fault system admittance matrix:matrix of complex numbers
Yˆ pre: pre-fault system admittance matrix:matrix of complex numbers
Yˆ post: post-fault system admittance matrix:matrix of complex numbers
ty peOM I B: type of OMIB equivalent model, ‘ZOOMIB’ for zero offset OMIB, and
‘COOMIB’ for constant offset OMIB:str
ty peC M I: type of CMI technique, ‘Acc’ for acceleration criterion, and ‘Comp’ for
composite criterion:str
f: index of the faulted bus in system admittance matrix for ’composite’ CMI, set to 1
by default:int
Output
CCT: critical clearing time:float
CC : set of names of synchronous generators identified as critical:set of str
NC : set of names of synchronous generators identified as non-critical:set of str
δ c: OMIB critical clearing angle:float
ω c: OMIB angular speed at critical clearing angle:float
tobs: observation time (the time to reach the return angle):float
Parameter
f 0 : system base frequency:float
threshold: CMI threshold:float
∆ δ : angle step size:float
δ max: OMIB maximum integration limit:float
1:s←length( S ): number of synchronous generators
2: CM = CMI ( S , Yˆ
red
dur, Yˆ
red
post, Yˆ pre, Yˆ post, ‘Acc’)
3: SCC , SNC = CCF ( S. name , CM )
4:cm←length( CM ): number of critical sets
5: for k=1 :cm do
6: CC = SCC [k]
7: NC = SNC [k]
8: PO ,M= OM IB ( S , Yˆ
pre
red, CC , NC , ‘ZOOM I B’)
9: PD ,M= OM IB ( S , Yˆ
dur
red, CC , NC , ‘ZOOM I B’)
10: PP ,M= OM IB ( S , Yˆ
post
red, CC , NC , ‘ZOOM I B’)
11: δ 0 =sin−^1
( PO [ 1 ].Pm− PO [ 1 ].Pc
PO [ 1 ].Pmax
)
+ PO [ 1 ].v
12: PD [− 1 ]. δ f= δ max
13: PP [− 1 ]. δ f= δ max
14: PD [ 1 ]. δ i= δ 0
15: PP [ 1 ]. δ i= δ 0
Algorithm A12 Cont.

16: dflag, tflag, δ c [k], δ r [k]= CCA ( PD , PP )
17: tc [k], ω c [k]= angle-to-time ( PD ,M, δ c [k], δ 0 , 0)
18: tr [k], ω r [k]= angle-to-time ( PP ,M, δ r [k], δ c [k], ω c [k])
19: end for
20:CCT=min( tc )
21:index = index of CCT in tc
22:True-CC= SCC [index]
23:True-NC= SNC [index]
24: δ c= δ c [index]
25: ω c= ω c [index]
26:tr= tr [index]
27:tobs=CCT+tr
28: return CCT, True-CC, True-NC, δ c, ω c,tobs
Algorithm A13 Third refinement scheme for EEAC

refinement-3 (CCT,CC,NC, δ c, ω c,tobs)
Input

CCT: critical clearing time:float
CC : set of names of synchronous generators identified as critical:set of str
NC : set of names of synchronous generators identified as non-critical:set of str
δ c: OMIB critical clearing angle:float
ω c: OMIB angular speed at critical clearing angle:float
tobs: observation time (the time to reach the return angle):float
Output
CCT: critical clearing time:float
CC : set of names of synchronous generators identified as critical:set of str
NC : set of names of synchronous generators identified as non-critical:set of str
δ c: OMIB critical clearing angle:float
ω c: OMIB angular speed at critical clearing angle:float
tobs: observation time (the time to reach the return angle):float
Parameter
f 0 : system base frequency:float
threshold: CMI threshold:float
∆ δ : angle step size:float
δ max: OMIB maximum integration limit:float
d: number of during-fault intervals for DOMIB or for generators’ angle trajectory
calculation:float
p: number of OMIB post-fault intervals for DOMIB or for generators’ angle trajectory
calculation:float
1:s←length( S ): number of synchronous generators
2: CM = CMI ( S , Yˆ
red
dur, Yˆ
red
post, Yˆ pre, Yˆ post, ‘Traj’ ,tobs)
3: SCC , SNC = CCF ( S. name , CM )
4:cm←length( CM ): number of critical sets
5: for k=1 :cm do
6: CC = SCC [k]
7: NC = SNC [k]
8: PO ,M= OM IB ( S , Yˆ
pre
red, CC , NC , ‘ZOOMIB’)
9: PD ,M= OM IB ( S , Yˆ
dur
red, CC , NC , ‘ZOOMIB’)
Algorithm A13 Cont.

10: PP ,M= OM IB ( S , Yˆ
post
red, CC , NC , ‘ZOOMIB’)
11: δ 0 =sin−^1
( PO [ 1 ].Pm− PO [ 1 ].Pc
PO [ 1 ].Pmax
)
+ PO [ 1 ].v
12: PD [− 1 ]. δ f= δ max
13: PP [− 1 ]. δ f= δ max
14: PD [ 1 ]. δ i= δ 0
15: PP [ 1 ]. δ i= δ 0
16: dflag, tflag, δ c, δ r= CCA ( PD , PP )
17: tc, ω c= angle-to-time ( PD ,M, δ c, δ 0 , 0)
18: tr, ω r= angle-to-time ( PP ,M, δ r, δ c, ω c)
19: tobs=tc+tmax
20: S. δ i , S. δ f , S. ω i , S. ω f , t = Trajectory ( S , Yˆ
red
dur, Yˆ
red
post,tc,tobs)
21: PO ,M= OM IB ( S , Yˆ
pre
red, CC , NC , ‘COOMIB’)
22: PD ,M= OM IB ( S , Yˆ
dur
red, CC , NC , ‘DOMIB’,(1,d))
23: PP ,M= OM IB ( S , Yˆ
post
red, CC , NC , ‘DOMIB’,(d+1,d+p))
24: δ 0 =sin−^1
( PO [ 1 ].Pm− PO [ 1 ].Pc
PO [ 1 ].Pmax
)
+ PO [ 1 ].v
25: PD [− 1 ]. δ f= δ max
26: PP [− 1 ]. δ f= δ max
27: PD [ 1 ]. δ i= δ 0
28: PP [ 1 ]. δ i= δ 0
29: dflag, tflag, δ c [k], δ r [k]= CCA ( PD , PP )
30: tc [k], ω c [k]= angle-to-time ( PD ,M, δ c [k], δ 0 , 0)
31: tr [k], ω r [k]= angle-to-time ( PP ,M, δ r [k], δ c [k], ω c [k])
32: end for
33:CCT=min( tc )
34:index = index of CCT in tc
35:True-CC= SCC [index]
36:True-NC= SNC [index]
37: δ c= δ c [index]
38: ω c= ω c [index]
39:tr= tr [index]
40:tobs=CCT+tr
41: return CCT, True-CC, True-NC, δ c, ω c,tobs
Appendix C. Taylor Series Expansion

The following subsections provide the Taylor series equations for the OMIB equivalent
model and for an individual generator.

Appendix C.1. Taylor Series for OMIB Equivalent

A Taylor series is a series expansion of a function about a point. A one-dimensional
Taylor series of a differentiable functionf(x)about a pointx=ais given by:

f(x) =f(a) +
f′(a)
1!
(x−a) +
f′′(a)
2!
(x−a)^2 +
f′′′(a)
3!
(x−a)^3 +... (A19)
The series is employed to relate the rotor angle evolution of OMIB model with time.
Forming the Taylor series about an initial angle δ i(corresponding to timeti) and truncating
it after thet^4 term yields:

δ (t) = δ
∣
∣
∣
∣
ti
+
d δ
dt
∣
∣
∣
∣
ti
t+
1
2
d^2 δ
dt^2
∣
∣
∣
∣
ti
t^2 +
1
6
d^3 δ
dt^3
∣
∣
∣
∣
ti
t^3 +
1
24
d^4 δ
dt^4
∣
∣
∣
∣
ti
t^4 (A20)
This polynomial equations can help to estimate the time to reach a predefined angle
from δ i. The derivatives of δ with respect to time can be obtained as follows:

d δ
dt
∣
∣
∣
∣
ti
= ω 0 ω
∣
∣
∣
∣
ti
(A21)
d^2 δ
dt^2
∣
∣
∣
∣
ti
= γ
∣
∣
∣
∣
ti
=
ω 0
M
(Pm−Pe
∣
∣
∣
∣
ti
) (A22)
d^3 δ
dt^3
∣
∣
∣
∣
ti
=
d γ
dt
∣
∣
∣
∣
ti
=
d γ
d δ
∣
∣
∣
∣
ti
(
d δ
dt
∣
∣
∣
∣
ti
) (A23)
d^4 δ
dt^4
∣
∣
∣
∣
ti
=
d^2 γ
dt^2
∣
∣
∣
∣
ti
=
d^2 γ
d δ^2
∣
∣
∣
∣
ti
(
d δ
dt
∣
∣
∣
∣
ti
)^2 + γ
∣
∣
∣
∣
t=ti
d γ
d δ
∣
∣
∣
∣
ti
(A24)
where, by considering the sinusoidal form of Equation 14 forPe, we have:

d γ
d δ
∣
∣
∣
∣
ti
=−
ω 0
M
Pmaxcos( δ
∣
∣
∣
∣t
i−v)
d^2 γ
d δ^2
∣
∣
∣
∣
ti
=
ω 0
M
Pmaxsin( δ
∣
∣
∣
∣
ti
−v)
Atti= 0 +, the angular speed ω =0 and the polynomial of Equation (A20) can be
solved to estimate the time to reach a predefined angle from δ i. However, as can be seen in
Equation (A21), for the next time intervals, ω should also be estimated. This can be done
by forming a Taylor series for ω :

ω (t) = ω
∣
∣
∣
∣
ti
+
d ω
dt
∣
∣
∣
∣
ti
t+
1
2
d^2 ω
dt^2
∣
∣
∣
∣
ti
t^2 +
1
6
d^3 ω
dt^3
∣
∣
∣
∣
ti
t^3 +
1
24
d^4 ω
dt^4
∣
∣
∣
∣
ti
t^4 (A25)
The derivatives of ω with respect to time can be obtained as follows:
d ω
dt
∣
∣
∣
∣
ti
=
1
ω 0
γ
∣
∣
∣
∣
ti
=
1
ω 0
(Pm−Pe
∣
∣
∣
∣
ti
) (A26)
d^2 ω
dt^2
∣
∣
∣
∣
ti
=
1
ω 0
d γ
d δ
∣
∣
∣
∣
ti
d δ
dt
∣
∣
∣
∣
ti
(A27)
d^3 ω
dt^3
∣
∣
∣
∣
ti
=
1
ω 0
(
d^2 γ
d δ^2
∣
∣
∣
∣
ti
(
d δ i
dt
∣
∣
∣
∣
ti
)^2 +
d γ
d δ
∣
∣
∣
∣
ti
(
d^2 δ
dt^2
∣
∣
∣
∣
ti
)
)
(A28)
d^4 ω
dt^4
∣
∣
∣
∣
ti
=
1
ω 0
(
d^3 γ
d δ^3
∣
∣
∣
∣
ti
(
d δ
dt
∣
∣
∣
∣
ti
)^3
+
d γ
d δ
∣
∣
∣
∣
ti
d^3 δ
dt^3
∣
∣
∣
∣
ti
+ 3
d^2 γ
d δ^2
∣
∣
∣
∣
ti
d^2 δ
dt^2
∣
∣
∣
∣
ti
d δ
dt
∣
∣
∣
∣
ti
) (A29)
wheredd γδ i

∣
∣
∣
∣
t=ta
andd
(^2) γ i
d δ^2

∣
∣
∣
∣
t=ta
can be calculated using the equations below Equations (A24)
andd

(^3) γ
d δ^3

∣
∣
∣
∣
ti
=−dd γδ
∣
∣
∣
∣
ti
.
To obtain the evolution of OMIB δ and ω with time, Equations (A20) and (A25) should
be updated together. The obtained values at each time instant should be employed to
initialize the Taylor series for the next time step.

Appendix C.2. Taylor Series for an Individual Generator

Expanding the Taylor series about the generatorkinitial angle δ k, at timeti, and
truncating it after thet^4 term, we have:

δ k(t) = δ k
∣
∣
∣
∣
ti
+
d δ k
dt
∣
∣
∣
∣
ti
t+
1
2
d^2 δ k
dt^2
∣
∣
∣
∣
ti
t^2 +
1
6
d^3 δ k
dt^3
∣
∣
∣
∣
ti
t^3 +
1
24
d^4 δ k
dt^4
∣
∣
∣
∣
ti
t^4 (A30)
The derivatives of δ kcan be obtained as follows:
d δ k
dt
∣
∣
∣
∣
ti
= ω 0 ω k
∣
∣
∣
∣
ti
(A31)
d^2 δ k
dt^2
∣
∣
∣
∣
ti
= γ k
∣
∣
∣
∣
ti
=
ω 0
Mk
(Pmk−Pek
∣
∣
∣
∣
ti
) (A32)
d^3 δ k
dt^3
∣
∣
∣
∣
ti
=
d γ k
d δ
∣
∣
∣
∣
ti
d δ k
dt
∣
∣
∣
∣
ti
(A33)
d^4 δ k
dt^4
∣
∣
∣
∣
ti
=
d^2 γ k
d δ^2
∣
∣
∣
∣
ti
(
d δ k
dt
∣
∣
∣
∣
ti
)^2 +
d γ k
d δ
∣
∣
∣
∣
ti
(
d^2 δ k
dt^2
∣
∣
∣
∣
ti
) (A34)
where, considering the classical model for synchronous generators we have:

Pek
∣
∣
∣
∣
ti
=
n
∑
j= 1
[EkEjyijcos( δ k
∣
∣
∣
∣
ti
− δ j
∣
∣
∣
∣
ti
− θ kj)]
d γ k
d δ
∣
∣∣
∣
ti
=
ω 0
Mk
n
∑
j= 1
[EkEjykjsin( δ k
∣
∣∣
∣
ti
− δ j
∣
∣∣
∣
ti
− θ kj)]
d^2 γ k
d δ^2
∣
∣
∣
∣
ti
=
ω 0
Mk
n
∑
j= 1
[EkEjykjcos( δ k
∣
∣
∣
∣
ti
− δ j
∣
∣
∣
∣
ti
− θ kj)]
wherenis the number of generators.
Atti= 0 +, the angular speed ω k=0 and the polynomial of Equation (A30) can be
solved to estimate δ kfor the next time instant. However, to obtain the generator angles for
the next intervals, the generators’ angular speed at their initial time needs to be estimated.
The Taylor series expansion of ω kcan be formed to obtain the evolution of each generator
angular speed with time:

ω k(t) = ω k
∣
∣
∣
∣
ti
+
d ω k
dt
∣
∣
∣
∣
ti
t+
1
2
d^2 ω k
dt^2
∣
∣
∣
∣
ti
t^2 +
1
6
d^3 ω k
dt^3
∣
∣
∣
∣
ti
t^3 +
1
24
d^4 ω k
dt^4
∣
∣
∣
∣
ti
t^4 (A35)
The derivatives of ω kcan be obtained as follows:
d ω k
dt
∣
∣
∣
∣
ti
=
1
ω 0
γ k
∣
∣
∣
∣
ti
=
1
M
(Pmk−Pek
∣
∣
∣
∣
ti
) (A36)
d^2 ω k
dt^2
∣
∣
∣
∣
ti
=
1
ω 0
d γ k
d δ
∣
∣
∣
∣
ti
d δ k
dt
∣
∣
∣
∣
ti
(A37)
d^3 ω k
dt^3
∣
∣
∣
∣
ti
=
1
ω 0
(
d^2 γ k
d δ^2
∣
∣
∣
∣
ti
(
d δ k
dt
∣
∣
∣
∣
ti
)^2 +
d γ k
d δ
∣
∣
∣
∣
ti
(
d^2 δ k
dt^2
∣
∣
∣
∣
ti
)
)
(A38)
d^4 ω k
dt^4
∣
∣
∣
∣
ti
=
1
ω 0
(
d^3 γ k
d δ^3
∣
∣
∣
∣
ti
(
d δ k
dt
∣
∣
∣
∣
ti
)^3
+
d γ k
d δ
∣
∣
∣
∣
ti
d^3 δ k
dt^3
∣
∣
∣
∣
ti
+ 3
d^2 γ k
d δ^2
∣
∣
∣
∣
ti
d^2 δ k
dt^2
∣
∣
∣
∣
ti
d δ k
dt
∣
∣
∣
∣
ti
) (A39)
wheredd γδ k
∣
∣
∣
∣
ti
andd
(^2) γ k
d δ^2

∣
∣
∣
∣
ti
can be calculated as described below Equation (A34) andd
(^3) γ k
d δ^3

∣
∣
∣
∣
ti
=
−dd γδ k
∣
∣
∣
∣
ti
.
To obtain the evolution of δ kand ω kwith time, Equations (A30) and (A35) should be
updated together. The obtained values at each time instant should be employed to initialize
the Taylor series for the next time step.
References

Pavella, M.; Ernst, D.; Ruiz-Vega, D.Transient Stability of Power Systems: a Unified Approach to Assessment and Control, 1st ed.;
Springer Science & Business Media: New York, NY, USA, 2012.
Dahl, O.G.C.Electric Circuits; Theory and Applications, 1st ed.; McGraw-Hill: New York, NY, USA, 1938.
Skilling, H.H.; Yamakawa, M.H. A graphical solution of transient stability.Electrical Eng. 1940 , 59 , 462–465. [CrossRef]
Kimbark, E.W.Power System Stability, 1st ed.; John Wiley & Sons: New York, NY, USA, 1948.
Xue, Y.; Rousseaux, P.; Gao, Z.; Belhomme, R.; Euxible, E.; Heilbronn, B. A new decomposition method and direct criterion for
trasient stability assessment of large-scale electric power systems. In Proceedings of the IMACS-IFAC Symposium on Modelling
and Simulation for Control of Lumped and Distributed Parameter Systems, Lille, France, 3–6 June 1986.
Xue, Y.; Van Cutsem, T.; Pavella, M. A simple direct method for fast transient stability assessment of large power systems.IEEE
Trans. Power Syst. 1988 , 3 , 400–412. [CrossRef]
Xue, Y.; Van Custem, T.; Pavella, M. Extended equal area criterion justifications, generalizations, applications.IEEE Trans. Power
Syst. 1989 , 4 , 44–52. [CrossRef]
Xue, Y.; Pavella, M. Extended equal-area criterion: An analytical ultra-fast method for transient stability assessment and
preventive control of power systems.Int. J. Electrical Power Energy Syst. 1989 , 11 , 131–149. [CrossRef]
Xue, Y.; Wehenkel, L.; Belhomme, R.; Rousseaux, P.; Pavella, M.; Euxibie, E.; Heilbronn, B.; Lesigne, J.-F. Extended equal area
criterion revisited (EHV power systems).IEEE Trans. Power Syst. 1992 , 7 , 1127–1130. [CrossRef]
Xue, Y.; Rousseaux, P.; Gao, Z.; Belhomme, R.; Euxible, E.; Heilbronn, B. Dynamic extended equal-area criterion. Part I:
Basic formulation. Part II: Recent extensions. In Proceedings of the Athens Power Tech, Athens, Greece, 5–8 September 1993;
pp. 889–900.
Xue, Y.; Pavella, M. Extended equal area criterion justifications, generalizations, applications.IEE Proc. C 1993 , 140 , 481–489.
Xue, Y.; Yu, Y.; Li, J.; Gao, A.; Ding, C.; Xue, F.; Wang, L.; Morison, G.K.; Kundur, P. A New Tool for Dynamic Security Assessment
of Power Systems. In Proceedings of the IFAC/CIGRE Symposium on Control of Power Systems and Power Plants; Beijing,
China, 12–15 August 1989; pp. 389–393. [CrossRef]
Zhang, Y. Hybrid Extended EqualArea Criterion: A General Method for Transient Stability Assessment of Multimachine Power
Systems. Ph.D. Thesis, University of Liége, Liége, Belgium, February 1995.
Zhang, Y.; Wehenkel, L.; Rousseaux, P.; Pavella, M. SIME: A Hybrid Approach to Fast Transient Stability Assessment and
Contingency Selection.J. EPES 1997 , 119 , 195–208. [CrossRef]
Zhang, Y.; Wehenkel, L.; Pavella, M. SIME: Method for RealTime Transient Stability Emergency Control. In Proceedings of the
CPSPP’97, IFAC/CIGRE Symp on Control of Power Systems and Power Plants, Beijing, China, 18–21 August 1997; pp. 673–678.
Zhang, Y.; Wehenkel, L.; Pavella, M. SIME: A Comprehensive Approach to Fast Transient Stability Assessment.Trans. IEE Jpn.
1998 ,118B, 127–133. [CrossRef]
Ernst, D.; Bettiol, A.L.; RuizVega, D.; Wehenkel, L.; Pavella, M. Compensation Schemes for Transient Stability Assessment and
Control. In Proceedings of the LESCOPE’98, Halifax, NS, Canada, 7–9 June 1998; pp. 225–230.
Ernst, D.; Bettiol, A.L.; Zhang, Y.; Wehenkel, L.; Pavella, M. RealTime Transient Stability Emergency Control of the South-Southeast
Brazilian System. In Proceedings of the SEPOPE’98, Curitiba, Brazil, 1998; pp. 1–9. Available online: https://www.researchgate.
net/publication/224007124_Real-Time_Transient_Stability_Emergency_Control_of_the_South-Southeast_Brazilian_System (ac-
cessed on 30 September 2021).
Ernst, D.; RuizVega, D.; Pavella, M. Preventive and Emergency Transient Stability Control. In Proceedings of the SEPOPE’2000,
Curitiba, Brazil, 21–26 May 2000; pp. 1–10. Available online: https://www.researchgate.net/publication/229003465_Preventive_
and_emergency_transient_stability_control (accessed on 30 September 2021).
Ernst, D.; Ruiz-Vega, D.; Pavella, M.; Hirsch, P.; Sobajic, D. SIME: A Unified Approach to Transient Stability Contingency Filtering,
Ranking and Assessment.IEEE Trans. Power Syst. 2001 , 16 , 435–443. [CrossRef]
McNabb, P.; Bialek, J. A priori transient stability indicator of islanded power systems using extended equal area criterion. In
Proceedings of the IEEE Power and Energy Society General Meeting, San Diego, CA, USA, 22–26 July 2012.
Chen, C.; Tang, A.; Huang, Y.; Zheng, X.; Xu, Q. The Research of DPFC Considering EEAC. In Proceedings of the International
Conference on Industrial Informatics-Computing Technology, Intelligent Technology, Industrial Information Integration, Wuhan,
China, 2–3 December 2017; pp. 246–249. [CrossRef]
Chenlu, W.; Xiaohua, Z.; Yuan, Z.; Chen, L.; Dezhuang, M. Impact identification of DFIG model on transient security analysis in
power system.Energy Rep. 2020 , 6 , 307–311. [CrossRef]
Li, Y.; Huang, S.; Li, H.; Zhang, J. Application of phase sequence exchange in emergency control of a multi-machine system.Int. J.
Electr. Power Energy Syst. 2020 , 121 , 106136. [CrossRef]
Li, F.; Wang, Q.; Tang, Y.; Xu, Y. An integrated method for critical clearing time prediction based on a model-driven and ensemble
cost-sensitive data-driven scheme.Int. J. Electr. Power Energy Syst. 2021 , 125 , 106513. [CrossRef]
Xue, Y.; Zhang, Y. Practical and Flexible Incorporation of AVR into Extended Equal Area Criterion.IFAC Proc. Vol. 1993 , 26 ,
753–759. [CrossRef]
Xue, Y.; Zhang, Y. Direct transient stability assessment with two-axis generator model.IFAC Proc. Vol. 1990 , 23 , 7–12. Available
online: https://www.sciencedirect.com/science/article/pii/S1474667017513907 (accessed on 30 September 2021).
Xue, Y.; Sun, K. Generalized Equal Area Criterion for Transient Stability Analysis. In Proceedings of the 4th IEEE Conference on
Energy Internet and Energy System Integration, Wuhun, China, 30 October–1 November 2020; pp. 2363–2368.
Tao, Q.; Xue, Y.; Li, C. Transient Stability Analysis of AC/DC System Considering Electromagnetic Transient Model. In
Proceedings of the IEEE Innovative Smart Grid Technologies, Chengdu, China, 21–24 May 2019; pp. 313–317.
Pavella, M.; Murthy, P.G.Transient Stability of Power Systems, Theory and Practice, 1st ed.; John Wiley & Sons: Chichester, UK, 1993.
Tavora, C.J.; Smith, O.J.M. Characterization of equilibrium and stability in power systems.IEEE Trans. Power App. Syst. 1972 , 3 ,
1127–1130. [CrossRef]