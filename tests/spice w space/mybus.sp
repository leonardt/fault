* NMOS/PMOS models from
* https://people.rit.edu/lffeee/SPICE_Examples.pdf

.model EENMOS NMOS (VTO=0.4 KP=432E-6 GAMMA=0.2 PHI=.88)
.model EEPMOS PMOS (VTO=-0.4 KP=122E-6 GAMMA=0.2 PHI=.88)

.subckt mybus a<1> b<2> a<0> b<1> b<0> vdd vss

* inverter at bit #0
MP0 b<0> a<0> vdd vdd EEPMOS w=0.7u l=0.1u
MN0 b<0> a<0> vss vss EENMOS w=0.4u l=0.1u

* buffer at bit #1
R0 b<1> a<1> 0.1

* constant at bit #2
R1 b<2> vdd 0.1

.ends
