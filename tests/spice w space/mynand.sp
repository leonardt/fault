* NMOS/PMOS models from
* https://people.rit.edu/lffeee/SPICE_Examples.pdf

.model EENMOS NMOS (VTO=0.4 KP=432E-6 GAMMA=0.2 PHI=.88)
.model EEPMOS PMOS (VTO=-0.4 KP=122E-6 GAMMA=0.2 PHI=.88)

.subckt mynand a b out vdd vss

MP0 out a vdd vdd EEPMOS w=0.7u l=0.1u
MP1 out b vdd vdd EEPMOS w=0.7u l=0.1u
MN0 mid a vss vss EENMOS w=0.4u l=0.1u
MN1 out b mid vss EENMOS w=0.4u l=0.1u

.ends
